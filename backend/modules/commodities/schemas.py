"""
Commodity Module Schemas

Pydantic schemas for validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ==================== Commodity Schemas ====================

class CommodityBase(BaseModel):
    """Base commodity fields"""
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    uom: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class CommodityCreate(CommodityBase):
    """Create commodity schema"""
    pass


class CommodityUpdate(BaseModel):
    """Update commodity schema (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    uom: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CommodityResponse(CommodityBase):
    """Commodity response schema"""
    id: UUID
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Variety Schemas ====================

class VarietyBase(BaseModel):
    """Base variety fields"""
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_standard: bool = False
    is_active: bool = True


class VarietyCreate(VarietyBase):
    """Create variety schema"""
    commodity_id: UUID


class VarietyUpdate(BaseModel):
    """Update variety schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_standard: Optional[bool] = None
    is_active: Optional[bool] = None


class VarietyResponse(VarietyBase):
    """Variety response schema"""
    id: UUID
    commodity_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Parameter Schemas ====================

class ParameterBase(BaseModel):
    """Base parameter fields"""
    parameter_name: str = Field(..., min_length=1, max_length=100)
    parameter_type: str = Field(..., pattern="^(NUMERIC|TEXT|RANGE)$")
    unit: Optional[str] = Field(None, max_length=50)
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    default_value: Optional[str] = Field(None, max_length=100)
    is_mandatory: bool = False
    display_order: Optional[int] = None


class ParameterCreate(ParameterBase):
    """Create parameter schema"""
    commodity_id: UUID


class ParameterUpdate(BaseModel):
    """Update parameter schema"""
    parameter_name: Optional[str] = Field(None, min_length=1, max_length=100)
    parameter_type: Optional[str] = Field(None, pattern="^(NUMERIC|TEXT|RANGE)$")
    unit: Optional[str] = Field(None, max_length=50)
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    default_value: Optional[str] = Field(None, max_length=100)
    is_mandatory: Optional[bool] = None
    display_order: Optional[int] = None


class ParameterResponse(ParameterBase):
    """Parameter response schema"""
    id: UUID
    commodity_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== System Parameter Schemas ====================

class SystemParameterCreate(BaseModel):
    """Create system parameter schema"""
    commodity_category: str = Field(..., min_length=1, max_length=100)
    parameter_name: str = Field(..., min_length=1, max_length=100)
    parameter_type: str = Field(..., pattern="^(NUMERIC|TEXT|RANGE)$")
    unit: Optional[str] = Field(None, max_length=50)
    typical_range_min: Optional[Decimal] = None
    typical_range_max: Optional[Decimal] = None
    description: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)


class SystemParameterResponse(SystemParameterCreate):
    """System parameter response schema"""
    id: UUID
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== Trade Type Schemas ====================

class TradeTypeBase(BaseModel):
    """Base trade type fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: bool = True


class TradeTypeCreate(TradeTypeBase):
    """Create trade type schema"""
    pass


class TradeTypeUpdate(BaseModel):
    """Update trade type schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TradeTypeResponse(TradeTypeBase):
    """Trade type response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Bargain Type Schemas ====================

class BargainTypeBase(BaseModel):
    """Base bargain type fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    requires_approval: bool = False
    is_active: bool = True


class BargainTypeCreate(BargainTypeBase):
    """Create bargain type schema"""
    pass


class BargainTypeUpdate(BaseModel):
    """Update bargain type schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    requires_approval: Optional[bool] = None
    is_active: Optional[bool] = None


class BargainTypeResponse(BargainTypeBase):
    """Bargain type response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Passing Term Schemas ====================

class PassingTermBase(BaseModel):
    """Base passing term fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    requires_quality_test: bool = False
    is_active: bool = True


class PassingTermCreate(PassingTermBase):
    """Create passing term schema"""
    pass


class PassingTermUpdate(BaseModel):
    """Update passing term schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    requires_quality_test: Optional[bool] = None
    is_active: Optional[bool] = None


class PassingTermResponse(PassingTermBase):
    """Passing term response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Weightment Term Schemas ====================

class WeightmentTermBase(BaseModel):
    """Base weightment term fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    weight_deduction_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: bool = True


class WeightmentTermCreate(WeightmentTermBase):
    """Create weightment term schema"""
    pass


class WeightmentTermUpdate(BaseModel):
    """Update weightment term schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    weight_deduction_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class WeightmentTermResponse(WeightmentTermBase):
    """Weightment term response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Delivery Term Schemas ====================

class DeliveryTermBase(BaseModel):
    """Base delivery term fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    includes_freight: bool = False
    includes_insurance: bool = False
    is_active: bool = True


class DeliveryTermCreate(DeliveryTermBase):
    """Create delivery term schema"""
    pass


class DeliveryTermUpdate(BaseModel):
    """Update delivery term schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    includes_freight: Optional[bool] = None
    includes_insurance: Optional[bool] = None
    is_active: Optional[bool] = None


class DeliveryTermResponse(DeliveryTermBase):
    """Delivery term response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Payment Term Schemas ====================

class PaymentTermBase(BaseModel):
    """Base payment term fields"""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    days: Optional[int] = Field(None, ge=0)
    payment_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: bool = True


class PaymentTermCreate(PaymentTermBase):
    """Create payment term schema"""
    pass


class PaymentTermUpdate(BaseModel):
    """Update payment term schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    days: Optional[int] = Field(None, ge=0)
    payment_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PaymentTermResponse(PaymentTermBase):
    """Payment term response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== Commission Schemas ====================

class CommissionBase(BaseModel):
    """Base commission fields"""
    commodity_id: Optional[UUID] = None
    trade_type_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=100)
    commission_type: str = Field(..., pattern="^(PERCENTAGE|FIXED|TIERED)$")
    rate: Optional[Decimal] = Field(None, ge=0)
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    applies_to: Optional[str] = Field(None, pattern="^(BUYER|SELLER|BOTH)$")
    description: Optional[str] = None
    is_active: bool = True


class CommissionCreate(CommissionBase):
    """Create commission schema"""
    pass


class CommissionUpdate(BaseModel):
    """Update commission schema"""
    commodity_id: Optional[UUID] = None
    trade_type_id: Optional[UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    commission_type: Optional[str] = Field(None, pattern="^(PERCENTAGE|FIXED|TIERED)$")
    rate: Optional[Decimal] = Field(None, ge=0)
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    applies_to: Optional[str] = Field(None, pattern="^(BUYER|SELLER|BOTH)$")
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CommissionResponse(CommissionBase):
    """Commission response schema"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ==================== AI Response Schemas ====================

class CategorySuggestion(BaseModel):
    """AI category suggestion"""
    category: str
    confidence: float = Field(..., ge=0, le=1)
    subcategory: Optional[str] = None


class HSNSuggestion(BaseModel):
    """AI HSN code suggestion"""
    hsn_code: str
    description: str
    gst_rate: Decimal
    confidence: float = Field(..., ge=0, le=1)


class ParameterSuggestion(BaseModel):
    """AI parameter suggestion"""
    name: str
    type: str
    unit: Optional[str]
    typical_range: Optional[List[Decimal]]
    mandatory: bool = False
    description: Optional[str] = None
