"""Add blueprint_fixtures to chat_sessions.

Revision ID: v6p3p0_blueprint_fixtures
Revises: v6p2p0_feedback_pricing_corrections
Create Date: 2026-06-10 17:45:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "v6p3p0_blueprint_fixtures"
down_revision = "v6p2p0_feedback_pricing_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("blueprint_fixtures", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "blueprint_fixtures")
