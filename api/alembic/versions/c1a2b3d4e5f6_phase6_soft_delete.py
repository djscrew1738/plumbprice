"""phase6: soft-delete columns on users/projects/estimates

Revision ID: c1a2b3d4e5f6
Revises: 07267bc91839
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "07267bc91839"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_users_deleted_at", ["deleted_at"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_projects_deleted_at", ["deleted_at"])

    with op.batch_alter_table("estimates") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_estimates_deleted_at", ["deleted_at"])


def downgrade() -> None:
    with op.batch_alter_table("estimates") as batch:
        batch.drop_index("ix_estimates_deleted_at")
        batch.drop_column("deleted_at")

    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_deleted_at")
        batch.drop_column("deleted_at")

    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_deleted_at")
        batch.drop_column("deleted_at")
