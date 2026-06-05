"""merge_heads

Revision ID: 52f8ce334bc7
Revises: c4ataaaaaaaa, v3p0p0_ai_overhaul
Create Date: 2026-06-04 23:52:17.437397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52f8ce334bc7'
down_revision: Union[str, None] = ('c4ataaaaaaaa', 'v3p0p0_ai_overhaul')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
