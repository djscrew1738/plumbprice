"""merge_p6_a

Revision ID: 07267bc91839
Revises: a9b8c7d6e5f4, f9c1d2e3a4b5
Create Date: 2026-04-18 22:56:07.529415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07267bc91839'
down_revision: Union[str, None] = ('a9b8c7d6e5f4', 'f9c1d2e3a4b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
