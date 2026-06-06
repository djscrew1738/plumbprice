"""Model A/B Testing Framework (E3.3).

Routes a configurable percentage of classify calls to a shadow (fine-tuned)
model and logs both results for comparison. The production model's output is
always returned — the shadow model runs silently.

Usage:
    from app.services.model_ab import model_ab

    result = await model_ab.classify_with_shadow(db, message, session_id, classify_fn)
"""
from __future__ import annotations

import random
from typing import Any, Callable, Coroutine, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ml_models import MLModel

logger = structlog.get_logger()


class ModelABService:
    """Shadow-routes a fraction of classify calls to the active shadow model."""

    async def get_shadow_model(self, db: AsyncSession) -> Optional[MLModel]:
        """Return the active shadow model, or None if none exists."""
        return (
            await db.execute(
                select(MLModel)
                .where(MLModel.status == "shadow")
                .order_by(MLModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_production_model(self, db: AsyncSession) -> Optional[MLModel]:
        """Return the active production fine-tuned model, or None."""
        return (
            await db.execute(
                select(MLModel)
                .where(MLModel.status == "production")
                .order_by(MLModel.promoted_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def classify_with_shadow(
        self,
        db: AsyncSession,
        *,
        user_message: str,
        production_classify_fn: Callable[[], Coroutine[Any, Any, Any]],
        shadow_classify_fn: Optional[Callable[[str], Coroutine[Any, Any, Any]]] = None,
    ) -> Any:
        """Run the production classify and optionally a silent shadow classify.

        Returns production result unconditionally.
        Shadow result is logged and used to update match statistics but
        is never returned to the caller.
        """
        production_result = await production_classify_fn()

        shadow_model = await self.get_shadow_model(db)
        if not shadow_model or not shadow_classify_fn:
            return production_result

        # Only shadow route according to configured traffic percentage
        if random.randint(1, 100) > settings.ml_shadow_traffic_pct:
            return production_result

        try:
            shadow_result = await shadow_classify_fn(shadow_model.model_id)
            match = _results_match(production_result, shadow_result)
            await self._record_shadow_call(db, shadow_model, matched=match)
            logger.debug(
                "model_ab.shadow_call",
                shadow_model_id=shadow_model.model_id,
                matched=match,
            )
        except Exception as exc:
            logger.warning("model_ab.shadow_failed", error=str(exc))

        return production_result

    async def _record_shadow_call(
        self, db: AsyncSession, model: MLModel, *, matched: bool
    ) -> None:
        """Increment shadow_calls counter and update rolling match rate."""
        new_calls = (model.shadow_calls or 0) + 1
        prev_rate = model.shadow_match_rate or 0.0
        # Rolling average: new_rate = prev_rate * (n-1)/n + matched/n
        new_rate = prev_rate * ((new_calls - 1) / new_calls) + (1.0 if matched else 0.0) / new_calls

        await db.execute(
            update(MLModel)
            .where(MLModel.id == model.id)
            .values(shadow_calls=new_calls, shadow_match_rate=round(new_rate, 4))
        )
        await db.commit()

    async def can_promote(self, db: AsyncSession, model_id: int) -> tuple[bool, str]:
        """Check whether a shadow model meets promotion criteria."""
        model = (
            await db.execute(select(MLModel).where(MLModel.id == model_id))
        ).scalar_one_or_none()

        if not model:
            return False, "Model not found"
        if model.status != "shadow":
            return False, f"Model status is '{model.status}', not 'shadow'"
        if (model.shadow_calls or 0) < 100:
            return False, f"Only {model.shadow_calls} shadow calls recorded (need ≥ 100)"

        baseline = model.baseline_score or 0.0
        match_rate = model.shadow_match_rate or 0.0
        if match_rate < baseline + 0.05:
            return False, (
                f"Shadow match rate {match_rate:.1%} does not exceed "
                f"baseline {baseline:.1%} by the required 5pp"
            )

        return True, "Promotion criteria met"

    async def promote(
        self, db: AsyncSession, model_id: int, promoted_by_user_id: int
    ) -> MLModel:
        """Promote a shadow model to production and retire the previous production model."""
        from datetime import datetime, timezone

        can, reason = await self.can_promote(db, model_id)
        if not can:
            raise ValueError(f"Cannot promote model: {reason}")

        # Retire current production model
        await db.execute(
            update(MLModel)
            .where(MLModel.status == "production")
            .values(
                status="retired",
                retired_at=datetime.now(timezone.utc),
            )
        )

        # Promote new model
        await db.execute(
            update(MLModel)
            .where(MLModel.id == model_id)
            .values(
                status="production",
                promoted_at=datetime.now(timezone.utc),
                promoted_by=promoted_by_user_id,
            )
        )
        await db.commit()

        return (await db.execute(select(MLModel).where(MLModel.id == model_id))).scalar_one()


def _results_match(prod: Any, shadow: Any) -> bool:
    """Compare two ClassifyResult objects for canonical item + job_type agreement."""
    try:
        prod_items = {
            f["canonical_item"] for f in (getattr(prod, "fixtures", None) or [])
        }
        shadow_items = {
            f["canonical_item"] for f in (getattr(shadow, "fixtures", None) or [])
        }
        if prod_items != shadow_items:
            return False
        return getattr(prod, "job_type", None) == getattr(shadow, "job_type", None)
    except Exception:
        return False


model_ab = ModelABService()
