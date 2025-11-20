"""merge organization and refresh_token branches

Revision ID: ebf8bb791693
Revises: 20251120_1400, 4295209465ab
Create Date: 2025-11-20 13:35:07.014414

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'ebf8bb791693'
down_revision = ('20251120_1400', '4295209465ab')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
