"""add_match_outcomes_table

Track match outcomes for ML model training.

Revision ID: 7a8b9c0d1e2f
Revises: 535888366798
Create Date: 2025-12-04

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '7a8b9c0d1e2f'
down_revision = '535888366798'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create match_outcomes table."""
    
    op.create_table(
        'match_outcomes',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('requirement_id', UUID(), nullable=False),
        sa.Column('availability_id', UUID(), nullable=False),
        sa.Column('trade_id', UUID(), nullable=True),
        
        # Match scoring features
        sa.Column('match_score', sa.Numeric(5, 4), nullable=False, comment='Overall match score (0.0-1.0)'),
        sa.Column('quality_score', sa.Numeric(5, 4), nullable=False, comment='Quality compatibility score (0.0-1.0)'),
        sa.Column('price_score', sa.Numeric(5, 4), nullable=False, comment='Price competitiveness score (0.0-1.0)'),
        sa.Column('delivery_score', sa.Numeric(5, 4), nullable=False, comment='Delivery logistics score (0.0-1.0)'),
        sa.Column('risk_score', sa.Numeric(5, 4), nullable=False, comment='Risk assessment score (0.0-1.0)'),
        
        # Additional features
        sa.Column('distance_km', sa.Numeric(10, 2), nullable=True, comment='Distance between buyer and seller'),
        sa.Column('price_difference_pct', sa.Numeric(6, 2), nullable=True, comment='Price difference percentage'),
        
        # Negotiation tracking
        sa.Column('negotiation_started', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('negotiation_rounds', sa.Integer(), nullable=True, comment='Number of negotiation rounds'),
        sa.Column('final_price', sa.Numeric(15, 2), nullable=True, comment='Final negotiated price per unit'),
        
        # Outcome tracking
        sa.Column('trade_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quality_accepted', sa.Boolean(), nullable=True, comment='Quality accepted on delivery'),
        sa.Column('payment_on_time', sa.Boolean(), nullable=True, comment='Payment made on time'),
        sa.Column('delivery_on_time', sa.Boolean(), nullable=True, comment='Delivery made on time'),
        
        # Satisfaction ratings
        sa.Column('buyer_satisfaction', sa.Integer(), nullable=True, comment='Buyer rating (1-5)'),
        sa.Column('seller_satisfaction', sa.Integer(), nullable=True, comment='Seller rating (1-5)'),
        
        # Additional features (JSONB for flexibility)
        sa.Column('additional_features', JSONB, nullable=True, comment='Additional ML features'),
        
        # Failure tracking
        sa.Column('failure_reason', sa.String(500), nullable=True, comment='Reason for failure'),
        
        # Timestamps
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['availability_id'], ['availabilities.id'], ondelete='CASCADE'),
        # NOTE: trade_id FK will be added when trades table is created (Trade Engine - Phase 5)
    )
    
    # Indexes for efficient querying
    op.create_index('ix_match_outcomes_requirement_id', 'match_outcomes', ['requirement_id'])
    op.create_index('ix_match_outcomes_availability_id', 'match_outcomes', ['availability_id'])
    op.create_index('ix_match_outcomes_trade_id', 'match_outcomes', ['trade_id'])
    op.create_index('ix_match_outcomes_matched_at', 'match_outcomes', ['matched_at'])
    op.create_index('ix_match_outcomes_trade_completed', 'match_outcomes', ['trade_completed'])


def downgrade() -> None:
    """Drop match_outcomes table."""
    op.drop_table('match_outcomes')
