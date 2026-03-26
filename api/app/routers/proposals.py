from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.services.proposal_service import proposal_service

logger = structlog.get_logger()
router = APIRouter()


@router.post("/{estimate_id}")
async def create_proposal(
    estimate_id: int,
    template_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate a proposal from an estimate (Phase 2)."""
    result = await proposal_service.generate_proposal(estimate_id, template_id)
    return result


@router.get("/{proposal_id}/pdf")
async def get_proposal_pdf(proposal_id: int):
    """Download proposal as PDF (Phase 2)."""
    raise HTTPException(status_code=501, detail="PDF generation coming in Phase 2")
