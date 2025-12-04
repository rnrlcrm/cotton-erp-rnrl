"""
Trade Signature Repository - Signature Audit Trail Data Access

Features:
- CRUD operations for trade signatures
- Query by trade, partner, signature tier
- Document hash verification
- Audit trail queries

Architecture:
- AsyncSession for high concurrency
- 3-tier signature support (BASIC, AADHAAR_ESIGN, DSC)
- Document integrity verification
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.trade_desk.models import TradeSignature


class SignatureRepository:
    """
    Repository for Trade Signature management.
    
    Handles 3-tier signature system and audit trail.
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
        signature_id: UUID,
        load_relationships: bool = False
    ) -> Optional[TradeSignature]:
        """
        Get signature by ID.
        
        Args:
            signature_id: Signature UUID
            load_relationships: If True, eager load trade, partner
        
        Returns:
            Signature if found, None otherwise
        """
        query = select(TradeSignature).where(TradeSignature.id == signature_id)
        
        if load_relationships:
            query = query.options(
                joinedload(TradeSignature.trade),
                joinedload(TradeSignature.partner),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_trade(
        self,
        trade_id: UUID
    ) -> List[TradeSignature]:
        """
        Get all signatures for a trade (typically 2: buyer + seller).
        
        Args:
            trade_id: Trade UUID
        
        Returns:
            List of signatures
        """
        query = select(TradeSignature).where(TradeSignature.trade_id == trade_id)
        query = query.order_by(TradeSignature.signed_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_partner_and_trade(
        self,
        partner_id: UUID,
        trade_id: UUID
    ) -> Optional[TradeSignature]:
        """
        Get signature for specific partner and trade.
        
        Unique constraint: one signature per partner per trade.
        
        Args:
            partner_id: Business partner UUID
            trade_id: Trade UUID
        
        Returns:
            Signature if exists, None otherwise
        """
        query = select(TradeSignature).where(
            and_(
                TradeSignature.partner_id == partner_id,
                TradeSignature.trade_id == trade_id
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, signature: TradeSignature) -> TradeSignature:
        """
        Create new signature.
        
        Args:
            signature: Signature model instance
        
        Returns:
            Created signature
        """
        self.db.add(signature)
        await self.db.flush()
        await self.db.refresh(signature)
        return signature
    
    # ========================
    # Tier Queries
    # ========================
    
    async def get_by_tier(
        self,
        signature_tier: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeSignature]:
        """
        Get signatures by tier (BASIC, AADHAAR_ESIGN, DSC).
        
        Args:
            signature_tier: Tier name
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of signatures
        """
        query = select(TradeSignature).where(
            TradeSignature.signature_tier == signature_tier
        )
        query = query.order_by(desc(TradeSignature.signed_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================
    # Verification
    # ========================
    
    async def verify_document_hash(
        self,
        signature_id: UUID,
        current_document_hash: str
    ) -> bool:
        """
        Verify signature's document hash matches current document.
        
        Args:
            signature_id: Signature UUID
            current_document_hash: Current document SHA-256 hash
        
        Returns:
            True if hash matches, False otherwise
        """
        signature = await self.get_by_id(signature_id)
        
        if not signature:
            return False
        
        return signature.verify_document_hash(current_document_hash)
    
    # ========================
    # Audit Queries
    # ========================
    
    async def get_signatures_by_partner(
        self,
        partner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeSignature]:
        """
        Get all signatures for a partner (audit trail).
        
        Args:
            partner_id: Business partner UUID
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of signatures
        """
        query = select(TradeSignature).where(
            TradeSignature.partner_id == partner_id
        )
        query = query.order_by(desc(TradeSignature.signed_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_signatures_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeSignature]:
        """
        Get all signatures by a user (who initiated signing).
        
        Args:
            user_id: User UUID
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of signatures
        """
        query = select(TradeSignature).where(
            TradeSignature.signed_by_user_id == user_id
        )
        query = query.order_by(desc(TradeSignature.signed_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
