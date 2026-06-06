"""add adobe oauth tokens

Revision ID: a1b2c3d4e5f6
Revises: f0ab4eb1db5b
Create Date: 2026-06-06

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f0ab4eb1db5b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'adobe_oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token_enc', sa.Text(), nullable=False),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('adobe_email', sa.String(length=255), nullable=True),
        sa.Column('adobe_display_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_adobe_oauth_tokens_user'),
    )
    op.create_index(op.f('ix_adobe_oauth_tokens_id'), 'adobe_oauth_tokens', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_adobe_oauth_tokens_id'), table_name='adobe_oauth_tokens')
    op.drop_table('adobe_oauth_tokens')
