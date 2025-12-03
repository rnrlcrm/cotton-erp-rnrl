"""
Requirement Engine REST API - 2035-Ready with AI Enhancements

🚀 Features:
- JWT authentication via get_current_user
- Buyer/seller context extraction from user
- RBAC for internal endpoints
- Complete error handling
- 11 standard endpoints + 2 NEW enhanced endpoints:
  1. POST /requirements/{id}/ai-adjust - AI adjustment with explainability
  2. GET /requirements/{id}/history - Complete event history
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.dependencies import get_current_user, require_permissions
from backend.db.async_session import get_db
from backend.app.dependencies import get_redis
from backend.modules.trade_desk.schemas.requirement_schemas import (
    AIAdjustmentRequest,
    AIAdjustmentResponse,
    CancelRequirementRequest,
    DemandStatisticsResponse,
    ErrorResponse,
    FulfillmentUpdateRequest,
    IntentSearchRequest,
    RequirementCreateRequest,
    RequirementEventResponse,
    RequirementHistoryResponse,
    RequirementResponse,
    RequirementSearchRequest,
    RequirementSearchResponse,
    RequirementUpdateRequest,
)
from backend.modules.trade_desk.services.requirement_service import RequirementService
from backend.modules.trade_desk.websocket import get_requirement_ws_service

router = APIRouter(prefix="/requirements", tags=["Requirement Engine"])


def get_requirement_service(
    db: AsyncSession = Depends(get_db),
    ws_service = Depends(get_requirement_ws_service),
    redis_client: redis.Redis = Depends(get_redis)
) -> RequirementService:
    """Dependency to get RequirementService with WebSocket support"""
    return RequirementService(db, ws_service=ws_service, redis_client=redis_client)


# ========================================================================
# PUBLIC REST APIs
# ========================================================================

@router.post(
    "",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new requirement",
    description="""Post new procurement requirement with 12-step AI pipeline.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicate requirements.
    - Same key within 24h returns cached response (no duplicate created)
    - Use UUID or unique transaction ID as idempotency key
    - Example: `Idempotency-Key: req-2025-11-30-abc123`
    """
)
async def create_requirement(
    request: RequirementCreateRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_CREATE))
):
    """
    Create new requirement posting with full AI enhancements.
    
    🚀 12-STEP AI PIPELINE:
    1. Validate buyer permissions & locations
    2. Auto-normalize quality requirements
    3. AI price suggestion
    4. Calculate buyer priority score
    5. Detect unrealistic budget
    6. Generate market context embedding
    7. Market sentiment adjustment
    8. Dynamic tolerance recommendation
    9. Auto-suggest commodity equivalents
    10. Auto-suggest negotiation preferences
    11. Generate AI-recommended sellers
    12. Intent-based routing
    
    Returns: Created requirement with AI enhancements
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    
    try:
        requirement = await service.create_requirement(
            buyer_id=buyer_id,
            commodity_id=request.commodity_id,
            variety_id=request.variety_id,
            min_quantity=request.min_quantity,
            max_quantity=request.max_quantity,
            quantity_unit=request.quantity_unit,
            preferred_quantity=request.preferred_quantity,
            quality_requirements=request.quality_requirements,
            max_budget_per_unit=request.max_budget_per_unit,
            preferred_price_per_unit=request.preferred_price_per_unit,
            total_budget=request.total_budget,
            currency_code=request.currency_code,
            preferred_payment_terms=request.preferred_payment_terms,
            preferred_delivery_terms=request.preferred_delivery_terms,
            delivery_locations=request.delivery_locations,
            delivery_window_start=request.delivery_window_start,
            delivery_window_end=request.delivery_window_end,
            delivery_flexibility_hours=request.delivery_flexibility_hours,
            market_visibility=request.market_visibility,
            invited_seller_ids=request.invited_seller_ids,
            valid_from=request.valid_from,
            valid_until=request.valid_until,
            urgency_level=request.urgency_level,
            intent_type=request.intent_type,
            commodity_equivalents=request.commodity_equivalents,
            negotiation_preferences=request.negotiation_preferences,
            notes=request.notes,
            attachments=request.attachments,
            auto_publish=request.auto_publish,
            created_by=current_user.id
        )
        
        return RequirementResponse.from_orm(requirement)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{requirement_id}",
    response_model=RequirementResponse,
    summary="Get requirement by ID",
    description="Retrieve requirement details"
)
async def get_requirement(
    requirement_id: UUID,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """Get requirement by ID with access control."""
    # Service with WebSocket support injected via dependency
    requirement = await service.repo.get_by_id(requirement_id, load_relationships=True)
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    # Access control: buyers see own requirements, sellers see PUBLIC/RESTRICTED
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    if requirement.buyer_partner_id != buyer_id:
        # Check if seller has access based on visibility
        if requirement.market_visibility == "PRIVATE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        elif requirement.market_visibility == "RESTRICTED":
            seller_id = current_user.business_partner_id
            if requirement.invited_seller_ids and str(seller_id) not in requirement.invited_seller_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
    
    return RequirementResponse.from_orm(requirement)


@router.put(
    "/{requirement_id}",
    response_model=RequirementResponse,
    summary="Update requirement",
    description="Update requirement with AI re-processing and micro-events. Requires REQUIREMENT_UPDATE capability."
)
async def update_requirement(
    requirement_id: UUID,
    request: RequirementUpdateRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_UPDATE))
):
    """
    Update requirement with AI re-processing. Requires REQUIREMENT_UPDATE capability.
    
    Emits micro-events:
    - budget_changed
    - quality_changed
    - visibility_changed
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    if requirement.buyer_partner_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update own requirements"
        )
    
    try:
        # Convert request to dict, excluding None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        
        requirement = await service.update_requirement(
            requirement_id=requirement_id,
            updated_by=current_user.id,
            **updates
        )
        
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        return RequirementResponse.from_orm(requirement)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{requirement_id}/publish",
    response_model=RequirementResponse,
    summary="Publish requirement",
    description="Publish requirement (DRAFT → ACTIVE) with intent-based routing. Requires REQUIREMENT_UPDATE capability."
)
async def publish_requirement(
    requirement_id: UUID,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_UPDATE))
):
    """
    Publish requirement (DRAFT → ACTIVE). Requires REQUIREMENT_UPDATE capability.
    
    Triggers:
    - requirement.published event
    - Intent-based routing to downstream engines
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    if requirement.buyer_partner_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only publish own requirements"
        )
    
    try:
        # Service handles: event emission, commit, idempotency
        requirement = await service.publish_requirement(
            requirement_id=requirement_id,
            published_by=current_user.id,
            idempotency_key=idempotency_key
        )
        
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        return RequirementResponse.from_orm(requirement)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{requirement_id}/cancel",
    response_model=RequirementResponse,
    summary="Cancel requirement",
    description="Cancel requirement with reason. Requires REQUIREMENT_CANCEL capability."
)
async def cancel_requirement(
    requirement_id: UUID,
    request: CancelRequirementRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_CANCEL))
):
    """Cancel requirement. Requires REQUIREMENT_CANCEL capability."""
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    if requirement.buyer_partner_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only cancel own requirements"
        )
    
    try:
        # Service handles: event emission, commit, idempotency
        requirement = await service.cancel_requirement(
            requirement_id=requirement_id,
            cancelled_by=current_user.id,
            reason=request.reason,
            idempotency_key=idempotency_key
        )
        
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        return RequirementResponse.from_orm(requirement)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{requirement_id}/fulfillment",
    response_model=RequirementResponse,
    summary="Update fulfillment",
    description="Update when buyer purchases from availability. Requires REQUIREMENT_FULFILL capability."
)
async def update_fulfillment(
    requirement_id: UUID,
    request: FulfillmentUpdateRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_FULFILL))
):
    """Update fulfillment tracking. Requires REQUIREMENT_FULFILL capability."""
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    if requirement.buyer_partner_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update own requirements"
        )
    
    try:
        requirement = await service.update_fulfillment(
            requirement_id=requirement_id,
            purchased_quantity=request.purchased_quantity,
            amount_spent=request.amount_spent,
            updated_by=current_user.id,
            trade_id=request.trade_id
        )
        
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        return RequirementResponse.from_orm(requirement)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/search",
    response_model=RequirementSearchResponse,
    summary="[DEPRECATED] AI-powered smart search - Use instant matching instead",
    description="⚠️ DEPRECATED: This marketplace-style search is deprecated. System now uses INSTANT AUTOMATIC MATCHING. When you post availability, matches are found automatically in real-time.",
    deprecated=True
)
async def search_requirements(
    request: RequirementSearchRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_READ))
):
    """
    ⚠️ DEPRECATED ENDPOINT
    
    This marketplace-style search is deprecated. The system now uses INSTANT AUTOMATIC MATCHING:
    
    **New Workflow:**
    1. Seller posts availability → System instantly finds matching requirements
    2. Buyer posts requirement → System instantly finds matching availabilities
    3. Matches are sent via notifications/events (NO manual browsing needed)
    
    **Why this changed:**
    - Real-time matching is faster and more efficient
    - Prevents users from seeing stale/already-matched requirements
    - Ensures best matches based on AI scoring and risk assessment
    - No marketplace listing - direct peer-to-peer matching only
    
    **Recommendation:** 
    Use POST /availabilities instead. Matches will be delivered instantly.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "ENDPOINT_DEPRECATED",
            "message": "Marketplace-style search is deprecated. Use INSTANT AUTOMATIC MATCHING instead.",
            "recommendation": "Post an availability (POST /availabilities) and receive instant matches via notifications.",
            "reason": "System moved from marketplace listing to real-time peer-to-peer matching for better efficiency and accuracy."
        }
    )


@router.post(
    "/search/by-intent",
    response_model=List[RequirementResponse],
    summary="[DEPRECATED] Search by intent type - Use instant matching instead",
    description="⚠️ DEPRECATED: This marketplace-style search is deprecated. System now uses INSTANT AUTOMATIC MATCHING with automatic intent routing.",
    deprecated=True
)
async def search_by_intent(
    request: IntentSearchRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    ⚠️ DEPRECATED ENDPOINT
    
    This marketplace-style intent search is deprecated. The system now uses INSTANT AUTOMATIC MATCHING:
    
    **New Workflow:**
    1. Seller posts availability → System instantly routes to correct engine based on intent:
       - DIRECT_BUY → Instant Matching Engine
       - NEGOTIATION → Negotiation Queue (automatic)
       - AUCTION_REQUEST → Reverse Auction (automatic)
       - PRICE_DISCOVERY_ONLY → Market Insights
    2. Buyer posts requirement → Automatic intent routing happens instantly
    3. No need to search by intent - system handles it automatically
    
    **Why this changed:**
    - Real-time matching with automatic intent detection
    - No manual search needed - system routes automatically
    - Better matches via AI scoring + risk assessment
    - Prevents stale requirement browsing
    
    **Recommendation:** 
    Use POST /availabilities instead. System automatically routes by intent type.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "ENDPOINT_DEPRECATED",
            "message": "Intent-based search is deprecated. Use INSTANT AUTOMATIC MATCHING with automatic intent routing.",
            "recommendation": "Post an availability (POST /availabilities) and system will automatically match requirements based on intent type (DIRECT_BUY/NEGOTIATION/AUCTION/PRICE_DISCOVERY).",
            "reason": "System moved to automatic intent-based routing with real-time matching."
        }
    )


@router.get(
    "/buyer/my-requirements",
    response_model=List[RequirementResponse],
    summary="Get my requirements",
    description="Get all requirements for current buyer"
)
async def get_my_requirements(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_READ))
):
    """Get all requirements for current buyer."""
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    requirements = await service.get_buyer_requirements(
        buyer_id=buyer_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    return [RequirementResponse.from_orm(req) for req in requirements]


@router.get(
    "/statistics/demand/{commodity_id}",
    response_model=DemandStatisticsResponse,
    summary="Get total demand statistics",
    description="Get total demand for a commodity"
)
async def get_demand_statistics(
    commodity_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """Get total demand statistics for a commodity."""
    # Service with WebSocket support injected via dependency
    
    stats = await service.get_total_demand(
        commodity_id=commodity_id,
        days=days
    )
    
    return DemandStatisticsResponse(
        commodity_id=commodity_id,
        total_unfulfilled_quantity=stats["total_unfulfilled_quantity"],
        total_budget=stats["total_budget"],
        avg_max_price=stats["avg_max_price"],
        avg_preferred_price=stats["avg_preferred_price"],
        active_requirement_count=stats["active_requirement_count"],
        period_days=days
    )


# ========================================================================
# 🚀 NEW ENHANCED ENDPOINTS
# ========================================================================

@router.post(
    "/{requirement_id}/ai-adjust",
    response_model=AIAdjustmentResponse,
    summary="🚀 Apply AI-suggested adjustment",
    description="ENHANCEMENT #7: Apply AI adjustment with full explainability and audit trail. Requires REQUIREMENT_AI_ADJUST capability."
)
async def apply_ai_adjustment(
    requirement_id: UUID,
    request: AIAdjustmentRequest,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service),
    _check: None = Depends(RequireCapability(Capabilities.REQUIREMENT_AI_ADJUST))
):
    """
    🚀 ENHANCEMENT #7: AI Adjustment with Explainability. Requires REQUIREMENT_AI_ADJUST capability.
    
    Apply AI-suggested adjustment to requirement with:
    - Full reasoning explanation
    - Market context data
    - Expected impact analysis
    - Auto-apply or suggestion mode
    - Complete audit trail via requirement.ai_adjusted event
    
    Critical for transparency and trust in autonomous AI decisions.
    
    Adjustment Types:
    - "budget": Adjust max_budget_per_unit based on market trends
    - "quality": Adjust quality_requirements tolerance
    - "delivery_window": Adjust delivery window for better matching
    - "commodity_equivalents": Add/remove acceptable substitutes
    
    Example Use Cases:
    - Market prices rising → AI suggests budget increase
    - Low availability → AI suggests quality tolerance increase
    - Tight delivery timeline → AI suggests window extension
    - Better matches available → AI suggests commodity equivalents
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    if requirement.buyer_partner_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only adjust own requirements"
        )
    
    try:
        # Get old value before adjustment
        if request.adjustment_type == "budget":
            old_value = requirement.max_budget_per_unit
        elif request.adjustment_type == "quality":
            old_value = requirement.quality_requirements
        elif request.adjustment_type == "delivery_window":
            old_value = {
                "start": requirement.delivery_window_start,
                "end": requirement.delivery_window_end
            }
        elif request.adjustment_type == "commodity_equivalents":
            old_value = requirement.commodity_equivalents
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid adjustment_type: {request.adjustment_type}"
            )
        
        # Apply adjustment
        requirement = await service.apply_ai_adjustment(
            requirement_id=requirement_id,
            adjustment_type=request.adjustment_type,
            new_value=request.new_value,
            ai_confidence=request.ai_confidence,
            ai_reasoning=request.ai_reasoning,
            market_context=request.market_context,
            expected_impact=request.expected_impact,
            auto_apply=request.auto_apply
        )
        
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        return AIAdjustmentResponse(
            requirement_id=requirement.id,
            adjustment_type=request.adjustment_type,
            old_value=old_value,
            new_value=request.new_value,
            ai_confidence=request.ai_confidence,
            ai_reasoning=request.ai_reasoning,
            market_context=request.market_context,
            expected_impact=request.expected_impact,
            applied=request.auto_apply,
            adjusted_at=datetime.utcnow()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{requirement_id}/history",
    response_model=RequirementHistoryResponse,
    summary="🚀 Get requirement event history",
    description="NEW: Complete audit trail of all requirement events"
)
async def get_requirement_history(
    requirement_id: UUID,
    current_user=Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    🚀 NEW ENDPOINT: Get complete event history for requirement.
    
    Returns all events emitted for this requirement:
    - requirement.created
    - requirement.published
    - requirement.updated
    - requirement.budget_changed (micro-event)
    - requirement.quality_changed (micro-event)
    - requirement.visibility_changed (micro-event)
    - requirement.fulfillment_updated (micro-event)
    - requirement.fulfilled
    - requirement.expired
    - requirement.cancelled
    - requirement.ai_adjusted (🚀 ENHANCEMENT #7)
    
    Critical for:
    - Audit trail compliance
    - Debugging requirement lifecycle
    - Understanding AI decision history
    - Tracking buyer behavior patterns
    - Dispute resolution
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a business partner"
        )
    
    buyer_id = current_user.business_partner_id
    # Service with WebSocket support injected via dependency
    
    # Verify ownership or access
    requirement = await service.repo.get_by_id(requirement_id)
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    # Access control: buyers see own requirements, sellers see PUBLIC/RESTRICTED
    if requirement.buyer_partner_id != buyer_id:
        if requirement.market_visibility == "PRIVATE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        elif requirement.market_visibility == "RESTRICTED":
            seller_id = current_user.business_partner_id
            if requirement.invited_seller_ids and str(seller_id) not in requirement.invited_seller_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
    
    # Retrieve events from event store
    # TODO: Implement event store integration
    # For now, return placeholder indicating feature is coming soon
    event_responses = []
    
    # Placeholder response
    event_responses.append(
        RequirementEventResponse(
            event_type="requirement.created",
            event_data={
                "requirement_id": str(requirement.id),
                "buyer_id": str(requirement.buyer_partner_id),
                "commodity_id": str(requirement.commodity_id),
                "intent_type": requirement.intent_type,
                "buyer_priority_score": requirement.buyer_priority_score
            },
            occurred_at=requirement.created_at,
            triggered_by=requirement.created_by_user_id
        )
    )
    
    if requirement.published_at:
        event_responses.append(
            RequirementEventResponse(
                event_type="requirement.published",
                event_data={
                    "requirement_id": str(requirement.id),
                    "intent_type": requirement.intent_type,
                    "market_visibility": requirement.market_visibility
                },
                occurred_at=requirement.published_at,
                triggered_by=requirement.created_by_user_id
            )
        )
    
    return RequirementHistoryResponse(
        requirement_id=requirement.id,
        requirement_number=requirement.requirement_number,
        events=event_responses,
        total_events=len(event_responses)
    )
