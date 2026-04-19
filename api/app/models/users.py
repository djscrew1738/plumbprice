import uuid

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.auth_tokens import GUID


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    license_number = Column(String(100))
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(10), default="TX")
    zip_code = Column(String(10))
    default_county = Column(String(100), default="Dallas")
    billing_email = Column(String(255), nullable=True)
    logo_url = Column(String(512), nullable=True)
    default_tax_rate = Column(Float, nullable=True)
    default_markup_percent = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="estimator")  # admin, estimator, viewer
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    organization = relationship("Organization", back_populates="users")


class UserInvite(Base):
    __tablename__ = "user_invites"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role = Column(String(50), nullable=False, default="estimator")
    full_name = Column(String(255), nullable=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization")
    inviter = relationship("User", foreign_keys=[invited_by])
