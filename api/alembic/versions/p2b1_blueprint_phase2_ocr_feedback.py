"""phase 2: blueprint OCR + detection feedback

Revision ID: p2b1ueprint01
Revises: p1r1v1c0lumns
Create Date: 2026-04-25 21:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2b1ueprint01"
down_revision: Union[str, None] = "p1r1v1c0lumns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-page OCR text + detected scale notation
    op.add_column("blueprint_pages", sa.Column("ocr_text", sa.Text(), nullable=True))
    op.add_column("blueprint_pages", sa.Column("scale_text", sa.String(length=100), nullable=True))

    # Low-confidence flagging on detections
    op.add_column(
        "blueprint_detections",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_blueprint_detections_needs_review",
        "blueprint_detections",
        ["needs_review"],
    )

    # Detection feedback table (user corrections)
    op.create_table(
        "blueprint_detection_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("detection_id", sa.Integer(),
                  sa.ForeignKey("blueprint_detections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column("corrected_fixture_type", sa.String(length=100), nullable=True),
        sa.Column("corrected_count", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_blueprint_detection_feedback_detection_id",
        "blueprint_detection_feedback",
        ["detection_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_blueprint_detection_feedback_detection_id",
                  table_name="blueprint_detection_feedback")
    op.drop_table("blueprint_detection_feedback")
    op.drop_index("ix_blueprint_detections_needs_review",
                  table_name="blueprint_detections")
    op.drop_column("blueprint_detections", "needs_review")
    op.drop_column("blueprint_pages", "scale_text")
    op.drop_column("blueprint_pages", "ocr_text")
