"""user invites + organization settings columns

Revision ID: f9c1d2e3a4b5
Revises: e90e208ac55e
Create Date: 2026-05-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c1d2e3a4b5"
down_revision: Union[str, None] = "e90e208ac55e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Organizations new columns ────────────────────────────────────────────
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("billing_email", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("logo_url", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("default_tax_rate", sa.Float(), nullable=True))
        batch.add_column(sa.Column("default_markup_percent", sa.Float(), nullable=True))

    # ── user_invites table ───────────────────────────────────────────────────
    op.create_table(
        "user_invites",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="estimator"),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "invited_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_user_invites_token_hash"),
    )
    op.create_index("ix_user_invites_email", "user_invites", ["email"])
    op.create_index("ix_user_invites_organization_id", "user_invites", ["organization_id"])
    op.create_index("ix_user_invites_token_hash", "user_invites", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_user_invites_token_hash", table_name="user_invites")
    op.drop_index("ix_user_invites_organization_id", table_name="user_invites")
    op.drop_index("ix_user_invites_email", table_name="user_invites")
    op.drop_table("user_invites")

    with op.batch_alter_table("organizations") as batch:
        batch.drop_column("default_markup_percent")
        batch.drop_column("default_tax_rate")
        batch.drop_column("logo_url")
        batch.drop_column("billing_email")
