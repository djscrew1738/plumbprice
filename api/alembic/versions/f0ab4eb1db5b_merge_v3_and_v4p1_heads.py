"""merge_v3_and_v4p1_heads

Revision ID: f0ab4eb1db5b
Revises: c81ad061b618, v4p1p0_hnsw_index
Create Date: 2026-06-06 09:08:10.137015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0ab4eb1db5b'
down_revision: Union[str, None] = ('c81ad061b618', 'v4p1p0_hnsw_index')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
