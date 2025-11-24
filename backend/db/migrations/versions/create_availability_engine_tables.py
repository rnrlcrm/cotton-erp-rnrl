"""create availability engine tables

Revision ID: create_availability_engine
Revises: (check latest)
Create Date: 2025-11-24 (current date)

AVAILABILITY ENGINE - Phase 1 Database Schema
==============================================

Enhancements:
- geo_index for location-based search
- market_visibility (PUBLIC, PRIVATE, RESTRICTED)
- allow_partial_order (boolean)
- ai_score_vector (JSONB for ML embeddings)
- seller location validation (seller=own location only, trader=any location)

Multi-commodity support: Cotton, Gold, Wheat, Oil, ANY commodity via JSONB
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_availability_engine'
down_revision = None  # Update this to latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create availability engine tables"""
    
    # ============================================================================
    # TABLE: availabilities
    # ============================================================================
    op.create_table(
        'availabilities',
        
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        
        # Foreign Keys
        sa.Column('seller_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('variety_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Quantity (Multi-unit support)
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('quantity_unit', sa.String(20), nullable=False),
        # Examples: bales, kg, tons, grams, barrels, quintals, liters
        
        # Quality Parameters (JSONB - Universal for ALL commodities)
        sa.Column('quality_params', postgresql.JSONB, nullable=False),
        # Cotton: {"staple_length": 29, "micronaire": 4.2, "moisture": 7, "trash": 2}
        # Gold: {"purity": 22, "weight": 100, "hallmark": "BIS", "form": "bar"}
        # Wheat: {"protein": 12.5, "moisture": 12, "test_weight": 78}
        
        # Test Report (Optional)
        sa.Column('test_report_url', sa.String(500), nullable=True),
        sa.Column('test_report_verified', sa.Boolean, default=False, nullable=False),
        
        # Price Matrix (JSONB - Multiple pricing options)
        sa.Column('price_options', postgresql.JSONB, nullable=False),
        # Example: {
        #   "cash_ex_gin": 59500,
        #   "15_days_ex_gin": 60500,
        #   "30_days_ex_gin": 61500,
        #   "cash_delivered_50km": 60700,
        #   "15_days_delivered_50km": 61700
        # }
        
        # Terms (Multiple options allowed)
        sa.Column('payment_term_options', postgresql.JSONB, nullable=False),
        # Array of payment_term UUIDs: ["uuid1", "uuid2", "uuid3"]
        
        sa.Column('delivery_term_options', postgresql.JSONB, nullable=False),
        # Array of delivery_term UUIDs: ["uuid1", "uuid2"]
        
        sa.Column('passing_term_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('weightment_term_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Delivery Coordinates (NEW - for distance calculation)
        sa.Column('delivery_latitude', sa.Float, nullable=True),
        sa.Column('delivery_longitude', sa.Float, nullable=True),
        
        # Availability Status
        sa.Column('status', sa.String(20), nullable=False, server_default='AVAILABLE'),
        # AVAILABLE, PARTIALLY_SOLD, SOLD, EXPIRED, CANCELLED
        
        # Quantity Tracking
        sa.Column('total_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('available_quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('reserved_quantity', sa.Numeric(15, 3), default=0, nullable=False),
        sa.Column('sold_quantity', sa.Numeric(15, 3), default=0, nullable=False),
        
        # NEW: Allow Partial Orders
        sa.Column('allow_partial_order', sa.Boolean, default=True, nullable=False),
        # If True: buyer can buy 100 out of 500 bales
        # If False: buyer must buy entire 500 bales
        
        sa.Column('min_order_quantity', sa.Numeric(15, 3), nullable=True),
        # Minimum quantity buyer must purchase (e.g., min 50 bales)
        
        # NEW: Market Visibility
        sa.Column('market_visibility', sa.String(20), nullable=False, server_default='PUBLIC'),
        # PUBLIC: Visible to all
        # PRIVATE: Only visible to seller's network
        # RESTRICTED: Only visible to invited buyers
        # INTERNAL: Only within seller's organization
        
        sa.Column('visibility_rules', postgresql.JSONB, nullable=True),
        # Example: {"allowed_partner_ids": ["uuid1", "uuid2"], "allowed_regions": ["WEST"]}
        
        # Validity
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        
        # AI Fields
        sa.Column('ai_suggested_price', sa.Numeric(15, 2), nullable=True),
        # AI-calculated fair market price
        
        sa.Column('ai_confidence_score', sa.Numeric(5, 2), nullable=True),
        # How confident AI is in price suggestion (0-100)
        
        # NEW: AI Score Vector (for ML embeddings)
        sa.Column('ai_score_vector', postgresql.JSONB, nullable=True),
        # Example: {
        #   "commodity_embedding": [0.23, 0.45, 0.67, ...],  # 512-dim vector
        #   "quality_score": 85.5,
        #   "price_competitiveness": 92.3,
        #   "seller_reliability": 88.7,
        #   "negotiation_readiness": 75.2,
        #   "demand_prediction": 82.1
        # }
        
        sa.Column('ai_price_anomaly_flag', sa.Boolean, default=False, nullable=False),
        # True if AI detects unrealistic price
        
        sa.Column('ai_anomaly_reason', sa.Text, nullable=True),
        # Why AI flagged this as anomaly
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        # Flexible field for additional data
        
        # Audit Fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('NOW()'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['seller_partner_id'], ['business_partners.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['variety_id'], ['commodity_varieties.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['settings_locations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['passing_term_id'], ['passing_terms.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['weightment_term_id'], ['weightment_terms.id'], ondelete='RESTRICT'),
    )
    
    # ============================================================================
    # INDEXES
    # ============================================================================
    
    # Core indexes
    op.create_index('ix_availabilities_seller_partner_id', 'availabilities', ['seller_partner_id'])
    op.create_index('ix_availabilities_commodity_id', 'availabilities', ['commodity_id'])
    op.create_index('ix_availabilities_location_id', 'availabilities', ['location_id'])
    op.create_index('ix_availabilities_status', 'availabilities', ['status'])
    op.create_index('ix_availabilities_market_visibility', 'availabilities', ['market_visibility'])
    
    # Time-based indexes
    op.create_index('ix_availabilities_valid_until', 'availabilities', ['valid_until'])
    op.create_index('ix_availabilities_created_at', 'availabilities', ['created_at'])
    
    # Composite indexes for common queries
    op.create_index(
        'ix_availabilities_commodity_status',
        'availabilities',
        ['commodity_id', 'status']
    )
    
    op.create_index(
        'ix_availabilities_commodity_visibility',
        'availabilities',
        ['commodity_id', 'market_visibility']
    )
    
    # NEW: Geo-spatial index for location-based search
    # This enables fast proximity searches
    op.create_index(
        'ix_availabilities_geo_location',
        'availabilities',
        ['location_id', 'delivery_latitude', 'delivery_longitude']
    )
    
    # JSONB GIN indexes for fast JSONB queries
    op.execute(
        'CREATE INDEX ix_availabilities_quality_params_gin ON availabilities USING GIN (quality_params)'
    )
    op.execute(
        'CREATE INDEX ix_availabilities_price_options_gin ON availabilities USING GIN (price_options)'
    )
    op.execute(
        'CREATE INDEX ix_availabilities_ai_score_vector_gin ON availabilities USING GIN (ai_score_vector)'
    )
    
    # Partial index for active availabilities (most queried)
    op.execute(
        """
        CREATE INDEX ix_availabilities_active 
        ON availabilities (commodity_id, location_id, available_quantity)
        WHERE status = 'AVAILABLE' AND valid_until > NOW()
        """
    )
    
    # ============================================================================
    # TRIGGERS (for auto-updating available_quantity)
    # ============================================================================
    
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_availability_quantities()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Auto-calculate available_quantity
            NEW.available_quantity := NEW.total_quantity - NEW.reserved_quantity - NEW.sold_quantity;
            
            -- Auto-update status based on quantities
            IF NEW.available_quantity <= 0 THEN
                NEW.status := 'SOLD';
            ELSIF NEW.available_quantity < NEW.total_quantity THEN
                NEW.status := 'PARTIALLY_SOLD';
            ELSE
                NEW.status := 'AVAILABLE';
            END IF;
            
            -- Check expiry
            IF NEW.valid_until < NOW() THEN
                NEW.status := 'EXPIRED';
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    
    op.execute(
        """
        CREATE TRIGGER trigger_update_availability_quantities
        BEFORE INSERT OR UPDATE ON availabilities
        FOR EACH ROW
        EXECUTE FUNCTION update_availability_quantities();
        """
    )
    
    # ============================================================================
    # VALIDATION CONSTRAINTS
    # ============================================================================
    
    # Ensure quantities are logical
    op.execute(
        """
        ALTER TABLE availabilities
        ADD CONSTRAINT check_quantity_logic
        CHECK (
            total_quantity > 0 AND
            reserved_quantity >= 0 AND
            sold_quantity >= 0 AND
            (reserved_quantity + sold_quantity) <= total_quantity
        )
        """
    )
    
    # Ensure valid_from < valid_until
    op.execute(
        """
        ALTER TABLE availabilities
        ADD CONSTRAINT check_validity_dates
        CHECK (valid_from < valid_until)
        """
    )
    
    # Ensure market_visibility is valid
    op.execute(
        """
        ALTER TABLE availabilities
        ADD CONSTRAINT check_market_visibility
        CHECK (market_visibility IN ('PUBLIC', 'PRIVATE', 'RESTRICTED', 'INTERNAL'))
        """
    )
    
    # Ensure status is valid
    op.execute(
        """
        ALTER TABLE availabilities
        ADD CONSTRAINT check_status
        CHECK (status IN ('AVAILABLE', 'PARTIALLY_SOLD', 'SOLD', 'EXPIRED', 'CANCELLED'))
        """
    )
    
    # ============================================================================
    # COMMENTS (for documentation)
    # ============================================================================
    
    op.execute(
        """
        COMMENT ON TABLE availabilities IS 
        'Seller inventory available for sale. Universal model for ALL commodities (Cotton, Gold, Wheat, Oil, etc.)';
        """
    )
    
    op.execute(
        """
        COMMENT ON COLUMN availabilities.quality_params IS 
        'JSONB field storing quality parameters. Structure varies by commodity type. AI normalizes for comparison.';
        """
    )
    
    op.execute(
        """
        COMMENT ON COLUMN availabilities.price_options IS 
        'Matrix of prices for different payment/delivery combinations. Enables flexible pricing strategies.';
        """
    )
    
    op.execute(
        """
        COMMENT ON COLUMN availabilities.ai_score_vector IS 
        'ML embeddings and AI scores for intelligent matching. Used by matching engine for compatibility scoring.';
        """
    )
    
    op.execute(
        """
        COMMENT ON COLUMN availabilities.market_visibility IS 
        'Controls who can see this availability: PUBLIC (all), PRIVATE (network), RESTRICTED (invited), INTERNAL (own org)';
        """
    )
    
    op.execute(
        """
        COMMENT ON COLUMN availabilities.allow_partial_order IS 
        'If true, buyers can purchase partial quantity. If false, must buy entire lot.';
        """
    )


def downgrade() -> None:
    """Drop availability engine tables"""
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS trigger_update_availability_quantities ON availabilities')
    op.execute('DROP FUNCTION IF EXISTS update_availability_quantities()')
    
    # Drop indexes (automatically dropped with table, but explicit for clarity)
    op.drop_index('ix_availabilities_active', 'availabilities')
    op.drop_index('ix_availabilities_ai_score_vector_gin', 'availabilities')
    op.drop_index('ix_availabilities_price_options_gin', 'availabilities')
    op.drop_index('ix_availabilities_quality_params_gin', 'availabilities')
    op.drop_index('ix_availabilities_geo_location', 'availabilities')
    op.drop_index('ix_availabilities_commodity_visibility', 'availabilities')
    op.drop_index('ix_availabilities_commodity_status', 'availabilities')
    op.drop_index('ix_availabilities_created_at', 'availabilities')
    op.drop_index('ix_availabilities_valid_until', 'availabilities')
    op.drop_index('ix_availabilities_market_visibility', 'availabilities')
    op.drop_index('ix_availabilities_status', 'availabilities')
    op.drop_index('ix_availabilities_location_id', 'availabilities')
    op.drop_index('ix_availabilities_commodity_id', 'availabilities')
    op.drop_index('ix_availabilities_seller_partner_id', 'availabilities')
    
    # Drop table
    op.drop_table('availabilities')
