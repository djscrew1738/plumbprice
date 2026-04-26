"""Agent memories CRUD API.

Lets users inspect, edit, and delete what the AI has remembered about them.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db, AsyncSessionLocal
from app.models.users import User
from app.services.memory_service import memory_service, VALID_KINDS

router = APIRouter()


class MemoryOut(BaseModel):
    id: int
    kind: str
    content: str
    importance: float
    metadata: Optional[dict] = None
    source_session_id: Optional[int] = None
    created_at: Optional[str] = None
    last_referenced_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "MemoryOut":
        return cls(
            id=row.id,
            kind=row.kind,
            content=row.content,
            importance=row.importance,
            metadata=row.metadata_json,
            source_session_id=row.source_session_id,
            created_at=row.created_at.isoformat() if row.created_at else None,
            last_referenced_at=row.last_referenced_at.isoformat() if row.last_referenced_at else None,
        )


class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=2, max_length=2000)
    kind: str = "fact"
    importance: float = 0.5


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=2, max_length=2000)
    kind: Optional[str] = None
    importance: Optional[float] = None


class ExtractRequest(BaseModel):
    session_id: int


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    kind: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kinds = [kind] if kind else None
    rows = await memory_service.list_for_user(db, user_id=current_user.id, kinds=kinds)
    return [MemoryOut.from_row(r) for r in rows]


@router.post("", response_model=MemoryOut)
async def create_memory(
    body: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {sorted(VALID_KINDS)}")
    row = await memory_service.store(
        db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        content=body.content,
        kind=body.kind,
        importance=body.importance,
        metadata={"source": "manual"},
    )
    return MemoryOut.from_row(row)


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: int,
    body: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.kind is not None and body.kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {sorted(VALID_KINDS)}")
    row = await memory_service.update_content(
        db,
        memory_id=memory_id,
        user_id=current_user.id,
        content=body.content,
        kind=body.kind,
        importance=body.importance,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return MemoryOut.from_row(row)


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await memory_service.delete(db, memory_id=memory_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="memory not found")
    return {"ok": True}


@router.post("/extract")
async def extract_memories(
    body: ExtractRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Manually trigger extraction from a chat session (background)."""
    async def _run():
        async with AsyncSessionLocal() as bg_db:
            await memory_service.extract_from_session(
                bg_db, user_id=current_user.id, session_id=body.session_id,
            )
    background_tasks.add_task(_run)
    return {"ok": True, "scheduled": True}


# ── Per-customer / per-address scoped memory (Track D4) ────────────────────


from app.services.scoped_memory import (  # noqa: E402
    memory_to_dict,
    recall_for_address,
    recall_for_customer,
    store_for_address,
    store_for_customer,
)


class CustomerMemoryBody(BaseModel):
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    content: str = Field(..., min_length=2)
    importance: float = Field(default=0.6, ge=0.0, le=1.0)


class AddressMemoryBody(BaseModel):
    street: str = Field(..., min_length=2)
    zip_code: Optional[str] = None
    content: str = Field(..., min_length=2)
    importance: float = Field(default=0.55, ge=0.0, le=1.0)


@router.post("/customer")
async def store_customer_memory(
    body: CustomerMemoryBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.customer_email and not body.customer_phone:
        raise HTTPException(status_code=400, detail="customer_email or customer_phone required")
    row = await store_for_customer(
        db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        content=body.content,
        importance=body.importance,
    )
    if row is None:
        raise HTTPException(status_code=400, detail="invalid customer key")
    return memory_to_dict(row)


@router.post("/address")
async def store_address_memory(
    body: AddressMemoryBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await store_for_address(
        db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        street=body.street,
        zip_code=body.zip_code,
        content=body.content,
        importance=body.importance,
    )
    if row is None:
        raise HTTPException(status_code=400, detail="invalid address")
    return memory_to_dict(row)


@router.get("/customer")
async def recall_customer_memory(
    customer_email: Optional[str] = Query(None),
    customer_phone: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await recall_for_customer(
        db, user_id=current_user.id,
        customer_email=customer_email, customer_phone=customer_phone, limit=limit,
    )
    return [memory_to_dict(r) for r in rows]


@router.get("/address")
async def recall_address_memory(
    street: str = Query(..., min_length=2),
    zip_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await recall_for_address(
        db, user_id=current_user.id,
        street=street, zip_code=zip_code, limit=limit,
    )
    return [memory_to_dict(r) for r in rows]
