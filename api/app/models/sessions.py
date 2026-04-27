from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)  # auto-set from first message
    county = Column(String(100), nullable=True)
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
