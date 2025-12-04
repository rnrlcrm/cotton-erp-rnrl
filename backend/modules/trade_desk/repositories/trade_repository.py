"""
Trade Repository - Data Access Layer for Trade/Contract Management

Features:
- CRUD operations for trades (binding contracts)
- Query by negotiation, partner, commodity
- Status-based filtering (ACTIVE, COMPLETED, etc.)
- Branch-aware queries (ship-to, bill-to, ship-from)
- Trade number generation with sequential numbering
- Address snapshot management

Architecture:
- AsyncSession for high concurrency
- EventMixin integration for event-driven updates
- Eager loading for relationships
- Frozen address snapshots (JSONB)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.trade_desk.models import Trade


class TradeRepository:
    """
    Repository for Trade (Contract) management.
    
    Handles instant binding contracts created on negotiation acceptance.
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
        trade_id: UUID,
        load_relationships: bool = False
    ) -> Optional[Trade]:
        """
        Get trade by ID.
        
        Args:
            trade_id: Trade UUID
            load_relationships: If True, eager load negotiation, partners, commodity
        
        Returns:
            Trade if found, None otherwise
        """
        query = select(Trade).where(Trade.id == trade_id)
        
        if load_relationships:
            query = query.options(
                joinedload(Trade.negotiation),
                joinedload(Trade.buyer_partner),
                joinedload(Trade.seller_partner),
                joinedload(Trade.commodity),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_negotiation(
        self,
        negotiation_id: UUID
    ) -> Optional[Trade]:
        """
        Get trade by negotiation ID (one-to-one relationship).
        
        Args:
            negotiation_id: Negotiation UUID
        
        Returns:
            Trade if exists, None otherwise
        """
        query = select(Trade).where(Trade.negotiation_id == negotiation_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_partner(
        self,
        partner_id: UUID,
        role: Optional[str] = None,  # 'buyer' or 'seller'
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get all trades for a partner.
        
        Args:
            partner_id: Business partner UUID
            role: Filter by 'buyer' or 'seller', None for both
            status: Optional status filter (ACTIVE, COMPLETED, etc.)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of trades
        """
        conditions = []
        
        if role == 'buyer':
            conditions.append(Trade.buyer_partner_id == partner_id)
        elif role == 'seller':
            conditions.append(Trade.seller_partner_id == partner_id)
        else:
            # Both buyer and seller
            conditions.append(
                or_(
                    Trade.buyer_partner_id == partner_id,
                    Trade.seller_partner_id == partner_id
                )
            )
        
        if status:
            conditions.append(Trade.status == status)
        
        query = select(Trade).where(and_(*conditions))
        query = query.order_by(desc(Trade.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_commodity(
        self,
        commodity_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get all trades for a commodity.
        
        Args:
            commodity_id: Commodity UUID
            status: Optional status filter
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of trades
        """
        conditions = [Trade.commodity_id == commodity_id]
        
        if status:
            conditions.append(Trade.status == status)
        
        query = select(Trade).where(and_(*conditions))
        query = query.order_by(desc(Trade.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, trade: Trade) -> Trade:
        """
        Create new trade (instant binding contract).
        
        Args:
            trade: Trade model instance
        
        Returns:
            Created trade
        """
        self.db.add(trade)
        await self.db.flush()
        await self.db.refresh(trade)
        return trade
    
    async def update(self, trade: Trade) -> Trade:
        """
        Update trade (already modified in-memory).
        
        Args:
            trade: Modified trade instance
        
        Returns:
            Updated trade
        """
        await self.db.flush()
        await self.db.refresh(trade)
        return trade
    
    # ========================
    # Trade Number Generation
    # ========================
    
    async def generate_trade_number(self, year: Optional[int] = None) -> str:
        """
        Generate sequential trade number: TR-2025-00001
        
        Args:
            year: Optional year (default: current year)
        
        Returns:
            Trade number string
        """
        if year is None:
            year = datetime.now(timezone.utc).year
        
        # Get last trade number for this year
        query = select(func.max(Trade.trade_number)).where(
            Trade.trade_number.like(f"TR-{year}-%")
        )
        result = await self.db.execute(query)
        last_number = result.scalar_one_or_none()
        
        if last_number:
            # Extract sequence: TR-2025-00001 → 00001 → 1
            sequence = int(last_number.split('-')[-1])
            next_sequence = sequence + 1
        else:
            next_sequence = 1
        
        # Format: TR-2025-00001 (zero-padded 5 digits)
        return f"TR-{year}-{next_sequence:05d}"
    
    # ========================
    # Status Queries
    # ========================
    
    async def get_active_trades(
        self,
        partner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get all active trades (ACTIVE status).
        
        Args:
            partner_id: Optional filter by partner (buyer or seller)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of active trades
        """
        conditions = [Trade.status == "ACTIVE"]
        
        if partner_id:
            conditions.append(
                or_(
                    Trade.buyer_partner_id == partner_id,
                    Trade.seller_partner_id == partner_id
                )
            )
        
        query = select(Trade).where(and_(*conditions))
        query = query.order_by(desc(Trade.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_branch_selection(
        self,
        partner_id: UUID
    ) -> List[Trade]:
        """
        Get trades pending branch selection (PENDING_BRANCH_SELECTION status).
        
        Args:
            partner_id: Partner UUID
        
        Returns:
            List of trades awaiting branch selection
        """
        query = select(Trade).where(
            and_(
                Trade.status == "PENDING_BRANCH_SELECTION",
                or_(
                    Trade.buyer_partner_id == partner_id,
                    Trade.seller_partner_id == partner_id
                )
            )
        )
        query = query.order_by(Trade.created_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================
    # Amendment Support
    # ========================
    
    async def get_trades_requiring_pdf_regeneration(self) -> List[Trade]:
        """
        Get trades that need PDF regeneration after amendment.
        
        Returns:
            List of trades with approved amendments but stale PDFs
        """
        # This will be used by background jobs to regenerate PDFs
        # after amendments are approved
        query = select(Trade).where(
            and_(
                Trade.status.in_(["ACTIVE", "IN_TRANSIT", "DELIVERED"]),
                # Add condition for amendment flag when implemented
            )
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================
    # Statistics
    # ========================
    
    async def get_total_value_by_partner(
        self,
        partner_id: UUID,
        status: Optional[str] = None
    ) -> Decimal:
        """
        Get total trade value for a partner.
        
        Args:
            partner_id: Business partner UUID
            status: Optional status filter
        
        Returns:
            Total value (quantity * rate)
        """
        conditions = [
            or_(
                Trade.buyer_partner_id == partner_id,
                Trade.seller_partner_id == partner_id
            )
        ]
        
        if status:
            conditions.append(Trade.status == status)
        
        query = select(
            func.sum(Trade.quantity_qtls * Trade.rate_per_qtl)
        ).where(and_(*conditions))
        
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        return total or Decimal("0.00")
    
    async def get_trade_count_by_status(
        self,
        partner_id: Optional[UUID] = None
    ) -> dict:
        """
        Get count of trades by status.
        
        Args:
            partner_id: Optional filter by partner
        
        Returns:
            Dict of {status: count}
        """
        conditions = []
        
        if partner_id:
            conditions.append(
                or_(
                    Trade.buyer_partner_id == partner_id,
                    Trade.seller_partner_id == partner_id
                )
            )
        
        query = select(
            Trade.status,
            func.count(Trade.id)
        )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.group_by(Trade.status)
        
        result = await self.db.execute(query)
        return {status: count for status, count in result.all()}
