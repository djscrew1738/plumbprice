"""user profile: phone and avatar_url columns

Revision ID: a0b1c2d3e4f5
Revises: f9c1d2e3a4b5
Create Date: 2026-04-19 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'f9c1d2e3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'phone')
