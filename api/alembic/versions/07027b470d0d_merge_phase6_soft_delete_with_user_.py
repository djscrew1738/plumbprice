"""merge phase6 soft delete with user phone/avatar heads

Revision ID: 07027b470d0d
Revises: a0b1c2d3e4f5, c1a2b3d4e5f6
Create Date: 2026-04-25 18:53:02.944909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07027b470d0d'
down_revision: Union[str, None] = ('a0b1c2d3e4f5', 'c1a2b3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
