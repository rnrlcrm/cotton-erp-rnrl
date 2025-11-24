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
- SELLER: Can only sell from registered locations (location_id must be in business_partner.locations)
- TRADER: Can sell from any location (no restriction)
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
        nullable=False,
        index=True
    )
    seller_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Quantity Management (auto-updated by trigger)
    total_quantity = Column(Numeric(15, 3), nullable=False)
    available_quantity = Column(Numeric(15, 3), nullable=False)
    reserved_quantity = Column(Numeric(15, 3), default=0, nullable=False)
    sold_quantity = Column(Numeric(15, 3), default=0, nullable=False)
    min_order_quantity = Column(Numeric(15, 3), nullable=True)
    allow_partial_order = Column(Boolean, default=True, nullable=False)
    
    # Pricing (supports multiple price structures)
    price_type = Column(String(20), default=PriceType.FIXED.value, nullable=False)
    base_price = Column(Numeric(15, 2), nullable=True)  # For FIXED/NEGOTIABLE
    price_matrix = Column(JSONB, nullable=True)  # For MATRIX (quality tiers)
    currency = Column(String(3), default="INR", nullable=False)
    price_uom = Column(String(20), nullable=True)  # Per MT, Quintal, Bale
    
    # Quality Parameters (JSONB for ANY commodity)
    quality_params = Column(JSONB, nullable=True)
    
    # AI Enhancement Fields
    ai_score_vector = Column(JSONB, nullable=True)  # ML embeddings for matching
    ai_suggested_price = Column(Numeric(15, 2), nullable=True)
    ai_confidence_score = Column(Numeric(5, 4), nullable=True)  # 0.0000 to 1.0000
    ai_price_anomaly_flag = Column(Boolean, default=False, nullable=False)
    
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
    
    # Temporal Constraints
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    
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
    seller = relationship("BusinessPartner", foreign_keys=[seller_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint("total_quantity > 0", name="check_total_quantity_positive"),
        CheckConstraint("available_quantity >= 0", name="check_available_quantity_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="check_reserved_quantity_non_negative"),
        CheckConstraint("sold_quantity >= 0", name="check_sold_quantity_non_negative"),
        CheckConstraint("min_order_quantity IS NULL OR min_order_quantity > 0", name="check_min_order_quantity_positive"),
        CheckConstraint("base_price IS NULL OR base_price > 0", name="check_base_price_positive"),
        CheckConstraint("available_until IS NULL OR available_from IS NULL OR available_until > available_from", name="check_date_range_valid"),
    )
    
    # ========================
    # Event Emission Methods
    # ========================
    
    def emit_created(self, user_id: UUID) -> None:
        """Emit availability.created event"""
        from backend.modules.trade_desk.events import AvailabilityCreatedEvent
        
        event = AvailabilityCreatedEvent(
            availability_id=self.id,
            seller_id=self.seller_id,
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
