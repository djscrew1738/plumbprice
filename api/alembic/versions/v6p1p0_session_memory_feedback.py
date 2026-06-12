"""v6_1_0_session_memory_feedback

Enriches ChatSession with pricing context fields (preferred_supplier,
job_type, access_type) and adds estimate_feedback table for the
thumbs-up/down feedback loop.

Revision ID: v6p1p0_session_memory_feedback
Revises: v6p0p0_chat_embeddings
Create Date: 2026-06-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v6p1p0_session_memory_feedback"
down_revision: Union[str, Sequence[str], None] = "v6p0p0_chat_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enrich chat_sessions ────────────────────────────────────────────────
    op.add_column(
        "chat_sessions",
        sa.Column("preferred_supplier", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("job_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("access_type", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_chat_sessions_county"),
        "chat_sessions",
        ["county"],
        unique=False,
    )

    # ── Create estimate_feedback ────────────────────────────────────────────
    op.create_table(
        "estimate_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "estimate_id",
            sa.Integer(),
            sa.ForeignKey("estimates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vote",
            sa.Enum("up", "down", name="feedbackvote"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estimate_id", "user_id", name="uq_estimate_user_feedback"),
    )


def downgrade() -> None:
    op.drop_table("estimate_feedback")
    op.drop_index(op.f("ix_chat_sessions_county"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "access_type")
    op.drop_column("chat_sessions", "job_type")
    op.drop_column("chat_sessions", "preferred_supplier")
