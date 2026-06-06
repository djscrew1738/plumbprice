"""v4_1_0_hnsw_index_document_chunks

Adds HNSW approximate nearest-neighbour index on document_chunks.embedding
for O(log n) pgvector similarity search.

IMPORTANT: CREATE INDEX CONCURRENTLY cannot run inside a transaction.
Alembic will execute this migration with transaction=False.

Revision ID: v4p1p0_hnsw_index
Revises: v4p1p0_foundation
Create Date: 2026-06-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "v4p1p0_hnsw_index"
down_revision: Union[str, Sequence[str], None] = "v4p1p0_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Run outside transaction — CONCURRENTLY is required to avoid table lock.
    # If the document_chunks table is small or empty this will complete quickly.
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS
            document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS document_chunks_embedding_hnsw")
