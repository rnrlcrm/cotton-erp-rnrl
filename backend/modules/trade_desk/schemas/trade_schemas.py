"""
Pydantic Schemas for Trade API

Request/Response models for instant contract creation and management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ---------- Enums ----------

class TradeStatus(str, Enum):
    """Trade lifecycle status"""
    PENDING_BRANCH_SELECTION = "PENDING_BRANCH_SELECTION"
    ACTIVE = "ACTIVE"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class GSTType(str, Enum):
    """GST calculation type"""
    INTRA_STATE = "INTRA_STATE"  # CGST + SGST
    INTER_STATE = "INTER_STATE"  # IGST


class AddressSource(str, Enum):
    """How address was selected"""
    AUTO_PRIMARY = "AUTO_PRIMARY"
    AUTO_SINGLE_BRANCH = "AUTO_SINGLE_BRANCH"
    AUTO_DEFAULT = "AUTO_DEFAULT"
    USER_SELECTED = "USER_SELECTED"


# ---------- Request Schemas ----------

class CreateTradeRequest(BaseModel):
    """
    Create instant binding contract from accepted negotiation.
    
    This is called when user accepts negotiation with legal disclaimer.
    """
    negotiation_id: UUID = Field(..., description="Accepted negotiation UUID")
    
    # Optional branch overrides (if user doesn't want AI selection)
    buyer_ship_to_branch_id: Optional[UUID] = Field(
        None, 
        description="Override ship-to branch (delivery address)"
    )
    buyer_bill_to_branch_id: Optional[UUID] = Field(
        None,
        description="Override bill-to branch (invoice address)"
    )
    seller_ship_from_branch_id: Optional[UUID] = Field(
        None,
        description="Override ship-from branch (dispatch address)"
    )
    
    # Legal acknowledgment (shown in frontend)
    acknowledged_binding_contract: bool = Field(
        ...,
        description="User acknowledged this creates legally binding contract"
    )
    
    @field_validator("acknowledged_binding_contract")
    @classmethod
    def must_acknowledge(cls, v):
        if not v:
            raise ValueError(
                "Must acknowledge contract is legally binding before creation"
            )
        return v


class UpdateTradeStatusRequest(BaseModel):
    """Update trade status in lifecycle"""
    new_status: TradeStatus = Field(..., description="New status")
    notes: Optional[str] = Field(None, description="Status change notes")


class GetBranchSuggestionsRequest(BaseModel):
    """
    Get AI-powered branch suggestions for trade.
    
    Used when partner has multiple branches - AI ranks them.
    """
    partner_id: UUID = Field(..., description="Partner UUID")
    commodity_code: str = Field(..., description="Commodity code")
    quantity_qtls: int = Field(..., gt=0, description="Quantity in quintals")
    target_state: str = Field(..., description="Counterparty state (for GST)")
    target_latitude: Optional[Decimal] = Field(None, description="For distance calc")
    target_longitude: Optional[Decimal] = Field(None, description="For distance calc")
    suggestion_type: str = Field(..., description="'ship_to' or 'ship_from'")
    
    @field_validator("suggestion_type")
    @classmethod
    def validate_type(cls, v):
        if v not in ['ship_to', 'ship_from']:
            raise ValueError("Must be 'ship_to' or 'ship_from'")
        return v


# ---------- Response Schemas ----------

class AddressSnapshot(BaseModel):
    """Frozen address snapshot (JSONB)"""
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


class GSTDetails(BaseModel):
    """GST calculation details"""
    gst_type: GSTType
    cgst_rate: Optional[Decimal]
    sgst_rate: Optional[Decimal]
    igst_rate: Optional[Decimal]
    cgst_amount: Optional[Decimal]
    sgst_amount: Optional[Decimal]
    igst_amount: Optional[Decimal]
    total_tax: Decimal
    
    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """Complete trade details"""
    id: UUID
    trade_number: str
    negotiation_id: UUID
    
    # Parties
    buyer_partner_id: UUID
    seller_partner_id: UUID
    
    # Branches (optional)
    ship_to_branch_id: Optional[UUID]
    bill_to_branch_id: Optional[UUID]
    ship_from_branch_id: Optional[UUID]
    
    # Frozen addresses (immutable snapshots)
    ship_to_address: AddressSnapshot
    bill_to_address: AddressSnapshot
    ship_from_address: AddressSnapshot
    ship_to_address_source: Optional[str]
    ship_from_address_source: Optional[str]
    
    # Commodity
    commodity_id: UUID
    commodity_variety_id: Optional[UUID]
    quantity: Decimal
    unit: str
    quality_parameters: Optional[Dict[str, Any]]
    
    # Pricing
    price_per_unit: Decimal
    total_amount: Decimal
    
    # GST
    gst_type: Optional[GSTType]
    cgst_rate: Optional[Decimal]
    sgst_rate: Optional[Decimal]
    igst_rate: Optional[Decimal]
    
    # Terms
    delivery_terms: Optional[str]
    payment_terms: Optional[str]
    delivery_timeline: Optional[str]
    delivery_city: Optional[str]
    delivery_state: Optional[str]
    
    # Contract document
    contract_pdf_url: Optional[str]
    contract_hash: Optional[str]
    contract_generated_at: Optional[datetime]
    
    # Status
    status: TradeStatus
    trade_date: date
    expected_delivery_date: Optional[date]
    actual_delivery_date: Optional[date]
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    
    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    """Paginated list of trades"""
    trades: List[TradeResponse]
    total: int
    skip: int
    limit: int


class TradeSummary(BaseModel):
    """Condensed trade info for lists"""
    id: UUID
    trade_number: str
    buyer_partner_id: UUID
    seller_partner_id: UUID
    commodity_code: str
    quantity: Decimal
    price_per_unit: Decimal
    total_amount: Decimal
    status: TradeStatus
    trade_date: date
    created_at: datetime
    
    class Config:
        from_attributes = True


class BranchSuggestion(BaseModel):
    """AI-scored branch suggestion"""
    branch_id: UUID
    branch_code: str
    branch_name: str
    address: AddressSnapshot
    
    # AI scoring
    score: float = Field(..., description="Total score 0-100")
    reasoning: str = Field(..., description="Why this score")
    breakdown: Dict[str, float] = Field(
        ..., 
        description="Score components (state_match, distance, capacity, commodity)"
    )
    
    # Capabilities
    can_receive_shipments: bool
    can_send_shipments: bool
    warehouse_capacity_qtls: Optional[int]
    current_stock_qtls: Optional[int]
    
    class Config:
        from_attributes = True


class BranchSuggestionsResponse(BaseModel):
    """Ranked list of branch suggestions"""
    suggestions: List[BranchSuggestion]
    total_branches: int
    best_match: Optional[BranchSuggestion] = Field(
        None,
        description="Highest scored branch (null if no branches)"
    )


class TradeStatistics(BaseModel):
    """Aggregate trade statistics"""
    total_trades: int
    total_value: Decimal
    average_value: Decimal
    by_status: Dict[str, int]
    
    class Config:
        from_attributes = True


class ContractGenerationStatus(BaseModel):
    """Status of async PDF generation"""
    trade_id: UUID
    trade_number: str
    contract_generated: bool
    contract_pdf_url: Optional[str]
    contract_hash: Optional[str]
    generated_at: Optional[datetime]
    error: Optional[str]
    
    class Config:
        from_attributes = True
