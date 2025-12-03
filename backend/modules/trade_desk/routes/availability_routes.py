"""
Availability Engine REST API - Complete with Authentication

Features:
- JWT authentication via get_current_user
- Seller/buyer context extraction from user
- RBAC for internal endpoints
- Complete error handling
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.dependencies import get_current_user, require_permissions
from backend.db.async_session import get_db
from backend.app.dependencies import get_redis
from backend.modules.trade_desk.schemas import (
    ApprovalRequest,
    AvailabilityCreateRequest,
    AvailabilityResponse,
    AvailabilitySearchRequest,
    AvailabilitySearchResponse,
    AvailabilityUpdateRequest,
    ErrorResponse,
    MarkSoldRequest,
    NegotiationReadinessResponse,
    ReleaseRequest,
    ReserveRequest,
    SimilarCommodityResponse,
)
from backend.modules.trade_desk.services import AvailabilityService

router = APIRouter(prefix="/availabilities", tags=["Availability Engine"])


# ========================
# Public REST APIs
# ========================

@router.post(
    "",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new availability",
    description="""Post new inventory availability with AI enhancements.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicate postings.
    - Same key within 24h returns cached response (no duplicate created)
    - Use UUID or unique transaction ID as idempotency key
    - Example: `Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000`
    """
)
async def create_availability(
    request: AvailabilityCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.TRADE_SELL))
):
    """
    Create new availability posting.
    
    Workflow:
    1. Validates seller location (SELLER=own, TRADER=any)
    2. Auto-normalizes quality parameters
    3. Detects price anomalies
    4. Calculates AI score vector
    5. Auto-fetches delivery coordinates
    6. Creates availability (status=DRAFT)
    7. Emits availability.created event
    
    **Idempotency**:
    - Middleware automatically handles `Idempotency-Key` header
    - If duplicate key detected within 24h: returns cached response (201 → 200)
    - No duplicate availability created
    - Recommended for all POST operations from mobile/unreliable networks
    
    Returns: Created availability with AI enhancements
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    seller_id = current_user.business_partner_id
    service = AvailabilityService(db, redis_client=redis_client)
    
    try:
        availability = await service.create_availability(
            seller_id=seller_id,
            commodity_id=request.commodity_id,
            location_id=request.location_id,
            total_quantity=request.total_quantity,
            quantity_unit=request.quantity_unit,
            base_price=request.base_price,
            price_unit=request.price_unit,
            price_matrix=request.price_matrix,
            quality_params=request.quality_params,
            test_report_url=request.test_report_url,
            media_urls=request.media_urls,
            market_visibility=request.market_visibility,
            allow_partial_order=request.allow_partial_order,
            min_order_quantity=request.min_order_quantity,
            delivery_terms=request.delivery_terms,
            delivery_address=request.delivery_address,
            expiry_date=request.expiry_date,
            created_by=current_user.id,
            notes=request.notes,
            tags={"tags": request.tags} if request.tags else None
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/search",
    response_model=AvailabilitySearchResponse,
    summary="[DEPRECATED] AI-powered smart search - Use instant matching instead",
    description="⚠️ DEPRECATED: This marketplace-style search is deprecated. System now uses INSTANT AUTOMATIC MATCHING. When you post a requirement, matches are found automatically in real-time.",
    deprecated=True
)
async def search_availabilities(
    request: AvailabilitySearchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.TRADE_BUY))
):
    """
    ⚠️ DEPRECATED ENDPOINT
    
    This marketplace-style search is deprecated. The system now uses INSTANT AUTOMATIC MATCHING:
    
    **New Workflow:**
    1. Buyer posts requirement → System instantly finds matching availabilities
    2. Seller posts availability → System instantly finds matching requirements
    3. Matches are sent via notifications/events (NO manual browsing needed)
    
    **Why this changed:**
    - Real-time matching is faster and more efficient
    - Prevents users from seeing stale/already-matched inventory
    - Ensures best matches based on AI scoring and risk assessment
    - No marketplace listing - direct peer-to-peer matching only
    
    **Recommendation:** 
    Use POST /requirements instead. Matches will be delivered instantly.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "ENDPOINT_DEPRECATED",
            "message": "Marketplace-style search is deprecated. Use INSTANT AUTOMATIC MATCHING instead.",
            "recommendation": "Post a requirement (POST /requirements) and receive instant matches via notifications.",
            "reason": "System moved from marketplace listing to real-time peer-to-peer matching for better efficiency and accuracy."
        }
    )


@router.get(
    "/my",
    response_model=List[AvailabilityResponse],
    summary="Get seller's inventory",
    description="Get all availabilities posted by current user"
)
async def get_my_availabilities(
    status_filter: str = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.TRADE_SELL))
):
    """Get seller's inventory list."""
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    seller_id = current_user.business_partner_id
    service = AvailabilityService(db, redis_client=redis_client)
    
    availabilities = await service.get_seller_availabilities(
        seller_id=seller_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    
    return [AvailabilityResponse.from_orm(a) for a in availabilities]


@router.get(
    "/{availability_id}",
    response_model=AvailabilityResponse,
    summary="Get availability by ID",
    responses={404: {"model": ErrorResponse}}
)
async def get_availability(
    availability_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get single availability by ID."""
    service = AvailabilityService(db, redis_client=redis_client)
    availability = await service.repo.get_by_id(availability_id, load_relationships=True)
    
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability not found"
        )
    
    return AvailabilityResponse.from_orm(availability)


@router.put(
    "/{availability_id}",
    response_model=AvailabilityResponse,
    summary="Update availability",
    responses={404: {"model": ErrorResponse}}
)
async def update_availability(
    availability_id: UUID,
    request: AvailabilityUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_UPDATE))
):
    """Update availability (seller only). Requires AVAILABILITY_UPDATE capability."""
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    seller_id = current_user.business_partner_id
    service = AvailabilityService(db, redis_client=redis_client)
    
    # Verify ownership
    existing = await service.repo.get_by_id(availability_id)
    if not existing or existing.seller_id != seller_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability not found or access denied"
        )
    
    try:
        availability = await service.update_availability(
            availability_id=availability_id,
            updates=request.dict(exclude_unset=True),
            updated_by=current_user.id
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{availability_id}/approve",
    response_model=AvailabilityResponse,
    summary="Approve availability",
    description="Approve availability for public listing (requires AVAILABILITY_APPROVE capability)"
)
async def approve_availability(
    availability_id: UUID,
    request: ApprovalRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_APPROVE))
):
    """Approve availability for public listing (CRITICAL). Requires AVAILABILITY_APPROVE capability."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    try:
        # Service handles: event emission, commit, idempotency
        availability = await service.approve_availability(
            availability_id=availability_id,
            approved_by=current_user.id,
            approval_notes=request.notes,
            idempotency_key=idempotency_key
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ========================
# Internal APIs (Matching/Negotiation Engines)
# ========================

@router.post(
    "/{availability_id}/reserve",
    response_model=AvailabilityResponse,
    summary="Reserve quantity (Internal API)",
    description="Called by Matching Engine to reserve quantity for negotiation. Requires AVAILABILITY_RESERVE capability.",
    tags=["Internal APIs"]
)
async def reserve_quantity(
    availability_id: UUID,
    request: ReserveRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_RESERVE))
):
    """Reserve quantity for negotiation (internal API). Requires AVAILABILITY_RESERVE capability."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    try:
        availability = await service.reserve_availability(
            availability_id=availability_id,
            quantity=request.quantity,
            buyer_id=request.buyer_id,
            reservation_hours=request.reservation_hours,
            reserved_by=current_user.id
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{availability_id}/release",
    response_model=AvailabilityResponse,
    summary="Release quantity (Internal API)",
    description="Called by Matching Engine to release reserved quantity. Requires AVAILABILITY_RELEASE capability.",
    tags=["Internal APIs"]
)
async def release_quantity(
    availability_id: UUID,
    request: ReleaseRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_RELEASE))
):
    """Release reserved quantity (internal API). Requires AVAILABILITY_RELEASE capability."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    try:
        availability = await service.release_availability(
            availability_id=availability_id,
            release_quantity=request.quantity,
            released_by=current_user.id
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{availability_id}/mark-sold",
    response_model=AvailabilityResponse,
    summary="Mark as sold (Internal API)",
    description="Called by Trade Finalization Engine to mark quantity as sold. Requires AVAILABILITY_MARK_SOLD capability.",
    tags=["Internal APIs"]
)
async def mark_as_sold(
    availability_id: UUID,
    request: MarkSoldRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_MARK_SOLD))
):
    """Mark quantity as sold (internal API). Requires AVAILABILITY_MARK_SOLD capability."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    try:
        availability = await service.mark_as_sold(
            availability_id=availability_id,
            sold_quantity=request.quantity,
            trade_id=request.trade_id,
            marked_by=current_user.id
        )
        
        return AvailabilityResponse.from_orm(availability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ========================
# AI/Analytics APIs
# ========================

@router.get(
    "/{availability_id}/negotiation-score",
    response_model=NegotiationReadinessResponse,
    summary="Get negotiation readiness score",
    description="AI-powered negotiation readiness analysis"
)
async def get_negotiation_readiness(
    availability_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get negotiation readiness score."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    availability = await service.repo.get_by_id(availability_id, load_relationships=True)
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability not found"
        )
    
    score_data = await service.calculate_negotiation_readiness_score(availability)
    
    return NegotiationReadinessResponse(
        availability_id=availability_id,
        negotiation_readiness_score=score_data["score"],
        factors=score_data["factors"],
        recommendations=score_data["recommendations"]
    )


@router.get(
    "/{availability_id}/similar",
    response_model=List[SimilarCommodityResponse],
    summary="Get similar commodities",
    description="AI-powered similar commodity suggestions"
)
async def get_similar_commodities(
    availability_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get similar commodity suggestions."""
    service = AvailabilityService(db, redis_client=redis_client)
    
    availability = await service.repo.get_by_id(availability_id, load_relationships=True)
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability not found"
        )
    
    similar = await service.suggest_similar_commodities(
        commodity_id=availability.commodity_id,
        quality_params=availability.quality_params,
        limit=limit
    )
    
    return [
        SimilarCommodityResponse(
            commodity_id=s["commodity_id"],
            commodity_name=s["commodity_name"],
            similarity_score=s["similarity_score"],
            reason=s["reason"]
        )
        for s in similar
    ]
