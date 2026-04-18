"""Tests for admin organization settings."""

from __future__ import annotations

import pytest

from app.core.auth import get_current_user
from app.main import app
from app.models.users import User


BASE = "/api/v1/admin"


@pytest.fixture
def non_admin_user():
    async def override():
        return User(
            id=888,
            email="viewer@example.com",
            full_name="Viewer",
            is_active=True,
            is_admin=False,
            role="viewer",
        )

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_my_organization(test_client):
    r = await test_client.get(f"{BASE}/organizations/me")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "default_tax_rate" in data
    assert "default_markup_percent" in data
    assert "logo_url" in data


@pytest.mark.asyncio
async def test_patch_organization_updates_fields(test_client):
    payload = {
        "name": "PlumbPro Inc",
        "default_tax_rate": 0.0825,
        "default_markup_percent": 1.35,
        "billing_email": "billing@plumbpro.example",
        "phone": "555-0100",
        "address": "123 Main St",
    }
    r = await test_client.patch(f"{BASE}/organizations/me", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "PlumbPro Inc"
    assert data["default_tax_rate"] == pytest.approx(0.0825)
    assert data["default_markup_percent"] == pytest.approx(1.35)
    assert data["billing_email"] == "billing@plumbpro.example"
    assert data["phone"] == "555-0100"
    assert data["address"] == "123 Main St"


@pytest.mark.asyncio
async def test_patch_organization_tax_rate_out_of_range(test_client):
    r = await test_client.patch(f"{BASE}/organizations/me", json={"default_tax_rate": 1.5})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_organization_markup_out_of_range(test_client):
    r = await test_client.patch(f"{BASE}/organizations/me", json={"default_markup_percent": 99.0})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_organization_forbidden_for_non_admin(test_client, non_admin_user):
    r = await test_client.patch(f"{BASE}/organizations/me", json={"name": "Nope"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_logo_upload_forbidden_for_non_admin(test_client, non_admin_user):
    files = {"file": ("logo.png", b"\x89PNG\r\n\x1a\nfake", "image/png")}
    r = await test_client.post(f"{BASE}/organizations/me/logo", files=files)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_logo_upload_rejects_non_image(test_client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = await test_client.post(f"{BASE}/organizations/me/logo", files=files)
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_logo_upload_success_returns_url(test_client, monkeypatch):
    """Storage is patched to simulate successful upload."""
    from app.core import storage as storage_mod

    monkeypatch.setattr(storage_mod.storage_client, "ensure_buckets", lambda: None)
    monkeypatch.setattr(
        storage_mod.storage_client,
        "upload_file",
        lambda **kwargs: True,
    )
    # Support positional calls too
    def _upload(*args, **kwargs):
        return True
    monkeypatch.setattr(storage_mod.storage_client, "upload_file", _upload)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {"file": ("logo.png", png_bytes, "image/png")}
    r = await test_client.post(f"{BASE}/organizations/me/logo", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["logo_url"].startswith("/media/")
    assert data["logo_url"].endswith(".png")
