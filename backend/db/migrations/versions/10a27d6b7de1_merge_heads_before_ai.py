"""merge_heads_before_ai

Revision ID: 10a27d6b7de1
Revises: 2025_12_01_eod_tz, add_module_schemas
Create Date: 2025-12-03 07:00:48.590979

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '10a27d6b7de1'
down_revision = ('2025_12_01_eod_tz', 'add_module_schemas')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
