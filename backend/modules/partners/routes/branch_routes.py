"""
Branch API Routes - Multi-Location Management

All business logic is in BranchService.
Routes handle HTTP protocol only.
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
from backend.modules.partners.services.branch_service import BranchService
from backend.modules.partners.repositories.branch_repository import BranchRepository
from backend.core.errors.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException
)
from backend.modules.partners.schemas.branch_schemas import (
    CreateBranchRequest,
    UpdateBranchRequest,
    SetDefaultBranchRequest,
    UpdateStockRequest,
    BranchResponse,
    BranchListResponse,
    BranchSummary,
    BranchCapacityInfo,
    BranchAddressResponse
)


router = APIRouter(prefix="/branches", tags=["Partner Branches"])


# ---------- Dependencies ----------

def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    """Dependency: Get branch service"""
    branch_repo = BranchRepository(db)
    return BranchService(db, branch_repo)


# ---------- POST: Create Branch ----------

@router.post(
    "/",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new branch for partner"
)
async def create_branch(
    request: CreateBranchRequest,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Create new branch (warehouse, office, etc.) for partner.
    
    Supports:
    - Multiple locations per partner
    - Geolocation (lat/long) for AI distance calculation
    - Warehouse capacity tracking
    - Commodity-specific capabilities
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users with business partner can create branches"
        )
    
    try:
        # Build address data
        address_data = {
            'address_line_1': request.address_line_1,
            'address_line_2': request.address_line_2,
            'city': request.city,
            'state': request.state,
            'postal_code': request.postal_code,
            'country': request.country,
            'latitude': request.latitude,
            'longitude': request.longitude,
            'gstin': request.gstin
        }
        
        # Build capabilities
        capabilities = {
            'branch_type': request.branch_type.value if request.branch_type else None,
            'can_receive_shipments': request.can_receive_shipments,
            'can_send_shipments': request.can_send_shipments,
            'warehouse_capacity_qtls': request.warehouse_capacity_qtls,
            'supported_commodities': request.supported_commodities,
            'is_head_office': request.is_head_office,
            'is_default_ship_to': request.is_default_ship_to,
            'is_default_ship_from': request.is_default_ship_from
        }
        
        # Create branch
        branch = await service.create_branch(
            partner_id=current_user.business_partner_id,
            branch_code=request.branch_code,
            branch_name=request.branch_name,
            address_data=address_data,
            capabilities=capabilities,
            user_id=current_user.id
        )
        
        return BranchResponse.model_validate(branch)
        
    except BusinessRuleException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create branch: {str(e)}"
        )


# ---------- GET: Branch by ID ----------

@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="Get branch details by ID"
)
async def get_branch(
    branch_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """Get complete branch details including capabilities and capacity."""
    try:
        branch = await service.get_branch_by_id(branch_id, load_relationships=True)
        
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_id} not found")
        
        # Authorization: Only owner or admin
        if current_user.business_partner_id:
            if branch.partner_id != current_user.business_partner_id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to view this branch"
                )
        elif not current_user.role or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return BranchResponse.model_validate(branch)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: Partner's Branches ----------

@router.get(
    "/",
    response_model=BranchListResponse,
    summary="Get all branches for current partner"
)
async def get_my_branches(
    is_active: bool = Query(True, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Get all branches for current user's partner.
    
    Useful for:
    - Branch selection during trade creation
    - Branch management UI
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users with business partner can view branches"
        )
    
    try:
        branches = await service.get_branches_by_partner(
            partner_id=current_user.business_partner_id,
            is_active=is_active
        )
        
        return BranchListResponse(
            branches=[BranchResponse.model_validate(b) for b in branches],
            total=len(branches)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: Ship-To Branches ----------

@router.get(
    "/ship-to/available",
    response_model=BranchListResponse,
    summary="Get branches that can receive shipments"
)
async def get_ship_to_branches(
    commodity_code: Optional[str] = Query(None, description="Filter by commodity support"),
    required_capacity_qtls: Optional[int] = Query(None, ge=0, description="Filter by capacity"),
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Get branches that can receive shipments (ship-to addresses).
    
    Filters:
    - Commodity support
    - Available warehouse capacity
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        branches = await service.get_ship_to_branches(
            partner_id=current_user.business_partner_id,
            commodity_code=commodity_code,
            required_capacity_qtls=required_capacity_qtls
        )
        
        return BranchListResponse(
            branches=[BranchResponse.model_validate(b) for b in branches],
            total=len(branches)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: Ship-From Branches ----------

@router.get(
    "/ship-from/available",
    response_model=BranchListResponse,
    summary="Get branches that can send shipments"
)
async def get_ship_from_branches(
    commodity_code: Optional[str] = Query(None, description="Filter by commodity support"),
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Get branches that can send shipments (ship-from addresses).
    
    Filters:
    - Commodity support
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        branches = await service.get_ship_from_branches(
            partner_id=current_user.business_partner_id,
            commodity_code=commodity_code
        )
        
        return BranchListResponse(
            branches=[BranchResponse.model_validate(b) for b in branches],
            total=len(branches)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- PATCH: Update Branch ----------

@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="Update branch details"
)
async def update_branch(
    branch_id: UUID,
    request: UpdateBranchRequest,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Update branch address, capabilities, or capacity.
    
    Note: Updating address does NOT affect existing trades.
    Trades store frozen address snapshots.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get branch to check authorization
        branch = await service.get_branch_by_id(branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_id} not found")
        
        if branch.partner_id != current_user.business_partner_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Update
        update_data = request.model_dump(exclude_unset=True)
        updated_branch = await service.update_branch(
            branch_id=branch_id,
            update_data=update_data,
            user_id=current_user.id
        )
        
        return BranchResponse.model_validate(updated_branch)
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- DELETE: Delete Branch ----------

@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete branch (soft delete)"
)
async def delete_branch(
    branch_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Soft delete branch (set inactive).
    
    Cannot delete:
    - Last remaining branch
    - Head office if it's the only branch
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get branch to check authorization
        branch = await service.get_branch_by_id(branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_id} not found")
        
        if branch.partner_id != current_user.business_partner_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Delete
        await service.delete_branch(
            branch_id=branch_id,
            user_id=current_user.id
        )
        
        return None
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST: Set Default Branch ----------

@router.post(
    "/set-default",
    response_model=dict,
    summary="Set default ship-to or ship-from branch"
)
async def set_default_branch(
    request: SetDefaultBranchRequest,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Set default branch for ship-to or ship-from.
    
    Automatically unsets previous default.
    One default per type per partner.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get branch to check authorization
        branch = await service.get_branch_by_id(request.branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {request.branch_id} not found")
        
        if branch.partner_id != current_user.business_partner_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Set default
        if request.default_type == 'ship_to':
            await service.set_default_ship_to(
                partner_id=current_user.business_partner_id,
                branch_id=request.branch_id
            )
        else:
            await service.set_default_ship_from(
                partner_id=current_user.business_partner_id,
                branch_id=request.branch_id
            )
        
        return {
            "message": f"Default {request.default_type} branch set successfully",
            "branch_id": str(request.branch_id)
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- POST: Update Stock (Internal - From Inventory Module) ----------

@router.post(
    "/{branch_id}/stock",
    response_model=BranchResponse,
    summary="Update branch stock level"
)
async def update_branch_stock(
    branch_id: UUID,
    request: UpdateStockRequest,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service)
):
    """
    Update branch stock level (called by inventory module).
    
    Used for capacity tracking in AI branch suggestions.
    """
    # This endpoint should ideally be internal/protected
    # For now, require admin or partner ownership
    
    try:
        branch = await service.get_branch_by_id(branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_id} not found")
        
        # Authorization
        if current_user.business_partner_id:
            if branch.partner_id != current_user.business_partner_id:
                raise HTTPException(status_code=403, detail="Not authorized")
        elif not current_user.role or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Update stock
        updated_branch = await service.update_stock_level(
            branch_id=branch_id,
            quantity_delta=request.quantity_delta
        )
        
        return BranchResponse.model_validate(updated_branch)
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
