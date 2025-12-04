"""
Negotiation API Routes - THIN WRAPPERS ONLY

All business logic is in NegotiationService.
Routes handle HTTP/WebSocket protocol only.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    Query
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.async_session import get_db
from backend.core.auth.dependencies import get_current_user
from backend.modules.settings.models.settings_models import User
from backend.modules.trade_desk.services.negotiation_service import NegotiationService
from backend.modules.trade_desk.services.ai_negotiation_service import AINegoticationService
from backend.modules.trade_desk.websocket.negotiation_rooms import negotiation_room_manager
from backend.core.errors.exceptions import AuthorizationException
from backend.modules.trade_desk.schemas.negotiation_schemas import (
    StartNegotiationRequest,
    MakeOfferRequest,
    AcceptOfferRequest,
    RejectOfferRequest,
    SendMessageRequest,
    AIAssistRequest,
    NegotiationResponse,
    NegotiationListResponse,
    NegotiationListItem,
    MessageResponse,
    AICounterOfferSuggestion,
    PartnerSummary,
    OfferResponse,
    PartyEnum
)


router = APIRouter(prefix="/negotiations", tags=["Negotiations"])
admin_router = APIRouter(prefix="/admin/negotiations", tags=["Admin Monitoring"])


# ---------- Helper: Get Service ----------

def get_negotiation_service(db: AsyncSession = Depends(get_db)) -> NegotiationService:
    """Dependency: Get negotiation service"""
    return NegotiationService(db)


def get_ai_service(db: AsyncSession = Depends(get_db)) -> AINegoticationService:
    """Dependency: Get AI negotiation service"""
    return AINegoticationService(db)


# ---------- POST: Start Negotiation ----------

@router.post("/start", response_model=NegotiationResponse, status_code=status.HTTP_201_CREATED)
async def start_negotiation(
    request: StartNegotiationRequest,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Start negotiation from match token.
    
    Reveals identities and creates negotiation session.
    """
    if not current_user.business_partner_id:
        raise HTTPException(
            status_code=403,
            detail="Only external users with business partner can negotiate"
        )
    
    try:
        negotiation = await service.start_negotiation(
            match_token=request.match_token,
            user_partner_id=current_user.business_partner_id,
            initial_message=request.initial_message
        )
        
        # Determine user role
        if negotiation.buyer_partner_id == current_user.business_partner_id:
            user_role = PartyEnum.BUYER
        else:
            user_role = PartyEnum.SELLER
        
        # Build response
        response = NegotiationResponse.model_validate(negotiation)
        response.user_role = user_role
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- POST: Make Offer ----------

@router.post("/{negotiation_id}/offer", response_model=OfferResponse)
async def make_offer(
    negotiation_id: UUID,
    request: MakeOfferRequest,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Make or counter an offer.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        offer = await service.make_offer(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id,
            price_per_unit=request.price_per_unit,
            quantity=request.quantity,
            delivery_terms=request.delivery_terms,
            payment_terms=request.payment_terms,
            quality_conditions=request.quality_conditions,
            message=request.message
        )
        
        return OfferResponse.model_validate(offer)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- POST: Accept Offer ----------

@router.post("/{negotiation_id}/accept", response_model=NegotiationResponse)
async def accept_offer(
    negotiation_id: UUID,
    request: AcceptOfferRequest,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Accept the current offer.
    
    Closes negotiation and creates trade contract.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        negotiation = await service.accept_offer(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id,
            acceptance_message=request.acceptance_message
        )
        
        # Determine user role
        if negotiation.buyer_partner_id == current_user.business_partner_id:
            user_role = PartyEnum.BUYER
        else:
            user_role = PartyEnum.SELLER
        
        response = NegotiationResponse.model_validate(negotiation)
        response.user_role = user_role
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- POST: Reject Offer ----------

@router.post("/{negotiation_id}/reject", response_model=NegotiationResponse)
async def reject_offer(
    negotiation_id: UUID,
    request: RejectOfferRequest,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Reject offer with optional counter.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        # Prepare counter-offer params if requested
        counter_params = None
        if request.make_counter_offer:
            if not request.counter_price or not request.counter_quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Counter price and quantity required"
                )
            
            counter_params = {
                "price_per_unit": request.counter_price,
                "quantity": request.counter_quantity,
                "delivery_terms": request.counter_delivery_terms,
                "payment_terms": request.counter_payment_terms,
                "quality_conditions": request.counter_quality_conditions,
                "message": request.counter_message
            }
        
        negotiation = await service.reject_offer(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id,
            rejection_reason=request.rejection_reason,
            make_counter_offer=request.make_counter_offer,
            counter_offer_params=counter_params
        )
        
        # Determine user role
        if negotiation.buyer_partner_id == current_user.business_partner_id:
            user_role = PartyEnum.BUYER
        else:
            user_role = PartyEnum.SELLER
        
        response = NegotiationResponse.model_validate(negotiation)
        response.user_role = user_role
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- POST: Send Message ----------

@router.post("/{negotiation_id}/messages", response_model=MessageResponse)
async def send_message(
    negotiation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Send chat message in negotiation.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        message = await service.send_message(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id,
            message=request.message,
            message_type=request.message_type.value
        )
        
        return MessageResponse.model_validate(message)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- GET: Negotiation Details ----------

@router.get("/{negotiation_id}", response_model=NegotiationResponse)
async def get_negotiation(
    negotiation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Get negotiation details with offers and messages.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        negotiation = await service.get_negotiation_by_id(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id
        )
        
        # Determine user role
        if negotiation.buyer_partner_id == current_user.business_partner_id:
            user_role = PartyEnum.BUYER
        else:
            user_role = PartyEnum.SELLER
        
        response = NegotiationResponse.model_validate(negotiation)
        response.user_role = user_role
        
        # Add partner summaries
        if negotiation.buyer_partner:
            response.buyer = PartnerSummary(
                id=negotiation.buyer_partner.id,
                business_name=negotiation.buyer_partner.business_name,
                business_type=negotiation.buyer_partner.business_type.value
            )
        
        if negotiation.seller_partner:
            response.seller = PartnerSummary(
                id=negotiation.seller_partner.id,
                business_name=negotiation.seller_partner.business_name,
                business_type=negotiation.seller_partner.business_type.value
            )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- GET: User's Negotiations ----------

@router.get("/", response_model=NegotiationListResponse)
async def list_negotiations(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    List user's negotiations with pagination.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        negotiations = await service.get_user_negotiations(
            user_partner_id=current_user.business_partner_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        # Build list items
        items = []
        for neg in negotiations:
            # Determine user role
            if neg.buyer_partner_id == current_user.business_partner_id:
                user_role = PartyEnum.BUYER
                counterparty_name = neg.seller_partner.business_name if neg.seller_partner else "Unknown"
            else:
                user_role = PartyEnum.SELLER
                counterparty_name = neg.buyer_partner.business_name if neg.buyer_partner else "Unknown"
            
            # Count unread messages
            unread_count = 0
            for msg in neg.messages:
                if user_role == PartyEnum.BUYER and not msg.read_by_buyer:
                    unread_count += 1
                elif user_role == PartyEnum.SELLER and not msg.read_by_seller:
                    unread_count += 1
            
            # Get commodity name
            commodity_name = "Unknown"
            if neg.requirement and neg.requirement.commodity:
                commodity_name = neg.requirement.commodity.name
            
            items.append(NegotiationListItem(
                id=neg.id,
                status=neg.status,
                current_round=neg.current_round,
                current_price_per_unit=neg.current_price_per_unit,
                user_role=user_role,
                counterparty_name=counterparty_name,
                commodity_name=commodity_name,
                initiated_at=neg.initiated_at,
                expires_at=neg.expires_at,
                unread_messages=unread_count
            ))
        
        return NegotiationListResponse(
            items=items,
            total=len(items),  # TODO: Get actual total from service
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- GET: AI Suggestion ----------

@router.post("/{negotiation_id}/ai-suggest", response_model=AICounterOfferSuggestion)
async def get_ai_suggestion(
    negotiation_id: UUID,
    request: AIAssistRequest,
    current_user: User = Depends(get_current_user),
    negotiation_service: NegotiationService = Depends(get_negotiation_service),
    ai_service: AINegoticationService = Depends(get_ai_service)
):
    """
    Get AI-powered counter-offer suggestion.
    """
    if not current_user.business_partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    try:
        # Get negotiation
        negotiation = await negotiation_service.get_negotiation_by_id(
            negotiation_id=negotiation_id,
            user_partner_id=current_user.business_partner_id
        )
        
        # Get latest offer
        if not negotiation.offers:
            raise HTTPException(status_code=400, detail="No offers to analyze")
        
        latest_offer = negotiation.offers[-1]
        
        # Determine user party
        if negotiation.buyer_partner_id == current_user.business_partner_id:
            user_party = "BUYER"
        else:
            user_party = "SELLER"
        
        # Get AI suggestion
        suggestion = await ai_service.suggest_counter_offer(
            negotiation=negotiation,
            current_offer=latest_offer,
            user_party=user_party
        )
        
        return AICounterOfferSuggestion(**suggestion)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------- WebSocket: Real-time Room ----------

@router.websocket("/{negotiation_id}/ws")
async def negotiation_websocket(
    websocket: WebSocket,
    negotiation_id: UUID,
    # Note: WebSocket auth would need custom implementation
    # For now, assume token passed as query param
):
    """
    WebSocket endpoint for real-time negotiation updates.
    
    Events received:
    - offer.created
    - offer.accepted
    - offer.rejected
    - message.received
    - typing.indicator
    - negotiation.status_changed
    """
    # TODO: Implement proper WebSocket authentication
    # For now, accept connection without auth
    user_partner_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
    
    try:
        await negotiation_room_manager.connect(
            negotiation_id=negotiation_id,
            websocket=websocket,
            user_partner_id=user_partner_id
        )
        
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Handle typing indicator
            if data.get("type") == "typing":
                await negotiation_room_manager.broadcast_typing_indicator(
                    negotiation_id=negotiation_id,
                    user_id=user_partner_id,
                    is_typing=data.get("is_typing", False)
                )
    
    except WebSocketDisconnect:
        await negotiation_room_manager.disconnect(
            negotiation_id=negotiation_id,
            websocket=websocket
        )


# ============================================================================
# ADMIN MONITORING ENDPOINTS (READ-ONLY)
# ============================================================================

@admin_router.get("", response_model=NegotiationListResponse)
async def admin_list_all_negotiations(
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Admin: Monitor ALL negotiations in real-time (READ-ONLY).
    
    Accessible ONLY to INTERNAL/SUPER_ADMIN users.
    Back office monitoring - NO participation allowed.
    """
    # Check admin access
    if current_user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
        raise AuthorizationException("Admin access required for monitoring")
    
    # Get ALL negotiations (no user filter)
    negotiations = await service.admin_get_all_negotiations(
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Convert to response
    items = []
    for neg in negotiations:
        items.append(NegotiationListItem(
            id=neg.id,
            requirement_id=neg.requirement_id,
            availability_id=neg.availability_id,
            buyer_partner=PartnerSummary(
                id=neg.buyer_partner.id,
                business_name=neg.buyer_partner.business_name
            ),
            seller_partner=PartnerSummary(
                id=neg.seller_partner.id,
                business_name=neg.seller_partner.business_name
            ),
            status=neg.status,
            current_round=neg.current_round,
            last_activity_at=neg.last_activity_at,
            created_at=neg.created_at
        ))
    
    return NegotiationListResponse(
        negotiations=items,
        total=len(items),
        limit=limit,
        offset=offset
    )


@admin_router.get("/{negotiation_id}", response_model=NegotiationResponse)
async def admin_get_negotiation_details(
    negotiation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    """
    Admin: View negotiation details in real-time (READ-ONLY).
    
    Accessible ONLY to INTERNAL/SUPER_ADMIN users.
    Back office monitoring - NO participation allowed.
    """
    # Check admin access
    if current_user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
        raise AuthorizationException("Admin access required for monitoring")
    
    try:
        # Get negotiation without authorization check
        negotiation = await service.admin_get_negotiation_by_id(negotiation_id)
        
        # Convert to response
        return NegotiationResponse(
            id=negotiation.id,
            requirement_id=negotiation.requirement_id,
            availability_id=negotiation.availability_id,
            buyer_partner=PartnerSummary(
                id=negotiation.buyer_partner.id,
                business_name=negotiation.buyer_partner.business_name
            ),
            seller_partner=PartnerSummary(
                id=negotiation.seller_partner.id,
                business_name=negotiation.seller_partner.business_name
            ),
            status=negotiation.status,
            current_round=negotiation.current_round,
            offers=[
                OfferResponse(
                    id=offer.id,
                    round_number=offer.round_number,
                    offered_by=PartyEnum(offer.offered_by),
                    price_per_unit=offer.price_per_unit,
                    quantity=offer.quantity,
                    delivery_terms=offer.delivery_terms,
                    payment_terms=offer.payment_terms,
                    quality_conditions=offer.quality_conditions,
                    message=offer.message,
                    status=offer.status,
                    ai_generated=offer.ai_generated,
                    ai_confidence=offer.ai_confidence,
                    created_at=offer.created_at
                )
                for offer in negotiation.offers
            ],
            messages=[
                MessageResponse(
                    id=msg.id,
                    sender=PartyEnum(msg.sender),
                    message=msg.message,
                    message_type=msg.message_type,
                    created_at=msg.created_at
                )
                for msg in negotiation.messages
            ],
            last_activity_at=negotiation.last_activity_at,
            created_at=negotiation.created_at,
            closed_at=negotiation.closed_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
