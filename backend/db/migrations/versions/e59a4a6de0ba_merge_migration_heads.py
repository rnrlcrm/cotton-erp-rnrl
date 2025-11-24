"""Merge migration heads

Revision ID: e59a4a6de0ba
Revises: 20251123_072109_gdpr, 9a8b7c6d5e4f, add_mobile_otp_fields
Create Date: 2025-11-24 06:16:12.021236

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'e59a4a6de0ba'
down_revision = ('20251123_072109_gdpr', '9a8b7c6d5e4f', 'add_mobile_otp_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
