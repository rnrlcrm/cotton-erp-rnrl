"""make_location_id_nullable_for_adhoc_locations

Revision ID: 6827270c0b0b
Revises: 20251129114154
Create Date: 2025-11-29 12:41:47.396415

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '6827270c0b0b'
down_revision = '20251129114154'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Make location_id nullable to support ad-hoc locations.
    
    Ad-hoc locations use Google Maps coordinates directly without
    requiring a registered location in settings_locations table.
    """
    op.alter_column(
        'availabilities',
        'location_id',
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=True,
        existing_nullable=False,
        comment='Registered location ID (NULL for ad-hoc Google Maps locations)'
    )


def downgrade() -> None:
    """Revert location_id to NOT NULL."""
    # Note: This will fail if any availabilities have NULL location_id
    op.alter_column(
        'availabilities',
        'location_id',
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=False,
        existing_nullable=True
    )
