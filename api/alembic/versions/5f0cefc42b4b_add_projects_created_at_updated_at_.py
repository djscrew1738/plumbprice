"""add_projects_created_at_updated_at_indexes

Revision ID: 5f0cefc42b4b
Revises: 71db5c2b547a
Create Date: 2026-04-18 00:43:31.622790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f0cefc42b4b'
down_revision: Union[str, None] = '71db5c2b547a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_projects_created_at'), 'projects', ['created_at'], unique=False)
    op.create_index(op.f('ix_projects_updated_at'), 'projects', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_projects_updated_at'), table_name='projects')
    op.drop_index(op.f('ix_projects_created_at'), table_name='projects')
