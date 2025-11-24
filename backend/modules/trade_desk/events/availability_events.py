"""
Availability Events

Micro-events for real-time matching engine updates and audit trail.

Event Types:
1. availability.created - New inventory posted
2. availability.updated - General update
3. availability.visibility_changed - Market visibility changed (PUBLIC/PRIVATE/etc.)
4. availability.price_changed - Price/price_matrix updated
5. availability.quantity_changed - Quantity updated (sold/reserved/released)
6. availability.reserved - Quantity reserved (temporary hold)
7. availability.released - Reserved quantity released
8. availability.sold - Fully sold (converted to trade)
9. availability.expired - Past expiry date
10. availability.cancelled - Cancelled by seller
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class AvailabilityCreatedEvent:
    """
    Emitted when new availability is posted.
    
    Triggers:
    - Matching engine real-time scan
    - WebSocket broadcast to commodity.{id} channel
    - AI price anomaly detection
    """
    availability_id: UUID
    seller_id: UUID
    commodity_id: UUID
    location_id: UUID
    quantity: Decimal
    price: Decimal
    market_visibility: str
    quality_params: Dict[str, Any]
    created_by: UUID
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "seller_id": str(self.seller_id),
            "commodity_id": str(self.commodity_id),
            "location_id": str(self.location_id),
            "quantity": float(self.quantity),
            "price": float(self.price),
            "market_visibility": self.market_visibility,
            "quality_params": self.quality_params,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AvailabilityUpdatedEvent:
    """
    General update event (non-specific changes).
    
    Triggers:
    - Audit trail logging
    - Cache invalidation
    """
    availability_id: UUID
    updated_fields: Dict[str, Any]
    updated_by: UUID
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "updated_fields": self.updated_fields,
            "updated_by": str(self.updated_by),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AvailabilityVisibilityChangedEvent:
    """
    MICRO-EVENT: Market visibility changed.
    
    Triggers:
    - Matching engine re-scan (if changed to PUBLIC)
    - WebSocket targeted broadcast
    - Access control cache update
    
    Use Case: Seller changes from PRIVATE → PUBLIC (now visible to all buyers)
    """
    availability_id: UUID
    old_visibility: str
    new_visibility: str
    changed_by: UUID
    changed_at: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "old_visibility": self.old_visibility,
            "new_visibility": self.new_visibility,
            "changed_by": str(self.changed_by),
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
        }


@dataclass
class AvailabilityPriceChangedEvent:
    """
    MICRO-EVENT: Price/price_matrix changed.
    
    Triggers:
    - Matching engine re-score (price tolerance recalculation)
    - AI anomaly detection (price spike/drop)
    - WebSocket broadcast to watchers
    - Historical price tracking
    
    Use Case: Seller adjusts price due to market conditions
    """
    availability_id: UUID
    old_price: Optional[Decimal]
    new_price: Optional[Decimal]
    old_price_matrix: Optional[Dict[str, Any]]
    new_price_matrix: Optional[Dict[str, Any]]
    price_change_pct: Optional[Decimal]
    changed_by: UUID
    changed_at: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "old_price": float(self.old_price) if self.old_price else None,
            "new_price": float(self.new_price) if self.new_price else None,
            "old_price_matrix": self.old_price_matrix,
            "new_price_matrix": self.new_price_matrix,
            "price_change_pct": float(self.price_change_pct) if self.price_change_pct else None,
            "changed_by": str(self.changed_by),
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
        }


@dataclass
class AvailabilityQuantityChangedEvent:
    """
    MICRO-EVENT: Quantity changed (reserved/sold/released).
    
    Triggers:
    - Matching engine eligibility update
    - WebSocket broadcast (quantity update)
    - Auto status change (SOLD if available_quantity = 0)
    
    Use Case: Partial order sold → available_quantity decreased
    """
    availability_id: UUID
    old_total_quantity: Decimal
    new_total_quantity: Decimal
    old_available_quantity: Decimal
    new_available_quantity: Decimal
    old_reserved_quantity: Decimal
    new_reserved_quantity: Decimal
    old_sold_quantity: Decimal
    new_sold_quantity: Decimal
    changed_by: UUID
    changed_at: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "old_total_quantity": float(self.old_total_quantity),
            "new_total_quantity": float(self.new_total_quantity),
            "old_available_quantity": float(self.old_available_quantity),
            "new_available_quantity": float(self.new_available_quantity),
            "old_reserved_quantity": float(self.old_reserved_quantity),
            "new_reserved_quantity": float(self.new_reserved_quantity),
            "old_sold_quantity": float(self.old_sold_quantity),
            "new_sold_quantity": float(self.new_sold_quantity),
            "changed_by": str(self.changed_by),
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
        }


@dataclass
class AvailabilityReservedEvent:
    """
    Quantity reserved (temporary hold during negotiation).
    
    Triggers:
    - Status change to RESERVED
    - WebSocket notification to seller
    - Matching engine pause for this quantity
    
    Use Case: Buyer starts negotiation → reserve quantity for 24 hours
    """
    availability_id: UUID
    reserved_quantity: Decimal
    buyer_id: UUID
    reservation_expiry: datetime
    reserved_by: UUID
    reserved_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "reserved_quantity": float(self.reserved_quantity),
            "buyer_id": str(self.buyer_id),
            "reservation_expiry": self.reservation_expiry.isoformat(),
            "reserved_by": str(self.reserved_by),
            "reserved_at": self.reserved_at.isoformat(),
        }


@dataclass
class AvailabilityReleasedEvent:
    """
    Reserved quantity released (negotiation failed/expired).
    
    Triggers:
    - Status change back to ACTIVE
    - Matching engine re-activation
    - WebSocket broadcast (available again)
    
    Use Case: Negotiation failed → release reserved quantity
    """
    availability_id: UUID
    released_quantity: Decimal
    buyer_id: UUID
    released_by: UUID
    released_at: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "released_quantity": float(self.released_quantity),
            "buyer_id": str(self.buyer_id),
            "released_by": str(self.released_by),
            "released_at": self.released_at.isoformat(),
            "reason": self.reason,
        }


@dataclass
class AvailabilitySoldEvent:
    """
    Fully sold (converted to binding trade).
    
    Triggers:
    - Status change to SOLD
    - Matching engine removal
    - Trade Finalization Engine activation
    - WebSocket broadcast (no longer available)
    
    Use Case: Negotiation successful → create trade contract
    """
    availability_id: UUID
    sold_quantity: Decimal
    buyer_id: UUID
    trade_id: UUID
    sold_price: Decimal
    sold_by: UUID
    sold_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "sold_quantity": float(self.sold_quantity),
            "buyer_id": str(self.buyer_id),
            "trade_id": str(self.trade_id),
            "sold_price": float(self.sold_price),
            "sold_by": str(self.sold_by),
            "sold_at": self.sold_at.isoformat(),
        }


@dataclass
class AvailabilityExpiredEvent:
    """
    Availability expired (past expiry date).
    
    Triggers:
    - Status change to EXPIRED
    - Matching engine removal
    - WebSocket notification to seller
    - Auto-archive after 30 days
    
    Use Case: System cron job marks expired availabilities
    """
    availability_id: UUID
    expiry_date: datetime
    expired_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "expiry_date": self.expiry_date.isoformat(),
            "expired_at": self.expired_at.isoformat(),
        }


@dataclass
class AvailabilityCancelledEvent:
    """
    Cancelled by seller.
    
    Triggers:
    - Status change to CANCELLED
    - Matching engine removal
    - WebSocket notification to interested buyers
    - Release any reserved quantities
    
    Use Case: Seller sold inventory offline → cancel availability
    """
    availability_id: UUID
    cancelled_by: UUID
    cancelled_at: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability_id": str(self.availability_id),
            "cancelled_by": str(self.cancelled_by),
            "cancelled_at": self.cancelled_at.isoformat(),
            "reason": self.reason,
        }
