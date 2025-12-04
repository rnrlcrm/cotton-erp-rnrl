"""
Trade Model - Engine 5: Instant binding contracts

Handles:
- Instant trade creation on negotiation acceptance
- Multi-branch address selection (AI-suggested or user-selected)
- Contract PDF generation with pre-uploaded signatures
- Amendment workflow
- GST calculation (intra-state vs inter-state)

State Machine:
    PENDING_BRANCH_SELECTION → ACTIVE → IN_TRANSIT → DELIVERED → COMPLETED

Relationships:
    - 1 Negotiation → 1 Trade
    - 1 Trade → 2+ TradeSignatures (buyer + seller)
    - 1 Trade → MANY TradeAmendments
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Boolean,
    Numeric, Integer, Text, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base import Base
from backend.core.events.mixins import EventMixin


class Trade(Base, EventMixin):
    """
    Trade - Binding contract between buyer and seller.
    
    Created AUTOMATICALLY when negotiation is accepted.
    Status becomes ACTIVE immediately after branch selection (if needed).
    
    Key Principles:
    - Acceptance with disclaimer = Legally binding
    - Signature uploaded in profile beforehand
    - Contract PDF generated with existing signatures (instant!)
    - Trade is ACTIVE even before PDF generation
    - Addresses frozen at creation (snapshot model)
    """
    __tablename__ = "trades"
    
    # ============================================
    # PRIMARY KEY
    # ============================================
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    trade_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique trade number (TR-2025-00001)"
    )
    
    # ============================================
    # LINK TO NEGOTIATION
    # ============================================
    negotiation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("negotiations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Negotiation that created this trade"
    )
    
    # ============================================
    # PARTIES (Main Partner IDs)
    # ============================================
    buyer_partner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    seller_partner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # ============================================
    # SELECTED BRANCHES (NULL if no branches)
    # ============================================
    ship_to_branch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("partner_branches.id", ondelete="SET NULL"),
        nullable=True,
        comment="Buyer branch for delivery"
    )
    
    bill_to_branch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("partner_branches.id", ondelete="SET NULL"),
        nullable=True,
        comment="Buyer branch for billing (usually same as ship-to)"
    )
    
    ship_from_branch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("partner_branches.id", ondelete="SET NULL"),
        nullable=True,
        comment="Seller branch for shipment"
    )
    
    # ============================================
    # FROZEN ADDRESS SNAPSHOTS
    # ============================================
    ship_to_address: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Ship-to address snapshot (frozen at trade creation)"
    )
    
    bill_to_address: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Bill-to address snapshot"
    )
    
    ship_from_address: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Ship-from address snapshot"
    )
    
    # ============================================
    # ADDRESS SELECTION METADATA
    # ============================================
    ship_to_address_source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="AUTO_PRIMARY, AUTO_SINGLE_BRANCH, USER_SELECTED, DEFAULT_BRANCH"
    )
    
    ship_from_address_source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    
    # ============================================
    # COMMODITY & PRICING (from negotiation)
    # ============================================
    commodity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commodities.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    commodity_variety_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commodity_varieties.id", ondelete="SET NULL"),
        nullable=True
    )
    
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Quantity in units"
    )
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="QUINTALS"
    )
    
    price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Total trade value (quantity * price)"
    )
    
    # ============================================
    # GST CALCULATION
    # ============================================
    gst_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="INTRA_STATE (CGST+SGST), INTER_STATE (IGST)"
    )
    
    cgst_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    
    sgst_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    
    igst_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    
    # ============================================
    # TERMS (from negotiation)
    # ============================================
    delivery_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    payment_terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    quality_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    delivery_timeline: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    delivery_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    delivery_state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # ============================================
    # CONTRACT DOCUMENT
    # ============================================
    contract_pdf_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="S3 URL to generated contract PDF"
    )
    
    contract_html: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Rendered HTML before PDF conversion (for amendments)"
    )
    
    contract_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash for contract integrity verification"
    )
    
    contract_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # ============================================
    # STATUS
    # ============================================
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING_BRANCH_SELECTION",
        comment="Trade status"
    )
    
    # ============================================
    # DATES
    # ============================================
    trade_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today
    )
    
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    actual_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
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
    # CONSTRAINTS
    # ============================================
    __table_args__ = (
        CheckConstraint(
            """status IN (
                'PENDING_BRANCH_SELECTION',
                'ACTIVE',
                'IN_TRANSIT',
                'DELIVERED',
                'COMPLETED',
                'CANCELLED',
                'DISPUTED'
            )""",
            name='ck_trades_status'
        ),
        CheckConstraint(
            "gst_type IN ('INTRA_STATE', 'INTER_STATE') OR gst_type IS NULL",
            name='ck_trades_gst_type'
        ),
        CheckConstraint('quantity > 0', name='ck_trades_positive_quantity'),
        CheckConstraint('price_per_unit > 0', name='ck_trades_positive_price'),
        CheckConstraint('total_amount > 0', name='ck_trades_positive_total'),
        
        Index('ix_trades_trade_number', 'trade_number', unique=True),
        Index('ix_trades_negotiation_id', 'negotiation_id'),
        Index('ix_trades_buyer_partner_id', 'buyer_partner_id'),
        Index('ix_trades_seller_partner_id', 'seller_partner_id'),
        Index('ix_trades_status', 'status'),
        Index('ix_trades_trade_date', 'trade_date'),
        Index('ix_trades_commodity_id', 'commodity_id'),
    )
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    # negotiation: Mapped["Negotiation"] = relationship("Negotiation", back_populates="trade")
    # buyer_partner: Mapped["BusinessPartner"] = relationship("BusinessPartner", foreign_keys=[buyer_partner_id])
    # seller_partner: Mapped["BusinessPartner"] = relationship("BusinessPartner", foreign_keys=[seller_partner_id])
    # ship_to_branch: Mapped[Optional["PartnerBranch"]] = relationship("PartnerBranch", foreign_keys=[ship_to_branch_id])
    # ship_from_branch: Mapped[Optional["PartnerBranch"]] = relationship("PartnerBranch", foreign_keys=[ship_from_branch_id])
    # signatures: Mapped[List["TradeSignature"]] = relationship("TradeSignature", back_populates="trade")
    # amendments: Mapped[List["TradeAmendment"]] = relationship("TradeAmendment", back_populates="trade")
    
    # ============================================
    # METHODS
    # ============================================
    def calculate_gst_type(self) -> str:
        """
        Calculate GST type based on buyer and seller states
        """
        buyer_state = self.ship_to_address.get("state")
        seller_state = self.ship_from_address.get("state")
        
        if buyer_state == seller_state:
            return "INTRA_STATE"
        else:
            return "INTER_STATE"
    
    def is_active(self) -> bool:
        """
        Check if trade is active (binding contract)
        """
        return self.status == "ACTIVE"
    
    def can_be_amended(self) -> bool:
        """
        Check if trade can be amended
        """
        return self.status in ["ACTIVE", "PENDING_BRANCH_SELECTION"]
    
    def __repr__(self) -> str:
        return f"<Trade {self.trade_number} - {self.status}>"
