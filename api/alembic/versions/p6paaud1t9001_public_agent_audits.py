"""public_agent_audits

Revision ID: p6paaud1t9001
Revises: p5j0bc05t9001
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p6paaud1t9001"
down_revision: Union[str, Sequence[str], None] = "p5j0bc05t9001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "public_agent_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("county", sa.String(100), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ok"),
        sa.Column("task_code", sa.String(64), nullable=True),
        sa.Column("grand_total", sa.Float(), nullable=True),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("anomaly_flags", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_public_agent_audits_created_at", "public_agent_audits", ["created_at"])
    op.create_index("ix_public_agent_audits_client_ip", "public_agent_audits", ["client_ip"])
    op.create_index("ix_public_agent_audits_status", "public_agent_audits", ["status"])
    op.create_index("ix_public_agent_audits_anomaly_score", "public_agent_audits", ["anomaly_score"])
    op.create_index("ix_pa_audits_score_created", "public_agent_audits", ["anomaly_score", "created_at"])
    op.create_index("ix_pa_audits_unreviewed", "public_agent_audits", ["reviewed_at", "anomaly_score"])


def downgrade() -> None:
    op.drop_index("ix_pa_audits_unreviewed", table_name="public_agent_audits")
    op.drop_index("ix_pa_audits_score_created", table_name="public_agent_audits")
    op.drop_index("ix_public_agent_audits_anomaly_score", table_name="public_agent_audits")
    op.drop_index("ix_public_agent_audits_status", table_name="public_agent_audits")
    op.drop_index("ix_public_agent_audits_client_ip", table_name="public_agent_audits")
    op.drop_index("ix_public_agent_audits_created_at", table_name="public_agent_audits")
    op.drop_table("public_agent_audits")
