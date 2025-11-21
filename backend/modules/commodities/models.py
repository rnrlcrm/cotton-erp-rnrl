"""
Commodity Master Models

Manages all commodity-related entities including commodities, varieties,
quality parameters, trading terms, and commission structures.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class Commodity(Base):
    """Core commodity entity"""
    
    __tablename__ = "commodities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    hsn_code = Column(String(20), nullable=True, index=True)
    gst_rate = Column(Numeric(5, 2), nullable=True)
    description = Column(Text, nullable=True)
    uom = Column(String(50), nullable=True)  # Unit: MT, Quintals, Bales
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    varieties = relationship("CommodityVariety", back_populates="commodity", cascade="all, delete-orphan")
    parameters = relationship("CommodityParameter", back_populates="commodity", cascade="all, delete-orphan")
    commissions = relationship("CommissionStructure", back_populates="commodity")


class CommodityVariety(Base):
    """Commodity varieties (e.g., DCH-32, Shankar-6)"""
    
    __tablename__ = "commodity_varieties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_standard = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    commodity = relationship("Commodity", back_populates="varieties")


class CommodityParameter(Base):
    """Quality parameters for commodities"""
    
    __tablename__ = "commodity_parameters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False)
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(String(50), nullable=False)  # NUMERIC, TEXT, RANGE
    unit = Column(String(50), nullable=True)
    min_value = Column(Numeric(10, 2), nullable=True)
    max_value = Column(Numeric(10, 2), nullable=True)
    default_value = Column(String(100), nullable=True)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    commodity = relationship("Commodity", back_populates="parameters")


class SystemCommodityParameter(Base):
    """AI-suggested standard parameters for commodity categories"""
    
    __tablename__ = "system_commodity_parameters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_category = Column(String(100), nullable=False, index=True)
    parameter_name = Column(String(100), nullable=False)
    parameter_type = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=True)
    typical_range_min = Column(Numeric(10, 2), nullable=True)
    typical_range_max = Column(Numeric(10, 2), nullable=True)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)  # Industry Standard, CCI, Custom
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class TradeType(Base):
    """Types of trades (Purchase, Sale, Transfer)"""
    
    __tablename__ = "trade_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    commissions = relationship("CommissionStructure", back_populates="trade_type")


class BargainType(Base):
    """Types of bargains (Open, Closed, Firm Offer)"""
    
    __tablename__ = "bargain_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    requires_approval = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)


class PassingTerm(Base):
    """Passing/Quality acceptance terms"""
    
    __tablename__ = "passing_terms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    requires_quality_test = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)


class WeightmentTerm(Base):
    """Weightment/Weight calculation terms"""
    
    __tablename__ = "weightment_terms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    weight_deduction_percent = Column(Numeric(5, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)


class DeliveryTerm(Base):
    """Delivery terms (FOB, CIF, Ex-Works)"""
    
    __tablename__ = "delivery_terms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    includes_freight = Column(Boolean, default=False, nullable=False)
    includes_insurance = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)


class PaymentTerm(Base):
    """Payment terms (Advance, Against Delivery, Credit)"""
    
    __tablename__ = "payment_terms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=True)
    days = Column(Integer, nullable=True)  # Credit period
    payment_percentage = Column(Numeric(5, 2), nullable=True)  # % upfront
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)


class CommissionStructure(Base):
    """Commission structures for trades"""
    
    __tablename__ = "commission_structures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodities.id"), nullable=True)
    trade_type_id = Column(UUID(as_uuid=True), ForeignKey("trade_types.id"), nullable=True)
    name = Column(String(100), nullable=False)
    commission_type = Column(String(50), nullable=False)  # PERCENTAGE, FIXED, TIERED
    rate = Column(Numeric(5, 2), nullable=True)
    min_amount = Column(Numeric(15, 2), nullable=True)
    max_amount = Column(Numeric(15, 2), nullable=True)
    applies_to = Column(String(50), nullable=True)  # BUYER, SELLER, BOTH
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    commodity = relationship("Commodity", back_populates="commissions")
    trade_type = relationship("TradeType", back_populates="commissions")
