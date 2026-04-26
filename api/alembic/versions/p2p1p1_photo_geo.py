"""photo lat/lng for jobsite GPS

Revision ID: p2p1p1ph0t0g3o
Revises: p2p5sca1ebar1
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


revision = "p2p1p1ph0t0g3o"
down_revision = "p2p5sca1ebar1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("lat", sa.Float(), nullable=True))
    op.add_column("photos", sa.Column("lng", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("photos", "lng")
    op.drop_column("photos", "lat")
