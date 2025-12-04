"""
Requirement Model - Engine 2: Buyers post procurement requirements

The inverse of Availability Engine. Buyers post commodity requirements with quality
tolerances, budget constraints, and delivery preferences. Supports ANY commodity via JSONB.

🚀 2035-READY ENHANCEMENTS:
1. Intent Layer: Routes based on buyer intent (DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY)
2. AI Market Context Embedding: 1536-dim vector for semantic matching
3. Dynamic Delivery Flexibility: delivery_window with flexibility hours
4. Multi-Commodity Conversion: Accepts substitutes (Cotton→Yarn, Paddy→Rice)
5. Negotiation Preferences: Self-negotiating system with auto-accept thresholds
6. Buyer Trust Score: Prioritizes serious buyers
7. AI Adjustment Events: Transparent AI decision making

Features:
- Min/Max quantity ranges (buyer flexibility)
- Quality tolerance ranges (min/max/preferred/exact)
- Multi-commodity JSONB quality requirements
- AI market context embeddings for vector similarity
- Budget constraints with preferred pricing
- Multiple delivery locations
- Market visibility controls (PUBLIC/PRIVATE/RESTRICTED/INTERNAL)
- Auto-update triggers for fulfillment status
- Event sourcing for complete audit trail
- Real-time WebSocket updates
- Intent-based routing for autonomous trade engine

Buyer Location Validation:
- BUYER: Can specify delivery to registered locations only
- TRADER: Can specify delivery to any location (no restriction)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from backend.core.events.mixins import EventMixin
from backend.db.session import Base
from backend.modules.trade_desk.enums import (
    IntentType,
    MarketVisibility,
    RequirementStatus,
    UrgencyLevel,
)
from backend.modules.trade_desk.events.requirement_events import (
    RequirementAIAdjustedEvent,
    RequirementBudgetChangedEvent,
    RequirementCancelledEvent,
    RequirementCreatedEvent,
    RequirementExpiredEvent,
    RequirementFulfilledEvent,
    RequirementFulfillmentUpdatedEvent,
    RequirementPublishedEvent,
    RequirementQualityChangedEvent,
    RequirementUpdatedEvent,
    RequirementVisibilityChangedEvent,
)


class Requirement(Base, EventMixin):
    """
    Requirement - Buyer procurement requirements for global multi-commodity trading.
    
    Lifecycle:
    1. DRAFT → Buyer creates requirement
    2. ACTIVE → Published and searchable (sellers can see per market_visibility)
    3. PARTIALLY_FULFILLED → Some quantity purchased
    4. FULFILLED → All quantity purchased
    5. EXPIRED → Past expiry date
    6. CANCELLED → Cancelled by buyer
    
    Events Emitted (11 Total):
    - requirement.created
    - requirement.published
    - requirement.updated
    - requirement.budget_changed (micro-event)
    - requirement.quality_changed (micro-event)
    - requirement.visibility_changed (micro-event)
    - requirement.fulfillment_updated (micro-event)
    - requirement.fulfilled
    - requirement.expired
    - requirement.cancelled
    - requirement.ai_adjusted (🚀 NEW - ENHANCEMENT #7)
    
    Intent-Based Routing:
    - DIRECT_BUY → Immediate matching engine
    - NEGOTIATION → Multi-round negotiation queue
    - AUCTION_REQUEST → Reverse auction module
    - PRICE_DISCOVERY_ONLY → Market insights only
    """
    
    __tablename__ = "requirements"
    
    # ========================================================================
    # PRIMARY KEY & CORE IDENTIFICATION
    # ========================================================================
    id = Column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        nullable=False,
        comment='Unique requirement identifier'
    )
    requirement_number = Column(
        String(50),
        unique=True,
        nullable=False,
        comment='Human-readable requirement number: REQ-2025-000001'
    )
    
    # ========================================================================
    # FOREIGN KEYS
    # ========================================================================
    buyer_partner_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment='Buyer posting the requirement'
    )
    commodity_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("commodities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment='Required commodity'
    )
    variety_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("commodity_varieties.id", ondelete="SET NULL"),
        nullable=True,
        comment='Specific variety (optional)'
    )
    created_by_user_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment='User who created requirement'
    )
    
    # ========================================================================
    # QUANTITY REQUIREMENTS (Min/Max Ranges for Flexibility)
    # ========================================================================
    min_quantity = Column(
        Numeric(15, 3),
        nullable=False,
        comment='Minimum acceptable quantity'
    )
    max_quantity = Column(
        Numeric(15, 3),
        nullable=False,
        comment='Maximum desired quantity'
    )
    quantity_unit = Column(
        String(20),
        nullable=False,
        comment='Unit: bales, kg, MT, grams, etc.'
    )
    preferred_quantity = Column(
        Numeric(15, 3),
        nullable=True,
        comment='Ideal/target quantity'
    )
    
    # ========================================================================
    # QUALITY REQUIREMENTS (JSONB - Flexible Tolerances)
    # ========================================================================
    quality_requirements = Column(
        JSONB,
        nullable=False,
        comment='Quality params with min/max/preferred/exact/accepted/required'
    )
    # Example: {"staple_length": {"min": 28, "max": 30, "preferred": 29},
    #           "micronaire": {"min": 3.8, "max": 4.5}}
    
    # ========================================================================
    # BUDGET & PRICING
    # ========================================================================
    max_budget_per_unit = Column(
        Numeric(15, 2),
        nullable=False,
        comment='Maximum price buyer willing to pay per unit'
    )
    preferred_price_per_unit = Column(
        Numeric(15, 2),
        nullable=True,
        comment='Target/desired price per unit'
    )
    total_budget = Column(
        Numeric(18, 2),
        nullable=True,
        comment='Overall budget limit for entire purchase'
    )
    currency_code = Column(
        String(3),
        nullable=False,
        server_default='INR',
        comment='Currency code (ISO 4217)'
    )
    
    # ========================================================================
    # 🚀 RISK MANAGEMENT & CREDIT CONTROL
    # ========================================================================
    estimated_trade_value = Column(
        Numeric(18, 2),
        nullable=True,
        comment='Auto-calculated estimated trade value (preferred_quantity * max_budget_per_unit)'
    )
    buyer_credit_limit_remaining = Column(
        Numeric(18, 2),
        nullable=True,
        comment='Remaining credit limit for this buyer from credit module'
    )
    buyer_exposure_after_trade = Column(
        Numeric(18, 2),
        nullable=True,
        comment='Projected buyer exposure if this trade executes'
    )
    risk_precheck_status = Column(
        String(20),
        nullable=True,
        comment='PASS, WARN, FAIL - Risk assessment status'
    )
    risk_precheck_score = Column(
        Integer,
        nullable=True,
        comment='Numeric risk score (0-100, higher is better)'
    )
    buyer_branch_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("partner_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment='Buyer branch/location ID (from partner_locations table) for internal trade blocking logic'
    )
    blocked_internal_trades = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='If true, blocks matching with same branch sellers'
    )
    buyer_rating_score = Column(
        Numeric(3, 2),
        nullable=True,
        comment='Buyer rating score (0.00-5.00) from rating module'
    )
    buyer_payment_performance_score = Column(
        Integer,
        nullable=True,
        comment='Payment performance score (0-100) based on history'
    )
    
    # ========================================================================
    # PAYMENT & DELIVERY PREFERENCES
    # ========================================================================
    preferred_payment_terms = Column(
        JSONB,
        nullable=True,
        comment='Array of acceptable payment term IDs'
    )
    # Example: ["cash-uuid", "15day-uuid", "30day-uuid"]
    
    preferred_delivery_terms = Column(
        JSONB,
        nullable=True,
        comment='Array of acceptable delivery term IDs'
    )
    # Example: ["ex-gin-uuid", "delivered-uuid"]
    
    delivery_locations = Column(
        JSONB,
        nullable=True,
        comment='Multiple acceptable delivery locations with proximity'
    )
    # Example: [{"location_id": "uuid", "latitude": 21.1, "longitude": 79.0, "max_distance_km": 50}]
    
    # ========================================================================
    # INTERNATIONAL TRADE FIELDS
    # ========================================================================
    destination_country = Column(
        String(2),
        nullable=True,
        index=True,
        comment='ISO 3166-1 alpha-2 country code for import destination (IN, US, CN, etc.)'
    )
    preferred_incoterm = Column(
        String(10),
        nullable=True,
        comment='Preferred Incoterm for international trade: FOB, CIF, EXW, DDP, etc.'
    )
    import_port = Column(
        String(255),
        nullable=True,
        comment='Port code for international imports (e.g., INNSA for Nhava Sheva)'
    )
    
    # ========================================================================
    # 🚀 ENHANCEMENT #3: DYNAMIC DELIVERY FLEXIBILITY WINDOW
    # ========================================================================
    delivery_window_start = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='Earliest acceptable delivery date'
    )
    delivery_window_end = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='Latest acceptable delivery date'
    )
    delivery_flexibility_hours = Column(
        Integer,
        nullable=False,
        server_default='168',
        comment='Flexibility window in hours (default: 7 days = 168 hours)'
    )
    
    # ========================================================================
    # MARKET VISIBILITY & PRIVACY
    # ========================================================================
    market_visibility = Column(
        String(20),
        nullable=False,
        server_default='PUBLIC',
        comment='PUBLIC, PRIVATE, RESTRICTED, INTERNAL'
    )
    invited_seller_ids = Column(
        JSONB,
        nullable=True,
        comment='Array of seller partner IDs for RESTRICTED visibility'
    )
    # Example: ["seller-uuid-1", "seller-uuid-2"]
    
    # ========================================================================
    # REQUIREMENT LIFECYCLE & STATUS
    # ========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='DRAFT',
        comment='DRAFT, ACTIVE, PARTIALLY_FULFILLED, FULFILLED, EXPIRED, CANCELLED'
    )
    valid_from = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Requirement valid from date'
    )
    valid_until = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Requirement valid until date'
    )
    eod_cutoff = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='End-of-day cutoff time (timezone-aware). Requirement expires at this time.'
    )
    urgency_level = Column(
        String(20),
        nullable=False,
        server_default='NORMAL',
        comment='URGENT, NORMAL, PLANNING'
    )
    
    # ========================================================================
    # 🚀 ENHANCEMENT #1: REQUIREMENT INTENT LAYER
    # ========================================================================
    intent_type = Column(
        String(30),
        nullable=False,
        server_default='DIRECT_BUY',
        comment='DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY'
    )
    
    # ========================================================================
    # MATCHING & FULFILLMENT TRACKING
    # ========================================================================
    total_matched_quantity = Column(
        Numeric(15, 3),
        nullable=False,
        server_default='0',
        comment='Total quantity matched with availabilities'
    )
    total_purchased_quantity = Column(
        Numeric(15, 3),
        nullable=False,
        server_default='0',
        comment='Total quantity actually purchased'
    )
    total_spent = Column(
        Numeric(18, 2),
        nullable=False,
        server_default='0',
        comment='Total amount spent on purchases'
    )
    active_negotiation_count = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Number of active negotiations'
    )
    
    # ========================================================================
    # 🚀 ENHANCEMENT #2: AI MARKET CONTEXT EMBEDDING
    # ========================================================================
    market_context_embedding = Column(
        ARRAY(Float),
        nullable=True,
        comment='1536-dim vector for semantic matching (OpenAI ada-002 compatible)'
    )
    # Vector similarity search enables:
    # - Find requirements with similar market context
    # - Match based on market sentiment, not just quality/price
    # - Predict future requirement patterns
    # - Autonomous trade engine decision making
    
    # ========================================================================
    # AI-POWERED FEATURES
    # ========================================================================
    ai_suggested_max_price = Column(
        Numeric(15, 2),
        nullable=True,
        comment='AI-suggested fair market price'
    )
    ai_confidence_score = Column(
        Integer,
        nullable=True,
        comment='AI confidence in price suggestion (0-100)'
    )
    ai_score_vector = Column(
        JSONB,
        nullable=True,
        comment='ML embeddings for smart matching'
    )
    # Example: {"commodity_embedding": [...], "quality_flexibility": 75.5,
    #           "price_sensitivity": 60.2, "urgency_score": 85.0}
    
    ai_price_alert_flag = Column(
        Boolean,
        nullable=False,
        server_default='false',
        comment='True if AI detects unrealistic budget'
    )
    ai_alert_reason = Column(
        Text,
        nullable=True,
        comment='Reason for AI price alert'
    )
    ai_recommended_sellers = Column(
        JSONB,
        nullable=True,
        comment='AI pre-scored seller suggestions'
    )
    
    # ========================================================================
    # 🚀 ENHANCEMENT #4: MULTI-COMMODITY CONVERSION RULES
    # ========================================================================
    commodity_equivalents = Column(
        JSONB,
        nullable=True,
        comment='Acceptable commodity substitutions with conversion ratios'
    )
    # Example: {"acceptable_substitutes": [
    #   {"commodity_id": "yarn-uuid", "conversion_ratio": 0.85, "quality_mapping": {...}},
    #   {"commodity_id": "fabric-uuid", "conversion_ratio": 0.75, "quality_mapping": {...}}
    # ]}
    
    # ========================================================================
    # 🚀 ENHANCEMENT #5: NEGOTIATION PREFERENCES BLOCK
    # ========================================================================
    negotiation_preferences = Column(
        JSONB,
        nullable=True,
        comment='Self-negotiation settings and thresholds'
    )
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
    buyer_priority_score = Column(
        Float,
        nullable=False,
        server_default='1.0',
        comment='Buyer priority/trust score (0.5=new, 1.0=standard, 1.5=repeat, 2.0=premium)'
    )
    
    # ========================================================================
    # METADATA & AUDIT
    # ========================================================================
    notes = Column(
        Text,
        nullable=True,
        comment='Buyer internal notes'
    )
    attachments = Column(
        JSONB,
        nullable=True,
        comment='Specifications, drawings, sample images'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('NOW()')
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('NOW()')
    )
    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='When requirement was made ACTIVE'
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_by_user_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    cancellation_reason = Column(
        Text,
        nullable=True
    )
    
    # ========================================================================
    # RELATIONSHIPS (will be defined when related models exist)
    # ========================================================================
    buyer_partner = relationship("BusinessPartner", foreign_keys=[buyer_partner_id])
    # commodity = relationship("Commodity", foreign_keys=[commodity_id])
    # variety = relationship("CommodityVariety", foreign_keys=[variety_id])
    # created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    # cancelled_by_user = relationship("User", foreign_keys=[cancelled_by_user_id])
    buyer_branch = relationship("PartnerLocation", foreign_keys=[buyer_branch_id])
    
    # Vector embedding relationship (one-to-one)
    embedding = relationship(
        "RequirementEmbedding",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __init__(self, **kwargs):
        """Initialize requirement with default values for fields that have server_default"""
        super().__init__(**kwargs)
        # Initialize instance-level pending events list (prevents sharing across instances)
        self._pending_events = []
        # Set ID if not provided (necessary for event emission in tests)
        if not hasattr(self, 'id') or self.id is None:
            self.id = uuid.uuid4()
        # Set defaults for fields that would normally be set by database server_default
        # These are necessary for tests that create instances without inserting to DB
        if not hasattr(self, 'status') or self.status is None:
            self.status = RequirementStatus.DRAFT.value
        if not hasattr(self, 'total_matched_quantity') or self.total_matched_quantity is None:
            self.total_matched_quantity = Decimal('0')
        if not hasattr(self, 'total_purchased_quantity') or self.total_purchased_quantity is None:
            self.total_purchased_quantity = Decimal('0')
        if not hasattr(self, 'total_spent') or self.total_spent is None:
            self.total_spent = Decimal('0')
        if not hasattr(self, 'active_negotiation_count') or self.active_negotiation_count is None:
            self.active_negotiation_count = 0
        if not hasattr(self, 'delivery_flexibility_hours') or self.delivery_flexibility_hours is None:
            self.delivery_flexibility_hours = 168
        if not hasattr(self, 'buyer_priority_score') or self.buyer_priority_score is None:
            self.buyer_priority_score = 1.0
        if not hasattr(self, 'currency_code') or self.currency_code is None:
            self.currency_code = 'INR'
        if not hasattr(self, 'market_visibility') or self.market_visibility is None:
            self.market_visibility = MarketVisibility.PUBLIC.value
        if not hasattr(self, 'urgency_level') or self.urgency_level is None:
            self.urgency_level = UrgencyLevel.NORMAL.value
        if not hasattr(self, 'intent_type') or self.intent_type is None:
            self.intent_type = IntentType.DIRECT_BUY.value
        if not hasattr(self, 'blocked_internal_trades') or self.blocked_internal_trades is None:
            self.blocked_internal_trades = True
        if not hasattr(self, 'ai_price_alert_flag') or self.ai_price_alert_flag is None:
            self.ai_price_alert_flag = False
    
    # ========================================================================
    # BUSINESS LOGIC METHODS
    # ========================================================================
    
    def can_update(self) -> bool:
        """Check if requirement can be updated"""
        return self.status in [RequirementStatus.DRAFT, RequirementStatus.ACTIVE]
    
    def can_cancel(self) -> bool:
        """Check if requirement can be cancelled"""
        return self.status not in [RequirementStatus.FULFILLED, RequirementStatus.CANCELLED]
    
    def can_publish(self) -> bool:
        """Check if requirement can be published (DRAFT → ACTIVE)"""
        return self.status == RequirementStatus.DRAFT
    
    def update_fulfillment(
        self,
        purchased_quantity: Decimal,
        amount_spent: Decimal,
        user_id: UUID,
        trade_id: Optional[UUID] = None
    ) -> None:
        """
        Update when buyer purchases from an availability.
        
        Args:
            purchased_quantity: Quantity purchased in this transaction
            amount_spent: Amount spent in this transaction
            user_id: User making the purchase
            trade_id: Optional trade ID reference
        """
        self.total_purchased_quantity += purchased_quantity
        self.total_spent += amount_spent
        
        # Calculate remaining
        remaining_quantity = self.max_quantity - self.total_purchased_quantity
        remaining_budget = (self.total_budget or Decimal('0')) - self.total_spent
        fulfillment_pct = (self.total_purchased_quantity / self.max_quantity) * Decimal('100')
        
        # Emit micro-event
        self.emit_fulfillment_updated(
            user_id=user_id,
            purchased_quantity=purchased_quantity,
            amount_spent=amount_spent,
            remaining_quantity=remaining_quantity,
            remaining_budget=remaining_budget,
            fulfillment_percentage=fulfillment_pct,
            trade_id=trade_id
        )
        
        # Auto-update status (trigger will handle this, but can be done here too)
        if self.total_purchased_quantity >= self.max_quantity:
            self.mark_fulfilled(user_id)
        elif self.total_purchased_quantity >= self.min_quantity:
            self.status = RequirementStatus.PARTIALLY_FULFILLED.value
    
    def mark_fulfilled(self, user_id: UUID) -> None:
        """Mark requirement as fully fulfilled"""
        self.status = RequirementStatus.FULFILLED.value
        
        # Calculate metrics
        avg_price = self.total_spent / self.total_purchased_quantity if self.total_purchased_quantity > 0 else Decimal('0')
        duration_hours = None
        if self.published_at:
            duration_hours = (datetime.utcnow() - self.published_at).total_seconds() / 3600
        
        self.emit_fulfilled(
            user_id=user_id,
            average_price_per_unit=avg_price,
            fulfillment_duration_hours=duration_hours
        )
    
    def cancel(self, user_id: UUID, reason: str) -> None:
        """Cancel requirement"""
        if not self.can_cancel():
            raise ValueError(f"Cannot cancel requirement with status {self.status}")
        
        self.status = RequirementStatus.CANCELLED.value
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by_user_id = user_id
        self.cancellation_reason = reason
        
        unfulfilled_quantity = self.max_quantity - self.total_purchased_quantity
        
        self.emit_cancelled(
            user_id=user_id,
            unfulfilled_quantity=unfulfilled_quantity,
            reason=reason
        )
    
    def publish(self, user_id: UUID) -> None:
        """Publish requirement (DRAFT → ACTIVE)"""
        if not self.can_publish():
            raise ValueError(f"Cannot publish requirement with status {self.status}")
        
        self.status = RequirementStatus.ACTIVE.value
        self.published_at = datetime.utcnow()
        
        self.emit_published(user_id=user_id)
    
    # ========================================================================
    # 🚀 RISK MANAGEMENT METHODS
    # ========================================================================
    
    def calculate_estimated_trade_value(self) -> Optional[Decimal]:
        """
        Auto-calculate estimated trade value.
        
        Returns:
            Estimated trade value or None if calculation not possible
        """
        if self.preferred_quantity and self.max_budget_per_unit:
            return self.preferred_quantity * self.max_budget_per_unit
        elif self.min_quantity and self.max_budget_per_unit:
            # Fallback to min_quantity if preferred not set
            return self.min_quantity * self.max_budget_per_unit
        return None
    
    def update_risk_precheck(
        self,
        credit_limit_remaining: Optional[Decimal] = None,
        rating_score: Optional[Decimal] = None,
        payment_performance_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update risk precheck status based on buyer's credit and performance metrics.
        
        Args:
            credit_limit_remaining: Buyer's remaining credit limit
            rating_score: Buyer rating (0-5.00)
            payment_performance_score: Payment performance (0-100)
        
        Returns:
            Dict with risk assessment details
        """
        # Update fields
        if credit_limit_remaining is not None:
            self.buyer_credit_limit_remaining = credit_limit_remaining
        if rating_score is not None:
            self.buyer_rating_score = rating_score
        if payment_performance_score is not None:
            self.buyer_payment_performance_score = payment_performance_score
        
        # Calculate estimated trade value
        estimated_value = self.calculate_estimated_trade_value()
        if estimated_value:
            self.estimated_trade_value = estimated_value
        
        # Calculate exposure after trade
        if self.buyer_credit_limit_remaining and self.estimated_trade_value:
            self.buyer_exposure_after_trade = self.buyer_credit_limit_remaining - self.estimated_trade_value
        
        # Risk scoring logic
        risk_score = 100  # Start optimistic
        risk_factors = []
        
        # Check credit limit
        if self.buyer_credit_limit_remaining and self.estimated_trade_value:
            if self.buyer_credit_limit_remaining < self.estimated_trade_value:
                risk_score -= 50
                risk_factors.append("Insufficient credit limit")
            elif self.buyer_exposure_after_trade and self.buyer_exposure_after_trade < 0:
                risk_score -= 30
                risk_factors.append("Trade exceeds credit limit")
            elif self.buyer_credit_limit_remaining < (self.estimated_trade_value * Decimal('1.2')):
                risk_score -= 15
                risk_factors.append("Low credit headroom (<20%)")
        
        # Check buyer rating
        if self.buyer_rating_score is not None:
            if self.buyer_rating_score < Decimal('2.0'):
                risk_score -= 25
                risk_factors.append("Low buyer rating (<2.0)")
            elif self.buyer_rating_score < Decimal('3.0'):
                risk_score -= 10
                risk_factors.append("Below average rating (<3.0)")
        
        # Check payment performance
        if self.buyer_payment_performance_score is not None:
            if self.buyer_payment_performance_score < 50:
                risk_score -= 20
                risk_factors.append("Poor payment history (<50)")
            elif self.buyer_payment_performance_score < 70:
                risk_score -= 10
                risk_factors.append("Fair payment history (<70)")
        
        # Ensure score is in range
        risk_score = max(0, min(100, risk_score))
        self.risk_precheck_score = risk_score
        
        # Determine status
        if risk_score >= 75:
            self.risk_precheck_status = "PASS"
        elif risk_score >= 50:
            self.risk_precheck_status = "WARN"
        else:
            self.risk_precheck_status = "FAIL"
        
        return {
            "risk_precheck_status": self.risk_precheck_status,
            "risk_precheck_score": self.risk_precheck_score,
            "estimated_trade_value": self.estimated_trade_value,
            "buyer_exposure_after_trade": self.buyer_exposure_after_trade,
            "risk_factors": risk_factors
        }
    
    def check_internal_trade_block(self, seller_branch_id: Optional[UUID]) -> bool:
        """
        Check if trade should be blocked due to internal trade policy.
        
        Args:
            seller_branch_id: Branch ID of the seller
        
        Returns:
            True if trade should be blocked, False otherwise
        """
        if not self.blocked_internal_trades:
            return False  # Internal trades allowed
        
        if not self.buyer_branch_id or not seller_branch_id:
            return False  # No branch info, allow
        
        # Block if same branch
        return self.buyer_branch_id == seller_branch_id
    
    # ========================================================================
    # EVENT EMISSION METHODS
    # ========================================================================
    
    def emit_created(self, user_id: UUID) -> None:
        """Emit requirement.created event"""
        event = RequirementCreatedEvent(
            requirement_id=self.id,
            buyer_id=self.buyer_partner_id,
            commodity_id=self.commodity_id,
            min_quantity=self.min_quantity,
            max_quantity=self.max_quantity,
            max_budget_per_unit=self.max_budget_per_unit,
            quality_requirements=self.quality_requirements,
            market_visibility=self.market_visibility,
            urgency_level=self.urgency_level,
            intent_type=self.intent_type,
            buyer_priority_score=self.buyer_priority_score,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        self.emit_event(event_type="requirement.created", user_id=user_id, data=event.to_dict())
    
    def emit_published(self, user_id: UUID) -> None:
        """Emit requirement.published event (CRITICAL for intent-based routing)"""
        event = RequirementPublishedEvent(
            requirement_id=self.id,
            buyer_id=self.buyer_partner_id,
            commodity_id=self.commodity_id,
            quality_requirements=self.quality_requirements,
            max_budget_per_unit=self.max_budget_per_unit,
            urgency_level=self.urgency_level,
            intent_type=self.intent_type,  # 🚀 CRITICAL for routing
            market_visibility=self.market_visibility,
            published_by=user_id,
            published_at=datetime.utcnow()
        )
        self.emit_event(event_type="requirement.published", user_id=user_id, data=event.to_dict())
    
    def emit_updated(self, user_id: UUID, updated_fields: Dict[str, Any]) -> None:
        """Emit requirement.updated event"""
        event = RequirementUpdatedEvent(
            requirement_id=self.id,
            updated_fields=updated_fields,
            updated_by=user_id,
            updated_at=datetime.utcnow()
        )
        self.emit_event(event_type="requirement.updated", user_id=user_id, data=event.to_dict())
    
    def emit_budget_changed(
        self,
        user_id: UUID,
        old_max_budget: Decimal,
        new_max_budget: Decimal,
        old_preferred_price: Optional[Decimal],
        new_preferred_price: Optional[Decimal],
        reason: Optional[str] = None
    ) -> None:
        """Emit requirement.budget_changed micro-event"""
        budget_change_pct = ((new_max_budget - old_max_budget) / old_max_budget) * Decimal('100')
        
        event = RequirementBudgetChangedEvent(
            requirement_id=self.id,
            old_max_budget=old_max_budget,
            new_max_budget=new_max_budget,
            old_preferred_price=old_preferred_price,
            new_preferred_price=new_preferred_price,
            budget_change_pct=budget_change_pct,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        self.emit_event(event_type="requirement.budget_changed", user_id=user_id, data=event.to_dict())
    
    def emit_quality_changed(
        self,
        user_id: UUID,
        old_quality_requirements: Dict[str, Any],
        new_quality_requirements: Dict[str, Any],
        reason: Optional[str] = None
    ) -> None:
        """Emit requirement.quality_changed micro-event"""
        # Detect changed parameters
        old_keys = set(old_quality_requirements.keys())
        new_keys = set(new_quality_requirements.keys())
        changed_parameters = list(old_keys.union(new_keys))
        
        event = RequirementQualityChangedEvent(
            requirement_id=self.id,
            old_quality_requirements=old_quality_requirements,
            new_quality_requirements=new_quality_requirements,
            changed_parameters=changed_parameters,
            tolerance_change_summary=None,  # Can be calculated
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        self.emit_event(event_type="requirement.quality_changed", user_id=user_id, data=event.to_dict())
    
    def emit_visibility_changed(
        self,
        user_id: UUID,
        old_visibility: str,
        new_visibility: str,
        reason: Optional[str] = None
    ) -> None:
        """Emit requirement.visibility_changed micro-event"""
        event = RequirementVisibilityChangedEvent(
            requirement_id=self.id,
            old_visibility=old_visibility,
            new_visibility=new_visibility,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        self.emit_event(event_type="requirement.visibility_changed", user_id=user_id, data=event.to_dict())
    
    def emit_fulfillment_updated(
        self,
        user_id: UUID,
        purchased_quantity: Decimal,
        amount_spent: Decimal,
        remaining_quantity: Decimal,
        remaining_budget: Decimal,
        fulfillment_percentage: Decimal,
        trade_id: Optional[UUID] = None
    ) -> None:
        """Emit requirement.fulfillment_updated micro-event"""
        event = RequirementFulfillmentUpdatedEvent(
            requirement_id=self.id,
            purchased_quantity=purchased_quantity,
            amount_spent=amount_spent,
            total_purchased_quantity=self.total_purchased_quantity,
            total_spent=self.total_spent,
            remaining_quantity=remaining_quantity,
            remaining_budget=remaining_budget,
            fulfillment_percentage=fulfillment_percentage,
            trade_id=trade_id,
            updated_by=user_id,
            updated_at=datetime.utcnow()
        )
        self.emit_event(event_type="requirement.fulfillment_updated", user_id=user_id, data=event.to_dict())
    
    def emit_fulfilled(
        self,
        user_id: UUID,
        average_price_per_unit: Decimal,
        fulfillment_duration_hours: Optional[float] = None
    ) -> None:
        """Emit requirement.fulfilled event"""
        event = RequirementFulfilledEvent(
            requirement_id=self.id,
            buyer_id=self.buyer_partner_id,
            commodity_id=self.commodity_id,
            total_quantity_purchased=self.total_purchased_quantity,
            total_spent=self.total_spent,
            average_price_per_unit=average_price_per_unit,
            number_of_trades=0,  # Will be calculated by service
            fulfillment_duration_hours=fulfillment_duration_hours,
            fulfilled_by=user_id,
            fulfilled_at=datetime.utcnow()
        )
        self.emit_event(event_type="requirement.fulfilled", user_id=user_id, data=event.to_dict())
    
    def emit_cancelled(
        self,
        user_id: UUID,
        unfulfilled_quantity: Decimal,
        reason: str
    ) -> None:
        """Emit requirement.cancelled event"""
        event = RequirementCancelledEvent(
            requirement_id=self.id,
            buyer_id=self.buyer_partner_id,
            commodity_id=self.commodity_id,
            unfulfilled_quantity=unfulfilled_quantity,
            cancelled_by=user_id,
            cancelled_at=datetime.utcnow(),
            cancellation_reason=reason
        )
        self.emit_event(event_type="requirement.cancelled", user_id=user_id, data=event.to_dict())
    
    def emit_ai_adjusted(
        self,
        user_id: UUID,  # Added user_id parameter
        adjustment_type: str,
        old_value: Any,
        new_value: Any,
        ai_confidence: float,
        ai_reasoning: str,
        market_context: Optional[Dict[str, Any]] = None,
        expected_impact: Optional[str] = None,
        adjusted_by_system: bool = False
    ) -> None:
        """
        🚀 ENHANCEMENT #7: Emit requirement.ai_adjusted event
        
        Critical for explainability & audit trail of AI decisions
        """
        event = RequirementAIAdjustedEvent(
            requirement_id=self.id,
            adjustment_type=adjustment_type,
            old_value=old_value,
            new_value=new_value,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            market_context=market_context,
            expected_impact=expected_impact,
            adjusted_by_system=adjusted_by_system,
            adjusted_at=datetime.utcnow()
        )
        # AI adjustments don't always have a user_id (system-initiated)
        user_for_event = user_id if not adjusted_by_system else UUID('00000000-0000-0000-0000-000000000000')
        self.emit_event(event_type="requirement.ai_adjusted", user_id=user_for_event, data=event.to_dict())
    
    def __repr__(self) -> str:
        return (
            f"<Requirement(id={self.id}, "
            f"requirement_number={self.requirement_number}, "
            f"buyer={self.buyer_partner_id}, "
            f"commodity={self.commodity_id}, "
            f"status={self.status}, "
            f"intent={self.intent_type})>"
        )
