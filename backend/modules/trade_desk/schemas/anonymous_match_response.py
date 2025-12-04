"""
Anonymous Match Response Schemas

Privacy-preserving response schemas that hide party identities until negotiation.

Disclosure Levels:
    - MATCHED: Anonymous tokens only, location shown as region
    - NEGOTIATING: Identities revealed when negotiation starts
    - TRADE: Full details for completed trades
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnonymousMatchScoreBreakdown(BaseModel):
    """Score breakdown for transparency (no PII)"""
    quality_score: float = Field(..., ge=0, le=1, description="Quality match score")
    price_score: float = Field(..., ge=0, le=1, description="Price competitiveness")
    delivery_score: float = Field(..., ge=0, le=1, description="Delivery timeline fit")
    risk_score: float = Field(..., ge=0, le=1, description="Risk assessment score")


class AnonymousMatchResponse(BaseModel):
    """
    Anonymous match result - hides party identities until negotiation.
    
    Users see:
        - Match quality score
        - Anonymous match token (e.g., MATCH-A7B2C)
        - General location (region only)
        - Quality/price fit
        
    Users DO NOT see:
        - Partner IDs
        - Company names
        - Exact locations
        - Contact details
    """
    # Anonymous identifier
    match_token: str = Field(
        ..., 
        description="Anonymous match token (e.g., MATCH-A7B2C)",
        example="MATCH-A7B2C"
    )
    
    # Match quality
    score: float = Field(..., ge=0, le=1, description="Overall match score")
    base_score: float = Field(..., ge=0, le=1, description="Base score before AI/risk adjustments")
    
    # Score adjustments (transparent)
    warn_penalty_applied: bool = Field(default=False, description="Risk warning penalty applied")
    warn_penalty_value: float = Field(default=0.0, ge=0, le=1, description="Penalty amount")
    ai_boost_applied: bool = Field(default=False, description="AI boost applied")
    ai_boost_value: float = Field(default=0.0, ge=0, le=1, description="AI boost amount")
    ai_recommended: bool = Field(default=False, description="AI highly recommends this match")
    
    # Risk assessment (anonymized)
    risk_status: Optional[str] = Field(None, description="PASS, WARN, or FAIL")
    risk_score: Optional[int] = Field(None, ge=0, le=100, description="Risk score 0-100")
    
    # Score breakdown
    score_breakdown: AnonymousMatchScoreBreakdown
    
    # AI recommendations (no PII)
    recommendations: str = Field(..., description="AI-generated recommendations")
    
    # Anonymous location info (region only)
    counterparty_region: Optional[str] = Field(
        None, 
        description="Counterparty region (e.g., 'North Gujarat')",
        example="North Gujarat"
    )
    
    counterparty_rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Counterparty rating (0-5 stars)"
    )
    
    # Match metadata
    matched_at: datetime = Field(..., description="When match was found")
    expires_at: Optional[datetime] = Field(None, description="Token expiration (30 days)")
    
    # Disclosure level tracking
    disclosure_level: str = Field(
        default="MATCHED",
        description="Current disclosure level: MATCHED, NEGOTIATING, or TRADE"
    )
    
    class Config:
        from_attributes = True


class AnonymousFindMatchesResponse(BaseModel):
    """Response for anonymous match finding"""
    matches: List[AnonymousMatchResponse] = Field(..., description="Anonymous match results")
    total_found: int = Field(..., description="Total matches found")
    request_id: UUID = Field(..., description="Your requirement/availability ID")
    commodity_code: str = Field(..., description="Commodity being matched")
    min_score_threshold: float = Field(..., ge=0, le=1, description="Minimum score threshold applied")
    ai_integration_enabled: bool = Field(default=False, description="AI features enabled")
    
    # Privacy notice
    privacy_notice: str = Field(
        default="Identities are hidden until you start negotiation. Click 'Start Negotiation' to reveal counterparty details.",
        description="Privacy protection notice"
    )
    
    class Config:
        from_attributes = True


class RevealedMatchResponse(BaseModel):
    """
    Match response with revealed identities (after negotiation starts).
    
    Now includes:
        - Partner company name
        - Exact location
        - Contact person (if available)
    """
    # All fields from AnonymousMatchResponse
    match_token: str
    score: float
    base_score: float
    warn_penalty_applied: bool
    warn_penalty_value: float
    ai_boost_applied: bool
    ai_boost_value: float
    ai_recommended: bool
    risk_status: Optional[str]
    risk_score: Optional[int]
    score_breakdown: AnonymousMatchScoreBreakdown
    recommendations: str
    matched_at: datetime
    expires_at: Optional[datetime]
    disclosure_level: str
    
    # REVEALED INFORMATION (only shown after negotiation starts)
    requirement_id: UUID = Field(..., description="Buyer requirement ID (revealed)")
    availability_id: UUID = Field(..., description="Seller availability ID (revealed)")
    
    # Party details (revealed)
    counterparty_id: UUID = Field(..., description="Counterparty partner ID")
    counterparty_name: str = Field(..., description="Company name")
    counterparty_city: Optional[str] = Field(None, description="City location")
    counterparty_state: Optional[str] = Field(None, description="State/region")
    counterparty_contact: Optional[Dict[str, Any]] = Field(None, description="Contact details")
    
    # Negotiation metadata
    negotiation_started_at: datetime = Field(..., description="When negotiation began")
    
    class Config:
        from_attributes = True
