"""
Trade API Routes - THIN WRAPPERS ONLY

All business logic is in TradeService.
Routes handle HTTP protocol and dependency injection only.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.async_session import get_db
from backend.core.auth.dependencies import get_current_user
from backend.modules.settings.models.settings_models import User
from backend.modules.trade_desk.services.trade_service import TradeService
from backend.modules.trade_desk.services.branch_suggestion_service import BranchSuggestionService
from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
from backend.modules.partners.repositories.branch_repository import BranchRepository
from backend.core.errors.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
    AuthorizationException
)
from backend.modules.trade_desk.schemas.trade_schemas import (
    CreateTradeRequest,
    UpdateTradeStatusRequest,
    GetBranchSuggestionsRequest,
    TradeResponse,
    TradeListResponse,
    TradeSummary,
    BranchSuggestionsResponse,
    BranchSuggestion,
    TradeStatistics,
    ContractGenerationStatus,
    AddressSnapshot
)


router = APIRouter(prefix="/trades", tags=["Trade Engine"])


# ---------- Dependencies ----------

def get_trade_service(db: AsyncSession = Depends(get_db)) -> TradeService:
    """Dependency: Get trade service with repositories"""
    trade_repo = TradeRepository(db)
    branch_repo = BranchRepository(db)
    return TradeService(db, trade_repo, branch_repo)


def get_branch_suggestion_service(db: AsyncSession = Depends(get_db)) -> BranchSuggestionService:
    """Dependency: Get AI branch suggestion service"""
    branch_repo = BranchRepository(db)
    return BranchSuggestionService(db, branch_repo)


# ---------- POST: Create Trade (Instant Contract) ----------

@router.post(
    "/create",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create instant binding contract from accepted negotiation"
)
async def create_trade(
    request: CreateTradeRequest,
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Create instant binding contract on negotiation acceptance.
    
    **Flow**:
    1. User accepts negotiation with legal disclaimer
    2. Signatures validated (both parties must have uploaded)
    3. Branches auto-selected OR user override
    4. Addresses frozen as immutable JSONB snapshots
    5. GST calculated (INTRA_STATE vs INTER_STATE)
    6. Trade created with status ACTIVE (legally binding!)
    7. PDF generation triggered async (5-10 seconds)
    
    **Important**: Trade is ACTIVE immediately, not waiting for PDF.
    Contract is legally binding from moment of acceptance.
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users with business partner can create trades"
        )
    
    try:
        # Build branch selections from request
        branch_selections = {}
        if request.buyer_ship_to_branch_id:
            branch_selections['buyer_ship_to_branch_id'] = request.buyer_ship_to_branch_id
        if request.buyer_bill_to_branch_id:
            branch_selections['buyer_bill_to_branch_id'] = request.buyer_bill_to_branch_id
        if request.seller_ship_from_branch_id:
            branch_selections['seller_ship_from_branch_id'] = request.seller_ship_from_branch_id
        
        # Create trade (instant contract)
        trade = await service.create_trade_from_negotiation(
            negotiation_id=request.negotiation_id,
            user_id=current_user.id,
            branch_selections=branch_selections if branch_selections else None
        )
        
        return TradeResponse.model_validate(trade)
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create trade: {str(e)}"
        )


# ---------- GET: Trade by ID ----------

@router.get(
    "/{trade_id}",
    response_model=TradeResponse,
    summary="Get trade details by ID"
)
async def get_trade(
    trade_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get complete trade details including contract, addresses, signatures.
    
    Only accessible to buyer, seller, or admin.
    """
    try:
        trade = await service.get_trade_by_id(trade_id, load_relationships=True)
        
        if not trade:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        
        # Authorization: Only buyer, seller, or admin
        if current_user.business_partner_id:
            if (trade.buyer_partner_id != current_user.business_partner_id and
                trade.seller_partner_id != current_user.business_partner_id):
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to view this trade"
                )
        elif not current_user.role or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return TradeResponse.model_validate(trade)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: My Trades ----------

@router.get(
    "/",
    response_model=TradeListResponse,
    summary="Get trades for current user's partner"
)
async def get_my_trades(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get all trades for current user's partner (as buyer or seller).
    
    Returns paginated list with filters.
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users with business partner can view trades"
        )
    
    try:
        trades = await service.get_trades_by_partner(
            partner_id=current_user.business_partner_id,
            status=status,
            skip=skip,
            limit=limit
        )
        
        return TradeListResponse(
            trades=[TradeResponse.model_validate(t) for t in trades],
            total=len(trades),
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- PATCH: Update Trade Status ----------

@router.patch(
    "/{trade_id}/status",
    response_model=TradeResponse,
    summary="Update trade status in lifecycle"
)
async def update_trade_status(
    trade_id: UUID,
    request: UpdateTradeStatusRequest,
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Update trade status (ACTIVE → IN_TRANSIT → DELIVERED → COMPLETED).
    
    Valid transitions enforced by service layer.
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users can update trade status"
        )
    
    try:
        # Get trade to check authorization
        trade = await service.get_trade_by_id(trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        
        # Authorization: Only buyer or seller
        if (trade.buyer_partner_id != current_user.business_partner_id and
            trade.seller_partner_id != current_user.business_partner_id):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to update this trade"
            )
        
        # Update status
        updated_trade = await service.update_status(
            trade_id=trade_id,
            new_status=request.new_status.value,
            user_id=current_user.id
        )
        
        return TradeResponse.model_validate(updated_trade)
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: Trade Statistics ----------

@router.get(
    "/statistics/summary",
    response_model=TradeStatistics,
    summary="Get trade statistics for partner"
)
async def get_trade_statistics(
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Get comprehensive trade statistics:
    - Total trades
    - Total value
    - Average value
    - Breakdown by status
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users can view statistics"
        )
    
    try:
        stats = await service.get_trade_statistics(
            partner_id=current_user.business_partner_id
        )
        
        return TradeStatistics(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST: Get AI Branch Suggestions ----------

@router.post(
    "/branch-suggestions",
    response_model=BranchSuggestionsResponse,
    summary="Get AI-powered branch suggestions for trade"
)
async def get_branch_suggestions(
    request: GetBranchSuggestionsRequest,
    current_user: User = Depends(get_current_user),
    ai_service: BranchSuggestionService = Depends(get_branch_suggestion_service)
):
    """
    Get AI-ranked branch suggestions based on:
    - State match (40 points) - Avoid IGST
    - Distance (30 points) - Closer = faster delivery
    - Capacity (20 points) - Warehouse space available
    - Commodity support (10 points)
    
    Returns ranked list with scores and reasoning.
    User can accept top suggestion or override.
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users can get branch suggestions"
        )
    
    # Authorization: User must be requesting for their own partner
    if request.partner_id != current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Can only get suggestions for your own partner"
        )
    
    try:
        # Get suggestions based on type
        if request.suggestion_type == 'ship_to':
            suggestions = await ai_service.suggest_ship_to_branch(
                partner_id=request.partner_id,
                commodity_code=request.commodity_code,
                quantity_qtls=request.quantity_qtls,
                target_state=request.target_state,
                target_latitude=request.target_latitude,
                target_longitude=request.target_longitude
            )
        else:  # ship_from
            suggestions = await ai_service.suggest_ship_from_branch(
                partner_id=request.partner_id,
                commodity_code=request.commodity_code,
                target_state=request.target_state,
                target_latitude=request.target_latitude,
                target_longitude=request.target_longitude
            )
        
        # Convert to response format
        branch_suggestions = []
        for sugg in suggestions:
            branch = sugg['branch']
            branch_suggestions.append(
                BranchSuggestion(
                    branch_id=branch.id,
                    branch_code=branch.branch_code,
                    branch_name=branch.branch_name,
                    address=AddressSnapshot(
                        branch_code=branch.branch_code,
                        branch_name=branch.branch_name,
                        address_line_1=branch.address_line_1,
                        address_line_2=branch.address_line_2,
                        city=branch.city,
                        state=branch.state,
                        postal_code=branch.postal_code,
                        country=branch.country,
                        gstin=branch.gstin
                    ),
                    score=sugg['score'],
                    reasoning=sugg['reasoning'],
                    breakdown=sugg['breakdown'],
                    can_receive_shipments=branch.can_receive_shipments,
                    can_send_shipments=branch.can_send_shipments,
                    warehouse_capacity_qtls=branch.warehouse_capacity_qtls,
                    current_stock_qtls=branch.current_stock_qtls
                )
            )
        
        return BranchSuggestionsResponse(
            suggestions=branch_suggestions,
            total_branches=len(branch_suggestions),
            best_match=branch_suggestions[0] if branch_suggestions else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get branch suggestions: {str(e)}"
        )


# ---------- GET: Contract Generation Status ----------

@router.get(
    "/{trade_id}/contract-status",
    response_model=ContractGenerationStatus,
    summary="Check async PDF generation status"
)
async def get_contract_status(
    trade_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service)
):
    """
    Check if contract PDF has been generated.
    
    PDF generation happens async (5-10 seconds) after trade creation.
    Trade is ACTIVE immediately, PDF follows.
    """
    try:
        trade = await service.get_trade_by_id(trade_id)
        
        if not trade:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        
        # Authorization check
        if current_user.business_partner_id:
            if (trade.buyer_partner_id != current_user.business_partner_id and
                trade.seller_partner_id != current_user.business_partner_id):
                raise HTTPException(status_code=403, detail="Not authorized")
        
        return ContractGenerationStatus(
            trade_id=trade.id,
            trade_number=trade.trade_number,
            contract_generated=bool(trade.contract_pdf_url),
            contract_pdf_url=trade.contract_pdf_url,
            contract_hash=trade.contract_hash,
            generated_at=trade.contract_generated_at,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
