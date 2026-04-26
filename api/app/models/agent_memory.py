"""Agent long-term memory.

Stores durable facts extracted from chat sessions plus user-provided
preferences so the AI agent can recall context across sessions.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Index
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    # Categorical kind lets us scope retrieval / display.
    # preference  – user prefers, defaults, working style
    # profile     – static facts about the business (rate, markups, region)
    # customer    – facts about a specific customer
    # job_history – outcome of a past job, useful for similar future jobs
    # fact        – generic durable fact pulled from chat
    kind = Column(String(32), nullable=False, default="fact", index=True)

    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    # 0.0 .. 1.0 — used for ranking and pruning.
    importance = Column(Float, nullable=False, default=0.5)

    source_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_referenced_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_agent_memories_user_kind", "user_id", "kind"),
    )
