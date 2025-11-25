"""add risk engine critical validations

Revision ID: 20251125_risk_validations
Revises: 20251125_add_availability_risk_fields
Create Date: 2025-11-25

RISK ENGINE - CRITICAL VALIDATIONS
===================================

Implements 4 mandatory risk validation features:

1. DUPLICATE ORDER PREVENTION (Option B: Relaxed)
   - Partial unique indexes excluding CANCELLED/FULFILLED status
   - Allows re-posting if previous order was cancelled
   - Prevents spam and accidental duplicates

2. PARTY LINKS DETECTION (Database Support)
   - Indexes for fast PAN/GST/mobile/bank lookups
   - Business logic in RiskEngine checks cross-party links

3. CIRCULAR TRADING PREVENTION (Database Support)
   - Composite indexes for same-day commodity checking
   - Business logic validates buyer doesn't have SELL open

4. ROLE RESTRICTION ENFORCEMENT (Database Support)
   - Indexes to support partner_type validation
   - Business logic prevents BUYER posting SELL, SELLER posting BUY

All validations enforce your approved options:
- Duplicate: Option B (Allow re-post if cancelled)
- Party Links: Option B (Block PAN/GST, warn mobile/bank)
- Circular: Option A (Same day only)
- Trader: Option A (Allow BUY+SELL, block same-day reversals)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251125_risk_validations'
down_revision = '20251125_add_availability_risk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add critical risk validation constraints and indexes
    """
    
    # ============================================================================
    # 1. DUPLICATE ORDER PREVENTION - REQUIREMENTS
    # ============================================================================
    # Option B: Partial unique index excluding CANCELLED/FULFILLED
    # Allows users to re-post if they cancelled previous requirement
    
    op.execute(
        """
        CREATE UNIQUE INDEX uq_requirements_no_duplicates
        ON requirements (
            buyer_partner_id, 
            commodity_id, 
            COALESCE(preferred_quantity, min_quantity),
            max_budget_per_unit,
            COALESCE(buyer_branch_id::text, 'NULL'),
            DATE(valid_from)
        )
        WHERE status NOT IN ('CANCELLED', 'FULFILLED', 'EXPIRED')
        """
    )
    # Explanation:
    # - COALESCE handles NULL buyer_branch_id (traders without branch)
    # - DATE(valid_from) prevents duplicates on same day
    # - WHERE clause allows re-posting after cancellation (Option B)
    
    # ============================================================================
    # 2. DUPLICATE ORDER PREVENTION - AVAILABILITIES
    # ============================================================================
    # Option B: Partial unique index excluding CANCELLED/SOLD
    
    op.execute(
        """
        CREATE UNIQUE INDEX uq_availabilities_no_duplicates
        ON availabilities (
            seller_id,
            commodity_id,
            total_quantity,
            location_id,
            DATE(created_at)
        )
        WHERE status NOT IN ('CANCELLED', 'SOLD', 'EXPIRED')
        """
    )
    # Explanation:
    # - Prevents seller from posting same commodity/quantity/location on same day
    # - Allows re-posting if previous availability was cancelled/sold (Option B)
    
    # ============================================================================
    # 3. PARTY LINKS DETECTION - FAST LOOKUP INDEXES
    # ============================================================================
    # Supports RiskEngine.check_party_links() for cross-party validation
    
    # PAN number index (for blocking same PAN trades)
    op.execute(
        """
        CREATE INDEX ix_business_partners_pan_lookup
        ON business_partners (pan_number)
        WHERE pan_number IS NOT NULL AND status = 'approved'
        """
    )
    
    # GST number index (for blocking same GST trades)
    op.execute(
        """
        CREATE INDEX ix_business_partners_gst_lookup
        ON business_partners (gst_number)
        WHERE gst_number IS NOT NULL AND status = 'approved'
        """
    )
    
    # Mobile number index (for warning on same mobile)
    op.execute(
        """
        CREATE INDEX ix_business_partners_mobile_lookup
        ON business_partners (primary_contact_phone)
        WHERE primary_contact_phone IS NOT NULL AND status = 'approved'
        """
    )
    
    # ============================================================================
    # 4. CIRCULAR TRADING PREVENTION - COMPOSITE INDEXES
    # ============================================================================
    # Option A: Same-day commodity checking
    # Supports checking if buyer has SELL open or seller has BUY open
    
    # Index for checking buyer's open SELL positions
    op.execute(
        """
        CREATE INDEX ix_availabilities_seller_commodity_date
        ON availabilities (
            seller_id,
            commodity_id,
            DATE(created_at)
        )
        WHERE status IN ('AVAILABLE', 'PARTIALLY_SOLD')
        """
    )
    
    # Index for checking seller's open BUY positions
    op.execute(
        """
        CREATE INDEX ix_requirements_buyer_commodity_date
        ON requirements (
            buyer_partner_id,
            commodity_id,
            DATE(created_at)
        )
        WHERE status IN ('DRAFT', 'ACTIVE', 'PARTIALLY_FULFILLED')
        """
    )
    
    # ============================================================================
    # 5. ROLE RESTRICTION ENFORCEMENT - PARTNER TYPE INDEX
    # ============================================================================
    # Fast lookup for validating partner_type before creating orders
    
    op.execute(
        """
        CREATE INDEX ix_business_partners_type_lookup
        ON business_partners (id, partner_type)
        WHERE status = 'approved'
        """
    )
    
    # ============================================================================
    # 6. RISK ASSESSMENT OPTIMIZATION - COMPOSITE INDEXES
    # ============================================================================
    # Speed up risk assessment queries
    
    # Buyer risk assessment index
    op.execute(
        """
        CREATE INDEX ix_requirements_risk_assessment
        ON requirements (
            buyer_partner_id,
            estimated_trade_value,
            risk_precheck_status,
            status
        )
        WHERE status IN ('DRAFT', 'ACTIVE')
        """
    )
    
    # Seller risk assessment index
    op.execute(
        """
        CREATE INDEX ix_availabilities_risk_assessment
        ON availabilities (
            seller_id,
            estimated_trade_value,
            risk_precheck_status,
            status
        )
        WHERE status IN ('AVAILABLE', 'PARTIALLY_SOLD')
        """
    )
    
    # ============================================================================
    # 7. TRADE MATCHING OPTIMIZATION
    # ============================================================================
    # Speed up matching queries between requirements and availabilities
    
    # Requirements matching index
    op.execute(
        """
        CREATE INDEX ix_requirements_matching
        ON requirements (
            commodity_id,
            status,
            market_visibility,
            intent_type,
            risk_precheck_status
        )
        WHERE status = 'ACTIVE' 
        AND risk_precheck_status IN ('PASS', 'WARN')
        AND valid_until > NOW()
        """
    )
    
    # Availabilities matching index
    op.execute(
        """
        CREATE INDEX ix_availabilities_matching
        ON availabilities (
            commodity_id,
            status,
            market_visibility,
            risk_precheck_status
        )
        WHERE status = 'AVAILABLE'
        AND risk_precheck_status IN ('PASS', 'WARN')
        AND valid_until > NOW()
        """
    )


def downgrade() -> None:
    """
    Remove risk validation constraints and indexes
    """
    
    # Drop all indexes created in upgrade
    op.execute('DROP INDEX IF EXISTS uq_requirements_no_duplicates')
    op.execute('DROP INDEX IF EXISTS uq_availabilities_no_duplicates')
    op.execute('DROP INDEX IF EXISTS ix_business_partners_pan_lookup')
    op.execute('DROP INDEX IF EXISTS ix_business_partners_gst_lookup')
    op.execute('DROP INDEX IF EXISTS ix_business_partners_mobile_lookup')
    op.execute('DROP INDEX IF EXISTS ix_availabilities_seller_commodity_date')
    op.execute('DROP INDEX IF EXISTS ix_requirements_buyer_commodity_date')
    op.execute('DROP INDEX IF EXISTS ix_business_partners_type_lookup')
    op.execute('DROP INDEX IF EXISTS ix_requirements_risk_assessment')
    op.execute('DROP INDEX IF EXISTS ix_availabilities_risk_assessment')
    op.execute('DROP INDEX IF EXISTS ix_requirements_matching')
    op.execute('DROP INDEX IF EXISTS ix_availabilities_matching')
