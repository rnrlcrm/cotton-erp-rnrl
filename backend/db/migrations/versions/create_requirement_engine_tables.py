"""create requirement engine tables

Revision ID: create_requirement_engine
Revises: create_availability_engine
Create Date: 2025-11-24 (current date)

REQUIREMENT ENGINE - Phase 1 Database Schema (2035-READY)
==========================================================

7 CRITICAL ENHANCEMENTS for Autonomous AI:
1. Intent Layer: intent_type (DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY)
2. AI Market Context Embedding: market_context_embedding VECTOR(1536)
3. Dynamic Delivery Flexibility: delivery_window_start/end, delivery_flexibility_hours
4. Multi-Commodity Conversion: commodity_equivalents JSONB
5. Negotiation Preferences: negotiation_preferences JSONB
6. Buyer Trust Score: buyer_priority_score FLOAT
7. AI Adjustment Event: Supports requirement.ai_adjusted event

Multi-commodity support: Cotton, Gold, Wheat, Oil, ANY commodity via JSONB
Vector similarity search: pgvector extension for semantic matching
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_requirement_engine'
down_revision = 'create_availability_engine'  # Update to actual latest
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create requirement engine tables with 2035 enhancements"""
    
    # ============================================================================
    # ENABLE PGVECTOR EXTENSION (for market_context_embedding)
    # ============================================================================
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')  # Commented out - install pgvector separately if needed
    
    # ============================================================================
    # TABLE: requirements
    # ============================================================================
    op.create_table(
        'requirements',
        
        # ========================================================================
        # PRIMARY KEY & CORE IDENTIFICATION
        # ========================================================================
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('requirement_number', sa.String(50), unique=True, nullable=False,
                  comment='Unique requirement number: REQ-2025-000001'),
        
        # ========================================================================
        # FOREIGN KEYS
        # ========================================================================
        sa.Column('buyer_partner_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Buyer posting the requirement'),
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Required commodity'),
        sa.Column('variety_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Specific variety (optional)'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='User who created requirement'),
        
        # ========================================================================
        # QUANTITY REQUIREMENTS (Min/Max Ranges for Flexibility)
        # ========================================================================
        sa.Column('min_quantity', sa.Numeric(15, 3), nullable=False,
                  comment='Minimum acceptable quantity'),
        sa.Column('max_quantity', sa.Numeric(15, 3), nullable=False,
                  comment='Maximum desired quantity'),
        sa.Column('quantity_unit', sa.String(20), nullable=False,
                  comment='Unit: bales, kg, MT, grams, etc.'),
        sa.Column('preferred_quantity', sa.Numeric(15, 3), nullable=True,
                  comment='Ideal/target quantity'),
        
        # ========================================================================
        # QUALITY REQUIREMENTS (JSONB - Flexible Tolerances)
        # ========================================================================
        sa.Column('quality_requirements', postgresql.JSONB, nullable=False,
                  comment='Quality params with min/max/preferred/exact/accepted/required'),
        # Example: {"staple_length": {"min": 28, "max": 30, "preferred": 29}, 
        #           "micronaire": {"min": 3.8, "max": 4.5}}
        
        # ========================================================================
        # BUDGET & PRICING
        # ========================================================================
        sa.Column('max_budget_per_unit', sa.Numeric(15, 2), nullable=False,
                  comment='Maximum price buyer willing to pay per unit'),
        sa.Column('preferred_price_per_unit', sa.Numeric(15, 2), nullable=True,
                  comment='Target/desired price per unit'),
        sa.Column('total_budget', sa.Numeric(18, 2), nullable=True,
                  comment='Overall budget limit for entire purchase'),
        sa.Column('currency_code', sa.String(3), nullable=False, server_default='INR',
                  comment='Currency code (ISO 4217)'),
        
        # ========================================================================
        # 🚀 RISK MANAGEMENT & CREDIT CONTROL
        # ========================================================================
        sa.Column('estimated_trade_value', sa.Numeric(18, 2), nullable=True,
                  comment='Auto-calculated estimated trade value (preferred_quantity * max_budget_per_unit)'),
        sa.Column('buyer_credit_limit_remaining', sa.Numeric(18, 2), nullable=True,
                  comment='Remaining credit limit for this buyer from credit module'),
        sa.Column('buyer_exposure_after_trade', sa.Numeric(18, 2), nullable=True,
                  comment='Projected buyer exposure if this trade executes'),
        sa.Column('risk_precheck_status', sa.String(20), nullable=True,
                  comment='PASS, WARN, FAIL - Risk assessment status'),
        sa.Column('risk_precheck_score', sa.Integer, nullable=True,
                  comment='Numeric risk score (0-100, higher is better)'),
        sa.Column('buyer_branch_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Buyer branch ID for internal trade blocking logic'),
        sa.Column('blocked_internal_trades', sa.Boolean, nullable=False, server_default='true',
                  comment='If true, blocks matching with same branch sellers'),
        sa.Column('buyer_rating_score', sa.Numeric(3, 2), nullable=True,
                  comment='Buyer rating score (0.00-5.00) from rating module'),
        sa.Column('buyer_payment_performance_score', sa.Integer, nullable=True,
                  comment='Payment performance score (0-100) based on history'),
        
        # ========================================================================
        # PAYMENT & DELIVERY PREFERENCES
        # ========================================================================
        sa.Column('preferred_payment_terms', postgresql.JSONB, nullable=True,
                  comment='Array of acceptable payment term IDs'),
        # Example: ["cash-uuid", "15day-uuid", "30day-uuid"]
        
        sa.Column('preferred_delivery_terms', postgresql.JSONB, nullable=True,
                  comment='Array of acceptable delivery term IDs'),
        # Example: ["ex-gin-uuid", "delivered-uuid"]
        
        sa.Column('delivery_locations', postgresql.JSONB, nullable=True,
                  comment='Multiple acceptable delivery locations with proximity'),
        # Example: [{"location_id": "uuid", "latitude": 21.1, "longitude": 79.0, "max_distance_km": 50}]
        
        # ========================================================================
        # 🚀 ENHANCEMENT #3: DYNAMIC DELIVERY FLEXIBILITY WINDOW
        # ========================================================================
        sa.Column('delivery_window_start', sa.TIMESTAMP(timezone=True), nullable=True,
                  comment='Earliest acceptable delivery date'),
        sa.Column('delivery_window_end', sa.TIMESTAMP(timezone=True), nullable=True,
                  comment='Latest acceptable delivery date'),
        sa.Column('delivery_flexibility_hours', sa.Integer, nullable=False, server_default='168',
                  comment='Flexibility window in hours (default: 7 days = 168 hours)'),
        
        # ========================================================================
        # MARKET VISIBILITY & PRIVACY
        # ========================================================================
        sa.Column('market_visibility', sa.String(20), nullable=False, server_default='PUBLIC',
                  comment='PUBLIC, PRIVATE, RESTRICTED, INTERNAL'),
        sa.Column('invited_seller_ids', postgresql.JSONB, nullable=True,
                  comment='Array of seller partner IDs for RESTRICTED visibility'),
        # Example: ["seller-uuid-1", "seller-uuid-2"]
        
        # ========================================================================
        # REQUIREMENT LIFECYCLE & STATUS
        # ========================================================================
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT',
                  comment='DRAFT, ACTIVE, PARTIALLY_FULFILLED, FULFILLED, EXPIRED, CANCELLED'),
        sa.Column('valid_from', sa.TIMESTAMP(timezone=True), nullable=False,
                  comment='Requirement valid from date'),
        sa.Column('valid_until', sa.TIMESTAMP(timezone=True), nullable=False,
                  comment='Requirement valid until date'),
        sa.Column('urgency_level', sa.String(20), nullable=False, server_default='NORMAL',
                  comment='URGENT, NORMAL, PLANNING'),
        
        # ========================================================================
        # 🚀 ENHANCEMENT #1: REQUIREMENT INTENT LAYER
        # ========================================================================
        sa.Column('intent_type', sa.String(30), nullable=False, server_default='DIRECT_BUY',
                  comment='DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY'),
        # CRITICAL: Enables intent-based routing to correct engine
        
        # ========================================================================
        # MATCHING & FULFILLMENT TRACKING
        # ========================================================================
        sa.Column('total_matched_quantity', sa.Numeric(15, 3), nullable=False, server_default='0',
                  comment='Total quantity matched with availabilities'),
        sa.Column('total_purchased_quantity', sa.Numeric(15, 3), nullable=False, server_default='0',
                  comment='Total quantity actually purchased'),
        sa.Column('total_spent', sa.Numeric(18, 2), nullable=False, server_default='0',
                  comment='Total amount spent on purchases'),
        sa.Column('active_negotiation_count', sa.Integer, nullable=False, server_default='0',
                  comment='Number of active negotiations'),
        
        # ========================================================================
        # 🚀 ENHANCEMENT #2: AI MARKET CONTEXT EMBEDDING
        # ========================================================================
        sa.Column('market_context_embedding', postgresql.ARRAY(sa.Float), nullable=True,
                  comment='1536-dim vector for semantic matching (OpenAI ada-002 compatible)'),
        # NOTE: Using ARRAY(Float) instead of vector type for compatibility
        # Vector operations will use pgvector functions in queries
        
        # ========================================================================
        # AI-POWERED FEATURES
        # ========================================================================
        sa.Column('ai_suggested_max_price', sa.Numeric(15, 2), nullable=True,
                  comment='AI-suggested fair market price'),
        sa.Column('ai_confidence_score', sa.Integer, nullable=True,
                  comment='AI confidence in price suggestion (0-100)'),
        sa.Column('ai_score_vector', postgresql.JSONB, nullable=True,
                  comment='ML embeddings for smart matching'),
        # Example: {"commodity_embedding": [...], "quality_flexibility": 75.5, 
        #           "price_sensitivity": 60.2, "urgency_score": 85.0}
        
        sa.Column('ai_price_alert_flag', sa.Boolean, nullable=False, server_default='false',
                  comment='True if AI detects unrealistic budget'),
        sa.Column('ai_alert_reason', sa.Text, nullable=True,
                  comment='Reason for AI price alert'),
        sa.Column('ai_recommended_sellers', postgresql.JSONB, nullable=True,
                  comment='AI pre-scored seller suggestions'),
        
        # ========================================================================
        # 🚀 ENHANCEMENT #4: MULTI-COMMODITY CONVERSION RULES
        # ========================================================================
        sa.Column('commodity_equivalents', postgresql.JSONB, nullable=True,
                  comment='Acceptable commodity substitutions with conversion ratios'),
        # Example: {"acceptable_substitutes": [
        #   {"commodity_id": "yarn-uuid", "conversion_ratio": 0.85, "quality_mapping": {...}},
        #   {"commodity_id": "fabric-uuid", "conversion_ratio": 0.75, "quality_mapping": {...}}
        # ]}
        
        # ========================================================================
        # 🚀 ENHANCEMENT #5: NEGOTIATION PREFERENCES BLOCK
        # ========================================================================
        sa.Column('negotiation_preferences', postgresql.JSONB, nullable=True,
                  comment='Self-negotiation settings and thresholds'),
        # Example: {
        #   "allow_auto_negotiation": true,
        #   "max_rounds": 5,
        #   "price_tolerance_percent": 3.0,
        #   "quantity_tolerance_percent": 10.0,
        #   "auto_accept_if_score": 0.95,
        #   "escalate_to_human_if_score": 0.60
        # }
        
        # ========================================================================
        # 🚀 ENHANCEMENT #6: BUYER TRUST SCORE WEIGHTING
        # ========================================================================
        sa.Column('buyer_priority_score', sa.Float, nullable=False, server_default='1.0',
                  comment='Buyer priority/trust score (0.5=new, 1.0=standard, 1.5=repeat, 2.0=premium)'),
        
        # ========================================================================
        # METADATA & AUDIT
        # ========================================================================
        sa.Column('notes', sa.Text, nullable=True,
                  comment='Buyer internal notes'),
        sa.Column('attachments', postgresql.JSONB, nullable=True,
                  comment='Specifications, drawings, sample images'),
        
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True,
                  comment='When requirement was made ACTIVE'),
        
        sa.Column('cancelled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('cancelled_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
        
        # ========================================================================
        # FOREIGN KEY CONSTRAINTS
        # ========================================================================
        sa.ForeignKeyConstraint(['buyer_partner_id'], ['business_partners.id'],
                                name='fk_requirements_buyer_partner',
                                ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'],
                                name='fk_requirements_commodity',
                                ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['variety_id'], ['commodity_varieties.id'],
                                name='fk_requirements_variety',
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'],
                                name='fk_requirements_created_by_user',
                                ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['cancelled_by_user_id'], ['users.id'],
                                name='fk_requirements_cancelled_by_user',
                                ondelete='SET NULL'),
        # sa.ForeignKeyConstraint(['buyer_branch_id'], ['branches.id'],  # Commented out - branches table doesn't exist yet
        #                         name='fk_requirements_buyer_branch',
        #                         ondelete='SET NULL'),
        
        # ========================================================================
        # CHECK CONSTRAINTS (Business Logic Validation)
        # ========================================================================
        sa.CheckConstraint('min_quantity > 0', name='check_min_quantity_positive'),
        sa.CheckConstraint('max_quantity >= min_quantity', name='check_max_quantity_ge_min'),
        sa.CheckConstraint(
            'preferred_quantity IS NULL OR (preferred_quantity >= min_quantity AND preferred_quantity <= max_quantity)',
            name='check_preferred_quantity_in_range'
        ),
        sa.CheckConstraint('total_purchased_quantity <= max_quantity', name='check_purchased_not_exceed_max'),
        sa.CheckConstraint('max_budget_per_unit > 0', name='check_max_budget_positive'),
        sa.CheckConstraint(
            'preferred_price_per_unit IS NULL OR preferred_price_per_unit <= max_budget_per_unit',
            name='check_preferred_price_le_max_budget'
        ),
        sa.CheckConstraint(
            'total_budget IS NULL OR total_budget >= (min_quantity * max_budget_per_unit)',
            name='check_total_budget_sufficient'
        ),
        sa.CheckConstraint('valid_from < valid_until', name='check_valid_dates_order'),
        sa.CheckConstraint(
            "market_visibility IN ('PUBLIC', 'PRIVATE', 'RESTRICTED', 'INTERNAL')",
            name='check_market_visibility_values'
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'PARTIALLY_FULFILLED', 'FULFILLED', 'EXPIRED', 'CANCELLED')",
            name='check_status_values'
        ),
        sa.CheckConstraint(
            "urgency_level IN ('URGENT', 'NORMAL', 'PLANNING')",
            name='check_urgency_level_values'
        ),
        sa.CheckConstraint(
            "intent_type IN ('DIRECT_BUY', 'NEGOTIATION', 'AUCTION_REQUEST', 'PRICE_DISCOVERY_ONLY')",
            name='check_intent_type_values'
        ),
        sa.CheckConstraint(
            'delivery_window_end IS NULL OR delivery_window_start IS NULL OR delivery_window_start < delivery_window_end',
            name='check_delivery_window_order'
        ),
        sa.CheckConstraint('buyer_priority_score >= 0.0', name='check_buyer_priority_score_non_negative'),
        sa.CheckConstraint(
            "risk_precheck_status IS NULL OR risk_precheck_status IN ('PASS', 'WARN', 'FAIL')",
            name='check_risk_precheck_status_values'
        ),
        sa.CheckConstraint(
            'risk_precheck_score IS NULL OR (risk_precheck_score >= 0 AND risk_precheck_score <= 100)',
            name='check_risk_precheck_score_range'
        ),
        sa.CheckConstraint(
            'buyer_rating_score IS NULL OR (buyer_rating_score >= 0.00 AND buyer_rating_score <= 5.00)',
            name='check_buyer_rating_score_range'
        ),
        sa.CheckConstraint(
            'buyer_payment_performance_score IS NULL OR (buyer_payment_performance_score >= 0 AND buyer_payment_performance_score <= 100)',
            name='check_buyer_payment_performance_score_range'
        ),
    )
    
    # ============================================================================
    # INDEXES - CORE
    # ============================================================================
    op.create_index('ix_requirements_buyer_partner_id', 'requirements', ['buyer_partner_id'])
    op.create_index('ix_requirements_commodity_id', 'requirements', ['commodity_id'])
    op.create_index('ix_requirements_status', 'requirements', ['status'])
    op.create_index('ix_requirements_market_visibility', 'requirements', ['market_visibility'])
    op.create_index('ix_requirements_urgency_level', 'requirements', ['urgency_level'])
    op.create_index('ix_requirements_intent_type', 'requirements', ['intent_type'])
    op.create_index('ix_requirements_buyer_priority_score', 'requirements', ['buyer_priority_score'])
    op.create_index('ix_requirements_risk_precheck_status', 'requirements', ['risk_precheck_status'])
    op.create_index('ix_requirements_buyer_branch_id', 'requirements', ['buyer_branch_id'])
    op.create_index('ix_requirements_buyer_rating_score', 'requirements', ['buyer_rating_score'])
    
    # ============================================================================
    # INDEXES - COMPOSITE (Query Optimization)
    # ============================================================================
    op.create_index(
        'ix_requirements_commodity_status',
        'requirements',
        ['commodity_id', 'status']
    )
    op.create_index(
        'ix_requirements_commodity_visibility',
        'requirements',
        ['commodity_id', 'market_visibility']
    )
    op.create_index(
        'ix_requirements_status_urgency',
        'requirements',
        ['status', 'urgency_level']
    )
    op.create_index(
        'ix_requirements_intent_status',
        'requirements',
        ['intent_type', 'status']
    )
    
    # ============================================================================
    # INDEXES - JSONB GIN (Fast JSONB Queries)
    # ============================================================================
    op.create_index(
        'ix_requirements_quality_requirements_gin',
        'requirements',
        ['quality_requirements'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_requirements_delivery_locations_gin',
        'requirements',
        ['delivery_locations'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_requirements_ai_score_vector_gin',
        'requirements',
        ['ai_score_vector'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_requirements_commodity_equivalents_gin',
        'requirements',
        ['commodity_equivalents'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_requirements_negotiation_preferences_gin',
        'requirements',
        ['negotiation_preferences'],
        postgresql_using='gin'
    )
    
    # ============================================================================
    # 🚀 INDEX - VECTOR SIMILARITY (for market_context_embedding)
    # ============================================================================
    # Note: Vector index will be created after data population for better performance
    # Can be added later with: CREATE INDEX ON requirements USING ivfflat (market_context_embedding vector_cosine_ops);
    
    # ============================================================================
    # INDEX - PARTIAL (Active Requirements Only - Performance Optimization)
    # ============================================================================
    op.execute("""
        CREATE INDEX ix_requirements_active
        ON requirements(commodity_id, buyer_partner_id, urgency_level, intent_type)
        WHERE status = 'ACTIVE'
    """)
    
    # ============================================================================
    # TRIGGER - Auto-Update Fulfillment Status
    # ============================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_requirement_status()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Auto-calculate fulfillment status based on purchased quantity
            IF NEW.total_purchased_quantity >= NEW.max_quantity THEN
                NEW.status := 'FULFILLED';
            ELSIF NEW.total_purchased_quantity >= NEW.min_quantity THEN
                NEW.status := 'PARTIALLY_FULFILLED';
            END IF;
            
            -- Auto-expire if past valid_until date
            IF NEW.valid_until < NOW() AND NEW.status = 'ACTIVE' THEN
                NEW.status := 'EXPIRED';
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_update_requirement_status
        BEFORE INSERT OR UPDATE ON requirements
        FOR EACH ROW
        EXECUTE FUNCTION update_requirement_status()
    """)
    
    # ============================================================================
    # TRIGGER - Auto-Update updated_at Timestamp
    # ============================================================================
    op.execute("""
        CREATE TRIGGER trigger_requirements_updated_at
        BEFORE UPDATE ON requirements
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)
    
    # ============================================================================
    # TABLE COMMENT
    # ============================================================================
    op.execute("""
        COMMENT ON TABLE requirements IS 
        'Buyer requirements for commodity procurement - Engine 2 of 5. 
        Includes 7 enhancements for 2035: Intent Layer, AI Market Embeddings, 
        Delivery Flexibility, Commodity Conversion, Negotiation Preferences, 
        Buyer Trust Score, AI Adjustment Events. 
        Risk Management: Credit limit checking, risk scoring, internal trade blocking, 
        buyer rating integration, payment performance tracking. 
        Supports autonomous AI trading with comprehensive risk controls.'
    """)


def downgrade() -> None:
    """Drop requirement engine tables"""
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS trigger_requirements_updated_at ON requirements')
    op.execute('DROP TRIGGER IF EXISTS trigger_update_requirement_status ON requirements')
    op.execute('DROP FUNCTION IF EXISTS update_requirement_status()')
    
    # Drop table
    op.drop_table('requirements')
    
    # Note: Keep pgvector extension as it might be used by other tables
    # op.execute('DROP EXTENSION IF EXISTS vector')
