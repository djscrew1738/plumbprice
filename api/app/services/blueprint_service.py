"""Blueprint Service — Phase 4 implementation."""

import structlog
from typing import Optional, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.blueprints import BlueprintJob, BlueprintPage, BlueprintDetection

logger = structlog.get_logger()


class BlueprintService:
    """Phase 4: Blueprint analysis and fixture takeoff."""

    async def generate_takeoff(self, db: AsyncSession, job_id: int) -> dict:
        """
        Generate a summarized takeoff (fixture counts) from detections.

        Phase 2 additions: returns per-page review summary, scale text, and
        a flat list of low-confidence detections that need user review.
        """
        try:
            # Query to aggregate fixture counts across all pages of the job
            query = (
                select(
                    BlueprintDetection.fixture_type,
                    func.sum(BlueprintDetection.count).label("total_count"),
                    func.avg(BlueprintDetection.confidence).label("avg_confidence"),
                    func.bool_or(BlueprintDetection.needs_review).label("any_needs_review"),
                )
                .join(BlueprintPage)
                .where(BlueprintPage.job_id == job_id)
                .group_by(BlueprintDetection.fixture_type)
            )
            
            result = await db.execute(query)
            rows = result.all()
            
            fixtures = []
            for row in rows:
                fixtures.append({
                    "type": row[0],
                    "count": int(row[1]),
                    "confidence": float(row[2] or 0.0),
                    "needs_review": bool(row[3]),
                })

            # Per-page summary (sheet type, scale, page number)
            pages_q = await db.execute(
                select(BlueprintPage)
                .where(BlueprintPage.job_id == job_id)
                .order_by(BlueprintPage.page_number)
            )
            pages = [
                {
                    "page_id": p.id,
                    "page_number": p.page_number,
                    "sheet_type": p.sheet_type,
                    "sheet_number": p.sheet_number,
                    "title": p.title,
                    "scale": p.scale_text,
                    "status": p.status,
                    "px_per_ft": p.px_per_ft,
                    "scale_calibrated": p.scale_calibrated,
                    "scale_source": p.scale_source,
                }
                for p in pages_q.scalars().all()
            ]

            # Flat list of detections flagged for review (low confidence)
            review_q = await db.execute(
                select(
                    BlueprintDetection.id,
                    BlueprintDetection.fixture_type,
                    BlueprintDetection.count,
                    BlueprintDetection.confidence,
                    BlueprintPage.page_number,
                )
                .join(BlueprintPage)
                .where(
                    BlueprintPage.job_id == job_id,
                    BlueprintDetection.needs_review.is_(True),
                )
                .order_by(BlueprintDetection.confidence.asc())
            )
            review_items = [
                {
                    "detection_id": r[0],
                    "fixture_type": r[1],
                    "count": int(r[2] or 1),
                    "confidence": float(r[3] or 0.0),
                    "page_number": r[4],
                }
                for r in review_q.all()
            ]

            return {
                "job_id": job_id,
                "status": "complete",
                "fixtures": fixtures,
                "pages": pages,
                "needs_review": review_items,
            }
            
        except Exception as e:
            logger.error("vision.takeoff_error", job_id=job_id, error=str(e))
            return {"job_id": job_id, "status": "error", "error": str(e)}

    async def get_job_status(self, db: AsyncSession, job_id: int) -> dict:
        """Get the status of a blueprint job."""
        result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None
            
        return {
            "id": job.id,
            "status": job.status,
            "page_count": job.page_count,
            "error": job.processing_error
        }


blueprint_service = BlueprintService()
