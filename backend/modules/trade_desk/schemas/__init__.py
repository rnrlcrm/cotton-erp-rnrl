"""
Trade Desk API Schemas

Pydantic schemas for request/response validation.
Includes Availability Engine and Requirement Engine schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Import Requirement schemas
from backend.modules.trade_desk.schemas.requirement_schemas import (
    AIAdjustmentRequest,
    AIAdjustmentResponse,
    CancelRequirementRequest,
    DemandStatisticsResponse,
    FulfillmentUpdateRequest,
    IntentSearchRequest,
    RequirementCreateRequest,
    RequirementEventResponse,
    RequirementHistoryResponse,
    RequirementResponse,
    RequirementSearchRequest,
    RequirementSearchResponse,
    RequirementSearchResult,
    RequirementUpdateRequest,
)

# Availability schemas remain in this file for backward compatibility


# ========================
# Request Schemas
# ========================

class AvailabilityCreateRequest(BaseModel):
    """
    Request schema for creating availability.
    
    MANDATORY FIELDS (as per business rules):
    - commodity_id: What is being sold
    - location_id: Where it's available (seller can use ANY location)
    - total_quantity: How much is available
    - quality_params: Quality parameters (commodity-specific, validated against CommodityParameter)
    
    AUTO-POPULATED FIELDS:
    - quantity_unit: Auto-populated from commodity.trade_unit (BALE, KG, CANDY, etc.)
    - price_unit: Auto-populated from commodity.rate_unit (per KG, per CANDY, etc.)
    
    OPTIONAL FIELDS:
    - base_price: Price is optional (can be negotiable/on-request)
    - test_report_url: Optional lab test report
    - media_urls: Optional photos/videos for AI quality detection
    """
    
    # ========== MANDATORY FIELDS ==========
    commodity_id: UUID = Field(..., description="Commodity UUID (REQUIRED)")
    
    # LOCATION: Either registered location_id OR ad-hoc location details
    location_id: Optional[UUID] = Field(None, description="Registered location UUID (use this OR provide ad-hoc location)")
    
    # AD-HOC LOCATION (if location_id not provided, these become REQUIRED)
    location_address: Optional[str] = Field(None, description="Full address (required if location_id not provided)")
    location_latitude: Optional[Decimal] = Field(None, description="Latitude from Google Maps (required if location_id not provided)")
    location_longitude: Optional[Decimal] = Field(None, description="Longitude from Google Maps (required if location_id not provided)")
    location_pincode: Optional[str] = Field(None, description="Pincode (optional for ad-hoc location)")
    location_region: Optional[str] = Field(None, description="Region/State (optional for ad-hoc location)")
    
    total_quantity: Decimal = Field(..., gt=0, description="Total quantity available (REQUIRED)")
    quality_params: Dict[str, Any] = Field(
        ..., 
        description="Quality parameters - MANDATORY (validated against commodity parameters)"
    )
    
    # ========== AUTO-POPULATED (DO NOT SEND FROM CLIENT) ==========
    quantity_unit: Optional[str] = Field(
        None, 
        description="AUTO: Populated from commodity.trade_unit (BALE, CANDY, MT, QTL, KG). DO NOT send from client."
    )
    price_unit: Optional[str] = Field(
        None, 
        description="AUTO: Populated from commodity.rate_unit (per CANDY, per KG). DO NOT send from client."
    )
    
    # ========== OPTIONAL FIELDS ==========
    base_price: Optional[Decimal] = Field(None, gt=0, description="Base price (OPTIONAL - can be negotiable)")
    price_matrix: Optional[Dict[str, Any]] = Field(None, description="Price matrix JSONB (for MATRIX type)")
    test_report_url: Optional[str] = Field(None, description="URL to test report PDF/Image")
    media_urls: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Photo/video URLs for AI: {'photos': [url1], 'videos': [url2]}"
    )
    market_visibility: str = Field("PUBLIC", description="PUBLIC, PRIVATE, RESTRICTED, INTERNAL")
    allow_partial_order: bool = Field(True, description="Allow partial fills")
    min_order_quantity: Optional[Decimal] = Field(None, gt=0, description="Minimum order quantity")
    delivery_terms: Optional[str] = Field(None, description="Ex-gin, Delivered, FOB")
    delivery_address: Optional[str] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @field_validator('quality_params')
    @classmethod
    def validate_quality_params_not_empty(cls, v):
        """Ensure quality_params is not empty."""
        if not v or len(v) == 0:
            raise ValueError("quality_params cannot be empty - at least one parameter required")
        return v
    
    @model_validator(mode='after')
    def validate_location(self):
        """Ensure EITHER location_id OR ad-hoc location is provided."""
        has_location_id = self.location_id is not None
        has_adhoc = all([
            self.location_address,
            self.location_latitude is not None,
            self.location_longitude is not None
        ])
        
        if not has_location_id and not has_adhoc:
            raise ValueError(
                "Must provide EITHER location_id (registered) OR ad-hoc location "
                "(location_address + location_latitude + location_longitude)"
            )
        
        if has_location_id and has_adhoc:
            raise ValueError(
                "Cannot provide BOTH location_id and ad-hoc location. Choose one."
            )
        
        return self
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Using REGISTERED location from settings table",
                    "value": {
                        "commodity_id": "123e4567-e89b-12d3-a456-426614174000",
                        "location_id": "123e4567-e89b-12d3-a456-426614174001",
                        "total_quantity": 100.0,
                        "base_price": 8000.0,
                        "quality_params": {
                            "length": 29.0,
                            "strength": 26.0,
                            "micronaire": 4.5
                        }
                    }
                },
                {
                    "description": "Using AD-HOC location with Google Maps coordinates",
                    "value": {
                        "commodity_id": "123e4567-e89b-12d3-a456-426614174000",
                        "location_address": "Warehouse 5, GIDC Industrial Area, Surat, Gujarat",
                        "location_latitude": 21.1702,
                        "location_longitude": 72.8311,
                        "location_pincode": "395008",
                        "location_region": "Gujarat",
                        "total_quantity": 100.0,
                        "base_price": 8000.0,
                        "quality_params": {
                            "length": 29.0,
                            "strength": 26.0,
                            "micronaire": 4.5
                        }
                    }
                }
            ]
        }


class AvailabilityUpdateRequest(BaseModel):
    """Request schema for updating availability."""
    
    total_quantity: Optional[Decimal] = Field(None, gt=0)
    base_price: Optional[Decimal] = Field(None, gt=0)
    # quantity_unit and price_unit are auto-populated from commodity master, cannot be updated
    price_matrix: Optional[Dict[str, Any]] = None
    quality_params: Optional[Dict[str, Any]] = None
    test_report_url: Optional[str] = None
    media_urls: Optional[Dict[str, List[str]]] = None
    market_visibility: Optional[str] = None
    allow_partial_order: Optional[bool] = None
    min_order_quantity: Optional[Decimal] = Field(None, gt=0)
    delivery_terms: Optional[str] = None
    delivery_address: Optional[str] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_price": 8200.0,
                "market_visibility": "RESTRICTED"
            }
        }


class AvailabilitySearchRequest(BaseModel):
    """Request schema for smart search."""
    
    commodity_id: Optional[UUID] = None
    quality_params: Optional[Dict[str, Any]] = None
    quality_tolerance: Optional[Dict[str, float]] = Field(
        None,
        description="Tolerance for each quality param (e.g., {'length': 1.0})"
    )
    min_price: Optional[Decimal] = Field(None, gt=0)
    max_price: Optional[Decimal] = Field(None, gt=0)
    price_tolerance_pct: Optional[float] = Field(None, ge=0, le=100)
    location_id: Optional[UUID] = None
    delivery_region: Optional[str] = None
    max_distance_km: Optional[float] = Field(None, gt=0)
    buyer_latitude: Optional[float] = Field(None, ge=-90, le=90)
    buyer_longitude: Optional[float] = Field(None, ge=-180, le=180)
    min_quantity: Optional[Decimal] = Field(None, gt=0)
    allow_partial: Optional[bool] = None
    market_visibility: Optional[List[str]] = None
    exclude_anomalies: bool = Field(True, description="Exclude price anomalies")
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "commodity_id": "123e4567-e89b-12d3-a456-426614174000",
                "quality_params": {"length": 29.0, "strength": 26.0},
                "quality_tolerance": {"length": 1.0, "strength": 2.0},
                "max_price": 75000.0,
                "price_tolerance_pct": 10.0,
                "buyer_latitude": 23.0225,
                "buyer_longitude": 72.5714,
                "max_distance_km": 200.0,
                "exclude_anomalies": True
            }
        }


class ReserveRequest(BaseModel):
    """Request schema for reserving quantity."""
    
    quantity: Decimal = Field(gt=0, description="Quantity to reserve")
    buyer_id: UUID = Field(description="Buyer partner UUID (who is reserving)")
    reservation_hours: int = Field(24, ge=1, le=168, description="Reservation duration (default 24h)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 50.0,
                "buyer_id": "123e4567-e89b-12d3-a456-426614174000",
                "reservation_hours": 24
            }
        }


class ReleaseRequest(BaseModel):
    """Request schema for releasing reserved quantity."""
    
    quantity: Decimal = Field(gt=0, description="Quantity to release")
    reason: Optional[str] = Field(None, description="Reason for release")
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 50.0,
                "reason": "Negotiation failed"
            }
        }


class MarkSoldRequest(BaseModel):
    """Request schema for marking availability as sold."""
    
    quantity: Decimal = Field(gt=0, description="Quantity sold")
    trade_id: UUID = Field(description="Trade contract UUID")
    sold_price: Decimal = Field(gt=0, description="Final negotiated price")
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 50.0,
                "trade_id": "123e4567-e89b-12d3-a456-426614174002",
                "sold_price": 71500.0
            }
        }


class ApprovalRequest(BaseModel):
    """Request schema for approving availability."""
    
    approval_notes: Optional[str] = Field(None, description="Approval notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "approval_notes": "Price verified against market rates"
            }
        }


# ========================
# Response Schemas
# ========================

class CommodityResponse(BaseModel):
    """Commodity details in response."""
    
    id: UUID
    name: str
    category: str
    hsn_code: Optional[str]
    uom: Optional[str]
    
    class Config:
        from_attributes = True


class LocationResponse(BaseModel):
    """Location details in response."""
    
    id: UUID
    name: str
    city: Optional[str]
    district: Optional[str]
    state: Optional[str]
    region: Optional[str]
    
    class Config:
        from_attributes = True


class BusinessPartnerResponse(BaseModel):
    """Business partner details in response."""
    
    id: UUID
    name: str
    partner_type: str
    
    class Config:
        from_attributes = True


class AvailabilityResponse(BaseModel):
    """Availability response with all details."""
    
    id: UUID
    seller_partner_id: UUID
    commodity_id: UUID
    location_id: UUID
    
    # Quantities
    total_quantity: Decimal
    quantity_unit: str
    quantity_in_base_unit: Optional[Decimal]
    available_quantity: Decimal
    reserved_quantity: Decimal
    sold_quantity: Decimal
    min_order_quantity: Optional[Decimal]
    allow_partial_order: bool
    
    # Pricing
    price_type: str
    base_price: Optional[Decimal]
    price_unit: Optional[str]
    price_per_base_unit: Optional[Decimal]
    price_matrix: Optional[Dict[str, Any]]
    currency: str
    price_uom: Optional[str]  # DEPRECATED: Use price_unit
    
    # Quality
    quality_params: Optional[Dict[str, Any]]
    
    # Test Report & Media (AI-ready)
    test_report_url: Optional[str]
    test_report_verified: bool
    test_report_data: Optional[Dict[str, Any]]
    media_urls: Optional[Dict[str, List[str]]]
    ai_detected_params: Optional[Dict[str, Any]]
    manual_override_params: bool
    
    # AI Fields
    ai_score_vector: Optional[Dict[str, Any]]
    ai_suggested_price: Optional[Decimal]
    ai_confidence_score: Optional[Decimal]
    ai_price_anomaly_flag: bool
    
    # Market Visibility
    market_visibility: str
    restricted_buyers: Optional[Dict[str, Any]]
    
    # Delivery
    delivery_terms: Optional[str]
    delivery_address: Optional[str]
    delivery_latitude: Optional[Decimal]
    delivery_longitude: Optional[Decimal]
    delivery_region: Optional[str]
    
    # Temporal
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    expiry_date: Optional[datetime]
    
    # Status
    status: str
    approval_status: str
    approval_notes: Optional[str]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    
    # Metadata
    notes: Optional[str]
    internal_reference: Optional[str]
    tags: Optional[Dict[str, Any]]
    
    # Audit
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Relationships (optional eager loading)
    commodity: Optional[CommodityResponse] = None
    location: Optional[LocationResponse] = None
    seller: Optional[BusinessPartnerResponse] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "seller_partner_id": "123e4567-e89b-12d3-a456-426614174004",
                "commodity_id": "123e4567-e89b-12d3-a456-426614174000",
                "location_id": "123e4567-e89b-12d3-a456-426614174001",
                "total_quantity": 100.0,
                "quantity_unit": "CANDY",
                "quantity_in_base_unit": 35562.22,
                "available_quantity": 100.0,
                "reserved_quantity": 0.0,
                "sold_quantity": 0.0,
                "allow_partial_order": True,
                "price_type": "FIXED",
                "base_price": 8000.0,
                "price_unit": "per CANDY",
                "price_per_base_unit": 22.50,
                "currency": "INR",
                "quality_params": {"length": 29.0, "strength": 26.0},
                "test_report_url": "https://storage.example.com/test-reports/abc123.pdf",
                "test_report_verified": False,
                "media_urls": {"photos": ["https://storage.example.com/photos/cotton1.jpg"], "videos": []},
                "manual_override_params": False,
                "ai_price_anomaly_flag": False,
                "market_visibility": "PUBLIC",
                "status": "ACTIVE",
                "approval_status": "APPROVED"
            }
        }


class AvailabilitySearchResult(BaseModel):
    """Single search result with match score."""
    
    availability: AvailabilityResponse
    match_score: float = Field(ge=0.0, le=1.0, description="AI match score (0.0 to 1.0)")
    distance_km: Optional[float] = Field(None, description="Distance from buyer in km")
    ai_confidence: Optional[Decimal] = Field(None, description="AI confidence score")
    ai_suggested_price: Optional[Decimal] = Field(None, description="AI suggested price")
    
    class Config:
        json_schema_extra = {
            "example": {
                "availability": {"id": "...", "status": "ACTIVE"},
                "match_score": 0.87,
                "distance_km": 45.2,
                "ai_confidence": 0.92
            }
        }


class AvailabilitySearchResponse(BaseModel):
    """Search response with multiple results."""
    
    results: List[AvailabilitySearchResult]
    total: int
    skip: int
    limit: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [],
                "total": 42,
                "skip": 0,
                "limit": 100
            }
        }


class NegotiationReadinessResponse(BaseModel):
    """Negotiation readiness score response."""
    
    readiness_score: float = Field(ge=0.0, le=1.0)
    factors: Dict[str, float]
    recommendations: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "readiness_score": 0.85,
                "factors": {
                    "quality_complete": 0.8,
                    "price_available": 1.0,
                    "delivery_clear": 1.0,
                    "quantity_adequate": 1.0
                },
                "recommendations": []
            }
        }


class SimilarCommodityResponse(BaseModel):
    """Similar commodity suggestion."""
    
    commodity_id: UUID
    commodity_name: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    reason: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "commodity_id": "123e4567-e89b-12d3-a456-426614174005",
                "commodity_name": "Cotton 28mm",
                "similarity_score": 0.92,
                "reason": "Similar length parameter (28mm vs 29mm)"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str
    error_code: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Availability not found",
                "error_code": "AVAILABILITY_NOT_FOUND"
            }
        }
