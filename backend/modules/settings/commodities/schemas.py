"""
Commodity Module Schemas

Pydantic schemas for validation and serialization.
Includes unit conversion schemas for Trade Desk integration.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID
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
    
    # LEGACY: Keep for backward compatibility
    uom: Optional[str] = Field(None, max_length=50)
    
    # UNIT CONVERSION FIELDS (NEW)
    base_unit: str = Field(
        default="KG", 
        max_length=50,
        description="Base storage unit (KG, METER, LITER, PIECE)"
    )
    trade_unit: Optional[str] = Field(
        None, 
        max_length=50,
        description="Trading unit (BALE, BAG, MT, QTL, CANDY, etc.)"
    )
    rate_unit: Optional[str] = Field(
        None, 
        max_length=50,
        description="Billing unit (CANDY, QTL, KG, MT, etc.)"
    )
    standard_weight_per_unit: Optional[Decimal] = Field(
        None, 
        ge=0,
        description="Custom weight for BALE/BAG (uses catalog default if null)"
    )
    
    # ==================== INTERNATIONAL FIELDS ====================
    
    # Multi-Currency Pricing
    default_currency: str = Field(default="USD", max_length=3)
    supported_currencies: Optional[List[str]] = None
    international_pricing_unit: Optional[str] = Field(None, max_length=50)
    
    # International Tax & Compliance
    hs_code_6digit: Optional[str] = Field(None, max_length=6)
    country_tax_codes: Optional[Dict] = None
    
    # Quality Standards
    quality_standards: Optional[List[str]] = None
    international_grades: Optional[Dict] = None
    certification_required: Optional[Dict] = None
    
    # Geography & Trading
    major_producing_countries: Optional[List[str]] = None
    major_consuming_countries: Optional[List[str]] = None
    trading_hubs: Optional[List[str]] = None
    
    # Exchange & Market
    traded_on_exchanges: Optional[List[str]] = None
    contract_specifications: Optional[Dict] = None
    price_volatility: Optional[str] = Field(None, max_length=20)
    
    # Import/Export
    export_regulations: Optional[Dict] = None
    import_regulations: Optional[Dict] = None
    phytosanitary_required: bool = False
    fumigation_required: bool = False
    
    # Seasonal & Storage
    seasonal_commodity: bool = False
    harvest_season: Optional[Dict] = None
    shelf_life_days: Optional[int] = None
    storage_conditions: Optional[Dict] = None
    
    # Contract Terms
    standard_lot_size: Optional[Dict] = None
    min_order_quantity: Optional[Dict] = None
    delivery_tolerance_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    weight_tolerance_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    
    is_active: bool = True


class CommodityCreate(CommodityBase):
    """Create commodity schema - inherits all international fields"""
    pass


class CommodityUpdate(BaseModel):
    """Update commodity schema (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    
    # LEGACY
    uom: Optional[str] = Field(None, max_length=50)
    
    # UNIT CONVERSION FIELDS
    base_unit: Optional[str] = Field(None, max_length=50)
    trade_unit: Optional[str] = Field(None, max_length=50)
    rate_unit: Optional[str] = Field(None, max_length=50)
    standard_weight_per_unit: Optional[Decimal] = Field(None, ge=0)
    
    # INTERNATIONAL FIELDS (all optional for update)
    default_currency: Optional[str] = Field(None, max_length=3)
    supported_currencies: Optional[List[str]] = None
    international_pricing_unit: Optional[str] = Field(None, max_length=50)
    hs_code_6digit: Optional[str] = Field(None, max_length=6)
    country_tax_codes: Optional[Dict] = None
    quality_standards: Optional[List[str]] = None
    international_grades: Optional[Dict] = None
    certification_required: Optional[Dict] = None
    major_producing_countries: Optional[List[str]] = None
    major_consuming_countries: Optional[List[str]] = None
    trading_hubs: Optional[List[str]] = None
    traded_on_exchanges: Optional[List[str]] = None
    contract_specifications: Optional[Dict] = None
    price_volatility: Optional[str] = Field(None, max_length=20)
    export_regulations: Optional[Dict] = None
    import_regulations: Optional[Dict] = None
    phytosanitary_required: Optional[bool] = None
    fumigation_required: Optional[bool] = None
    seasonal_commodity: Optional[bool] = None
    harvest_season: Optional[Dict] = None
    shelf_life_days: Optional[int] = None
    storage_conditions: Optional[Dict] = None
    standard_lot_size: Optional[Dict] = None
    min_order_quantity: Optional[Dict] = None
    delivery_tolerance_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    weight_tolerance_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    
    is_active: Optional[bool] = None


class CommodityResponse(CommodityBase):
    """Commodity response schema"""
    id: UUID
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # UNIT CONVERSION FIELDS (explicitly included for clarity)
    base_unit: str  # Inherited from CommodityBase but made explicit
    trade_unit: Optional[str] = None
    rate_unit: Optional[str] = None
    standard_weight_per_unit: Optional[Decimal] = None
    
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


class SystemParameterUpdate(BaseModel):
    """Update system parameter schema"""
    commodity_category: Optional[str] = Field(None, min_length=1, max_length=100)
    parameter_name: Optional[str] = Field(None, min_length=1, max_length=100)
    parameter_type: Optional[str] = Field(None, pattern="^(NUMERIC|TEXT|RANGE)$")
    unit: Optional[str] = Field(None, max_length=50)
    typical_range_min: Optional[Decimal] = None
    typical_range_max: Optional[Decimal] = None
    description: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)


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


class InternationalFieldsSuggestion(BaseModel):
    """AI-powered international fields suggestion"""
    confidence: float = Field(..., ge=0, le=1, description="AI confidence in suggestions")
    template_used: str = Field(..., description="Template used (Cotton, Wheat, Gold, DEFAULT)")
    international_fields: Dict = Field(..., description="Complete international field values")


class BulkUploadResult(BaseModel):
    """Result of bulk upload operation"""
    success_count: int
    error_count: int
    errors: List[str]


# ==================== Aliases for backward compatibility ====================
# Router uses longer names, schemas use shorter names

CommodityVarietyCreate = VarietyCreate
CommodityVarietyUpdate = VarietyUpdate
CommodityVarietyResponse = VarietyResponse

CommodityParameterCreate = ParameterCreate
CommodityParameterUpdate = ParameterUpdate
CommodityParameterResponse = ParameterResponse

SystemCommodityParameterCreate = SystemParameterCreate
SystemCommodityParameterUpdate = SystemParameterUpdate  
SystemCommodityParameterResponse = SystemParameterResponse

CommissionStructureCreate = CommissionCreate
CommissionStructureUpdate = CommissionUpdate
CommissionStructureResponse = CommissionResponse

BulkOperationResult = BulkUploadResult  # Alias


# ==================== Unit Conversion Schemas ====================

class ConversionCalculationRequest(BaseModel):
    """Request schema for conversion calculation endpoint"""
    trade_quantity: Decimal = Field(..., gt=0, description="Quantity in trade units (e.g., 600 BALES)")
    rate_per_unit: Decimal = Field(..., gt=0, description="Rate per rate unit (e.g., ₹50,000 per CANDY)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "trade_quantity": 600,
                "rate_per_unit": 50000
            }
        }


class ConversionCalculationResponse(BaseModel):
    """Response schema for conversion calculation with complete breakdown"""
    commodity_id: UUID
    commodity_name: str
    
    # Input values
    trade_quantity: Decimal
    trade_unit: str
    rate_per_unit: Decimal
    rate_unit: str
    
    # Calculated values
    quantity_in_base_unit: Decimal
    base_unit: str
    rate_per_base_unit: Decimal
    theoretical_billing_amount: Decimal
    
    # Breakdown details
    conversion_factors: dict = Field(
        ...,
        description="Conversion factors used",
        json_schema_extra={
            "example": {
                "trade_unit_to_base": "1 BALE = 170 KG",
                "rate_unit_to_base": "1 CANDY = 355.6222 KG"
            }
        }
    )
    
    calculation_formula: str = Field(
        ...,
        description="Human-readable calculation formula",
        json_schema_extra={
            "example": "600 BALES × 170 KG/BALE × 0.002812 CANDY/KG × ₹50,000/CANDY = ₹14,341,200"
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "commodity_id": "123e4567-e89b-12d3-a456-426614174000",
                "commodity_name": "Cotton (Shankar-6)",
                "trade_quantity": 600,
                "trade_unit": "BALE",
                "rate_per_unit": 50000,
                "rate_unit": "CANDY",
                "quantity_in_base_unit": 102000,
                "base_unit": "KG",
                "rate_per_base_unit": 140.61,
                "theoretical_billing_amount": 14341200,
                "conversion_factors": {
                    "trade_unit_to_base": "1 BALE = 170 KG",
                    "rate_unit_to_base": "1 CANDY = 355.6222 KG"
                },
                "calculation_formula": "600 BALES × 170 KG/BALE × 0.002812 CANDY/KG × ₹50,000/CANDY = ₹14,341,200"
            }
        }


class UnitInfo(BaseModel):
    """Unit information schema"""
    code: str
    name: str
    category: str
    base_unit: str
    conversion_factor: Decimal
    description: Optional[str] = None


class UnitsListResponse(BaseModel):
    """Response schema for units list endpoint"""
    categories: List[str]
    units_by_category: dict = Field(
        ...,
        description="Units grouped by category",
        json_schema_extra={
            "example": {
                "weight": [
                    {"code": "KG", "name": "Kilogram", "conversion_factor": "1.00"},
                    {"code": "CANDY", "name": "Candy", "conversion_factor": "355.6222"}
                ],
                "count": [
                    {"code": "BALE", "name": "Bale (Cotton)", "conversion_factor": "170.00"}
                ]
            }
        }
    )
    total_units: int

