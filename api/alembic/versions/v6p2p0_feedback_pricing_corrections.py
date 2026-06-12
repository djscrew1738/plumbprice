"""v6_2_0_feedback_pricing_corrections

Adds source tracking to pricing_recommendations so admins can distinguish
outcome-driven variance recommendations from feedback-driven ones.

Revision ID: v6p2p0_feedback_pricing_corrections
Revises: v6p1p0_session_memory_feedback
Create Date: 2026-06-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v6p2p0_feedback_pricing_corrections"
down_revision: Union[str, Sequence[str], None] = "v6p1p0_session_memory_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pricing_recommendations",
        sa.Column("source", sa.String(length=20), server_default="outcome", nullable=False),
    )
    op.create_index(
        "ix_pricing_recs_source_status",
        "pricing_recommendations",
        ["source", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pricing_recs_source_status", table_name="pricing_recommendations")
    op.drop_column("pricing_recommendations", "source")
