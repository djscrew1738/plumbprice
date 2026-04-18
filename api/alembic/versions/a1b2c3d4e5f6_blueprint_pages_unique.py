"""add unique constraint on blueprint_pages (job_id, page_number)

Revision ID: a1b2c3d4e5f6
Revises: 5f0cefc42b4b
Create Date: 2026-04-18 19:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5f0cefc42b4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Best-effort dedup before adding the constraint, in case the worker has
    # produced duplicate rows in any existing environments.
    op.execute(
        """
        DELETE FROM blueprint_pages
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY job_id, page_number ORDER BY id) AS rn
                FROM blueprint_pages
            ) t
            WHERE t.rn > 1
        );
        """
    )
    op.create_unique_constraint(
        "uq_blueprint_pages_job_page",
        "blueprint_pages",
        ["job_id", "page_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_blueprint_pages_job_page",
        "blueprint_pages",
        type_="unique",
    )
