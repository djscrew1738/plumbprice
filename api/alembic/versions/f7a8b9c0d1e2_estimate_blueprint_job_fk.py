"""add estimates.blueprint_job_id FK

Revision ID: f7a8b9c0d1e2
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estimates",
        sa.Column("blueprint_job_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_estimates_blueprint_job_id",
        "estimates",
        ["blueprint_job_id"],
    )
    op.create_foreign_key(
        "fk_estimates_blueprint_job_id",
        "estimates",
        "blueprint_jobs",
        ["blueprint_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_estimates_blueprint_job_id", "estimates", type_="foreignkey"
    )
    op.drop_index("ix_estimates_blueprint_job_id", table_name="estimates")
    op.drop_column("estimates", "blueprint_job_id")
