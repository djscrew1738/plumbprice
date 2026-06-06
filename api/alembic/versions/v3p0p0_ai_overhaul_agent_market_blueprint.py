"""v3_ai_overhaul_agent_market_blueprint

Revision ID: v3p0p0_ai_overhaul
Revises: p6paaud1t9001
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v3p0p0_ai_overhaul"
down_revision: Union[str, Sequence[str], None] = "p6paaud1t9001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New tables ────────────────────────────────────────────────────────────

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_tool_calls_estimate_id", "agent_tool_calls", ["estimate_id"])
    op.create_index("ix_agent_tool_calls_created_at", "agent_tool_calls", ["created_at"])

    op.create_table(
        "market_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("factor", sa.Float(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("applies_to", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("counties", sa.JSON(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(50), server_default="admin", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index("ix_market_adjustments_active_dates", "market_adjustments", ["is_active", "effective_from", "effective_until"])
    op.create_index("ix_market_adjustments_category", "market_adjustments", ["category", "is_active"])

    op.create_table(
        "blueprint_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blueprint_job_id", sa.Integer(), sa.ForeignKey("blueprint_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("room_type", sa.String(50), nullable=False),
        sa.Column("room_name", sa.String(100), nullable=True),
        sa.Column("bounding_box", sa.JSON(), nullable=True),
        sa.Column("area_sqft", sa.Float(), nullable=True),
        sa.Column("fixture_count", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_blueprint_rooms_job_id", "blueprint_rooms", ["blueprint_job_id"])

    op.create_table(
        "blueprint_pipe_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blueprint_job_id", sa.Integer(), sa.ForeignKey("blueprint_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("pipe_type", sa.String(50), nullable=False),
        sa.Column("length_ft", sa.Float(), nullable=False),
        sa.Column("start_point", sa.JSON(), nullable=True),
        sa.Column("end_point", sa.JSON(), nullable=True),
        sa.Column("bounding_box", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_blueprint_pipe_runs_job_id", "blueprint_pipe_runs", ["blueprint_job_id"])

    op.create_table(
        "supplier_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("endpoint_url", sa.String(1000), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_supplier_webhooks_supplier_id", "supplier_webhooks", ["supplier_id"])
    op.create_index("ix_supplier_webhooks_active", "supplier_webhooks", ["is_active"])

    # ── Modified tables ───────────────────────────────────────────────────────

    op.add_column("estimates", sa.Column("market_adjustment_applied", sa.Float(), server_default="1.0", nullable=False))
    op.add_column("estimates", sa.Column("agent_trace", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("estimates", sa.Column("blueprint_room_count", sa.Integer(), nullable=True))
    op.add_column("estimates", sa.Column("blueprint_pipe_run_ft", sa.Float(), nullable=True))
    op.add_column("estimates", sa.Column("confidence_components", sa.JSON(), server_default="{}", nullable=False))


def downgrade() -> None:
    op.drop_column("estimates", "confidence_components")
    op.drop_column("estimates", "blueprint_pipe_run_ft")
    op.drop_column("estimates", "blueprint_room_count")
    op.drop_column("estimates", "agent_trace")
    op.drop_column("estimates", "market_adjustment_applied")

    op.drop_index("ix_supplier_webhooks_active", table_name="supplier_webhooks")
    op.drop_index("ix_supplier_webhooks_supplier_id", table_name="supplier_webhooks")
    op.drop_table("supplier_webhooks")

    op.drop_index("ix_blueprint_pipe_runs_job_id", table_name="blueprint_pipe_runs")
    op.drop_table("blueprint_pipe_runs")

    op.drop_index("ix_blueprint_rooms_job_id", table_name="blueprint_rooms")
    op.drop_table("blueprint_rooms")

    op.drop_index("ix_market_adjustments_category", table_name="market_adjustments")
    op.drop_index("ix_market_adjustments_active_dates", table_name="market_adjustments")
    op.drop_table("market_adjustments")

    op.drop_index("ix_agent_tool_calls_created_at", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_estimate_id", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")
