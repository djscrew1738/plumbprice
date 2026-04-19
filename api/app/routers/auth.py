from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime, timezone
import hashlib
import secrets
import structlog

from app.database import get_db
from app.models.users import User, UserInvite
from app.models.auth_tokens import PasswordResetToken
from app.core.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.core import rate_limit
from app.config import settings
from app.services.email_service import send_password_reset_email

logger = structlog.get_logger()
router = APIRouter()

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15
_LOCKOUT_WINDOW_SECONDS = LOCKOUT_WINDOW_MINUTES * 60


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class MessageResponse(BaseModel):
    message: str


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_admin: bool
    organization_id: int | None = None
    phone: str | None = None
    avatar_url: str | None = None


async def _check_brute_force(email: str) -> None:
    """Block login if too many recent failed attempts."""
    count = await rate_limit.get_count(email.lower(), _LOCKOUT_WINDOW_SECONDS)
    if count >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in {LOCKOUT_WINDOW_MINUTES} minutes.",
        )


async def _record_failed_attempt(email: str) -> None:
    await rate_limit.record_failure(email.lower(), _LOCKOUT_WINDOW_SECONDS)


async def _clear_attempts(email: str) -> None:
    await rate_limit.clear(email.lower())


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="8-128 characters")
    full_name: str = ""


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with username/password, returns JWT token."""
    await _check_brute_force(form_data.username)

    result = await db.execute(
        select(User).where(User.email == form_data.username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        await _record_failed_attempt(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await _clear_attempts(form_data.username)

    # Track last successful login. Cache attributes before commit to avoid
    # lazy-load after expiration in sessions where expire_on_commit=True.
    user.last_login = datetime.now(timezone.utc)
    user_id = user.id
    user_email = user.email
    user_full_name = user.full_name
    user_role = user.role
    user_is_admin = user.is_admin
    await db.commit()

    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_email,
            "full_name": user_full_name,
            "role": user_role,
            "is_admin": user_is_admin,
        },
    }


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        role="estimator",
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name or "",
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "organization_id": current_user.organization_id,
        "phone": current_user.phone,
        "avatar_url": current_user.avatar_url,
    }


# ─── Profile update ──────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update name, email, and/or phone for the current user."""
    if payload.email and payload.email != current_user.email:
        existing = await db.execute(
            select(User).where(User.email == payload.email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use by another account")
        current_user.email = payload.email

    if payload.name is not None:
        current_user.full_name = payload.name

    if payload.phone is not None:
        current_user.phone = payload.phone or None

    await db.commit()
    await db.refresh(current_user)
    logger.info("user.profile_updated", user_id=current_user.id)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name or "",
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "organization_id": current_user.organization_id,
        "phone": current_user.phone,
        "avatar_url": current_user.avatar_url,
    }


# ─── Change password ─────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password after verifying the existing one."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    logger.info("user.password_changed", user_id=current_user.id)
    return {"message": "Password updated successfully"}


# ─── Avatar upload ───────────────────────────────────────────────────────────

import io as _io
import uuid as _uuid
from fastapi import UploadFile, File

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a profile avatar image. Returns the new avatar URL."""
    from app.core.storage import storage_client
    from app.config import settings as _cfg

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type. Use JPEG, PNG, WebP, or GIF.")

    content = await file.read()
    if len(content) > _MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB limit")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    object_name = f"avatars/{current_user.id}/{_uuid.uuid4()}.{ext}"

    # Use blueprints bucket (public-ish) or documents bucket; reuse available bucket
    bucket = getattr(_cfg, "minio_bucket_blueprints", "blueprints")
    ok = storage_client.upload_file(
        bucket,
        object_name,
        _io.BytesIO(content),
        len(content),
        content_type=file.content_type or "image/jpeg",
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

    # Build URL — MinIO endpoint + bucket + object path
    endpoint = _cfg.minio_endpoint
    scheme = "https" if _cfg.minio_secure else "http"
    avatar_url = f"{scheme}://{endpoint}/{bucket}/{object_name}"

    current_user.avatar_url = avatar_url
    await db.commit()
    logger.info("user.avatar_uploaded", user_id=current_user.id)
    return {"avatar_url": avatar_url}


PASSWORD_RESET_RATE_LIMIT = 3
_PASSWORD_RESET_WINDOW_SECONDS = 60 * 60  # 1 hour
PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)

GENERIC_FORGOT_RESPONSE = {
    "message": "If an account exists for that email, a reset link has been sent. Check your inbox."
}


def _hash_reset_token(token: str) -> str:
    """Fast deterministic hash for reset tokens (random 32-byte secrets — no bcrypt needed)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link. Always returns 200 to prevent enumeration."""
    email_key = f"pwreset:{payload.email.lower()}"
    attempts = await rate_limit.get_count(email_key, _PASSWORD_RESET_WINDOW_SECONDS)
    if attempts >= PASSWORD_RESET_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Try again in 1 hour.",
        )
    await rate_limit.record_failure(email_key, _PASSWORD_RESET_WINDOW_SECONDS)

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.info("password_reset.requested_unknown", email=payload.email)
        return GENERIC_FORGOT_RESPONSE

    raw_token = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_TTL,
    )
    db.add(token)
    user_id = user.id
    user_email = user.email
    await db.commit()

    frontend_base = getattr(settings, "frontend_url", None) or "https://app.ctlplumbingllc.com"
    reset_url = f"{frontend_base.rstrip('/')}/reset-password?token={raw_token}"

    await send_password_reset_email(user_email, reset_url)
    logger.info("password_reset.requested", user_id=user_id)

    return GENERIC_FORGOT_RESPONSE


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Consume a password-reset token and set a new password."""
    token_hash = _hash_reset_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if token_row is None or token_row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = get_password_hash(payload.new_password)
    token_row.used_at = datetime.now(timezone.utc)
    user_id = user.id
    user_email = user.email
    await db.commit()

    await rate_limit.clear(f"pwreset:{user_email.lower()}")
    logger.info("password_reset.completed", user_id=user_id)

    return {"message": "Password updated successfully."}


# ─── Accept invite ────────────────────────────────────────────────────────────

class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    payload: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept a user invite token and create the account, returning a JWT."""
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()

    result = await db.execute(
        select(UserInvite).where(UserInvite.token_hash == token_hash)
    )
    invite = result.scalar_one_or_none()

    if invite is None:
        raise HTTPException(status_code=400, detail="Invalid or expired invite token")

    now = datetime.now(timezone.utc)
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(status_code=400, detail="Invite token has expired")

    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite token has already been used")

    is_admin_role = invite.role == "admin"
    user = User(
        email=invite.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name or invite.full_name,
        role=invite.role,
        is_active=True,
        is_admin=is_admin_role,
        organization_id=invite.organization_id,
    )
    db.add(user)
    invite.accepted_at = now
    await db.flush()
    user_id = user.id
    user_email = user.email
    user_full_name = user.full_name
    user_role = user.role
    user_is_admin = user.is_admin
    invited_by = invite.invited_by  # capture before commit (expires session objects)
    await db.commit()

    # Notify the invite sender
    if invited_by is not None:
        try:
            from app.services.notifications_service import notify
            name_display = user_full_name or user_email
            await notify(
                db,
                user_id=invited_by,
                kind="invite_accepted",
                title=f"{name_display} accepted your invitation",
                body=f"{user_email} joined as {user_role}",
                link="/admin?tab=users",
            )
            await db.commit()
        except Exception:
            logger.warning("invite.notify_failed", invitee=user_email)

    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info("invite.accepted", user_id=user_id, email=user_email)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_email,
            "full_name": user_full_name,
            "role": user_role,
            "is_admin": user_is_admin,
        },
    }
