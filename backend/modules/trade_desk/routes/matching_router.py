"""
Matching Engine REST API Endpoints

Provides HTTP endpoints for:
- Manual match finding for requirements
- Manual match finding for availabilities
- Match details retrieval
- Match status queries

Part of GLOBAL MULTI-COMMODITY Platform - works for Cotton, Gold, Wheat, Rice, Oil, ANY commodity.

Security:
    - Authentication required (JWT)
    - Authorization: Users can only access their own matches
    - No data leakage: Match results ONLY to matched parties
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import redis.asyncio as redis

from backend.db.async_session import get_db
from backend.app.dependencies import get_redis
from backend.core.auth.dependencies import get_current_user
from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.capabilities.decorators import RequireCapability
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.matching.matching_engine import MatchingEngine, MatchResult
from backend.modules.trade_desk.matching.validators import MatchValidator
from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.risk.risk_engine import RiskEngine
from backend.modules.trade_desk.repositories.requirement_repository import RequirementRepository
from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
from backend.modules.trade_desk.services.matching_service import MatchingService


router = APIRouter(prefix="/api/v1/matching", tags=["matching"])


# ========================================================================
# REQUEST/RESPONSE SCHEMAS
# ========================================================================

class MatchScoreBreakdown(BaseModel):
    """Score breakdown for transparency"""
    quality_score: float = Field(..., ge=0, le=1)
    price_score: float = Field(..., ge=0, le=1)
    delivery_score: float = Field(..., ge=0, le=1)
    risk_score: float = Field(..., ge=0, le=1)


class MatchResponse(BaseModel):
    """Single match result response"""
    requirement_id: UUID
    availability_id: UUID
    score: float = Field(..., ge=0, le=1)
    base_score: float = Field(..., ge=0, le=1)
    warn_penalty_applied: bool
    warn_penalty_value: float
    ai_boost_applied: bool = False
    ai_boost_value: float = 0.0
    ai_recommended: bool = False
    risk_status: Optional[str] = None
    risk_score: Optional[int] = None
    score_breakdown: MatchScoreBreakdown
    recommendations: str
    matched_at: datetime
    
    class Config:
        from_attributes = True


class FindMatchesResponse(BaseModel):
    """Response for find matches endpoint"""
    matches: List[MatchResponse]
    total_found: int
    request_id: UUID
    commodity_code: str
    min_score_threshold: float
    ai_integration_enabled: bool = False
    
    class Config:
        from_attributes = True


class MatchDetailsResponse(BaseModel):
    """Detailed match information"""
    match: MatchResponse
    requirement_summary: dict
    availability_summary: dict
    can_proceed: bool
    warnings: List[str] = []
    ai_alerts: List[str] = []
    
    class Config:
        from_attributes = True


# ========================================================================
# DEPENDENCY INJECTION
# ========================================================================

def get_matching_service(db: AsyncSession = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)) -> MatchingService:
    """Dependency injection for MatchingService"""
    config = MatchingConfig()
    req_repo = RequirementRepository(db)
    avail_repo = AvailabilityRepository(db)
    risk_engine = RiskEngine(db)
    scorer = MatchScorer(db, risk_engine, config)
    
    matching_engine = MatchingEngine(
        db=db,
        req_repo=req_repo,
        avail_repo=avail_repo,
        scorer=scorer,
        config=config
    )
    
    validator = MatchValidator(db, risk_engine, config)
    
    return MatchingService(
        db=db,
        matching_engine=matching_engine,
        validator=validator,
        config=config,
        redis_client=redis_client
    )

def get_matching_engine(db: AsyncSession = Depends(get_db)) -> MatchingEngine:
    """Dependency injection for MatchingEngine"""
    config = MatchingConfig()
    req_repo = RequirementRepository(db)
    avail_repo = AvailabilityRepository(db)
    risk_engine = RiskEngine(db)
    scorer = MatchScorer(db, risk_engine, config)
    
    return MatchingEngine(
        db=db,
        req_repo=req_repo,
        avail_repo=avail_repo,
        scorer=scorer,
        config=config
    )


def get_match_validator(db: AsyncSession = Depends(get_db)) -> MatchValidator:
    """Dependency injection for MatchValidator"""
    config = MatchingConfig()
    risk_engine = RiskEngine(db)
    
    return MatchValidator(db, risk_engine, config)


# ========================================================================
# ENDPOINTS
# ========================================================================

@router.post(
    "/requirements/{requirement_id}/find-matches",
    response_model=FindMatchesResponse,
    summary="Find matches for requirement",
    description="""
    Find seller availabilities matching a buyer requirement.
    
    - Location-first filtering applied
    - Returns top matches sorted by score
    - Only active availabilities considered
    - Min score threshold applied per commodity
    - AI integration if available
    """
)
async def find_matches_for_requirement(
    requirement_id: UUID,
    limit: int = Query(default=10, ge=1, le=50, description="Max number of matches"),
    min_score: Optional[float] = Query(default=None, ge=0, le=1, description="Override min score threshold"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    matching_engine: MatchingEngine = Depends(get_matching_engine),
    matching_service: MatchingService = Depends(get_matching_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.MATCHING_MANUAL))
) -> FindMatchesResponse:
    """
    Find matches for a buyer requirement. Requires MATCHING_MANUAL capability.
    
    Security: User must own the requirement
    """
    # Get requirement using service
    requirement = await matching_service.get_requirement_by_id(requirement_id)
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement {requirement_id} not found"
        )
    
    # Authorization: User must own requirement
    if requirement.party_id != current_user.party_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this requirement"
        )
    
    # Check requirement is active
    if requirement.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requirement status is {requirement.status}, must be ACTIVE"
        )
    
    # Execute matching
    matches = await matching_engine.find_matches_for_requirement(requirement)
    
    # Apply score threshold
    config = MatchingConfig()
    commodity_code = requirement.commodity.code if requirement.commodity else "default"
    threshold = min_score if min_score is not None else config.get_min_score_threshold(commodity_code)
    
    matches = [m for m in matches if m.score >= threshold]
    
    # Limit results
    matches = matches[:limit]
    
    # Build response
    match_responses = [
        MatchResponse(
            requirement_id=m.requirement_id,
            availability_id=m.availability_id,
            score=m.score,
            base_score=m.base_score,
            warn_penalty_applied=m.warn_penalty_applied,
            warn_penalty_value=getattr(m, 'warn_penalty_value', 0.0),
            ai_boost_applied=m.score_breakdown.get('ai_boost_applied', False),
            ai_boost_value=m.score_breakdown.get('ai_boost_value', 0.0),
            ai_recommended=m.score_breakdown.get('ai_recommended', False),
            risk_status=m.risk_status,
            risk_score=getattr(m, 'risk_score', None),
            score_breakdown=MatchScoreBreakdown(**m.score_breakdown.get('breakdown', {})),
            recommendations=m.score_breakdown.get('recommendations', ''),
            matched_at=datetime.utcnow()
        )
        for m in matches
    ]
    
    return FindMatchesResponse(
        matches=match_responses,
        total_found=len(match_responses),
        request_id=requirement_id,
        commodity_code=commodity_code,
        min_score_threshold=threshold,
        ai_integration_enabled=bool(requirement.ai_recommended_sellers)
    )


@router.post(
    "/availabilities/{availability_id}/find-matches",
    response_model=FindMatchesResponse,
    summary="Find matches for availability",
    description="""
    Find buyer requirements matching a seller availability.
    
    - Location-first filtering applied
    - Returns top matches sorted by score
    - Only active requirements considered
    - Min score threshold applied per commodity
    - AI integration if available
    """
)
async def find_matches_for_availability(
    availability_id: UUID,
    limit: int = Query(default=10, ge=1, le=50, description="Max number of matches"),
    min_score: Optional[float] = Query(default=None, ge=0, le=1, description="Override min score threshold"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    matching_engine: MatchingEngine = Depends(get_matching_engine),
    matching_service: MatchingService = Depends(get_matching_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.MATCHING_MANUAL))
) -> FindMatchesResponse:
    """
    Find matches for a seller availability. Requires MATCHING_MANUAL capability.
    
    Security: User must own the availability
    """
    # Get availability using service
    availability = await matching_service.get_availability_by_id(availability_id)
    
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Availability {availability_id} not found"
        )
    
    # Authorization: User must own availability
    if availability.party_id != current_user.party_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this availability"
        )
    
    # Check availability is active
    if availability.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Availability status is {availability.status}, must be ACTIVE"
        )
    
    # Execute matching
    matches = await matching_engine.find_matches_for_availability(availability)
    
    # Apply score threshold
    config = MatchingConfig()
    commodity_code = availability.commodity.code if availability.commodity else "default"
    threshold = min_score if min_score is not None else config.get_min_score_threshold(commodity_code)
    
    matches = [m for m in matches if m.score >= threshold]
    
    # Limit results
    matches = matches[:limit]
    
    # Build response
    match_responses = [
        MatchResponse(
            requirement_id=m.requirement_id,
            availability_id=m.availability_id,
            score=m.score,
            base_score=m.base_score,
            warn_penalty_applied=m.warn_penalty_applied,
            warn_penalty_value=getattr(m, 'warn_penalty_value', 0.0),
            ai_boost_applied=m.score_breakdown.get('ai_boost_applied', False),
            ai_boost_value=m.score_breakdown.get('ai_boost_value', 0.0),
            ai_recommended=m.score_breakdown.get('ai_recommended', False),
            risk_status=m.risk_status,
            risk_score=getattr(m, 'risk_score', None),
            score_breakdown=MatchScoreBreakdown(**m.score_breakdown.get('breakdown', {})),
            recommendations=m.score_breakdown.get('recommendations', ''),
            matched_at=datetime.utcnow()
        )
        for m in matches
    ]
    
    return FindMatchesResponse(
        matches=match_responses,
        total_found=len(match_responses),
        request_id=availability_id,
        commodity_code=commodity_code,
        min_score_threshold=threshold,
        ai_integration_enabled=False  # AI recommendations are on requirement side
    )


@router.get(
    "/matches/{requirement_id}/{availability_id}",
    response_model=MatchDetailsResponse,
    summary="Get match details",
    description="""
    Get detailed information about a specific match.
    
    - Returns match score and breakdown
    - Includes requirement and availability summaries
    - Shows warnings and AI alerts
    - Authorization: Only matched parties can access
    """
)
async def get_match_details(
    requirement_id: UUID,
    availability_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    matching_engine: MatchingEngine = Depends(get_matching_engine),
    matching_service: MatchingService = Depends(get_matching_service),
    validator: MatchValidator = Depends(get_match_validator)
) -> MatchDetailsResponse:
    """
    Get detailed match information
    
    Security: Only buyer or seller can access their match details
    """
    # Get requirement and availability using service
    requirement = await matching_service.get_requirement_by_id(requirement_id)
    availability = await matching_service.get_availability_by_id(availability_id)
    
    if not requirement or not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement or availability not found"
        )
    
    # Authorization: User must be buyer OR seller (ITERATION #13 - no data leakage)
    if current_user.party_id not in [requirement.party_id, availability.party_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this match"
        )
    
    # Calculate match score
    matches = await matching_engine.find_matches_for_requirement(requirement)
    match_result = next(
        (m for m in matches if m.availability_id == availability_id),
        None
    )
    
    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found or below threshold"
        )
    
    # Validate match
    validation = await validator.validate_match_eligibility(requirement, availability)
    
    # Build response
    return MatchDetailsResponse(
        match=MatchResponse(
            requirement_id=match_result.requirement_id,
            availability_id=match_result.availability_id,
            score=match_result.score,
            base_score=match_result.base_score,
            warn_penalty_applied=match_result.warn_penalty_applied,
            warn_penalty_value=getattr(match_result, 'warn_penalty_value', 0.0),
            ai_boost_applied=match_result.score_breakdown.get('ai_boost_applied', False),
            ai_boost_value=match_result.score_breakdown.get('ai_boost_value', 0.0),
            ai_recommended=match_result.score_breakdown.get('ai_recommended', False),
            risk_status=match_result.risk_status,
            risk_score=getattr(match_result, 'risk_score', None),
            score_breakdown=MatchScoreBreakdown(**match_result.score_breakdown.get('breakdown', {})),
            recommendations=match_result.score_breakdown.get('recommendations', ''),
            matched_at=datetime.utcnow()
        ),
        requirement_summary={
            "id": str(requirement.id),
            "commodity": requirement.commodity.code if requirement.commodity else "UNKNOWN",
            "quantity": float(requirement.preferred_quantity),
            "budget": float(requirement.max_budget),
            "status": requirement.status
        },
        availability_summary={
            "id": str(availability.id),
            "commodity": availability.commodity.code if availability.commodity else "UNKNOWN",
            "quantity": float(availability.available_quantity),
            "price": float(availability.asking_price),
            "status": availability.status
        },
        can_proceed=validation.is_valid,
        warnings=validation.warnings,
        ai_alerts=validation.ai_alerts
    )


@router.get(
    "/health",
    summary="Health check",
    description="Check matching engine service health"
)
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "matching-engine",
        "version": "2.0.0",
        "features": [
            "location-first",
            "event-driven",
            "risk-integrated",
            "ai-enhanced",
            "multi-commodity"
        ]
    }
