"""Add variant_group_id and variant_label to estimates.

Revision ID: v6p4p0_estimate_variants
Revises: v6p3p0_blueprint_fixtures
Create Date: 2026-06-10 18:15:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "v6p4p0_estimate_variants"
down_revision = "v6p3p0_blueprint_fixtures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("estimates", sa.Column("variant_group_id", sa.String(36), nullable=True, index=True))
    op.add_column("estimates", sa.Column("variant_label", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("estimates", "variant_label")
    op.drop_column("estimates", "variant_group_id")
