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
        """
        try:
            # Query to aggregate fixture counts across all pages of the job
            query = (
                select(
                    BlueprintDetection.fixture_type,
                    func.sum(BlueprintDetection.count).label("total_count"),
                    func.avg(BlueprintDetection.confidence).label("avg_confidence")
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
                    "confidence": float(row[2])
                })
            
            return {
                "job_id": job_id,
                "status": "complete",
                "fixtures": fixtures
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
