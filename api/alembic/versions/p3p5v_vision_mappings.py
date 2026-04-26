"""phase 3.5: vision item mappings table

Revision ID: p3p5v1s10n_map
Revises: p3p5h0t0s001
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p3p5v1s10n_map"
down_revision: Union[str, None] = "p3p5h0t0s001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vision_item_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_type", sa.String(length=80), nullable=False, unique=True),
        sa.Column("default_task_code", sa.String(length=120), nullable=False),
        sa.Column("problem_task_code", sa.String(length=120), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_vision_mappings_item_type", "vision_item_mappings", ["item_type"], unique=True)
    op.create_index("ix_vision_mappings_org", "vision_item_mappings", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_vision_mappings_org", table_name="vision_item_mappings")
    op.drop_index("ix_vision_mappings_item_type", table_name="vision_item_mappings")
    op.drop_table("vision_item_mappings")
