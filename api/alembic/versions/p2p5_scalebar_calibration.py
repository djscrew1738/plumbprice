"""phase 2.5: pixel-scale calibration columns on blueprint_pages

Revision ID: p2p5sca1ebar1
Revises: p3p5v1s10n_map
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


revision = "p2p5sca1ebar1"
down_revision = "p3p5v1s10n_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blueprint_pages", sa.Column("px_per_ft", sa.Float(), nullable=True))
    op.add_column(
        "blueprint_pages",
        sa.Column("scale_calibrated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("blueprint_pages", sa.Column("scale_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("blueprint_pages", "scale_source")
    op.drop_column("blueprint_pages", "scale_calibrated")
    op.drop_column("blueprint_pages", "px_per_ft")
