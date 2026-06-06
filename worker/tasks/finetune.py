"""Celery task: LLM fine-tuning pipeline (E3.2).

Orchestrates the full fine-tuning workflow:
  1. Extract training data via finetune_data service
  2. Upload JSONL to OpenAI Files API
  3. Create fine-tuning job
  4. Poll for completion (re-enqueue with countdown)
  5. On success: store model in ml_models with status="shadow"

Gate: requires ML_FINETUNE_ENABLED=true and at least ML_FINETUNE_MIN_SAMPLES
quality training pairs before starting a job.
"""
from __future__ import annotations

import asyncio

import structlog

from worker.worker import app

logger = structlog.get_logger()


async def _async_run_finetune() -> dict:
    """Extract training data and submit fine-tuning job to OpenAI."""
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.services.finetune_data import extract_training_data

    if not settings.ml_finetune_enabled:
        logger.info("finetune.disabled", reason="ML_FINETUNE_ENABLED is false")
        return {"status": "disabled"}

    async with AsyncSessionLocal() as db:
        pairs = await extract_training_data(db)

    if len(pairs) < settings.ml_finetune_min_samples:
        logger.info(
            "finetune.insufficient_data",
            count=len(pairs),
            minimum=settings.ml_finetune_min_samples,
        )
        return {"status": "insufficient_data", "count": len(pairs)}

    if not settings.openai_api_key:
        logger.warning("finetune.no_openai_key")
        return {"status": "no_api_key"}

    try:
        import openai
        import json
        import tempfile
        import os

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

        # Write JSONL to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            for pair in pairs:
                f.write(json.dumps(pair) + "\n")
            tmp_path = f.name

        try:
            # Upload to OpenAI
            with open(tmp_path, "rb") as f:
                file_resp = await client.files.create(file=f, purpose="fine-tune")

            file_id = file_resp.id
            logger.info("finetune.file_uploaded", file_id=file_id, samples=len(pairs))

            # Create fine-tuning job
            job_resp = await client.fine_tuning.jobs.create(
                training_file=file_id,
                model=settings.default_llm_model,
                suffix="plumbprice-v4",
            )
            job_id = job_resp.id
        finally:
            os.unlink(tmp_path)

        # Persist job record to ml_models with status=shadow
        async with AsyncSessionLocal() as db:
            from app.models.ml_models import MLModel

            record = MLModel(
                model_id=job_id,
                base_model=settings.default_llm_model,
                provider="openai",
                training_samples=len(pairs),
                status="shadow",
                openai_job_id=job_id,
            )
            db.add(record)
            await db.commit()
            logger.info("finetune.job_created", job_id=job_id, ml_model_id=record.id)

        return {"status": "submitted", "job_id": job_id, "samples": len(pairs)}

    except Exception as exc:
        logger.error("finetune.submission_failed", error=str(exc))
        raise


async def _async_poll_finetune(job_id: str) -> dict:
    """Poll OpenAI for fine-tuning job completion and promote on success."""
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.models.ml_models import MLModel
    from sqlalchemy import select

    if not settings.openai_api_key:
        return {"status": "no_api_key"}

    import openai

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    job = await client.fine_tuning.jobs.retrieve(job_id)

    logger.info("finetune.poll", job_id=job_id, status=job.status)

    if job.status in ("validating_files", "queued", "running"):
        return {"status": "running", "job_id": job_id}

    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                select(MLModel).where(MLModel.openai_job_id == job_id)
            )
        ).scalar_one_or_none()

        if not row:
            logger.warning("finetune.poll_model_not_found", job_id=job_id)
            return {"status": "not_found"}

        if job.status == "succeeded" and job.fine_tuned_model:
            row.model_id = job.fine_tuned_model
            row.status = "shadow"  # Stays shadow until admin promotes
            await db.commit()
            logger.info(
                "finetune.succeeded",
                model_id=job.fine_tuned_model,
                job_id=job_id,
            )
            return {"status": "succeeded", "model_id": job.fine_tuned_model}

        if job.status in ("failed", "cancelled"):
            row.status = "retired"
            row.notes = f"OpenAI job {job.status}"
            await db.commit()
            logger.error("finetune.failed", job_id=job_id, openai_status=job.status)
            return {"status": job.status}

    return {"status": job.status}


@app.task(
    name="worker.tasks.finetune.run_finetune",
    bind=True,
    max_retries=1,
    queue="ml",
)
def run_finetune(self):
    """Submit a new fine-tuning job."""
    try:
        return asyncio.run(_async_run_finetune())
    except Exception as exc:
        logger.error("finetune.task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=3600)


@app.task(
    name="worker.tasks.finetune.poll_finetune_job",
    bind=True,
    max_retries=48,  # up to 48 × 30-min = 24 hours of polling
    queue="ml",
)
def poll_finetune_job(self, job_id: str):
    """Poll an in-flight fine-tuning job and re-enqueue itself if still running."""
    try:
        result = asyncio.run(_async_poll_finetune(job_id))
        if result.get("status") == "running":
            raise self.retry(countdown=1800)  # re-check in 30 minutes
        return result
    except Exception as exc:
        logger.error("finetune.poll_failed", job_id=job_id, error=str(exc))
        raise
