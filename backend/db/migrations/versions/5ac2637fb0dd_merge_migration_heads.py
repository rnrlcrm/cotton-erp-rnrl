"""merge migration heads

Revision ID: 5ac2637fb0dd
Revises: 1ea89afdffb6, 003_seed_capabilities
Create Date: 2025-12-01 15:03:02.242068

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '5ac2637fb0dd'
down_revision = ('1ea89afdffb6', '003_seed_capabilities')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
