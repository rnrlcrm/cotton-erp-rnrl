"""
Availability Model - Engine 1: Sellers post inventory

The foundation of the 5-Engine Trading System. Sellers post available inventory
with quality parameters, pricing, and delivery terms. Supports ANY commodity via JSONB.

Features:
- Multi-commodity JSONB quality parameters
- AI score vectors for ML-powered matching
- Geo-spatial indexing for location-based search
- Market visibility controls (PUBLIC/PRIVATE/RESTRICTED/INTERNAL)
- Partial order support
- Auto-update triggers for quantities and status
- Event sourcing for complete audit trail
- Real-time WebSocket updates

Seller Location Validation:
- ALL SELLERS: Can sell from ANY location (no restriction)
- Reason: Traders may source from multiple locations, sellers may have temporary stock
- Validation: Only check if location exists in settings_locations table
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from backend.core.events.mixins import EventMixin
from backend.db.session import Base
from backend.modules.trade_desk.enums import (
    ApprovalStatus,
    AvailabilityStatus,
    MarketVisibility,
    PriceType,
)


class Availability(Base, EventMixin):
    """
    Availability - Seller inventory postings for global multi-commodity trading.
    
    Lifecycle:
    1. DRAFT → Seller creates availability
    2. ACTIVE → Approved and posted (visible per market_visibility)
    3. RESERVED → Quantity reserved during negotiation
    4. SOLD → Fully sold (converted to trade)
    5. EXPIRED → Past expiry date
    6. CANCELLED → Cancelled by seller
    
    Events Emitted:
    - availability.created
    - availability.updated
    - availability.visibility_changed (micro-event)
    - availability.price_changed (micro-event)
    - availability.quantity_changed (micro-event)
    - availability.reserved
    - availability.released
    - availability.sold
    - availability.expired
    - availability.cancelled
    """
    
    __tablename__ = "availabilities"
    
    # Primary Key
    id = Column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Foreign Keys
    commodity_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("commodities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    location_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("settings_locations.id", ondelete="RESTRICT"),
        nullable=True,  # 🔥 NULLABLE: Ad-hoc locations use NULL + coordinates
        index=True,
        comment='Registered location ID (NULL for ad-hoc Google Maps locations)'
    )
    seller_partner_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Quantity Management (auto-updated by trigger)
    total_quantity = Column(Numeric(15, 3), nullable=False)
    quantity_unit = Column(
        String(20),
        nullable=False,
        comment='Unit of quantity: BALE, BAG, KG, MT, CANDY, QTL, etc.'
    )
    quantity_in_base_unit = Column(
        Numeric(18, 6),
        nullable=True,
        comment='Auto-calculated quantity in commodity base_unit (KG/METER/LITER)'
    )
    available_quantity = Column(Numeric(15, 3), nullable=False)
    reserved_quantity = Column(Numeric(15, 3), default=0, nullable=False)
    sold_quantity = Column(Numeric(15, 3), default=0, nullable=False)
    min_order_quantity = Column(Numeric(15, 3), nullable=True)
    allow_partial_order = Column(Boolean, default=True, nullable=False)
    
    # Pricing (supports multiple price structures)
    price_type = Column(String(20), default=PriceType.FIXED.value, nullable=False)
    base_price = Column(Numeric(15, 2), nullable=True)  # For FIXED/NEGOTIABLE
    price_unit = Column(
        String(20),
        nullable=True,
        comment='Unit for pricing: per KG, per CANDY, per MT, per BALE'
    )
    price_per_base_unit = Column(
        Numeric(15, 2),
        nullable=True,
        comment='Auto-calculated price per base_unit for consistent matching'
    )
    price_matrix = Column(JSONB, nullable=True)  # For MATRIX type
    
    # Quality Parameters (JSONB for ANY commodity)
    quality_params = Column(JSONB, nullable=True)
    
    # Test Report & Media (AI-ready for parameter extraction)
    test_report_url = Column(String(500), nullable=True, comment='PDF/Image URL of lab test report')
    test_report_verified = Column(Boolean, default=False, nullable=False)
    test_report_data = Column(
        JSONB,
        nullable=True,
        comment='AI-extracted parameters from test report: {"length": 29.0, "source": "OCR"}'
    )
    media_urls = Column(
        JSONB,
        nullable=True,
        comment='Photo/video URLs for AI quality detection: {"photos": [url1, url2], "videos": [url3]}'
    )
    ai_detected_params = Column(
        JSONB,
        nullable=True,
        comment='AI-detected quality from photos/videos: {"color": "white", "trash": 2.5, "confidence": 0.85}'
    )
    manual_override_params = Column(
        Boolean,
        default=False,
        nullable=False,
        comment='True if seller manually overrode AI-detected parameters'
    )
    
    # AI Enhancement Fields
    ai_score_vector = Column(JSONB, nullable=True)  # ML embeddings for matching
    ai_suggested_price = Column(Numeric(15, 2), nullable=True)
    ai_confidence_score = Column(Numeric(5, 4), nullable=True)  # 0.0000 to 1.0000
    ai_price_anomaly_flag = Column(Boolean, default=False, nullable=False)
    
    # Risk Management Fields (Added 2025-11-25)
    expected_price = Column(Numeric(15, 2), nullable=True)  # Seller's expected price
    estimated_trade_value = Column(Numeric(18, 2), nullable=True)  # Auto-calculated
    risk_precheck_status = Column(String(20), nullable=True, index=True)  # PASS/WARN/FAIL
    risk_precheck_score = Column(Integer, nullable=True)  # 0-100
    seller_exposure_after_trade = Column(Numeric(18, 2), nullable=True)
    seller_branch_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("partner_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment='Seller branch/location ID (from partner_locations table) for internal trade blocking logic'
    )
    blocked_for_branches = Column(Boolean, default=False, nullable=False, index=True)
    seller_rating_score = Column(Numeric(3, 2), nullable=True)  # 0.00-5.00
    seller_delivery_score = Column(Integer, nullable=True)  # 0-100
    risk_flags = Column(JSONB, nullable=True)  # Risk-related metadata
    
    # Market Visibility & Access Control
    market_visibility = Column(
        String(20),
        default=MarketVisibility.PUBLIC.value,
        nullable=False,
        index=True
    )
    restricted_buyers = Column(JSONB, nullable=True)  # For PRIVATE/RESTRICTED
    
    # Delivery Details
    delivery_terms = Column(String(50), nullable=True)  # Ex-gin, Delivered, FOB
    delivery_address = Column(Text, nullable=True)
    delivery_latitude = Column(Numeric(10, 7), nullable=True)
    delivery_longitude = Column(Numeric(10, 7), nullable=True)
    delivery_region = Column(String(50), nullable=True, index=True)
    
    # International Trade Fields
    currency_code = Column(
        String(3),
        default='INR',
        nullable=False,
        comment='Currency code (ISO 4217): INR, USD, EUR, etc.'
    )
    country_of_origin = Column(
        String(2),
        nullable=True,
        index=True,
        comment='ISO 3166-1 alpha-2 country code (IN, US, BR, etc.)'
    )
    supported_incoterms = Column(
        JSONB,
        nullable=True,
        comment='Array of supported Incoterms: ["FOB", "CIF", "EXW", "DDP"]'
    )
    export_port = Column(
        String(255),
        nullable=True,
        comment='Port code for international shipments (e.g., INNSA for Nhava Sheva)'
    )
    
    # Temporal Constraints
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    eod_cutoff = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='End-of-day cutoff time (timezone-aware). Availability expires at this time.'
    )
    
    # Status & Approval
    status = Column(
        String(20),
        default=AvailabilityStatus.DRAFT.value,
        nullable=False,
        index=True
    )
    approval_status = Column(
        String(20),
        default=ApprovalStatus.PENDING.value,
        nullable=False
    )
    approval_notes = Column(Text, nullable=True)
    approved_by = Column(PostgreSQLUUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Metadata
    notes = Column(Text, nullable=True)
    internal_reference = Column(String(100), nullable=True)
    tags = Column(JSONB, nullable=True)  # Array of tags for search
    
    # Audit Fields
    created_by = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    updated_by = Column(PostgreSQLUUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=datetime.utcnow,
        nullable=True
    )
    
    # Soft Delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_by = Column(PostgreSQLUUID(as_uuid=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    commodity = relationship("Commodity", foreign_keys=[commodity_id])
    location = relationship("Location", foreign_keys=[location_id])
    seller = relationship("BusinessPartner", foreign_keys=[seller_partner_id])
    seller_branch = relationship("PartnerLocation", foreign_keys=[seller_branch_id])
    
    # Vector embedding relationship (one-to-one)
    embedding = relationship(
        "AvailabilityEmbedding",
        back_populates="availability",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("total_quantity > 0", name="check_total_quantity_positive"),
        CheckConstraint("available_quantity >= 0", name="check_available_quantity_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="check_reserved_quantity_non_negative"),
        CheckConstraint("sold_quantity >= 0", name="check_sold_quantity_non_negative"),
        CheckConstraint("min_order_quantity IS NULL OR min_order_quantity > 0", name="check_min_order_quantity_positive"),
        CheckConstraint("base_price IS NULL OR base_price > 0", name="check_base_price_positive"),
        CheckConstraint("available_until IS NULL OR available_from IS NULL OR available_until > available_from", name="check_date_range_valid"),
        # Risk management constraints
        CheckConstraint("risk_precheck_status IS NULL OR risk_precheck_status IN ('PASS', 'WARN', 'FAIL')", name="check_risk_precheck_status_valid"),
        CheckConstraint("risk_precheck_score IS NULL OR (risk_precheck_score >= 0 AND risk_precheck_score <= 100)", name="check_risk_precheck_score_range"),
        CheckConstraint("seller_rating_score IS NULL OR (seller_rating_score >= 0 AND seller_rating_score <= 5)", name="check_seller_rating_score_range"),
        CheckConstraint("seller_delivery_score IS NULL OR (seller_delivery_score >= 0 AND seller_delivery_score <= 100)", name="check_seller_delivery_score_range"),
        CheckConstraint("expected_price IS NULL OR expected_price > 0", name="check_expected_price_positive"),
    )
    
    # ========================
    # Event Emission Methods
    # ========================
    
    def emit_created(self, user_id: UUID) -> None:
        """Emit availability.created event"""
        from backend.modules.trade_desk.events import AvailabilityCreatedEvent
        
        event = AvailabilityCreatedEvent(
            availability_id=self.id,
            seller_id=self.seller_partner_id,
            commodity_id=self.commodity_id,
            location_id=self.location_id,
            quantity=self.total_quantity,
            price=self.base_price or Decimal(0),
            market_visibility=self.market_visibility,
            quality_params=self.quality_params or {},
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        self.emit_event(
            event_type="availability.created",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_visibility_changed(
        self,
        old_visibility: str,
        new_visibility: str,
        user_id: UUID,
        reason: Optional[str] = None
    ) -> None:
        """Emit availability.visibility_changed micro-event"""
        from backend.modules.trade_desk.events import AvailabilityVisibilityChangedEvent
        
        event = AvailabilityVisibilityChangedEvent(
            availability_id=self.id,
            old_visibility=old_visibility,
            new_visibility=new_visibility,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        
        self.emit_event(
            event_type="availability.visibility_changed",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_price_changed(
        self,
        old_price: Optional[Decimal],
        new_price: Optional[Decimal],
        user_id: UUID,
        old_price_matrix: Optional[Dict[str, Any]] = None,
        new_price_matrix: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None
    ) -> None:
        """Emit availability.price_changed micro-event"""
        from backend.modules.trade_desk.events import AvailabilityPriceChangedEvent
        
        # Calculate price change percentage
        price_change_pct = None
        if old_price and new_price and old_price > 0:
            price_change_pct = ((new_price - old_price) / old_price) * 100
        
        event = AvailabilityPriceChangedEvent(
            availability_id=self.id,
            old_price=old_price,
            new_price=new_price,
            old_price_matrix=old_price_matrix,
            new_price_matrix=new_price_matrix,
            price_change_pct=price_change_pct,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        
        self.emit_event(
            event_type="availability.price_changed",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_quantity_changed(
        self,
        old_total: Decimal,
        old_available: Decimal,
        old_reserved: Decimal,
        old_sold: Decimal,
        user_id: UUID,
        reason: Optional[str] = None
    ) -> None:
        """Emit availability.quantity_changed micro-event"""
        from backend.modules.trade_desk.events import AvailabilityQuantityChangedEvent
        
        event = AvailabilityQuantityChangedEvent(
            availability_id=self.id,
            old_total_quantity=old_total,
            new_total_quantity=self.total_quantity,
            old_available_quantity=old_available,
            new_available_quantity=self.available_quantity,
            old_reserved_quantity=old_reserved,
            new_reserved_quantity=self.reserved_quantity,
            old_sold_quantity=old_sold,
            new_sold_quantity=self.sold_quantity,
            changed_by=user_id,
            changed_at=datetime.utcnow(),
            reason=reason
        )
        
        self.emit_event(
            event_type="availability.quantity_changed",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_reserved(
        self,
        reserved_qty: Decimal,
        buyer_id: UUID,
        reservation_expiry: datetime,
        user_id: UUID
    ) -> None:
        """Emit availability.reserved event"""
        from backend.modules.trade_desk.events import AvailabilityReservedEvent
        
        event = AvailabilityReservedEvent(
            availability_id=self.id,
            reserved_quantity=reserved_qty,
            buyer_id=buyer_id,
            reservation_expiry=reservation_expiry,
            reserved_by=user_id,
            reserved_at=datetime.utcnow()
        )
        
        self.emit_event(
            event_type="availability.reserved",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_released(
        self,
        released_qty: Decimal,
        buyer_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None
    ) -> None:
        """Emit availability.released event"""
        from backend.modules.trade_desk.events import AvailabilityReleasedEvent
        
        event = AvailabilityReleasedEvent(
            availability_id=self.id,
            released_quantity=released_qty,
            buyer_id=buyer_id,
            released_by=user_id,
            released_at=datetime.utcnow(),
            reason=reason
        )
        
        self.emit_event(
            event_type="availability.released",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_sold(
        self,
        sold_qty: Decimal,
        buyer_id: UUID,
        trade_id: UUID,
        sold_price: Decimal,
        user_id: UUID
    ) -> None:
        """Emit availability.sold event"""
        from backend.modules.trade_desk.events import AvailabilitySoldEvent
        
        event = AvailabilitySoldEvent(
            availability_id=self.id,
            sold_quantity=sold_qty,
            buyer_id=buyer_id,
            trade_id=trade_id,
            sold_price=sold_price,
            sold_by=user_id,
            sold_at=datetime.utcnow()
        )
        
        self.emit_event(
            event_type="availability.sold",
            user_id=user_id,
            data=event.to_dict()
        )
    
    def emit_cancelled(
        self,
        user_id: UUID,
        reason: Optional[str] = None
    ) -> None:
        """Emit availability.cancelled event"""
        from backend.modules.trade_desk.events import AvailabilityCancelledEvent
        
        event = AvailabilityCancelledEvent(
            availability_id=self.id,
            cancelled_by=user_id,
            cancelled_at=datetime.utcnow(),
            reason=reason
        )
        
        self.emit_event(
            event_type="availability.cancelled",
            user_id=user_id,
            data=event.to_dict()
        )
    
    # ========================
    # Business Logic Methods
    # ========================
    
    def can_reserve(self, quantity: Decimal) -> bool:
        """Check if quantity can be reserved"""
        if self.status != AvailabilityStatus.ACTIVE.value:
            return False
        
        if not self.allow_partial_order and quantity < self.total_quantity:
            return False
        
        if self.min_order_quantity and quantity < self.min_order_quantity:
            return False
        
        return self.available_quantity >= quantity
    
    def reserve_quantity(
        self,
        quantity: Decimal,
        buyer_id: UUID,
        reservation_expiry: datetime,
        user_id: UUID
    ) -> None:
        """Reserve quantity for negotiation"""
        if not self.can_reserve(quantity):
            raise ValueError("Cannot reserve requested quantity")
        
        old_available = self.available_quantity
        old_reserved = self.reserved_quantity
        
        self.reserved_quantity += quantity
        self.available_quantity -= quantity
        
        if self.available_quantity == 0:
            self.status = AvailabilityStatus.RESERVED.value
        
        # Emit events
        self.emit_reserved(quantity, buyer_id, reservation_expiry, user_id)
        self.emit_quantity_changed(
            self.total_quantity, old_available, old_reserved, self.sold_quantity,
            user_id, f"Reserved {quantity} for buyer {buyer_id}"
        )
    
    def release_quantity(
        self,
        quantity: Decimal,
        buyer_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None
    ) -> None:
        """Release reserved quantity"""
        if quantity > self.reserved_quantity:
            raise ValueError("Cannot release more than reserved quantity")
        
        old_available = self.available_quantity
        old_reserved = self.reserved_quantity
        
        self.reserved_quantity -= quantity
        self.available_quantity += quantity
        
        if self.reserved_quantity == 0 and self.available_quantity > 0:
            self.status = AvailabilityStatus.ACTIVE.value
        
        # Emit events
        self.emit_released(quantity, buyer_id, user_id, reason)
        self.emit_quantity_changed(
            self.total_quantity, old_available, old_reserved, self.sold_quantity,
            user_id, reason or f"Released {quantity} from buyer {buyer_id}"
        )
    
    def mark_sold(
        self,
        quantity: Decimal,
        buyer_id: UUID,
        trade_id: UUID,
        sold_price: Decimal,
        user_id: UUID
    ) -> None:
        """Mark quantity as sold"""
        if quantity > self.reserved_quantity:
            raise ValueError("Cannot sell more than reserved quantity")
        
        old_available = self.available_quantity
        old_reserved = self.reserved_quantity
        old_sold = self.sold_quantity
        
        self.reserved_quantity -= quantity
        self.sold_quantity += quantity
        
        if self.available_quantity == 0 and self.reserved_quantity == 0:
            self.status = AvailabilityStatus.SOLD.value
        
        # Emit events
        self.emit_sold(quantity, buyer_id, trade_id, sold_price, user_id)
        self.emit_quantity_changed(
            self.total_quantity, old_available, old_reserved, old_sold,
            user_id, f"Sold {quantity} to buyer {buyer_id}"
        )
    
    # ========================
    # Risk Management Methods
    # ========================
    
    def calculate_estimated_trade_value(self) -> Decimal:
        """
        Calculate estimated trade value based on available quantity and expected price.
        Uses expected_price if available, otherwise falls back to base_price.
        
        Returns:
            Decimal: Estimated trade value
        """
        price = self.expected_price or self.base_price or Decimal(0)
        quantity = self.available_quantity or Decimal(0)
        
        self.estimated_trade_value = price * quantity
        return self.estimated_trade_value
    
    def update_risk_precheck(
        self,
        seller_credit_limit_remaining: Decimal,
        seller_rating: Decimal,
        seller_delivery_performance: int,
        seller_exposure: Decimal,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Update risk precheck status and score based on seller metrics.
        Mirrors the buyer risk check from Requirement Engine.
        
        Args:
            seller_credit_limit_remaining: Remaining credit limit
            seller_rating: Seller rating score (0.00-5.00)
            seller_delivery_performance: Delivery score (0-100)
            seller_exposure: Current seller exposure
            user_id: User performing the check
            
        Returns:
            Dict with risk assessment details
        """
        # Calculate estimated trade value first
        self.calculate_estimated_trade_value()
        
        # Calculate exposure after this trade
        trade_value = self.estimated_trade_value or Decimal(0)
        self.seller_exposure_after_trade = seller_exposure + trade_value
        
        # Update seller scores
        self.seller_rating_score = seller_rating
        self.seller_delivery_score = seller_delivery_performance
        
        # Risk scoring (0-100)
        risk_score = 100
        risk_factors = []
        
        # Factor 1: Credit limit check (40 points)
        if self.seller_exposure_after_trade > seller_credit_limit_remaining:
            risk_score -= 40
            risk_factors.append(
                f"Insufficient seller credit limit (need: {trade_value}, "
                f"available: {seller_credit_limit_remaining})"
            )
        elif seller_credit_limit_remaining < trade_value * Decimal("1.2"):
            risk_score -= 20
            risk_factors.append("Low seller credit limit buffer (<20%)")
        
        # Factor 2: Seller rating (30 points)
        if seller_rating < Decimal("3.0"):
            risk_score -= 30
            risk_factors.append(f"Low seller rating (<3.0): {seller_rating}")
        elif seller_rating < Decimal("4.0"):
            risk_score -= 15
            risk_factors.append(f"Moderate seller rating (<4.0): {seller_rating}")
        
        # Factor 3: Delivery performance (30 points)
        if seller_delivery_performance < 50:
            risk_score -= 30
            risk_factors.append(f"Poor delivery history (<50): {seller_delivery_performance}")
        elif seller_delivery_performance < 75:
            risk_score -= 15
            risk_factors.append(f"Moderate delivery history (<75): {seller_delivery_performance}")
        
        # Determine status based on score
        if risk_score >= 80:
            self.risk_precheck_status = "PASS"
        elif risk_score >= 60:
            self.risk_precheck_status = "WARN"
        else:
            self.risk_precheck_status = "FAIL"
        
        self.risk_precheck_score = max(0, risk_score)
        
        # Store risk factors in JSONB
        self.risk_flags = {
            "risk_factors": risk_factors,
            "credit_limit_remaining": float(seller_credit_limit_remaining),
            "exposure_after_trade": float(self.seller_exposure_after_trade),
            "rating_score": float(seller_rating),
            "delivery_score": seller_delivery_performance,
            "assessed_at": datetime.utcnow().isoformat()
        }
        
        return {
            "risk_precheck_status": self.risk_precheck_status,
            "risk_precheck_score": self.risk_precheck_score,
            "estimated_trade_value": self.estimated_trade_value,
            "seller_exposure_after_trade": self.seller_exposure_after_trade,
            "risk_factors": risk_factors
        }
    
    def check_internal_trade_block(self, buyer_branch_id: Optional[UUID]) -> bool:
        """
        Check if availability is blocked for buyer's branch (internal trade prevention).
        
        Args:
            buyer_branch_id: Branch ID of the buyer
            
        Returns:
            bool: True if trade is blocked (same branch), False if allowed
        """
        if not self.blocked_for_branches:
            return False
        
        if not buyer_branch_id or not self.seller_branch_id:
            return False
        
        # Block if buyer and seller are from same branch
        return self.seller_branch_id == buyer_branch_id
