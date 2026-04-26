"""Feature flags router.

Two surfaces:
  * GET /api/v1/flags          — public to authenticated users; returns the
                                  enabled bag so the frontend can gate UI.
  * GET /api/v1/admin/flags    — admin-only; returns full rows incl.
                                  description and updated_at.
  * PUT /api/v1/admin/flags/{key} — admin toggle.
  * POST /api/v1/admin/flags   — admin upsert (key + description + enabled).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models.feature_flags import FeatureFlag


router = APIRouter()


class FlagOut(BaseModel):
    key: str
    enabled: bool
    description: Optional[str] = None
    updated_at: Optional[str] = None


class FlagWrite(BaseModel):
    key: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    enabled: bool = False
    description: Optional[str] = Field(default=None, max_length=2000)


class FlagToggle(BaseModel):
    enabled: bool


@router.get("/flags")
async def list_flags_public(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Return {key: bool} for the current bag. Cheap, cacheable on the client."""
    rows = (await db.execute(select(FeatureFlag.key, FeatureFlag.enabled))).all()
    return {k: bool(v) for k, v in rows}


@router.get("/admin/flags")
async def list_flags_admin(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    rows = (await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))).scalars().all()
    return [
        FlagOut(
            key=f.key,
            enabled=bool(f.enabled),
            description=f.description,
            updated_at=f.updated_at.isoformat() if f.updated_at else None,
        )
        for f in rows
    ]


@router.put("/admin/flags/{key}")
async def toggle_flag(
    key: str,
    body: FlagToggle,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    flag = (
        await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    ).scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="flag not found")
    flag.enabled = body.enabled
    await db.commit()
    return {"key": key, "enabled": body.enabled}


@router.post("/admin/flags")
async def upsert_flag(
    body: FlagWrite,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    stmt = (
        pg_insert(FeatureFlag)
        .values(key=body.key, enabled=body.enabled, description=body.description)
        .on_conflict_do_update(
            index_elements=[FeatureFlag.key],
            set_={"enabled": body.enabled, "description": body.description},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"key": body.key, "enabled": body.enabled, "description": body.description}


@router.delete("/admin/flags/{key}")
async def delete_flag(
    key: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    res = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = res.scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="flag not found")
    await db.delete(flag)
    await db.commit()
    return {"deleted": key}
