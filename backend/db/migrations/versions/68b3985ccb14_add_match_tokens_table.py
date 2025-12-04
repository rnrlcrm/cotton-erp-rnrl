"""add_match_tokens_table

Revision ID: 68b3985ccb14
Revises: 4d450ec4d324
Create Date: 2025-12-04 06:45:36.557992

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '68b3985ccb14'
down_revision = '4d450ec4d324'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create match_tokens table for anonymous matching."""
    op.create_table(
        'match_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('token', sa.String(32), unique=True, nullable=False, comment='Anonymous token shown to users (e.g., MATCH-A7B2C)'),
        sa.Column('requirement_id', UUID(as_uuid=True), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False, comment='Buyer requirement ID (hidden)'),
        sa.Column('availability_id', UUID(as_uuid=True), sa.ForeignKey('availabilities.id', ondelete='CASCADE'), nullable=False, comment='Seller availability ID (hidden)'),
        sa.Column('match_score', sa.String(10), nullable=False, comment='Match score (0.00-1.00) as string for JSON'),
        sa.Column('disclosed_to_buyer', sa.String(20), nullable=False, server_default='MATCHED', comment='Disclosure level for buyer: MATCHED, NEGOTIATING, TRADE'),
        sa.Column('disclosed_to_seller', sa.String(20), nullable=False, server_default='MATCHED', comment='Disclosure level for seller: MATCHED, NEGOTIATING, TRADE'),
        sa.Column('negotiation_started_at', sa.DateTime, nullable=True, comment='When negotiation began and identities were revealed'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False, comment='Token expires after 30 days if no negotiation'),
    )
    
    # Create indexes
    op.create_index('idx_match_tokens_token', 'match_tokens', ['token'])
    op.create_index('idx_match_tokens_requirement', 'match_tokens', ['requirement_id'])
    op.create_index('idx_match_tokens_availability', 'match_tokens', ['availability_id'])
    op.create_index('idx_match_tokens_expires', 'match_tokens', ['expires_at'])


def downgrade() -> None:
    """Drop match_tokens table."""
    op.drop_index('idx_match_tokens_expires', 'match_tokens')
    op.drop_index('idx_match_tokens_availability', 'match_tokens')
    op.drop_index('idx_match_tokens_requirement', 'match_tokens')
    op.drop_index('idx_match_tokens_token', 'match_tokens')
    op.drop_table('match_tokens')
