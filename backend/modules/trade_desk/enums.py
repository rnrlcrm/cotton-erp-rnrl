"""
Trade Desk Enums

Availability status, market visibility, and other enumeration types for Trade Desk module.
"""

from enum import Enum


class AvailabilityStatus(str, Enum):
    """
    Lifecycle status of an availability posting.
    
    DRAFT: Created but not yet posted
    ACTIVE: Posted and available for matching
    RESERVED: Partially/fully reserved (temporary hold)
    SOLD: Fully sold (converted to trade)
    EXPIRED: Past expiry date
    CANCELLED: Cancelled by seller
    BLOCKED: Risk check failed (circular trading, party links, etc.)
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class MarketVisibility(str, Enum):
    """
    Market visibility controls for availability postings.
    
    PUBLIC: Visible to all buyers on the platform
    PRIVATE: Visible only to specific buyers (direct relationships)
    RESTRICTED: Visible to buyers in specific regions/categories
    INTERNAL: Internal inventory (not shown externally)
    """
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    RESTRICTED = "RESTRICTED"
    INTERNAL = "INTERNAL"


class ApprovalStatus(str, Enum):
    """
    Approval workflow status for availability postings.
    
    PENDING: Awaiting approval
    APPROVED: Approved and can be posted
    REJECTED: Rejected with reason
    AUTO_APPROVED: Auto-approved based on rules
    """
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


class PriceType(str, Enum):
    """
    Price structure type.
    
    FIXED: Single fixed price
    MATRIX: Multi-dimensional price matrix (quality tiers)
    NEGOTIABLE: Price negotiable (base price provided)
    SPOT: Current spot market price
    """
    FIXED = "FIXED"
    MATRIX = "MATRIX"
    NEGOTIABLE = "NEGOTIABLE"
    SPOT = "SPOT"


# ============================================================================
# REQUIREMENT ENGINE ENUMS (Engine 2 of 5)
# ============================================================================

class RequirementStatus(str, Enum):
    """
    Lifecycle status of a requirement posting.
    
    DRAFT: Being created, not yet published
    ACTIVE: Published and searchable by sellers
    PARTIALLY_FULFILLED: Some quantity purchased
    FULFILLED: All quantity purchased
    EXPIRED: Past valid_until date
    CANCELLED: Cancelled by buyer
    BLOCKED: Risk check failed (circular trading, party links, etc.)
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class UrgencyLevel(str, Enum):
    """
    Urgency level for requirement procurement.
    
    URGENT: Need immediately (high priority matching)
    NORMAL: Standard procurement timeline
    PLANNING: Future planning (low urgency)
    """
    URGENT = "URGENT"
    NORMAL = "NORMAL"
    PLANNING = "PLANNING"


class IntentType(str, Enum):
    """
    🚀 ENHANCEMENT #1: Buyer intent type for intelligent routing.
    
    DIRECT_BUY: Immediate purchase intent (route to matching engine)
    NEGOTIATION: Want multiple offers and negotiate (route to negotiation engine)
    AUCTION_REQUEST: Reverse auction mode (route to auction module)
    PRICE_DISCOVERY_ONLY: Just exploring market prices (analytics only)
    
    Critical for autonomous trade engine decision making!
    """
    DIRECT_BUY = "DIRECT_BUY"
    NEGOTIATION = "NEGOTIATION"
    AUCTION_REQUEST = "AUCTION_REQUEST"
    PRICE_DISCOVERY_ONLY = "PRICE_DISCOVERY_ONLY"
