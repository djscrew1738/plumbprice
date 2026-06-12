"""v6_0_0_chat_embeddings

Creates chat_embeddings table for semantic task-code retrieval in the v3
pricing chat. Stores pgvector embeddings of canonical item descriptions so
the classifier can dynamically surface the most relevant task codes.

Revision ID: v6p0p0_chat_embeddings
Revises: v5p8p0_expand_pricing_catalog
Create Date: 2026-06-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

revision: str = "v6p0p0_chat_embeddings"
down_revision: Union[str, Sequence[str], None] = "v5p8p0_expand_pricing_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=1024),
            nullable=True,
        ),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_code"),
    )
    op.create_index(
        op.f("ix_chat_embeddings_task_code"),
        "chat_embeddings",
        ["task_code"],
        unique=False,
    )
    op.create_index(
        "ix_chat_embeddings_embedding_hnsw",
        "chat_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_embeddings_embedding_hnsw",
        table_name="chat_embeddings",
    )
    op.drop_index(
        op.f("ix_chat_embeddings_task_code"),
        table_name="chat_embeddings",
    )
    op.drop_table("chat_embeddings")
