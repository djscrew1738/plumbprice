from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)  # auto-set from first message
    county = Column(String(100), nullable=True)
    preferred_supplier = Column(String(100), nullable=True)
    job_type = Column(String(50), nullable=True)
    access_type = Column(String(50), nullable=True)
    # Phase 11 — blueprint fixture counts auto-seeded into estimates
    blueprint_fixtures = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    attachments = relationship(
        "ChatAttachment",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatAttachment.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class ChatAttachment(Base):
    """
    Multi-modal attachments associated with a ChatSession (d1).

    `kind` is a free-form discriminator: 'photo', 'voice', 'blueprint',
    'estimate', 'document'. `ref_id` points at the corresponding row in
    the relevant table (e.g. photo_quotes.id for photos, blueprints.id
    for blueprints, estimates.id for estimates). When the agent requests
    an attachment mid-conversation we insert a row with status='requested'
    and let the upload pipeline fill in `ref_id` once the artifact lands.
    """

    __tablename__ = "chat_attachments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id = Column(
        Integer, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind = Column(String(32), nullable=False)
    ref_id = Column(Integer, nullable=True)
    # 'requested' | 'attached' | 'failed' — drives the agent's "still waiting" UX.
    status = Column(String(32), nullable=False, default="attached")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="attachments")

    __table_args__ = (
        Index("ix_chat_attachments_session_kind", "session_id", "kind"),
    )


class ChatSessionShare(Base):
    __tablename__ = "chat_session_shares"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    permission = Column(String(20), nullable=False, default="read")  # read | comment
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    template = Column(Text, nullable=False)
    is_personal = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatEmbedding(Base):
    """Semantic embeddings for labor template task codes.

    Used by the v3 pricing chat classifier to dynamically surface the most
    relevant task codes based on the user's query embedding.
    """
    __tablename__ = "chat_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    model_name = Column(String(100), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
