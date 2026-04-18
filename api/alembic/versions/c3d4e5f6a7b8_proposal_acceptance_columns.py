"""add proposal acceptance columns (public_token + timestamps + signature + client audit)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("public_token", sa.String(length=64), nullable=True))
    op.add_column("proposals", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("proposals", sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("proposals", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("proposals", sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("proposals", sa.Column("decline_reason", sa.Text(), nullable=True))
    op.add_column("proposals", sa.Column("client_signature", sa.String(length=200), nullable=True))
    op.add_column("proposals", sa.Column("client_ip", sa.String(length=45), nullable=True))
    op.add_column("proposals", sa.Column("client_user_agent", sa.String(length=500), nullable=True))
    op.create_index("ix_proposals_public_token", "proposals", ["public_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_proposals_public_token", table_name="proposals")
    op.drop_column("proposals", "client_user_agent")
    op.drop_column("proposals", "client_ip")
    op.drop_column("proposals", "client_signature")
    op.drop_column("proposals", "decline_reason")
    op.drop_column("proposals", "declined_at")
    op.drop_column("proposals", "accepted_at")
    op.drop_column("proposals", "opened_at")
    op.drop_column("proposals", "token_expires_at")
    op.drop_column("proposals", "public_token")
