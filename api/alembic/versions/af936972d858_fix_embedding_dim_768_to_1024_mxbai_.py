"""fix embedding dim 768 to 1024 (mxbai-embed-large)

Revision ID: af936972d858
Revises: e4601e7c47d1
Create Date: 2026-04-25 18:59:42.469954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af936972d858'
down_revision: Union[str, None] = 'e4601e7c47d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # mxbai-embed-large emits 1024-dim vectors. The original schema declared
    # 768. The columns currently hold no real data (document_chunks empty,
    # agent_memories just created) so we can drop and re-add cleanly.
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024) USING NULL")
    op.execute("ALTER TABLE agent_memories ALTER COLUMN embedding TYPE vector(1024) USING NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL")
    op.execute("ALTER TABLE agent_memories ALTER COLUMN embedding TYPE vector(768) USING NULL")
