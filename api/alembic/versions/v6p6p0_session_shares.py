"""v6.6.0 — Session sharing

Revision ID: v6p6p0_session_shares
Revises: v6p5p0_estimate_branches
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'v6p6p0_session_shares'
down_revision = 'v6p5p0_estimate_branches'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chat_session_shares',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('permission', sa.String(20), nullable=False, server_default='read'),  # read | comment
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Note: indexes for token and session_id are created automatically by index=True on the columns above.

    # Estimate comments table
    op.create_table(
        'estimate_comments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('estimate_id', sa.Integer(), sa.ForeignKey('estimates.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('estimate_comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Note: index for estimate_id is created automatically by index=True on the column above.


def downgrade() -> None:
    op.drop_table('estimate_comments')
    op.drop_table('chat_session_shares')
