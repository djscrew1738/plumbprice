"""privacy retention: deleted_at columns + indexes

Revision ID: p1r1v1c0lumns
Revises: af936972d858
Create Date: 2026-04-25 21:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p1r1v1c0lumns"
down_revision: Union[str, None] = "af936972d858"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft-delete + retention bookkeeping for blueprints
    op.add_column(
        "blueprint_jobs",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "blueprint_jobs",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_blueprint_jobs_retention_until",
        "blueprint_jobs",
        ["retention_until"],
    )
    op.create_index(
        "ix_blueprint_jobs_deleted_at",
        "blueprint_jobs",
        ["deleted_at"],
    )

    # Same for uploaded documents
    op.add_column(
        "uploaded_documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "uploaded_documents",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_uploaded_documents_retention_until",
        "uploaded_documents",
        ["retention_until"],
    )
    op.create_index(
        "ix_uploaded_documents_deleted_at",
        "uploaded_documents",
        ["deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_uploaded_documents_deleted_at", table_name="uploaded_documents")
    op.drop_index("ix_uploaded_documents_retention_until", table_name="uploaded_documents")
    op.drop_column("uploaded_documents", "retention_until")
    op.drop_column("uploaded_documents", "deleted_at")

    op.drop_index("ix_blueprint_jobs_deleted_at", table_name="blueprint_jobs")
    op.drop_index("ix_blueprint_jobs_retention_until", table_name="blueprint_jobs")
    op.drop_column("blueprint_jobs", "retention_until")
    op.drop_column("blueprint_jobs", "deleted_at")
