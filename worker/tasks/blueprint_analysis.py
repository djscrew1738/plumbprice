"""Celery task: Analyze blueprint PDFs for fixture detection (Phase 4)."""

import asyncio
import io
import os
import random
import re
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


# Common architectural / engineering scale notations.
_SCALE_PATTERNS = [
    re.compile(r'(\d+\s*/\s*\d+)\s*"?\s*=\s*1\'?[-\s]*0?"?', re.IGNORECASE),  # 1/4" = 1'-0"
    re.compile(r'(\d+)\s*"?\s*=\s*1\'?[-\s]*0?"?', re.IGNORECASE),             # 1" = 1'-0"
    re.compile(r'1\s*:\s*(\d{2,4})'),                                          # 1:50, 1:100
    re.compile(r'scale\s*[:=]?\s*([^\n,;]{1,30})', re.IGNORECASE),
]


def _detect_scale(text: str) -> str | None:
    """Pull the first scale notation out of native PDF text, if any."""
    if not text:
        return None
    for pat in _SCALE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0).strip()[:60]
    return None


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

            total_fixture_count = 0
            review_threshold = float(getattr(settings, "blueprint_review_threshold", 0.65))
            for i in range(len(pdf)):
                page = pdf[i]
                # High resolution render for vision
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")

                # Native PDF text extraction (cheap, no LLM round-trip)
                try:
                    page_text = page.get_text("text") or ""
                except Exception as text_exc:  # pragma: no cover
                    logger.warning("vision.text_extract_failed",
                                   job_id=job_id, page=i + 1, error=str(text_exc))
                    page_text = ""
                page_text = page_text.strip()
                scale_text = _detect_scale(page_text)

                # Upload page image to MinIO
                page_filename = f"jobs/{job_id}/page_{i+1}.png"
                storage_client.upload_file(
                    bucket,
                    page_filename,
                    io.BytesIO(img_data),
                    len(img_data),
                    content_type="image/png"
                )

                # Create or fetch BlueprintPage record (dedup on (job_id, page_number))
                from sqlalchemy import select as _select
                existing_page = await db.execute(
                    _select(BlueprintPage).where(
                        BlueprintPage.job_id == job_id,
                        BlueprintPage.page_number == i + 1,
                    )
                )
                bp_page = existing_page.scalar_one_or_none()
                if bp_page is None:
                    bp_page = BlueprintPage(
                        job_id=job_id,
                        page_number=i+1,
                        storage_path=page_filename,
                        status="processing",
                        ocr_text=page_text[:50000] if page_text else None,
                        scale_text=scale_text,
                    )
                    db.add(bp_page)
                    await db.flush()
                else:
                    bp_page.storage_path = page_filename
                    bp_page.status = "processing"
                    bp_page.ocr_text = page_text[:50000] if page_text else None
                    bp_page.scale_text = scale_text
                    await db.flush()

                # 4. Classify sheet (with OCR hint)
                classification = await vision_service.classify_sheet(img_data, ocr_hint=page_text)
                bp_page.sheet_type = classification.get("sheet_type")
                bp_page.sheet_number = classification.get("sheet_number")
                bp_page.title = classification.get("title")
                
                # 5. Detect fixtures ONLY if it's a plumbing sheet
                if bp_page.sheet_type == "plumbing":
                    detect_result = await vision_service.detect_fixtures(img_data, ocr_hint=page_text)
                    detections = detect_result.get("fixtures", [])
                    if detect_result.get("status") == "error":
                        # Surface vision failures rather than silently producing 0 fixtures.
                        logger.warning(
                            "vision.detect_failed_for_page",
                            job_id=job_id,
                            page=i + 1,
                            error=detect_result.get("error"),
                        )
                        bp_page.status = "vision_error"
                    for det in detections:
                        det_count = int(det.get("count", 1) or 1)
                        det_conf  = float(det.get("confidence", 0.0) or 0.0)
                        total_fixture_count += det_count
                        db.add(BlueprintDetection(
                            page_id=bp_page.id,
                            fixture_type=det.get("type"),
                            count=det_count,
                            confidence=det_conf,
                            needs_review=(det_conf < review_threshold),
                        ))
                
                bp_page.status = "complete"
                await db.commit()

            job.status = "complete"
            await db.commit()
            pdf.close()

            # Push WS notification so the frontend can stop polling immediately
            try:
                from app.routers.ws import pipeline_hub
                await pipeline_hub.broadcast({
                    "type": "blueprint_status",
                    "job_id": str(job_id),
                    "status": "completed",
                    "fixture_count": total_fixture_count,
                })
            except Exception as ws_exc:
                logger.warning("vision.ws_broadcast_failed", job_id=job_id, error=str(ws_exc))
            
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
            # Push WS error notification (best-effort)
            try:
                from app.routers.ws import pipeline_hub
                await pipeline_hub.broadcast({
                    "type": "blueprint_status",
                    "job_id": str(job_id),
                    "status": "error",
                    "error": str(e),
                })
            except Exception as ws_exc:
                logger.warning("vision.ws_broadcast_failed", job_id=job_id, error=str(ws_exc))
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
        try:
            raise self.retry(exc=exc, countdown=backoff)
        except self.MaxRetriesExceededError:
            # Terminal failure — notify job owner (best-effort).
            try:
                asyncio.run(_notify_blueprint_failure(job_id, str(exc)))
            except Exception as notify_exc:  # pragma: no cover
                logger.warning("vision.notify_failed", job_id=job_id, error=str(notify_exc))
            raise


async def _notify_blueprint_failure(job_id: int, error: str) -> None:
    """Best-effort notification to the blueprint job owner on terminal failure."""
    from app.services.notifications_service import notify as _notify

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job or job.created_by is None:
            return
        await _notify(
            db=db,
            user_id=job.created_by,
            kind="job_failed",
            title="Blueprint analysis failed",
            body=(error or "Unknown error")[:500],
            link=f"/blueprints/{job_id}",
        )
        await db.commit()
