"""
Partner Branch Model - Multi-location support for business partners

Handles:
- Multiple branches/locations per business partner
- Branch-specific GSTIN (for GST optimization)
- Warehouse capacity tracking
- Ship-to/ship-from capabilities
- Geolocation for distance calculation
- Commodity handling capabilities

Used by Trade Engine for:
- AI-driven branch suggestion (state matching, distance, capacity)
- Address selection during contract generation
- GST calculation (intra-state vs inter-state)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean,
    Numeric, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base import Base
from backend.core.events.mixins import EventMixin


class PartnerBranch(Base, EventMixin):
    """
    Business Partner Branch/Location.
    
    Represents physical locations (factories, warehouses, offices)
    where a business partner can send or receive shipments.
    
    Relationships:
        - MANY PartnerBranches → 1 BusinessPartner
        - MANY Trades can reference each branch (ship-to, ship-from, bill-to)
    """
    __tablename__ = "partner_branches"
    
    # ============================================
    # PRIMARY KEY
    # ============================================
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # ============================================
    # PARENT RELATIONSHIP
    # ============================================
    partner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="CASCADE"),
        nullable=False,
        comment="Business partner who owns this branch"
    )
    
    # ============================================
    # BRANCH IDENTIFICATION
    # ============================================
    branch_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique branch code within partner (e.g., MUM-HO, AHD-01)"
    )
    
    branch_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Branch name (e.g., Mumbai Head Office, Ahmedabad Factory)"
    )
    
    branch_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="HEAD_OFFICE, FACTORY, WAREHOUSE, SALES_OFFICE, REGIONAL_OFFICE"
    )
    
    # ============================================
    # ADDRESS
    # ============================================
    address_line1: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India"
    )
    
    # ============================================
    # GEOLOCATION (for AI distance calculation)
    # ============================================
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8),
        nullable=True,
        comment="Latitude for distance calculation in AI branch suggestion"
    )
    
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(11, 8),
        nullable=True,
        comment="Longitude for distance calculation"
    )
    
    # ============================================
    # TAX
    # ============================================
    branch_gstin: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="Branch-specific GSTIN (if different from main partner GSTIN)"
    )
    
    # ============================================
    # CAPABILITIES
    # ============================================
    can_receive_shipments: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Can be used as ship-to address in trades"
    )
    
    can_send_shipments: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Can be used as ship-from address in trades"
    )
    
    warehouse_capacity_qtls: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Warehouse capacity in quintals (used by AI for suggestion)"
    )
    
    # ============================================
    # COMMODITY HANDLING
    # ============================================
    supported_commodities: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of commodity types this branch can handle, e.g., ['COTTON_RAW', 'COTTON_BALES']"
    )
    
    # ============================================
    # FLAGS
    # ============================================
    is_head_office: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    is_default_ship_to: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Use as default for receiving shipments (buyer side)"
    )
    
    is_default_ship_from: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Use as default for sending shipments (seller side)"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # ============================================
    # AUDIT
    # ============================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # ============================================
    # CONSTRAINTS (defined in __table_args__)
    # ============================================
    __table_args__ = (
        UniqueConstraint('partner_id', 'branch_code', name='uq_partner_branch_code'),
        CheckConstraint(
            "branch_type IN ('HEAD_OFFICE', 'FACTORY', 'WAREHOUSE', 'SALES_OFFICE', 'REGIONAL_OFFICE') OR branch_type IS NULL",
            name='ck_partner_branches_branch_type'
        ),
        CheckConstraint(
            'warehouse_capacity_qtls >= 0 OR warehouse_capacity_qtls IS NULL',
            name='ck_partner_branches_positive_capacity'
        ),
        Index('ix_partner_branches_partner_id', 'partner_id'),
        Index('ix_partner_branches_city_state', 'city', 'state'),
        Index('ix_partner_branches_gstin', 'branch_gstin'),
        Index('ix_partner_branches_active', 'is_active'),
        Index('ix_partner_branches_branch_type', 'branch_type'),
    )
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    # Will be defined when BusinessPartner model is updated
    # partner: Mapped["BusinessPartner"] = relationship("BusinessPartner", back_populates="branches")
    
    # ============================================
    # METHODS
    # ============================================
    def to_address_dict(self) -> Dict[str, Any]:
        """
        Convert branch to address dictionary for trade contract
        """
        return {
            "branch_id": str(self.id),
            "branch_code": self.branch_code,
            "branch_name": self.branch_name,
            "branch_type": self.branch_type,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "country": self.country,
            "gstin": self.branch_gstin,
        }
    
    def can_handle_commodity(self, commodity_type: str) -> bool:
        """
        Check if branch can handle specific commodity type
        """
        if not self.supported_commodities:
            return True  # No restriction
        
        return commodity_type in self.supported_commodities
    
    def has_capacity_for(self, quantity_qtls: Decimal) -> bool:
        """
        Check if branch has warehouse capacity for quantity
        """
        if not self.warehouse_capacity_qtls:
            return True  # No capacity limit defined
        
        return quantity_qtls <= self.warehouse_capacity_qtls
    
    def __repr__(self) -> str:
        return f"<PartnerBranch {self.branch_code} - {self.branch_name}>"
