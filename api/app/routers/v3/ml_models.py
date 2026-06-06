"""
ML Model Registry endpoints — /api/v3/ml/models

Admin-only endpoints for listing, promoting, and retiring fine-tuned models.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.auth import get_current_admin
from app.database import get_db
from app.models.ml_models import MLModel
from app.models.users import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ml/models", tags=["ml-models"])


# ─── Response schemas ─────────────────────────────────────────────────────────


class MLModelOut(BaseModel):
    id: int
    model_id: str
    base_model: str
    training_samples: int | None
    eval_score: float | None
    shadow_calls: int
    shadow_match_rate: float | None
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class ModelsResponse(BaseModel):
    models: list[MLModelOut]
    baseline_match_rate: float | None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _model_to_out(m: MLModel) -> MLModelOut:
    return MLModelOut(
        id=m.id,
        model_id=m.model_id,
        base_model=m.base_model,
        training_samples=m.training_samples,
        eval_score=m.eval_score,
        shadow_calls=m.shadow_calls or 0,
        shadow_match_rate=m.shadow_match_rate,
        status=m.status,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=ModelsResponse)
async def list_ml_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> ModelsResponse:
    """List all ML model versions ordered by creation date descending."""
    result = await db.execute(
        select(MLModel).order_by(MLModel.created_at.desc()).limit(50)
    )
    models = result.scalars().all()

    # Baseline = eval_score of the current production model
    baseline: float | None = None
    for m in models:
        if m.status == "production" and m.baseline_score is not None:
            baseline = m.baseline_score
            break

    return ModelsResponse(
        models=[_model_to_out(m) for m in models],
        baseline_match_rate=baseline,
    )


@router.post("/{model_id}/promote")
async def promote_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """Promote a shadow model to production. Retires any existing production model."""
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model.status != "shadow":
        raise HTTPException(status_code=409, detail=f"Model status is '{model.status}', not 'shadow'")

    # Retire existing production model
    existing_prod = await db.execute(
        select(MLModel).where(MLModel.status == "production")
    )
    for existing in existing_prod.scalars().all():
        existing.status = "retired"
        existing.retired_at = datetime.utcnow()

    model.status = "production"
    model.promoted_at = datetime.utcnow()
    model.promoted_by = current_user.id
    await db.commit()

    logger.info(
        "ml_model_promoted",
        model_id=model.model_id,
        admin_id=current_user.id,
    )
    return {"status": "promoted", "model_id": model.model_id}


@router.post("/{model_id}/retire")
async def retire_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """Retire a model (shadow or production)."""
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model.status == "retired":
        raise HTTPException(status_code=409, detail="Model is already retired")

    model.status = "retired"
    model.retired_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "ml_model_retired",
        model_id=model.model_id,
        admin_id=current_user.id,
    )
    return {"status": "retired"}
