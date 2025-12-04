"""
Pydantic Schemas for Partner Branch API

Request/Response models for multi-location management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ---------- Enums ----------

class BranchType(str, Enum):
    """Branch type classification"""
    HEAD_OFFICE = "head_office"
    WAREHOUSE = "warehouse"
    SALES_OFFICE = "sales_office"
    FACTORY = "factory"
    REGIONAL_OFFICE = "regional_office"


# ---------- Request Schemas ----------

class CreateBranchRequest(BaseModel):
    """Create new branch for partner"""
    branch_code: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="Unique code within partner (e.g., 'HO', 'WH-01')"
    )
    branch_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Display name (e.g., 'Head Office - Mumbai')"
    )
    branch_type: Optional[BranchType] = Field(None, description="Branch classification")
    
    # Address
    address_line_1: str = Field(..., max_length=200)
    address_line_2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100, description="For GST calculation")
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="India", max_length=100)
    
    # Geolocation (optional - for AI distance calculation)
    latitude: Optional[Decimal] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude for distance calculation"
    )
    longitude: Optional[Decimal] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude for distance calculation"
    )
    
    # Tax
    gstin: Optional[str] = Field(
        None,
        max_length=15,
        description="Branch-specific GSTIN if different from head office"
    )
    
    # Capabilities
    can_receive_shipments: bool = Field(
        default=False,
        description="Can be used as ship-to address"
    )
    can_send_shipments: bool = Field(
        default=False,
        description="Can be used as ship-from address"
    )
    warehouse_capacity_qtls: Optional[int] = Field(
        None,
        ge=0,
        description="Total warehouse capacity in quintals"
    )
    
    # Commodity-specific
    supported_commodities: Optional[List[str]] = Field(
        None,
        description="Array of commodity codes this branch can handle"
    )
    
    # Flags
    is_head_office: bool = Field(
        default=False,
        description="Is this the head office (default bill-to)"
    )
    is_default_ship_to: bool = Field(
        default=False,
        description="Default ship-to address"
    )
    is_default_ship_from: bool = Field(
        default=False,
        description="Default ship-from address"
    )


class UpdateBranchRequest(BaseModel):
    """Update branch details"""
    branch_name: Optional[str] = Field(None, max_length=200)
    
    # Address updates
    address_line_1: Optional[str] = Field(None, max_length=200)
    address_line_2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Geolocation
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    
    # Capabilities
    can_receive_shipments: Optional[bool] = None
    can_send_shipments: Optional[bool] = None
    warehouse_capacity_qtls: Optional[int] = Field(None, ge=0)
    supported_commodities: Optional[List[str]] = None


class SetDefaultBranchRequest(BaseModel):
    """Set default ship-to or ship-from branch"""
    branch_id: UUID = Field(..., description="Branch to set as default")
    default_type: str = Field(
        ...,
        description="'ship_to' or 'ship_from'"
    )
    
    @field_validator("default_type")
    @classmethod
    def validate_type(cls, v):
        if v not in ['ship_to', 'ship_from']:
            raise ValueError("Must be 'ship_to' or 'ship_from'")
        return v


class UpdateStockRequest(BaseModel):
    """Update branch stock level (from inventory module)"""
    quantity_delta: int = Field(
        ...,
        description="Change in stock (+ increase, - decrease)"
    )


# ---------- Response Schemas ----------

class BranchResponse(BaseModel):
    """Complete branch details"""
    id: UUID
    partner_id: UUID
    
    # Identification
    branch_code: str
    branch_name: str
    branch_type: Optional[str]
    
    # Address
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    state: str
    postal_code: str
    country: str
    
    # Geolocation
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    
    # Tax
    gstin: Optional[str]
    
    # Capabilities
    can_receive_shipments: bool
    can_send_shipments: bool
    warehouse_capacity_qtls: Optional[int]
    current_stock_qtls: Optional[int]
    
    # Commodity support
    supported_commodities: Optional[List[str]]
    
    # Flags
    is_head_office: bool
    is_default_ship_to: bool
    is_default_ship_from: bool
    is_active: bool
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    
    class Config:
        from_attributes = True


class BranchSummary(BaseModel):
    """Condensed branch info for lists"""
    id: UUID
    branch_code: str
    branch_name: str
    city: str
    state: str
    can_receive_shipments: bool
    can_send_shipments: bool
    is_head_office: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class BranchListResponse(BaseModel):
    """List of branches"""
    branches: List[BranchResponse]
    total: int


class BranchCapacityInfo(BaseModel):
    """Branch capacity details"""
    branch_id: UUID
    branch_name: str
    warehouse_capacity_qtls: Optional[int]
    current_stock_qtls: Optional[int]
    available_capacity_qtls: Optional[int]
    utilization_percentage: Optional[float]
    
    class Config:
        from_attributes = True


class BranchAddressResponse(BaseModel):
    """Address-only response (for contract freezing)"""
    branch_code: str
    branch_name: str
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    state: str
    postal_code: str
    country: str
    gstin: Optional[str]
    
    class Config:
        from_attributes = True
