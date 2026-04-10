from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime, timezone
from collections import defaultdict
import structlog

from app.database import get_db
from app.models.users import User
from app.core.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.config import settings

logger = structlog.get_logger()
router = APIRouter()

# In-memory brute force protection
_login_attempts: dict[str, list[datetime]] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def _check_brute_force(email: str) -> None:
    """Block login if too many recent failed attempts."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    # Purge old attempts
    _login_attempts[email] = [t for t in _login_attempts[email] if t > cutoff]
    if len(_login_attempts[email]) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in {LOCKOUT_WINDOW_MINUTES} minutes.",
        )


def _record_failed_attempt(email: str) -> None:
    _login_attempts[email].append(datetime.now(timezone.utc))


def _clear_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="8-128 characters")
    full_name: str = ""


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with username/password, returns JWT token."""
    _check_brute_force(form_data.username)

    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        _record_failed_attempt(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_attempts(form_data.username)

    # Track last successful login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_admin": user.is_admin,
        },
    }


@router.post("/register")
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


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "organization_id": current_user.organization_id,
    }
