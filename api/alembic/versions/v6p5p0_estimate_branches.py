"""Add branch_id to estimates for versioning & branching.

Revision ID: v6p5p0_estimate_branches
Revises: v6p4p0_estimate_variants
Create Date: 2026-06-10 20:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "v6p5p0_estimate_branches"
down_revision = "v6p4p0_estimate_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("estimates", sa.Column("branch_id", sa.String(36), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("estimates", "branch_id")
