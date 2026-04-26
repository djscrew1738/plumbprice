"""phase 3.5: photos table

Revision ID: p3p5h0t0s001
Revises: p2b1ueprint01
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p3p5h0t0s001"
down_revision: Union[str, None] = "p2b1ueprint01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("urgency", sa.String(length=40), nullable=True),
        sa.Column("access", sa.String(length=40), nullable=True),
        sa.Column("vision", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("quote", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_photos_project_id", "photos", ["project_id"])
    op.create_index("ix_photos_estimate_id", "photos", ["estimate_id"])
    op.create_index("ix_photos_uploaded_by", "photos", ["uploaded_by"])
    op.create_index("ix_photos_organization_id", "photos", ["organization_id"])
    op.create_index("ix_photos_created_at", "photos", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_photos_created_at", table_name="photos")
    op.drop_index("ix_photos_organization_id", table_name="photos")
    op.drop_index("ix_photos_uploaded_by", table_name="photos")
    op.drop_index("ix_photos_estimate_id", table_name="photos")
    op.drop_index("ix_photos_project_id", table_name="photos")
    op.drop_table("photos")
