"""feature flags table

Revision ID: p4f1f1ag5001
Revises: p3p5v1s10n_map
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p4f1f1ag5001"
down_revision: Union[str, Sequence[str], None] = ("p3p5v1s10n_map", "p2p1p1ph0t0g3o")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed a few flags so the admin UI has something to show.
    op.execute(
        """
        INSERT INTO feature_flags (key, enabled, description) VALUES
          ('public_agent', false, 'Expose the public-facing AI estimator agent at /pa.'),
          ('voice_input', true, 'Voice transcription for estimator notes.'),
          ('blueprint_ocr_v2', false, 'Use the Phase 3 vision pipeline on new blueprint uploads.'),
          ('outbox_offline', false, 'Queue mutations to IndexedDB when offline (a2 rollout).'),
          ('agent_long_term_memory', false, 'Per-customer/per-address long-term memory recall in chat.')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
