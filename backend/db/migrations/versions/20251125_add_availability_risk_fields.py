"""add availability risk management fields

Revision ID: 20251125_add_availability_risk
Revises: create_availability_engine
Create Date: 2025-11-25

AVAILABILITY ENGINE - Risk Management Enhancement
==================================================

Adding 10 risk management fields to align with Requirement Engine:

1. expected_price - Seller's expected price for quick matching
2. estimated_trade_value - Auto-calculated trade value
3. risk_precheck_status - Risk assessment status (PASS/WARN/FAIL)
4. risk_precheck_score - Risk score 0-100
5. seller_exposure_after_trade - Seller's exposure calculation
6. seller_branch_id - For internal trade blocking
7. blocked_for_branches - Block availability from certain branches
8. seller_rating_score - Seller reputation score
9. seller_delivery_score - Delivery performance score
10. risk_flags - JSONB for risk-related metadata

These fields enable:
- Symmetric risk management (buyer + seller)
- Internal trade blocking logic
- Seller reputation scoring
- Trade value estimation
- Risk-based matching/filtering
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251125_add_availability_risk'
down_revision = 'create_availability_engine'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add risk management fields to availabilities table"""
    
    # 1. Expected Price (for quick price matching)
    op.add_column(
        'availabilities',
        sa.Column('expected_price', sa.Numeric(15, 2), nullable=True)
    )
    
    # 2. Estimated Trade Value (auto-calculated)
    op.add_column(
        'availabilities',
        sa.Column('estimated_trade_value', sa.Numeric(18, 2), nullable=True)
    )
    
    # 3. Risk Precheck Status (PASS, WARN, FAIL)
    op.add_column(
        'availabilities',
        sa.Column(
            'risk_precheck_status',
            sa.String(20),
            nullable=True
        )
    )
    
    # 4. Risk Precheck Score (0-100)
    op.add_column(
        'availabilities',
        sa.Column(
            'risk_precheck_score',
            sa.Integer,
            nullable=True
        )
    )
    
    # 5. Seller Exposure After Trade
    op.add_column(
        'availabilities',
        sa.Column('seller_exposure_after_trade', sa.Numeric(18, 2), nullable=True)
    )
    
    # 6. Seller Branch ID (for internal trade blocking)
    op.add_column(
        'availabilities',
        sa.Column(
            'seller_branch_id',
            postgresql.UUID(as_uuid=True),
            nullable=True
        )
    )
    
    # 7. Blocked for Branches (prevent internal trades)
    op.add_column(
        'availabilities',
        sa.Column(
            'blocked_for_branches',
            sa.Boolean,
            nullable=False,
            server_default='false'
        )
    )
    
    # 8. Seller Rating Score (0.00 - 5.00)
    op.add_column(
        'availabilities',
        sa.Column(
            'seller_rating_score',
            sa.Numeric(3, 2),
            nullable=True
        )
    )
    
    # 9. Seller Delivery Score (0-100)
    op.add_column(
        'availabilities',
        sa.Column(
            'seller_delivery_score',
            sa.Integer,
            nullable=True
        )
    )
    
    # 10. Risk Flags (JSONB for risk metadata)
    op.add_column(
        'availabilities',
        sa.Column('risk_flags', postgresql.JSONB, nullable=True)
    )
    
    # ============================================================================
    # INDEXES
    # ============================================================================
    
    # Index for risk status filtering
    op.create_index(
        'ix_availabilities_risk_precheck_status',
        'availabilities',
        ['risk_precheck_status']
    )
    
    # Index for seller branch (internal trade blocking)
    op.create_index(
        'ix_availabilities_seller_branch_id',
        'availabilities',
        ['seller_branch_id']
    )
    
    # Index for blocked_for_branches filtering
    op.create_index(
        'ix_availabilities_blocked_for_branches',
        'availabilities',
        ['blocked_for_branches']
    )
    
    # Composite index for risk-based queries
    op.create_index(
        'ix_availabilities_risk_composite',
        'availabilities',
        ['risk_precheck_status', 'seller_rating_score', 'seller_delivery_score']
    )
    
    # GIN index for risk_flags JSONB
    op.execute(
        'CREATE INDEX ix_availabilities_risk_flags_gin ON availabilities USING GIN (risk_flags)'
    )
    
    # ============================================================================
    # CONSTRAINTS
    # ============================================================================
    
    # Risk precheck status must be valid
    op.create_check_constraint(
        'check_risk_precheck_status_valid',
        'availabilities',
        "risk_precheck_status IS NULL OR risk_precheck_status IN ('PASS', 'WARN', 'FAIL')"
    )
    
    # Risk score must be 0-100
    op.create_check_constraint(
        'check_risk_precheck_score_range',
        'availabilities',
        'risk_precheck_score IS NULL OR (risk_precheck_score >= 0 AND risk_precheck_score <= 100)'
    )
    
    # Seller rating must be 0.00-5.00
    op.create_check_constraint(
        'check_seller_rating_score_range',
        'availabilities',
        'seller_rating_score IS NULL OR (seller_rating_score >= 0 AND seller_rating_score <= 5)'
    )
    
    # Seller delivery score must be 0-100
    op.create_check_constraint(
        'check_seller_delivery_score_range',
        'availabilities',
        'seller_delivery_score IS NULL OR (seller_delivery_score >= 0 AND seller_delivery_score <= 100)'
    )
    
    # Expected price must be positive
    op.create_check_constraint(
        'check_expected_price_positive',
        'availabilities',
        'expected_price IS NULL OR expected_price > 0'
    )
    
    # Foreign key for seller_branch_id - commented out since branches table doesn't exist yet
    # op.create_foreign_key(
    #     'fk_availabilities_seller_branch_id',
    #     'availabilities',
    #     'branches',
    #     ['seller_branch_id'],
    #     ['id'],
    #     ondelete='SET NULL'
    # )

def downgrade() -> None:
    """Remove risk management fields from availabilities table"""
    
    # Drop foreign key
    op.drop_constraint('fk_availabilities_seller_branch_id', 'availabilities', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_availabilities_risk_flags_gin', 'availabilities')
    op.drop_index('ix_availabilities_risk_composite', 'availabilities')
    op.drop_index('ix_availabilities_blocked_for_branches', 'availabilities')
    op.drop_index('ix_availabilities_seller_branch_id', 'availabilities')
    op.drop_index('ix_availabilities_risk_precheck_status', 'availabilities')
    
    # Drop constraints
    op.drop_constraint('check_expected_price_positive', 'availabilities', type_='check')
    op.drop_constraint('check_seller_delivery_score_range', 'availabilities', type_='check')
    op.drop_constraint('check_seller_rating_score_range', 'availabilities', type_='check')
    op.drop_constraint('check_risk_precheck_score_range', 'availabilities', type_='check')
    op.drop_constraint('check_risk_precheck_status_valid', 'availabilities', type_='check')
    
    # Drop columns
    op.drop_column('availabilities', 'risk_flags')
    op.drop_column('availabilities', 'seller_delivery_score')
    op.drop_column('availabilities', 'seller_rating_score')
    op.drop_column('availabilities', 'blocked_for_branches')
    op.drop_column('availabilities', 'seller_branch_id')
    op.drop_column('availabilities', 'seller_exposure_after_trade')
    op.drop_column('availabilities', 'risk_precheck_score')
    op.drop_column('availabilities', 'risk_precheck_status')
    op.drop_column('availabilities', 'estimated_trade_value')
    op.drop_column('availabilities', 'expected_price')
