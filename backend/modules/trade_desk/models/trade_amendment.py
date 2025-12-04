"""
Trade Amendment Model - Change requests for active trades

Handles:
- Address changes after contract generation
- Quantity/price amendments (future)
- Delivery date changes
- Approval workflow (counterparty consent)
- Contract regeneration after approval

Amendment Types:
- ADDRESS_CHANGE: Change ship-to, ship-from, or bill-to address
- QUANTITY_CHANGE: Modify quantity (future)
- PRICE_CHANGE: Adjust price (future)
- DELIVERY_DATE_CHANGE: Change expected delivery date
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Text,
    Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base import Base
from backend.core.events.mixins import EventMixin


class TradeAmendment(Base, EventMixin):
    """
    Trade Amendment - Change request for active trade.
    
    Workflow:
    1. Party requests amendment (e.g., change delivery address)
    2. System determines if counterparty approval needed:
       - Trade status PENDING_BRANCH_SELECTION: Auto-approve
       - Trade status ACTIVE: Requires approval
    3. Counterparty approves/rejects
    4. If approved: Contract PDF regenerated, emails sent
    5. Amendment logged for audit trail
    """
    __tablename__ = "trade_amendments"
    
    # ============================================
    # PRIMARY KEY
    # ============================================
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # ============================================
    # TRADE REFERENCE
    # ============================================
    trade_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # ============================================
    # AMENDMENT TYPE
    # ============================================
    amendment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ADDRESS_CHANGE, QUANTITY_CHANGE, PRICE_CHANGE, DELIVERY_DATE_CHANGE"
    )
    
    # ============================================
    # WHAT CHANGED
    # ============================================
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Field that was amended (e.g., ship_to_address, quantity)"
    )
    
    old_value: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Original value before amendment"
    )
    
    new_value: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="New value after amendment"
    )
    
    # ============================================
    # REASON
    # ============================================
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for amendment provided by requesting party"
    )
    
    # ============================================
    # APPROVAL WORKFLOW
    # ============================================
    requires_counterparty_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether counterparty approval is needed"
    )
    
    requested_by_party: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="BUYER or SELLER"
    )
    
    requested_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # ============================================
    # STATUS
    # ============================================
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="PENDING, APPROVED, REJECTED"
    )
    
    # ============================================
    # APPROVAL
    # ============================================
    approved_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for rejection (if rejected)"
    )
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # ============================================
    # CONSTRAINTS
    # ============================================
    __table_args__ = (
        CheckConstraint(
            "amendment_type IN ('ADDRESS_CHANGE', 'QUANTITY_CHANGE', 'PRICE_CHANGE', 'DELIVERY_DATE_CHANGE')",
            name='ck_trade_amendments_type'
        ),
        CheckConstraint(
            "requested_by_party IN ('BUYER', 'SELLER')",
            name='ck_trade_amendments_party'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name='ck_trade_amendments_status'
        ),
        Index('ix_trade_amendments_trade_id', 'trade_id'),
        Index('ix_trade_amendments_status', 'status'),
    )
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    # trade: Mapped["Trade"] = relationship("Trade", back_populates="amendments")
    # requested_by_user: Mapped["User"] = relationship("User", foreign_keys=[requested_by_user_id])
    # approved_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_user_id])
    
    # ============================================
    # METHODS
    # ============================================
    def is_pending(self) -> bool:
        """
        Check if amendment is awaiting approval
        """
        return self.status == "PENDING"
    
    def is_approved(self) -> bool:
        """
        Check if amendment was approved
        """
        return self.status == "APPROVED"
    
    def is_rejected(self) -> bool:
        """
        Check if amendment was rejected
        """
        return self.status == "REJECTED"
    
    def approve(self, approved_by_user_id: UUID) -> None:
        """
        Approve amendment
        """
        self.status = "APPROVED"
        self.approved_by_user_id = approved_by_user_id
        self.approved_at = datetime.utcnow()
    
    def reject(self, rejected_by_user_id: UUID, reason: str) -> None:
        """
        Reject amendment
        """
        self.status = "REJECTED"
        self.approved_by_user_id = rejected_by_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
    
    def __repr__(self) -> str:
        return f"<TradeAmendment {self.amendment_type} - {self.status}>"
