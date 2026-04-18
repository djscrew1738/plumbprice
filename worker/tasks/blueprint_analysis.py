"""Celery task: Analyze blueprint PDFs for fixture detection (Phase 4)."""

import asyncio
import io
import os
import random
import fitz  # PyMuPDF
import structlog
from worker.worker import app
from app.core.storage import storage_client
from app.services.vision_service import vision_service
from app.database import AsyncSessionLocal
from app.models.blueprints import BlueprintJob, BlueprintPage, BlueprintDetection
from app.config import settings
from sqlalchemy import select

logger = structlog.get_logger()


async def _async_analyze_blueprint(job_id: int, storage_path: str):
    """Internal async implementation of blueprint analysis."""
    async with AsyncSessionLocal() as db:
        try:
            # 1. Update status to processing
            result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error("vision.job_not_found", job_id=job_id)
                return
            
            job.status = "processing"
            await db.commit()

            # 2. Download from MinIO
            bucket = settings.minio_bucket_blueprints
            file_data = storage_client.download_file(bucket, storage_path)
            if not file_data:
                raise ValueError(f"Failed to download file from {bucket}/{storage_path}")

            # 3. Open PDF and render pages
            pdf = fitz.open(stream=file_data, filetype="pdf")
            job.page_count = len(pdf)
            await db.commit()

            for i in range(len(pdf)):
                page = pdf[i]
                # High resolution render for vision
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                
                # Upload page image to MinIO
                page_filename = f"jobs/{job_id}/page_{i+1}.png"
                storage_client.upload_file(
                    bucket,
                    page_filename,
                    io.BytesIO(img_data),
                    len(img_data),
                    content_type="image/png"
                )

                # Create BlueprintPage record
                bp_page = BlueprintPage(
                    job_id=job_id,
                    page_number=i+1,
                    storage_path=page_filename,
                    status="processing"
                )
                db.add(bp_page)
                await db.flush()

                # 4. Classify sheet
                classification = await vision_service.classify_sheet(img_data)
                bp_page.sheet_type = classification.get("sheet_type")
                bp_page.sheet_number = classification.get("sheet_number")
                bp_page.title = classification.get("title")
                
                # 5. Detect fixtures ONLY if it's a plumbing sheet
                if bp_page.sheet_type == "plumbing":
                    detections = await vision_service.detect_fixtures(img_data)
                    for det in detections:
                        db.add(BlueprintDetection(
                            page_id=bp_page.id,
                            fixture_type=det.get("type"),
                            count=det.get("count", 1),
                            confidence=det.get("confidence", 0.0)
                        ))
                
                bp_page.status = "complete"
                await db.commit()

            job.status = "complete"
            await db.commit()
            pdf.close()
            
            logger.info("vision.analysis_complete", job_id=job_id, pages=job.page_count)
            return {"job_id": job_id, "status": "complete", "pages": job.page_count}

        except Exception as e:
            await db.rollback()
            try:
                result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "error"
                    job.processing_error = str(e)
                    await db.commit()
            except Exception as status_update_exc:
                logger.warning(
                    "vision.status_update_failed",
                    job_id=job_id,
                    error=str(status_update_exc),
                )
            raise e


@app.task(bind=True, max_retries=3)
def analyze_blueprint(self, job_id: int, storage_path: str):
    """
    Analyze a blueprint PDF for plumbing fixture detection.
    Phase 4: Page classification -> fixture detection -> takeoff generation.
    """
    logger.info("Starting blueprint analysis", job_id=job_id)

    try:
        result = asyncio.run(_async_analyze_blueprint(job_id, storage_path))
        return result

    except Exception as exc:
        logger.error("Blueprint analysis failed", job_id=job_id, error=str(exc), exc_info=True)
        # Exponential backoff with jitter, capped at 10 minutes
        backoff = min(60 * (2 ** self.request.retries) + random.uniform(0, 30), 600)
        raise self.retry(exc=exc, countdown=backoff)
