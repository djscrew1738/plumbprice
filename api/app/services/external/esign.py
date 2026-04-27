"""E-signature provider abstraction (e1).

Default vendor target: Dropbox Sign (HelloSign). Mock always available so
/p/{token} accept flow can run end-to-end in dev without API keys.

Live integration is gated on the user's vendor decision + DROPBOX_SIGN_API_KEY.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional

import structlog

from . import ProviderHealth, ProviderMode

logger = structlog.get_logger()


@dataclass
class SignatureRequest:
    request_id: str
    proposal_token: str
    signer_email: str
    signer_name: str
    sign_url: str
    status: str = "awaiting_signature"  # awaiting_signature | signed | declined | expired
    signed_at: Optional[str] = None


class BaseEsignProvider(ABC):
    name: str = "esign"

    @abstractmethod
    async def create_request(
        self, *, proposal_token: str, signer_email: str, signer_name: str
    ) -> SignatureRequest: ...

    @abstractmethod
    async def get_status(self, request_id: str) -> SignatureRequest: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...


class MockEsignProvider(BaseEsignProvider):
    """In-memory mock — sign URL points back at /p/{token} accept dialog."""

    def __init__(self) -> None:
        self._store: Dict[str, SignatureRequest] = {}

    async def create_request(
        self, *, proposal_token: str, signer_email: str, signer_name: str
    ) -> SignatureRequest:
        rid = f"mock-{uuid.uuid4().hex[:12]}"
        req = SignatureRequest(
            request_id=rid,
            proposal_token=proposal_token,
            signer_email=signer_email,
            signer_name=signer_name,
            sign_url=f"/p/{proposal_token}#esign={rid}",
        )
        self._store[rid] = req
        logger.info("esign.mock.created", request_id=rid, token=proposal_token)
        return req

    async def get_status(self, request_id: str) -> SignatureRequest:
        if request_id not in self._store:
            raise KeyError(f"unknown signature request {request_id!r}")
        return self._store[request_id]

    async def mark_signed(self, request_id: str, when: str) -> None:
        if request_id in self._store:
            self._store[request_id].status = "signed"
            self._store[request_id].signed_at = when

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, mode=ProviderMode.MOCK, ok=True,
            detail=f"{len(self._store)} mock requests in-memory",
        )


_provider: Optional[BaseEsignProvider] = None


def get_esign_provider() -> BaseEsignProvider:
    global _provider
    if _provider is not None:
        return _provider
    api_key = os.getenv("DROPBOX_SIGN_API_KEY", "").strip()
    if api_key:
        # TODO(esign-live): wire DropboxSignProvider once a vendor decision lands.
        logger.warning("esign.live_provider_pending", note="API key set but live class not implemented yet")
    _provider = MockEsignProvider()
    return _provider
