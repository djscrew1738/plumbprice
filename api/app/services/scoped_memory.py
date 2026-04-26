"""Per-customer / per-address long-term memory (Track D4).

Thin wrapper over MemoryService that normalizes customer + address keys
into metadata_json so the agent can recall facts the next time the same
person calls or the next time a tech is dispatched to the same house.

Keys (stored in AgentMemory.metadata_json):
  * customer_key — lower-cased email if present, else digits-only phone,
    else None.
  * address_key  — sha1 hex of "street|zip" (street lower-cased, all
    non-alphanumeric stripped). Hashing keeps it stable across casing/
    punctuation drift without storing PII verbatim in the index.

Retrieval is metadata-filtered + ordered by importance + recency. We
intentionally don't require an embedding hit here — when a tech opens
a job at 123 Main St, we want *every* prior fact about that house, not
just ones similar to the current chat turn.
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory
from app.services.memory_service import MemoryService

memory_service = MemoryService()


_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_DIGITS = re.compile(r"\d+")


def normalize_customer_key(*, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[str]:
    if email:
        e = email.strip().lower()
        if "@" in e:
            return e
    if phone:
        digits = "".join(_DIGITS.findall(phone))
        if len(digits) >= 7:
            return digits[-10:]  # last 10 digits handles +1 prefix variations
    return None


def normalize_address_key(*, street: Optional[str], zip_code: Optional[str] = None) -> Optional[str]:
    if not street or not street.strip():
        return None
    s = _NON_ALNUM.sub("", street.lower())
    if not s:
        return None
    z = (zip_code or "").strip()[:5]
    raw = f"{s}|{z}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


async def store_for_customer(
    db: AsyncSession,
    *,
    user_id: int,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    content: str,
    importance: float = 0.6,
    organization_id: Optional[int] = None,
    extra_metadata: Optional[dict] = None,
) -> Optional[AgentMemory]:
    key = normalize_customer_key(email=customer_email, phone=customer_phone)
    if not key:
        return None
    md = {"customer_key": key, "customer_email": customer_email, "customer_phone": customer_phone}
    if extra_metadata:
        md.update(extra_metadata)
    return await memory_service.store(
        db,
        user_id=user_id,
        content=content,
        kind="customer",
        importance=importance,
        organization_id=organization_id,
        metadata=md,
    )


async def store_for_address(
    db: AsyncSession,
    *,
    user_id: int,
    street: Optional[str],
    zip_code: Optional[str],
    content: str,
    importance: float = 0.55,
    organization_id: Optional[int] = None,
    extra_metadata: Optional[dict] = None,
) -> Optional[AgentMemory]:
    key = normalize_address_key(street=street, zip_code=zip_code)
    if not key:
        return None
    md = {"address_key": key, "street": street, "zip": zip_code}
    if extra_metadata:
        md.update(extra_metadata)
    return await memory_service.store(
        db,
        user_id=user_id,
        content=content,
        kind="job_history",
        importance=importance,
        organization_id=organization_id,
        metadata=md,
    )


def _key_filter(column_attr: str, key: str):
    """Deprecated: replaced by Python-side filtering for portability across
    postgres JSONB / sqlite JSON. Kept as a stub to avoid import errors.
    """
    return AgentMemory.id.is_(None)  # never matches; no-op


async def recall_for_customer(
    db: AsyncSession,
    *,
    user_id: int,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    limit: int = 20,
) -> list[AgentMemory]:
    key = normalize_customer_key(email=customer_email, phone=customer_phone)
    if not key:
        return []
    stmt = (
        select(AgentMemory)
        .where(AgentMemory.user_id == user_id)
        .where(AgentMemory.kind == "customer")
        .order_by(AgentMemory.importance.desc(), AgentMemory.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    matched = [r for r in rows if (r.metadata_json or {}).get("customer_key") == key]
    return matched[:limit]


async def recall_for_address(
    db: AsyncSession,
    *,
    user_id: int,
    street: Optional[str],
    zip_code: Optional[str] = None,
    limit: int = 20,
) -> list[AgentMemory]:
    key = normalize_address_key(street=street, zip_code=zip_code)
    if not key:
        return []
    stmt = (
        select(AgentMemory)
        .where(AgentMemory.user_id == user_id)
        .where(AgentMemory.kind == "job_history")
        .order_by(AgentMemory.importance.desc(), AgentMemory.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    matched = [r for r in rows if (r.metadata_json or {}).get("address_key") == key]
    return matched[:limit]


def memory_to_dict(m: AgentMemory) -> dict:
    return {
        "id": m.id,
        "kind": m.kind,
        "content": m.content,
        "importance": m.importance,
        "metadata": m.metadata_json or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "last_referenced_at": m.last_referenced_at.isoformat() if m.last_referenced_at else None,
    }
