"""Proposal Service — Scaffolded for Phase 2."""

from typing import Optional
import structlog

logger = structlog.get_logger()


class ProposalService:
    """Phase 2: Proposal generation and PDF output."""

    async def generate_proposal(self, estimate_id: int, template_id: Optional[int] = None) -> dict:
        """Generate a proposal document. Phase 2 implementation."""
        logger.info("Proposal generation — Phase 2 not yet implemented", estimate_id=estimate_id)
        return {"status": "not_implemented", "phase": 2, "estimate_id": estimate_id}

    async def generate_pdf(self, proposal_id: int) -> bytes:
        """Generate PDF from proposal. Phase 2 implementation."""
        return b""

    async def send_proposal(self, proposal_id: int, recipient_email: str) -> dict:
        """Send proposal via email. Phase 2 implementation."""
        return {"status": "not_implemented"}


proposal_service = ProposalService()
