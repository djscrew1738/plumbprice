"""v4_1_1_add_blueprint_celery_task_id

Adds:
 - celery_task_id to blueprint_jobs (track Celery task ownership)
 - needs_review to blueprint_pipe_runs (flag for AI-low-confidence runs)

Revision ID: v4p1p1_blueprint_additions
Revises: f0ab4eb1db5b
Create Date: 2026-06-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v4p1p1_blueprint_additions"
down_revision: Union[str, Sequence[str], None] = "cb538ce3e4f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "blueprint_jobs",
        sa.Column("celery_task_id", sa.String(255), nullable=True, index=True),
    )
    op.add_column(
        "blueprint_pipe_runs",
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_column("blueprint_pipe_runs", "needs_review")
    op.drop_column("blueprint_jobs", "celery_task_id")
