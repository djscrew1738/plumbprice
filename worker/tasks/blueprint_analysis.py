"""Celery task: Analyze blueprint PDFs for fixture detection (Phase 4)."""

from worker import app
import structlog

logger = structlog.get_logger()


@app.task(bind=True, max_retries=3)
def analyze_blueprint(self, job_id: int, storage_path: str):
    """
    Analyze a blueprint PDF for plumbing fixture detection.
    Phase 4: Page classification -> fixture detection -> takeoff generation.
    """
    logger.info("Analyzing blueprint", job_id=job_id)

    try:
        # TODO Phase 4: implement blueprint analysis pipeline
        # 1. Download PDF from MinIO
        # 2. Render pages to images (PyMuPDF)
        # 3. Classify sheets (plumbing, architectural, etc.)
        # 4. Run fixture detection on plumbing sheets
        # 5. Generate takeoff quantities
        # 6. Update DB with results
        raise NotImplementedError("Blueprint analysis pipeline is not yet implemented.")
        logger.info("Blueprint analysis complete (Phase 4 stub)", job_id=job_id)
        return {"job_id": job_id, "status": "complete", "fixtures": []}

    except Exception as exc:
        logger.error("Blueprint analysis failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc, countdown=120)


@app.task
def classify_sheet(page_id: int, image_path: str) -> dict:
    """Classify a single blueprint page. Phase 4."""
    return {"page_id": page_id, "sheet_type": "unknown", "confidence": 0.0}
