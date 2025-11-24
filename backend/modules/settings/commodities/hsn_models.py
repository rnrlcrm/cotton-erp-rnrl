"""
HSN Knowledge Base Models

Self-learning HSN code mapping system.
Stores learned mappings from API calls and user confirmations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.db.session import Base


class HSNKnowledgeBase(Base):
    """
    Learned HSN code mappings.
    
    Grows over time as:
    - Users create commodities and confirm HSN codes
    - System queries HSN APIs
    - AI learns from patterns
    
    Used for instant suggestions without API calls.
    """
    
    __tablename__ = "hsn_knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Search keys
    commodity_name = Column(String(200), nullable=False, index=True)
    commodity_category = Column(String(100), nullable=True, index=True)
    
    # HSN Data
    hsn_code = Column(String(20), nullable=False, index=True)
    hsn_description = Column(Text, nullable=True)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    
    # Metadata
    source = Column(String(50), nullable=False)  # API, MANUAL, AI_LEARNED, SEED
    confidence = Column(Numeric(3, 2), nullable=False, default=Decimal("1.0"))  # 0.0 to 1.0
    is_verified = Column(Boolean, default=False, nullable=False)  # User confirmed?
    usage_count = Column(Numeric(10, 0), default=0, nullable=False)  # How many times used
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Prevent duplicate mappings
    __table_args__ = (
        UniqueConstraint('commodity_name', 'hsn_code', name='uix_commodity_hsn'),
    )
    
    def __repr__(self):
        return f"<HSNKnowledge {self.commodity_name} -> {self.hsn_code} ({self.source})>"
