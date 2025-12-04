"""
Trade Amendment Repository - Amendment Workflow Data Access

Features:
- CRUD operations for trade amendments
- Query by trade, status, type
- Approval workflow support
- Amendment history tracking

Architecture:
- AsyncSession for high concurrency
- Status-based queries (PENDING, APPROVED, REJECTED)
- Type filtering (ADDRESS_CHANGE, QUANTITY_CHANGE, etc.)
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.trade_desk.models import TradeAmendment


class AmendmentRepository:
    """
    Repository for Trade Amendment management.
    
    Handles address changes and other contract amendments.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    # ========================
    # Basic CRUD Operations
    # ========================
    
    async def get_by_id(
        self,
        amendment_id: UUID,
        load_relationships: bool = False
    ) -> Optional[TradeAmendment]:
        """
        Get amendment by ID.
        
        Args:
            amendment_id: Amendment UUID
            load_relationships: If True, eager load trade, requester
        
        Returns:
            Amendment if found, None otherwise
        """
        query = select(TradeAmendment).where(TradeAmendment.id == amendment_id)
        
        if load_relationships:
            query = query.options(
                joinedload(TradeAmendment.trade),
                joinedload(TradeAmendment.requested_by_user),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_trade(
        self,
        trade_id: UUID,
        status: Optional[str] = None
    ) -> List[TradeAmendment]:
        """
        Get all amendments for a trade.
        
        Args:
            trade_id: Trade UUID
            status: Optional status filter (PENDING, APPROVED, REJECTED)
        
        Returns:
            List of amendments
        """
        conditions = [TradeAmendment.trade_id == trade_id]
        
        if status:
            conditions.append(TradeAmendment.status == status)
        
        query = select(TradeAmendment).where(and_(*conditions))
        query = query.order_by(desc(TradeAmendment.requested_at))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, amendment: TradeAmendment) -> TradeAmendment:
        """
        Create new amendment request.
        
        Args:
            amendment: Amendment model instance
        
        Returns:
            Created amendment
        """
        self.db.add(amendment)
        await self.db.flush()
        await self.db.refresh(amendment)
        return amendment
    
    async def update(self, amendment: TradeAmendment) -> TradeAmendment:
        """
        Update amendment (already modified in-memory).
        
        Args:
            amendment: Modified amendment instance
        
        Returns:
            Updated amendment
        """
        await self.db.flush()
        await self.db.refresh(amendment)
        return amendment
    
    # ========================
    # Type Queries
    # ========================
    
    async def get_by_type(
        self,
        amendment_type: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeAmendment]:
        """
        Get amendments by type.
        
        Args:
            amendment_type: Amendment type (ADDRESS_CHANGE, QUANTITY_CHANGE, etc.)
            status: Optional status filter
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of amendments
        """
        conditions = [TradeAmendment.amendment_type == amendment_type]
        
        if status:
            conditions.append(TradeAmendment.status == status)
        
        query = select(TradeAmendment).where(and_(*conditions))
        query = query.order_by(desc(TradeAmendment.requested_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================
    # Status Queries
    # ========================
    
    async def get_pending_amendments(
        self,
        trade_id: Optional[UUID] = None
    ) -> List[TradeAmendment]:
        """
        Get all pending amendments.
        
        Args:
            trade_id: Optional filter by trade
        
        Returns:
            List of pending amendments
        """
        conditions = [TradeAmendment.status == "PENDING"]
        
        if trade_id:
            conditions.append(TradeAmendment.trade_id == trade_id)
        
        query = select(TradeAmendment).where(and_(*conditions))
        query = query.order_by(TradeAmendment.requested_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_for_partner(
        self,
        partner_id: UUID
    ) -> List[TradeAmendment]:
        """
        Get pending amendments requiring partner's approval.
        
        This joins with trades to find amendments where partner is buyer/seller
        and requires counterparty approval.
        
        Args:
            partner_id: Business partner UUID
        
        Returns:
            List of amendments awaiting approval
        """
        from backend.modules.trade_desk.models import Trade
        
        query = select(TradeAmendment).join(
            Trade, TradeAmendment.trade_id == Trade.id
        ).where(
            and_(
                TradeAmendment.status == "PENDING",
                TradeAmendment.requires_counterparty_approval == True,  # noqa: E712
                # Partner is buyer or seller (not requester)
                or_(
                    Trade.buyer_partner_id == partner_id,
                    Trade.seller_partner_id == partner_id
                )
            )
        )
        
        query = query.order_by(TradeAmendment.requested_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_approved_amendments(
        self,
        trade_id: UUID
    ) -> List[TradeAmendment]:
        """
        Get all approved amendments for a trade.
        
        Args:
            trade_id: Trade UUID
        
        Returns:
            List of approved amendments
        """
        query = select(TradeAmendment).where(
            and_(
                TradeAmendment.trade_id == trade_id,
                TradeAmendment.status == "APPROVED"
            )
        )
        query = query.order_by(TradeAmendment.approved_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================
    # Amendment History
    # ========================
    
    async def get_amendment_history(
        self,
        trade_id: UUID
    ) -> List[TradeAmendment]:
        """
        Get complete amendment history for a trade (all statuses).
        
        Args:
            trade_id: Trade UUID
        
        Returns:
            List of all amendments (chronological)
        """
        query = select(TradeAmendment).where(
            TradeAmendment.trade_id == trade_id
        )
        query = query.order_by(TradeAmendment.requested_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_amendments(
        self,
        days: int = 7,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeAmendment]:
        """
        Get recent amendments (for admin dashboard).
        
        Args:
            days: Number of days to look back
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of recent amendments
        """
        from datetime import datetime, timedelta, timezone
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(TradeAmendment).where(
            TradeAmendment.requested_at >= cutoff
        )
        query = query.order_by(desc(TradeAmendment.requested_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
