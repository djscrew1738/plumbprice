"""chat_attachments (d1 multi-modal sessions)

Revision ID: c4ataaaaaaaa
Revises: p6paaud1t9001
Create Date: 2026-04-27
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4ataaaaaaaa"
down_revision: Union[str, Sequence[str], None] = "p6paaud1t9001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="attached"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_attachments_session_kind",
        "chat_attachments",
        ["session_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_attachments_session_kind", table_name="chat_attachments")
    op.drop_table("chat_attachments")
