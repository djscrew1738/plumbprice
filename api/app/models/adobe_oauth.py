from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class AdobeOAuthToken(Base):
    """Encrypted Adobe Document Cloud OAuth tokens, one row per user."""
    __tablename__ = "adobe_oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Fernet-encrypted tokens (stored as opaque strings)
    access_token_enc = Column(Text, nullable=False)
    refresh_token_enc = Column(Text, nullable=True)
    # When the access token expires (UTC)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    # Display info fetched during OAuth
    adobe_email = Column(String(255), nullable=True)
    adobe_display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_adobe_oauth_tokens_user"),
    )
