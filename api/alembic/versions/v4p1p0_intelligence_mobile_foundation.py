"""v4_1_0_intelligence_mobile_foundation

Adds all schema additions for PlumbPrice v4.1:
 - supplier_price_alerts (E1.3)
 - actual cost columns on estimate_outcomes (E2.1)
 - pricing_adjustments (E2.4)
 - ml_models (E3.2)
 - photo_sessions (E4.1)
 - field_tech to users.role comment (E6.2 — role is VARCHAR, no enum migration needed)
 - push_subscriptions (E6.5)
 - blueprint_pipe_runs.routing_json column (E5.3)
 - scale_ratio on blueprint_pages (E5.1)
 - price_trend on supplier_products (E1.4)

Revision ID: v4p1p0_foundation
Revises: v3p0p0_ai_overhaul
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "v4p1p0_foundation"
down_revision: Union[str, Sequence[str], None] = "v3p0p0_ai_overhaul"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── supplier_price_alerts ─────────────────────────────────────────────────
    op.create_table(
        "supplier_price_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_item", sa.String(200), nullable=False),
        sa.Column("old_price", sa.Float(), nullable=False),
        sa.Column("new_price", sa.Float(), nullable=False),
        sa.Column("delta_pct", sa.Float(), nullable=False),
        sa.Column("alerted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("acknowledged_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_price_alerts_supplier_id", "supplier_price_alerts", ["supplier_id"])
    op.create_index("ix_price_alerts_canonical_item", "supplier_price_alerts", ["canonical_item"])
    op.create_index("ix_price_alerts_unacknowledged", "supplier_price_alerts", ["acknowledged", "alerted_at"])

    # ── pricing_adjustments ───────────────────────────────────────────────────
    op.create_table(
        "pricing_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("adjustment_type", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_key", sa.String(200), nullable=False),
        sa.Column("adjustment_value", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("source_recommendation_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index("ix_pricing_adjustments_org_active", "pricing_adjustments", ["organization_id", "is_active"])
    op.create_index("ix_pricing_adjustments_target", "pricing_adjustments", ["target_type", "target_key", "is_active"])

    # ── ml_models ─────────────────────────────────────────────────────────────
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.String(255), nullable=False, unique=True),
        sa.Column("base_model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("training_samples", sa.Integer(), nullable=True),
        sa.Column("eval_score", sa.Float(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="shadow"),
        sa.Column("shadow_calls", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shadow_match_rate", sa.Float(), nullable=True),
        sa.Column("openai_job_id", sa.String(255), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index("ix_ml_models_status", "ml_models", ["status"])
    op.create_index("ix_ml_models_created_at", "ml_models", ["created_at"])

    # ── photo_sessions ────────────────────────────────────────────────────────
    op.create_table(
        "photo_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("county", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("photo_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detection_results", sa.JSON(), nullable=True),
        sa.Column("job_notes", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index("ix_photo_sessions_org", "photo_sessions", ["organization_id"])
    op.create_index("ix_photo_sessions_status", "photo_sessions", ["status", "created_at"])
    op.create_index("ix_photo_sessions_created_by", "photo_sessions", ["created_by"])

    # ── push_subscriptions ────────────────────────────────────────────────────
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("keys_json", sa.JSON(), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id", "is_active"])
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)

    # ── pricing_recommendations ───────────────────────────────────────────────
    op.create_table(
        "pricing_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("task_code", sa.String(100), nullable=False),
        sa.Column("recommendation_type", sa.String(50), nullable=False),
        sa.Column("avg_variance_pct", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("suggested_adjustment", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pricing_recs_org_status", "pricing_recommendations", ["organization_id", "status"])
    op.create_index("ix_pricing_recs_task_code", "pricing_recommendations", ["task_code"])

    # ── Column additions ──────────────────────────────────────────────────────

    # estimate_outcomes: actual cost capture
    op.add_column("estimate_outcomes", sa.Column("actual_materials_cost", sa.Float(), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("actual_labor_hours", sa.Float(), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("actual_labor_cost", sa.Float(), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("actual_total", sa.Float(), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("variance_pct", sa.Float(), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("closed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("estimate_outcomes", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))

    # blueprint_pipe_runs: routing details for E5.3
    op.add_column("blueprint_pipe_runs", sa.Column("routing_json", sa.JSON(), nullable=True))
    op.add_column("blueprint_pipe_runs", sa.Column("from_fixture", sa.String(100), nullable=True))
    op.add_column("blueprint_pipe_runs", sa.Column("to_fixture", sa.String(100), nullable=True))
    op.add_column("blueprint_pipe_runs", sa.Column("material_type", sa.String(50), nullable=True))

    # blueprint_pages: scale calibration (E5.1)
    op.add_column("blueprint_pages", sa.Column("scale_ratio", sa.Float(), nullable=True))
    op.add_column("blueprint_pages", sa.Column("scale_notation", sa.String(60), nullable=True))

    # supplier_products: price trend label (E1.4)
    op.add_column("supplier_products", sa.Column("price_trend", sa.String(20), nullable=True))
    op.add_column("supplier_products", sa.Column("price_trend_computed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("supplier_products", sa.Column("scrape_method", sa.String(20), nullable=True))


def downgrade() -> None:
    # supplier_products columns
    op.drop_column("supplier_products", "scrape_method")
    op.drop_column("supplier_products", "price_trend_computed_at")
    op.drop_column("supplier_products", "price_trend")

    # blueprint_pages columns
    op.drop_column("blueprint_pages", "scale_notation")
    op.drop_column("blueprint_pages", "scale_ratio")

    # blueprint_pipe_runs columns
    op.drop_column("blueprint_pipe_runs", "material_type")
    op.drop_column("blueprint_pipe_runs", "to_fixture")
    op.drop_column("blueprint_pipe_runs", "from_fixture")
    op.drop_column("blueprint_pipe_runs", "routing_json")

    # estimate_outcomes columns
    op.drop_column("estimate_outcomes", "closed_at")
    op.drop_column("estimate_outcomes", "closed_by_user_id")
    op.drop_column("estimate_outcomes", "variance_pct")
    op.drop_column("estimate_outcomes", "actual_total")
    op.drop_column("estimate_outcomes", "actual_labor_cost")
    op.drop_column("estimate_outcomes", "actual_labor_hours")
    op.drop_column("estimate_outcomes", "actual_materials_cost")

    # New tables
    op.drop_index("ix_pricing_recs_task_code", table_name="pricing_recommendations")
    op.drop_index("ix_pricing_recs_org_status", table_name="pricing_recommendations")
    op.drop_table("pricing_recommendations")

    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

    op.drop_index("ix_photo_sessions_created_by", table_name="photo_sessions")
    op.drop_index("ix_photo_sessions_status", table_name="photo_sessions")
    op.drop_index("ix_photo_sessions_org", table_name="photo_sessions")
    op.drop_table("photo_sessions")

    op.drop_index("ix_ml_models_created_at", table_name="ml_models")
    op.drop_index("ix_ml_models_status", table_name="ml_models")
    op.drop_table("ml_models")

    op.drop_index("ix_pricing_adjustments_target", table_name="pricing_adjustments")
    op.drop_index("ix_pricing_adjustments_org_active", table_name="pricing_adjustments")
    op.drop_table("pricing_adjustments")

    op.drop_index("ix_price_alerts_unacknowledged", table_name="supplier_price_alerts")
    op.drop_index("ix_price_alerts_canonical_item", table_name="supplier_price_alerts")
    op.drop_index("ix_price_alerts_supplier_id", table_name="supplier_price_alerts")
    op.drop_table("supplier_price_alerts")
