"""v6.7.0 — Prompt templates

Revision ID: v6p7p0_prompt_templates
Revises: v6p6p0_session_shares
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'v6p7p0_prompt_templates'
down_revision = 'v6p6p0_session_shares'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('is_personal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('prompt_templates')
