"""add composite index on estimate_line_items (estimate_id, sort_order)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-18 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_line_items_estimate_sort_order",
        "estimate_line_items",
        ["estimate_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_line_items_estimate_sort_order",
        table_name="estimate_line_items",
    )
