"""Adobe Document Cloud OAuth 2.0 service.

Flow:
  1. User clicks "Connect Adobe Cloud" → GET /auth/url → redirect to Adobe IMS
  2. Adobe redirects back to /auth/callback?code=...
  3. Backend exchanges code for tokens, encrypts and stores them
  4. User can then browse and import files from their DC storage

API base: https://dc-api.adobe.io
OAuth:    https://ims-na1.adobelogin.com/ims/
"""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.adobe_oauth import AdobeOAuthToken

logger = structlog.get_logger()

_ADOBE_AUTH_URL = "https://ims-na1.adobelogin.com/ims/authorize/v2"
_ADOBE_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
_ADOBE_DC_API = "https://dc-api.adobe.io"
_ADOBE_PROFILE_URL = "https://ims-na1.adobelogin.com/ims/userinfo"


# ── Token encryption ─────────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    """Derive a stable Fernet key from SECRET_KEY via SHA-256."""
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt(text: str) -> str:
    return _get_fernet().encrypt(text.encode()).decode()


def _decrypt(cipher: str) -> str:
    try:
        return _get_fernet().decrypt(cipher.encode()).decode()
    except (InvalidToken, Exception) as exc:
        raise ValueError("Failed to decrypt Adobe token — reconnect required") from exc


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def get_auth_url(state: str) -> str:
    """Build the Adobe IMS authorization URL for user consent."""
    if not settings.adobe_client_id:
        raise ValueError("ADOBE_CLIENT_ID is not configured")
    params = urlencode({
        "client_id": settings.adobe_client_id,
        "redirect_uri": settings.adobe_redirect_uri,
        "response_type": "code",
        "scope": settings.adobe_scopes,
        "state": state,
    })
    return f"{_ADOBE_AUTH_URL}?{params}"


async def exchange_code(code: str) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _ADOBE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.adobe_client_id,
                "client_secret": settings.adobe_client_secret,
                "code": code,
                "redirect_uri": settings.adobe_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Use a refresh token to get a new access token."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _ADOBE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.adobe_client_id,
                "client_secret": settings.adobe_client_secret,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_adobe_profile(access_token: str) -> dict[str, Any]:
    """Fetch user profile from Adobe IMS."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            _ADOBE_PROFILE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-api-key": settings.adobe_client_id or "",
            },
        )
        resp.raise_for_status()
        return resp.json()


# ── DB helpers ────────────────────────────────────────────────────────────────

async def save_tokens(
    db: AsyncSession,
    user_id: int,
    token_data: dict[str, Any],
    adobe_email: Optional[str] = None,
    adobe_display_name: Optional[str] = None,
) -> AdobeOAuthToken:
    """Persist (upsert) encrypted Adobe tokens for a user."""
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    result = await db.execute(
        select(AdobeOAuthToken).where(AdobeOAuthToken.user_id == user_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        record = AdobeOAuthToken(user_id=user_id)
        db.add(record)

    record.access_token_enc = _encrypt(token_data["access_token"])
    if token_data.get("refresh_token"):
        record.refresh_token_enc = _encrypt(token_data["refresh_token"])
    record.expires_at = expires_at
    if adobe_email:
        record.adobe_email = adobe_email
    if adobe_display_name:
        record.adobe_display_name = adobe_display_name

    await db.commit()
    await db.refresh(record)
    return record


async def get_valid_access_token(db: AsyncSession, user_id: int) -> str:
    """Return a valid (non-expired) access token for the user, refreshing if needed."""
    result = await db.execute(
        select(AdobeOAuthToken).where(AdobeOAuthToken.user_id == user_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("Adobe account not connected — please connect your Adobe account first")

    now = datetime.now(timezone.utc)
    token_expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at else now

    # Refresh if within 5 minutes of expiry
    if token_expires - now < timedelta(minutes=5):
        if not record.refresh_token_enc:
            raise ValueError("Adobe token expired and no refresh token available — reconnect required")
        refresh_tok = _decrypt(record.refresh_token_enc)
        token_data = await refresh_access_token(refresh_tok)
        record.access_token_enc = _encrypt(token_data["access_token"])
        expires_in = token_data.get("expires_in", 3600)
        record.expires_at = now + timedelta(seconds=int(expires_in))
        if token_data.get("refresh_token"):
            record.refresh_token_enc = _encrypt(token_data["refresh_token"])
        await db.commit()
        logger.info("adobe.token.refreshed", user_id=user_id)

    return _decrypt(record.access_token_enc)


# ── DC Files API ──────────────────────────────────────────────────────────────

async def list_files(
    access_token: str,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
) -> dict[str, Any]:
    """List PDF files from the user's Adobe Document Cloud storage."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if search:
        params["q"] = search

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{_ADOBE_DC_API}/assets",
            params=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-api-key": settings.adobe_client_id or "",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 401:
            raise ValueError("Adobe token invalid or expired — reconnect required")
        if resp.status_code == 403:
            raise ValueError("Adobe account does not have Document Cloud API access")
        resp.raise_for_status()
        return resp.json()


async def get_asset_download_url(access_token: str, asset_id: str) -> str:
    """Get a pre-signed download URL for a specific Adobe DC asset."""
    async with httpx.AsyncClient(timeout=15) as client:
        # Try the rendition endpoint first (resolves to direct PDF)
        resp = await client.get(
            f"{_ADOBE_DC_API}/assets/{asset_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-api-key": settings.adobe_client_id or "",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 401:
            raise ValueError("Adobe token invalid or expired")
        resp.raise_for_status()
        data = resp.json()

        # The DC API returns a downloadUri or a rendition download link
        download_url = (
            data.get("downloadUri")
            or data.get("download_uri")
            or data.get("uri")
        )
        if not download_url:
            # Fall back to rendition endpoint
            r2 = await client.get(
                f"{_ADOBE_DC_API}/assets/{asset_id}/renditions/pdf",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "x-api-key": settings.adobe_client_id or "",
                },
                follow_redirects=False,
            )
            if r2.is_redirect:
                download_url = r2.headers.get("location", "")
            elif r2.status_code == 200:
                download_url = r2.url.__str__()

        if not download_url:
            raise ValueError(f"Could not resolve download URL for asset {asset_id}")
        return download_url


async def download_asset(access_token: str, asset_id: str) -> tuple[bytes, str]:
    """Download an asset and return (pdf_bytes, filename)."""
    download_url = await get_asset_download_url(access_token, asset_id)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(
            download_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-api-key": settings.adobe_client_id or "",
            },
        )
        resp.raise_for_status()
        # Extract filename from Content-Disposition or URL
        cd = resp.headers.get("content-disposition", "")
        filename = "adobe_floorplan.pdf"
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip().strip('"')
        elif "/" in str(resp.url):
            url_part = str(resp.url).split("?")[0].split("/")[-1]
            if url_part.endswith(".pdf"):
                filename = url_part
        return resp.content, filename
