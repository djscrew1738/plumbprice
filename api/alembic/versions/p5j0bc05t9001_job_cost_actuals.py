"""job cost actuals

Revision ID: p5j0bc05t9001
Revises: p4f1f1ag5001
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p5j0bc05t9001"
down_revision: Union[str, Sequence[str], None] = "p4f1f1ag5001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estimate_actuals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "estimate_id",
            sa.Integer(),
            sa.ForeignKey("estimates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("actual_labor_hours", sa.Float(), nullable=True),
        sa.Column("actual_labor_cost", sa.Float(), nullable=True),
        sa.Column("actual_materials_cost", sa.Float(), nullable=True),
        sa.Column("actual_subcontractor_cost", sa.Float(), nullable=True),
        sa.Column("actual_other_cost", sa.Float(), nullable=True),
        sa.Column("actual_revenue", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recorded_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_actuals_org_closed",
        "estimate_actuals",
        ["organization_id", "closed_at"],
    )
    op.create_index(
        "ix_estimate_actuals_estimate_id",
        "estimate_actuals",
        ["estimate_id"],
    )

    op.create_table(
        "job_cost_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "estimate_id",
            sa.Integer(),
            sa.ForeignKey("estimates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("task_code", sa.String(length=80), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Float(), server_default="1.0"),
        sa.Column("unit", sa.String(length=50), server_default="ea"),
        sa.Column("unit_cost", sa.Float(), server_default="0.0"),
        sa.Column("total_cost", sa.Float(), server_default="0.0"),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "recorded_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_job_cost_entries_estimate_id",
        "job_cost_entries",
        ["estimate_id"],
    )
    op.create_index(
        "ix_job_cost_entries_kind",
        "job_cost_entries",
        ["kind"],
    )
    op.create_index(
        "ix_job_cost_entries_task_code",
        "job_cost_entries",
        ["task_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_cost_entries_task_code", table_name="job_cost_entries")
    op.drop_index("ix_job_cost_entries_kind", table_name="job_cost_entries")
    op.drop_index("ix_job_cost_entries_estimate_id", table_name="job_cost_entries")
    op.drop_table("job_cost_entries")

    op.drop_index("ix_estimate_actuals_estimate_id", table_name="estimate_actuals")
    op.drop_index("ix_actuals_org_closed", table_name="estimate_actuals")
    op.drop_table("estimate_actuals")
