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
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


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
