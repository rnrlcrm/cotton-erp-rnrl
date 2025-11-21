"""
Commodity API Router

REST API endpoints for commodity management.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events.emitter import EventEmitter
from backend.db.session_module import get_async_session
from backend.modules.commodities.ai_helpers import CommodityAIHelper
from backend.modules.commodities.bulk_operations import (
    BulkOperationResult,
    CommodityBulkOperations,
)
from backend.modules.commodities.filters import CommodityFilter
from backend.modules.commodities.schemas import (
    BargainTypeCreate,
    BargainTypeResponse,
    BargainTypeUpdate,
    CategorySuggestion,
    CommodityCreate,
    CommodityParameterCreate,
    CommodityParameterResponse,
    CommodityParameterUpdate,
    CommodityResponse,
    CommodityUpdate,
    CommodityVarietyCreate,
    CommodityVarietyResponse,
    CommodityVarietyUpdate,
    CommissionStructureCreate,
    CommissionStructureResponse,
    CommissionStructureUpdate,
    DeliveryTermCreate,
    DeliveryTermResponse,
    DeliveryTermUpdate,
    HSNSuggestion,
    ParameterSuggestion,
    PassingTermCreate,
    PassingTermResponse,
    PassingTermUpdate,
    PaymentTermCreate,
    PaymentTermResponse,
    PaymentTermUpdate,
    SystemCommodityParameterCreate,
    SystemCommodityParameterResponse,
    SystemCommodityParameterUpdate,
    TradeTypeCreate,
    TradeTypeResponse,
    TradeTypeUpdate,
    WeightmentTermCreate,
    WeightmentTermResponse,
    WeightmentTermUpdate,
)
from backend.modules.commodities.services import (
    BargainTypeService,
    CommodityParameterService,
    CommodityService,
    CommodityVarietyService,
    CommissionStructureService,
    DeliveryTermService,
    PassingTermService,
    PaymentTermService,
    SystemCommodityParameterService,
    TradeTypeService,
    WeightmentTermService,
)

router = APIRouter(prefix="/commodities", tags=["commodities"])


# Dependency for current user (mock for now)
async def get_current_user_id() -> UUID:
    """Get current user ID from auth context"""
    # TODO: Replace with actual auth dependency
    from uuid import uuid4
    return uuid4()


# Dependency for event emitter
async def get_event_emitter(
    session: AsyncSession = Depends(get_async_session)
) -> EventEmitter:
    """Get event emitter instance"""
    return EventEmitter(session)


# Dependency for AI helper
def get_ai_helper() -> CommodityAIHelper:
    """Get AI helper instance"""
    return CommodityAIHelper()


# ===== COMMODITY ENDPOINTS =====

@router.post("/", response_model=CommodityResponse, status_code=status.HTTP_201_CREATED)
async def create_commodity(
    data: CommodityCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    ai_helper: CommodityAIHelper = Depends(get_ai_helper),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create new commodity with AI enrichment"""
    service = CommodityService(session, event_emitter, ai_helper, user_id)
    commodity = await service.create_commodity(data)
    return commodity


@router.get("/{commodity_id}", response_model=CommodityResponse)
async def get_commodity(
    commodity_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    ai_helper: CommodityAIHelper = Depends(get_ai_helper),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get commodity by ID"""
    service = CommodityService(session, event_emitter, ai_helper, user_id)
    commodity = await service.get_commodity(commodity_id)
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {commodity_id} not found"
        )
    return commodity


@router.get("/", response_model=List[CommodityResponse])
async def list_commodities(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    ai_helper: CommodityAIHelper = Depends(get_ai_helper),
    user_id: UUID = Depends(get_current_user_id)
):
    """List commodities with optional filters"""
    service = CommodityService(session, event_emitter, ai_helper, user_id)
    commodities = await service.list_commodities(category=category, is_active=is_active)
    return commodities


@router.put("/{commodity_id}", response_model=CommodityResponse)
async def update_commodity(
    commodity_id: UUID,
    data: CommodityUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    ai_helper: CommodityAIHelper = Depends(get_ai_helper),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update commodity"""
    service = CommodityService(session, event_emitter, ai_helper, user_id)
    commodity = await service.update_commodity(commodity_id, data)
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {commodity_id} not found"
        )
    return commodity


@router.delete("/{commodity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_commodity(
    commodity_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    ai_helper: CommodityAIHelper = Depends(get_ai_helper),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete commodity"""
    service = CommodityService(session, event_emitter, ai_helper, user_id)
    success = await service.delete_commodity(commodity_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {commodity_id} not found"
        )


# ===== COMMODITY AI ENDPOINTS =====

@router.post("/ai/detect-category", response_model=CategorySuggestion)
async def detect_category(
    name: str,
    description: Optional[str] = None,
    ai_helper: CommodityAIHelper = Depends(get_ai_helper)
):
    """AI: Detect commodity category from name/description"""
    suggestion = await ai_helper.detect_commodity_category(name, description)
    return suggestion


@router.post("/ai/suggest-hsn", response_model=HSNSuggestion)
async def suggest_hsn(
    name: str,
    category: str,
    description: Optional[str] = None,
    ai_helper: CommodityAIHelper = Depends(get_ai_helper)
):
    """AI: Suggest HSN code and GST rate"""
    suggestion = await ai_helper.suggest_hsn_code(name, category, description)
    return suggestion


@router.post("/{commodity_id}/ai/suggest-parameters", response_model=List[ParameterSuggestion])
async def suggest_parameters(
    commodity_id: UUID,
    category: str,
    name: str,
    ai_helper: CommodityAIHelper = Depends(get_ai_helper)
):
    """AI: Suggest quality parameters for commodity"""
    suggestions = await ai_helper.suggest_quality_parameters(commodity_id, category, name)
    return suggestions


# ===== COMMODITY VARIETY ENDPOINTS =====

@router.post("/{commodity_id}/varieties", response_model=CommodityVarietyResponse, status_code=status.HTTP_201_CREATED)
async def add_variety(
    commodity_id: UUID,
    data: CommodityVarietyCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Add variety to commodity"""
    # Ensure commodity_id matches
    data.commodity_id = commodity_id
    
    service = CommodityVarietyService(session, event_emitter, user_id)
    variety = await service.add_variety(data)
    return variety


@router.get("/{commodity_id}/varieties", response_model=List[CommodityVarietyResponse])
async def list_varieties(
    commodity_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List varieties for commodity"""
    service = CommodityVarietyService(session, event_emitter, user_id)
    varieties = await service.list_varieties(commodity_id=commodity_id)
    return varieties


@router.put("/varieties/{variety_id}", response_model=CommodityVarietyResponse)
async def update_variety(
    variety_id: UUID,
    data: CommodityVarietyUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update variety"""
    service = CommodityVarietyService(session, event_emitter, user_id)
    variety = await service.update_variety(variety_id, data)
    if not variety:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variety {variety_id} not found"
        )
    return variety


# ===== COMMODITY PARAMETER ENDPOINTS =====

@router.post("/{commodity_id}/parameters", response_model=CommodityParameterResponse, status_code=status.HTTP_201_CREATED)
async def add_parameter(
    commodity_id: UUID,
    data: CommodityParameterCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Add quality parameter to commodity"""
    # Ensure commodity_id matches
    data.commodity_id = commodity_id
    
    service = CommodityParameterService(session, event_emitter, user_id)
    parameter = await service.add_parameter(data)
    return parameter


@router.get("/{commodity_id}/parameters", response_model=List[CommodityParameterResponse])
async def list_parameters(
    commodity_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List parameters for commodity"""
    service = CommodityParameterService(session, event_emitter, user_id)
    parameters = await service.list_parameters(commodity_id=commodity_id)
    return parameters


@router.put("/parameters/{parameter_id}", response_model=CommodityParameterResponse)
async def update_parameter(
    parameter_id: UUID,
    data: CommodityParameterUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update parameter"""
    service = CommodityParameterService(session, event_emitter, user_id)
    parameter = await service.update_parameter(parameter_id, data)
    if not parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter {parameter_id} not found"
        )
    return parameter


# ===== SYSTEM PARAMETER ENDPOINTS =====

@router.post("/system-parameters", response_model=SystemCommodityParameterResponse, status_code=status.HTTP_201_CREATED)
async def create_system_parameter(
    data: SystemCommodityParameterCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create system-wide commodity parameter"""
    service = SystemCommodityParameterService(session)
    parameter = await service.create_parameter(data)
    return parameter


@router.get("/system-parameters", response_model=List[SystemCommodityParameterResponse])
async def list_system_parameters(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """List system parameters"""
    service = SystemCommodityParameterService(session)
    parameters = await service.list_parameters(category=category)
    return parameters


@router.put("/system-parameters/{parameter_id}", response_model=SystemCommodityParameterResponse)
async def update_system_parameter(
    parameter_id: UUID,
    data: SystemCommodityParameterUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update system parameter"""
    service = SystemCommodityParameterService(session)
    parameter = await service.update_parameter(parameter_id, data)
    if not parameter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System parameter {parameter_id} not found"
        )
    return parameter


# ===== TRADE TYPE ENDPOINTS =====

@router.post("/trade-types", response_model=TradeTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_trade_type(
    data: TradeTypeCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create trade type"""
    service = TradeTypeService(session, event_emitter, user_id)
    trade_type = await service.create_trade_type(data)
    return trade_type


@router.get("/trade-types", response_model=List[TradeTypeResponse])
async def list_trade_types(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all trade types"""
    service = TradeTypeService(session, event_emitter, user_id)
    trade_types = await service.list_trade_types()
    return trade_types


@router.put("/trade-types/{trade_type_id}", response_model=TradeTypeResponse)
async def update_trade_type(
    trade_type_id: UUID,
    data: TradeTypeUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update trade type"""
    service = TradeTypeService(session, event_emitter, user_id)
    trade_type = await service.update_trade_type(trade_type_id, data)
    if not trade_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade type {trade_type_id} not found"
        )
    return trade_type


# ===== BARGAIN TYPE ENDPOINTS =====

@router.post("/bargain-types", response_model=BargainTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_bargain_type(
    data: BargainTypeCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create bargain type"""
    service = BargainTypeService(session, event_emitter, user_id)
    bargain_type = await service.create_bargain_type(data)
    return bargain_type


@router.get("/bargain-types", response_model=List[BargainTypeResponse])
async def list_bargain_types(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all bargain types"""
    service = BargainTypeService(session, event_emitter, user_id)
    bargain_types = await service.list_bargain_types()
    return bargain_types


@router.put("/bargain-types/{bargain_type_id}", response_model=BargainTypeResponse)
async def update_bargain_type(
    bargain_type_id: UUID,
    data: BargainTypeUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update bargain type"""
    service = BargainTypeService(session, event_emitter, user_id)
    bargain_type = await service.update_bargain_type(bargain_type_id, data)
    if not bargain_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bargain type {bargain_type_id} not found"
        )
    return bargain_type


# ===== PASSING TERM ENDPOINTS =====

@router.post("/passing-terms", response_model=PassingTermResponse, status_code=status.HTTP_201_CREATED)
async def create_passing_term(
    data: PassingTermCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create passing term"""
    service = PassingTermService(session, event_emitter, user_id)
    term = await service.create_passing_term(data)
    return term


@router.get("/passing-terms", response_model=List[PassingTermResponse])
async def list_passing_terms(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all passing terms"""
    service = PassingTermService(session, event_emitter, user_id)
    terms = await service.list_passing_terms()
    return terms


@router.put("/passing-terms/{term_id}", response_model=PassingTermResponse)
async def update_passing_term(
    term_id: UUID,
    data: PassingTermUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update passing term"""
    service = PassingTermService(session, event_emitter, user_id)
    term = await service.update_passing_term(term_id, data)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passing term {term_id} not found"
        )
    return term


# ===== WEIGHTMENT TERM ENDPOINTS =====

@router.post("/weightment-terms", response_model=WeightmentTermResponse, status_code=status.HTTP_201_CREATED)
async def create_weightment_term(
    data: WeightmentTermCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create weightment term"""
    service = WeightmentTermService(session, event_emitter, user_id)
    term = await service.create_weightment_term(data)
    return term


@router.get("/weightment-terms", response_model=List[WeightmentTermResponse])
async def list_weightment_terms(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all weightment terms"""
    service = WeightmentTermService(session, event_emitter, user_id)
    terms = await service.list_weightment_terms()
    return terms


@router.put("/weightment-terms/{term_id}", response_model=WeightmentTermResponse)
async def update_weightment_term(
    term_id: UUID,
    data: WeightmentTermUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update weightment term"""
    service = WeightmentTermService(session, event_emitter, user_id)
    term = await service.update_weightment_term(term_id, data)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weightment term {term_id} not found"
        )
    return term


# ===== DELIVERY TERM ENDPOINTS =====

@router.post("/delivery-terms", response_model=DeliveryTermResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_term(
    data: DeliveryTermCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create delivery term"""
    service = DeliveryTermService(session, event_emitter, user_id)
    term = await service.create_delivery_term(data)
    return term


@router.get("/delivery-terms", response_model=List[DeliveryTermResponse])
async def list_delivery_terms(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all delivery terms"""
    service = DeliveryTermService(session, event_emitter, user_id)
    terms = await service.list_delivery_terms()
    return terms


@router.put("/delivery-terms/{term_id}", response_model=DeliveryTermResponse)
async def update_delivery_term(
    term_id: UUID,
    data: DeliveryTermUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update delivery term"""
    service = DeliveryTermService(session, event_emitter, user_id)
    term = await service.update_delivery_term(term_id, data)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery term {term_id} not found"
        )
    return term


# ===== PAYMENT TERM ENDPOINTS =====

@router.post("/payment-terms", response_model=PaymentTermResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_term(
    data: PaymentTermCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create payment term"""
    service = PaymentTermService(session, event_emitter, user_id)
    term = await service.create_payment_term(data)
    return term


@router.get("/payment-terms", response_model=List[PaymentTermResponse])
async def list_payment_terms(
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all payment terms"""
    service = PaymentTermService(session, event_emitter, user_id)
    terms = await service.list_payment_terms()
    return terms


@router.put("/payment-terms/{term_id}", response_model=PaymentTermResponse)
async def update_payment_term(
    term_id: UUID,
    data: PaymentTermUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update payment term"""
    service = PaymentTermService(session, event_emitter, user_id)
    term = await service.update_payment_term(term_id, data)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment term {term_id} not found"
        )
    return term


# ===== COMMISSION STRUCTURE ENDPOINTS =====

@router.post("/{commodity_id}/commission", response_model=CommissionStructureResponse, status_code=status.HTTP_201_CREATED)
async def set_commission(
    commodity_id: UUID,
    data: CommissionStructureCreate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Set commission structure for commodity"""
    # Ensure commodity_id matches
    data.commodity_id = commodity_id
    
    service = CommissionStructureService(session, event_emitter, user_id)
    commission = await service.set_commission(data)
    return commission


@router.get("/{commodity_id}/commission", response_model=CommissionStructureResponse)
async def get_commission(
    commodity_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get commission structure for commodity"""
    service = CommissionStructureService(session, event_emitter, user_id)
    commission = await service.get_commission(commodity_id)
    if not commission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commission structure not found for commodity {commodity_id}"
        )
    return commission


@router.put("/commission/{commission_id}", response_model=CommissionStructureResponse)
async def update_commission(
    commission_id: UUID,
    data: CommissionStructureUpdate,
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update commission structure"""
    service = CommissionStructureService(session, event_emitter, user_id)
    commission = await service.update_commission(commission_id, data)
    if not commission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commission structure {commission_id} not found"
        )
    return commission


# ===== BULK OPERATIONS & EXCEL ENDPOINTS =====

@router.post("/bulk/upload", response_model=BulkOperationResult)
async def bulk_upload_commodities(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Bulk upload commodities from Excel file.
    
    Accepts .xlsx or .csv file with columns:
    - name, category, hsn_code, gst_rate, description, uom
    
    Returns summary of import results.
    """
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be Excel (.xlsx) or CSV (.csv)"
        )
    
    content = await file.read()
    bulk_ops = CommodityBulkOperations(session, event_emitter, user_id)
    
    result = await bulk_ops.import_from_excel(BytesIO(content))
    return result


@router.get("/bulk/download")
async def download_commodities_template(
    include_data: bool = False,
    session: AsyncSession = Depends(get_async_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Download Excel template for bulk commodity upload.
    
    - include_data=false: Returns empty template
    - include_data=true: Returns template with existing commodities
    """
    bulk_ops = CommodityBulkOperations(session, None, user_id)
    
    if include_data:
        # Export existing commodities
        excel_file = await bulk_ops.export_to_excel()
        filename = "commodities_export.xlsx"
    else:
        # Download empty template
        excel_file = await bulk_ops.generate_template()
        filename = "commodities_template.xlsx"
    
    return StreamingResponse(
        BytesIO(excel_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/search/advanced", response_model=List[CommodityResponse])
async def advanced_search_commodities(
    query: Optional[str] = None,
    category: Optional[str] = None,
    hsn_code: Optional[str] = None,
    min_gst_rate: Optional[float] = None,
    max_gst_rate: Optional[float] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Advanced search with multiple filters.
    
    Supports:
    - Full-text search in name and description
    - Category filtering
    - HSN code filtering
    - GST rate range
    - Active/inactive status
    - Pagination
    """
    filter_criteria = CommodityFilter(
        query=query,
        category=category,
        hsn_code=hsn_code,
        min_gst_rate=min_gst_rate,
        max_gst_rate=max_gst_rate,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    service = CommodityService(session, event_emitter=EventEmitter(session), user_id=user_id)
    commodities = await service.search_commodities(filter_criteria)
    return commodities


@router.post("/bulk/validate")
async def validate_bulk_upload(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Validate bulk upload file without importing.
    
    Returns validation errors and warnings before actual import.
    """
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be Excel (.xlsx) or CSV (.csv)"
        )
    
    content = await file.read()
    bulk_ops = CommodityBulkOperations(session, None, user_id)
    
    validation_result = await bulk_ops.validate_import_file(BytesIO(content))
    return validation_result
