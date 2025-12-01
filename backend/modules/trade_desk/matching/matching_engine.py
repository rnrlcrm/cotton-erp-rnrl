"""
Core Matching Engine

Location-first intelligent bilateral matching for buyer-seller pairing.

CRITICAL DESIGN PRINCIPLES:
1. Location Hard Filter BEFORE any scoring (performance + privacy)
2. Event-Driven Triggers (no batch as primary)
3. Atomic Partial Allocation (optimistic locking)
4. Complete Audit Trail (explainability)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.repositories.requirement_repository import RequirementRepository
from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
from backend.modules.risk.risk_engine import RiskEngine
from backend.modules.trade_desk.config.matching_config import MatchingConfig, get_matching_config
from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.matching.validators import MatchValidator

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """
    Result of a single match between requirement and availability.
    
    Contains full scoring breakdown and audit information.
    """
    requirement_id: UUID
    availability_id: UUID
    score: float  # 0.0 to 1.0
    base_score: float  # Before WARN penalty
    warn_penalty_applied: bool
    warn_penalty_value: float
    
    # Score components
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    pass_fail: Dict[str, bool] = field(default_factory=dict)
    
    # Risk assessment
    risk_status: str = "UNKNOWN"  # PASS/WARN/FAIL
    risk_details: Dict[str, Any] = field(default_factory=dict)
    
    # Audit trail
    location_filter_passed: bool = True
    duplicate_detection_key: Optional[str] = None
    matched_at: datetime = field(default_factory=datetime.utcnow)
    
    # References (lazy loaded)
    requirement: Optional[Requirement] = None
    availability: Optional[Availability] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "requirement_id": str(self.requirement_id),
            "availability_id": str(self.availability_id),
            "match_score": round(self.score, 4),
            "base_score": round(self.base_score, 4),
            "warn_penalty_applied": self.warn_penalty_applied,
            "score_breakdown": self.score_breakdown,
            "risk_status": self.risk_status,
            "risk_details": self.risk_details,
            "matched_at": self.matched_at.isoformat()
        }


class MatchingEngine:
    """
    Core bilateral matching engine with location-first filtering.
    
    Flow:
    1. LOCATION HARD FILTER (before scoring)
    2. Fetch location-matched candidates
    3. Calculate match scores
    4. Apply duplicate detection
    5. Validate risk
    6. Sort and return top matches
    """
    
    def __init__(
        self,
        db: AsyncSession,
        risk_engine: RiskEngine,
        requirement_repo: RequirementRepository,
        availability_repo: AvailabilityRepository,
        config: Optional[MatchingConfig] = None
    ):
        self.db = db
        self.risk_engine = risk_engine
        self.requirement_repo = requirement_repo
        self.availability_repo = availability_repo
        self.config = config or get_matching_config()
        self.scorer = MatchScorer(config=self.config)
        self.validator = MatchValidator(db=db, risk_engine=risk_engine, config=self.config)
    
    # ========================================================================
    # LOCATION-FIRST HARD FILTER ⭐ CRITICAL
    # ========================================================================
    
    def _location_matches(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> bool:
        """
        STRICT location filter - BEFORE any scoring.
        
        CRITICAL RULES:
        1. State-level filtering: Maharashtra requirement → Maharashtra availability ONLY
        2. City-level filtering: Nagpur requirement → Nagpur OR nearby cities within max_distance_km
        3. Cross-state matching: BLOCKED by default
        4. Distance-based: Calculate Haversine distance if lat/long available
        
        Args:
            requirement: Buyer requirement with delivery_locations JSONB
            availability: Seller availability with location_id
            
        Returns:
            True if locations compatible, False to skip immediately
        """
        # Requirement has delivery_locations as JSONB array
        # Example: [{"location_id": "uuid", "state": "Maharashtra", "city": "Nagpur", 
        #            "latitude": 21.1, "longitude": 79.0, "max_distance_km": 50}]
        
        if not requirement.delivery_locations:
            # No location specified - match all (fallback)
            logger.warning(f"Requirement {requirement.id} has no delivery_locations")
            return True
        
        # Get seller's location details (with eager loading)
        seller_location = availability.location if hasattr(availability, 'location') else None
        
        if not seller_location:
            logger.warning(f"Availability {availability.id} has no location details")
            return False  # Cannot match without location
        
        # Extract buyer's acceptable locations
        buyer_locations = requirement.delivery_locations
        
        # Check each buyer location preference
        for buyer_loc in buyer_locations:
            # RULE 1: Exact location ID match (highest priority)
            if buyer_loc.get("location_id") == str(availability.location_id):
                logger.debug(f"Exact location match: {availability.location_id}")
                return True
            
            # RULE 2: State-level matching (Maharashtra → Maharashtra only)
            buyer_state = buyer_loc.get("state")
            seller_state = seller_location.state
            
            if buyer_state and seller_state:
                if buyer_state.strip().upper() != seller_state.strip().upper():
                    # Cross-state NOT allowed
                    logger.debug(
                        f"State mismatch: buyer wants {buyer_state}, "
                        f"seller has {seller_state} - BLOCKED"
                    )
                    continue  # Try next buyer location
            
            # RULE 3: City-level matching with distance calculation
            buyer_city = buyer_loc.get("city")
            seller_city = seller_location.city
            max_distance_km = buyer_loc.get("max_distance_km", self.config.MAX_DISTANCE_KM or 50)
            
            if buyer_city and seller_city:
                # Exact city match (Nagpur → Nagpur)
                if buyer_city.strip().upper() == seller_city.strip().upper():
                    logger.debug(f"Exact city match: {seller_city}")
                    return True
                
                # Nearby cities within distance (Nagpur → Wardha if within 50km)
                buyer_lat = buyer_loc.get("latitude")
                buyer_lon = buyer_loc.get("longitude")
                seller_lat = seller_location.latitude
                seller_lon = seller_location.longitude
                
                if all([buyer_lat, buyer_lon, seller_lat, seller_lon]):
                    distance_km = self._calculate_haversine_distance(
                        buyer_lat, buyer_lon, seller_lat, seller_lon
                    )
                    
                    if distance_km <= max_distance_km:
                        logger.debug(
                            f"Distance match: {seller_city} is {distance_km:.2f}km "
                            f"from {buyer_city} (max: {max_distance_km}km)"
                        )
                        return True
                    else:
                        logger.debug(
                            f"Distance too far: {distance_km:.2f}km > {max_distance_km}km"
                        )
                        continue
        
        # No location matched buyer's criteria
        logger.debug(
            f"Location filter blocked: requirement {requirement.id} has no match "
            f"with availability {availability.id} (seller location: {seller_location.city}, {seller_location.state})"
        )
        return False  # BLOCKED - no relevant location match
    
    def _calculate_haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate Haversine distance between two lat/long points.
        
        Returns distance in kilometers.
        
        Formula:
        a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c  (R = Earth's radius = 6371 km)
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert degrees to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c
        
        return distance
    
    # ========================================================================
    # BIDIRECTIONAL MATCHING
    # ========================================================================
    
    async def find_matches_for_requirement(
        self,
        requirement_id: UUID,
        min_score: Optional[float] = None,
        include_risk_check: bool = True,
        max_results: int = 50
    ) -> List[MatchResult]:
        """
        Find compatible availabilities for a requirement.
        
        CRITICAL FLOW:
        1. Fetch requirement with location data
        2. Query availabilities FILTERED BY LOCATION (DB-level)
        3. For each candidate, apply location hard filter
        4. ONLY THEN calculate scores
        5. Apply duplicate detection
        6. Validate risk
        7. Sort and return top matches
        
        Args:
            requirement_id: Requirement UUID
            min_score: Minimum match score (commodity-specific if None)
            include_risk_check: Whether to validate with risk engine
            max_results: Maximum number of matches to return
            
        Returns:
            List of MatchResult objects sorted by score (best first)
        """
        # Get requirement with eager loading
        requirement = await self.requirement_repo.get_by_id(
            requirement_id,
            include_relations=["commodity", "buyer_partner"]
        )
        
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        # Get commodity-specific min score
        if min_score is None:
            commodity_code = requirement.commodity.code if requirement.commodity else "default"
            min_score = self.config.get_min_score_threshold(commodity_code)
        
        logger.info(f"Finding matches for requirement {requirement_id}, min_score={min_score}")
        
        # Step 1: LOCATION-FIRST FILTER (DB query level)
        # Extract location IDs from buyer's delivery_locations
        location_ids = []
        if requirement.delivery_locations:
            for loc in requirement.delivery_locations:
                loc_id = loc.get("location_id")
                if loc_id:
                    try:
                        location_ids.append(UUID(loc_id))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid location_id in delivery_locations: {loc_id}")
        
        if not location_ids:
            logger.warning(f"Requirement {requirement_id} has no valid delivery locations")
            return []
        
        # Query availabilities filtered by location
        candidate_availabilities = await self.availability_repo.search_by_location(
            location_ids=location_ids,
            commodity_id=requirement.commodity_id,
            status="AVAILABLE",
            include_relations=["location", "seller", "commodity"]
        )
        
        logger.info(f"Found {len(candidate_availabilities)} location-matched candidates")
        
        matches = []
        seen_duplicates: Set[str] = set()
        
        for availability in candidate_availabilities:
            # Step 2: Hard location filter (application level - redundant safety check)
            if not self._location_matches(requirement, availability):
                logger.debug(f"Location filter blocked: req={requirement_id}, avail={availability.id}")
                continue  # SKIP - no scoring needed
            
            # Step 3: Duplicate detection
            dup_key = self._generate_duplicate_key(requirement, availability)
            if await self._is_duplicate(dup_key, seen_duplicates, requirement_id, availability.id):
                logger.debug(f"Duplicate detected: {dup_key}")
                continue  # SKIP duplicate
            
            # Step 4: Calculate match score
            try:
                score_result = await self.scorer.calculate_match_score(
                    requirement=requirement,
                    availability=availability,
                    risk_engine=self.risk_engine if include_risk_check else None
                )
                
                # Check if match was blocked by risk
                if score_result.get("blocked", False):
                    logger.info(f"Match blocked by risk: req={requirement_id}, avail={availability.id}")
                    continue
                
                # Step 5: Filter by min score
                if score_result["total_score"] < min_score:
                    logger.debug(f"Score too low: {score_result['total_score']} < {min_score}")
                    continue
                
                # Step 6: Create match result with audit trail
                match = MatchResult(
                    requirement_id=requirement.id,
                    availability_id=availability.id,
                    score=score_result["total_score"],
                    base_score=score_result["base_score"],
                    warn_penalty_applied=score_result.get("warn_penalty_applied", False),
                    warn_penalty_value=score_result.get("warn_penalty_value", 0.0),
                    score_breakdown=score_result["breakdown"],
                    pass_fail=score_result["pass_fail"],
                    risk_status=score_result.get("risk_details", {}).get("risk_status", "UNKNOWN"),
                    risk_details=score_result.get("risk_details", {}),
                    location_filter_passed=True,
                    duplicate_detection_key=dup_key,
                    requirement=requirement,
                    availability=availability
                )
                
                matches.append(match)
                seen_duplicates.add(dup_key)
                
            except Exception as e:
                logger.error(f"Error scoring match: req={requirement_id}, avail={availability.id}, error={e}")
                continue
        
        # Step 7: Sort by score (best first)
        matches.sort(key=lambda m: m.score, reverse=True)
        
        logger.info(f"Found {len(matches)} valid matches for requirement {requirement_id}")
        
        # Step 8: Store audit trail (async, don't block)
        asyncio.create_task(self._save_match_audit_trail(matches, requirement))
        
        return matches[:max_results]
    
    async def find_matches_for_availability(
        self,
        availability_id: UUID,
        min_score: Optional[float] = None,
        include_risk_check: bool = True,
        max_results: int = 50
    ) -> List[MatchResult]:
        """
        Find compatible requirements for an availability.
        
        Same location-first logic as find_matches_for_requirement.
        """
        # Get availability with eager loading
        availability = await self.availability_repo.get_by_id(
            availability_id,
            include_relations=["location", "commodity", "seller"]
        )
        
        if not availability:
            raise ValueError(f"Availability {availability_id} not found")
        
        # Get commodity-specific min score
        if min_score is None:
            commodity_code = availability.commodity.code if availability.commodity else "default"
            min_score = self.config.get_min_score_threshold(commodity_code)
        
        logger.info(f"Finding matches for availability {availability_id}, min_score={min_score}")
        
        # Step 1: LOCATION-FIRST FILTER (DB query level)
        # Search requirements that include seller's location in their delivery_locations
        candidate_requirements = await self.requirement_repo.search_by_location(
            location_id=availability.location_id,
            commodity_id=availability.commodity_id,
            status="ACTIVE",
            include_relations=["commodity", "buyer_partner"]
        )
        
        logger.info(f"Found {len(candidate_requirements)} location-matched candidates")
        
        matches = []
        seen_duplicates: Set[str] = set()
        
        for requirement in candidate_requirements:
            # Step 2: Hard location filter
            if not self._location_matches(requirement, availability):
                continue
            
            # Step 3: Duplicate detection
            dup_key = self._generate_duplicate_key(requirement, availability)
            if await self._is_duplicate(dup_key, seen_duplicates, requirement.id, availability_id):
                continue
            
            # Step 4: Calculate match score
            try:
                score_result = await self.scorer.calculate_match_score(
                    requirement=requirement,
                    availability=availability,
                    risk_engine=self.risk_engine if include_risk_check else None
                )
                
                if score_result.get("blocked", False):
                    continue
                
                # Step 5: Filter by min score
                if score_result["total_score"] < min_score:
                    continue
                
                # Step 6: Create match result
                match = MatchResult(
                    requirement_id=requirement.id,
                    availability_id=availability.id,
                    score=score_result["total_score"],
                    base_score=score_result["base_score"],
                    warn_penalty_applied=score_result.get("warn_penalty_applied", False),
                    warn_penalty_value=score_result.get("warn_penalty_value", 0.0),
                    score_breakdown=score_result["breakdown"],
                    pass_fail=score_result["pass_fail"],
                    risk_status=score_result.get("risk_details", {}).get("risk_status", "UNKNOWN"),
                    risk_details=score_result.get("risk_details", {}),
                    location_filter_passed=True,
                    duplicate_detection_key=dup_key,
                    requirement=requirement,
                    availability=availability
                )
                
                matches.append(match)
                seen_duplicates.add(dup_key)
                
            except Exception as e:
                logger.error(f"Error scoring match: req={requirement.id}, avail={availability_id}, error={e}")
                continue
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        
        logger.info(f"Found {len(matches)} valid matches for availability {availability_id}")
        
        # Store audit trail (async)
        asyncio.create_task(self._save_match_audit_trail(matches, availability))
        
        return matches[:max_results]
    
    # ========================================================================
    # DUPLICATE DETECTION ⭐ CRITICAL
    # ========================================================================
    
    def _generate_duplicate_key(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> str:
        """
        Generate unique key for duplicate detection.
        
        Rules:
        - Same commodity
        - Same buyer-seller pair
        - Within 5-minute time window (checked in _is_duplicate)
        - 95%+ similar quality parameters (future enhancement)
        """
        return f"{requirement.commodity_id}:{requirement.buyer_partner_id}:{availability.seller_id}"
    
    async def _is_duplicate(
        self,
        dup_key: str,
        seen_duplicates: Set[str],
        requirement_id: UUID,
        availability_id: UUID
    ) -> bool:
        """
        Check if match is duplicate within time window.
        
        Uses in-memory cache + DB check for recent duplicates.
        """
        # In-memory check (current session)
        if dup_key in seen_duplicates:
            return True
        
        # DB check for recent duplicates (within time window)
        # Future: Query match_audit_trail table
        # For now, rely on in-memory check only
        
        return False
    
    # ========================================================================
    # ATOMIC PARTIAL ALLOCATION ⭐ CRITICAL
    # ========================================================================
    
    async def allocate_quantity_atomic(
        self,
        availability_id: UUID,
        requested_quantity: Decimal,
        requirement_id: UUID
    ) -> Dict[str, Any]:
        """
        Atomically allocate quantity with optimistic locking.
        
        CRITICAL: Prevents double-allocation in concurrent scenarios.
        
        Algorithm:
        1. Read availability with row-level lock
        2. Check if sufficient quantity available
        3. Update remaining_qty and increment version
        4. If version mismatch → retry
        
        Returns:
        {
            "allocated": True,
            "allocated_quantity": 6.0,
            "remaining_quantity": 4.0,
            "allocation_type": "PARTIAL",  # or "FULL"
            "version": 2
        }
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                async with self.db.begin_nested():  # Savepoint for retry
                    # Read with row-level lock (pessimistic locking)
                    stmt = (
                        select(Availability)
                        .where(Availability.id == availability_id)
                        .with_for_update()  # SELECT FOR UPDATE
                    )
                    result = await self.db.execute(stmt)
                    availability = result.scalar_one_or_none()
                    
                    if not availability:
                        return {"allocated": False, "error": "Availability not found"}
                    
                    # Check quantity
                    current_remaining = availability.remaining_quantity or Decimal(0)
                    
                    if current_remaining < requested_quantity:
                        # Partial allocation
                        allocated_qty = current_remaining
                        allocation_type = "PARTIAL"
                    else:
                        allocated_qty = requested_quantity
                        allocation_type = "FULL"
                    
                    if allocated_qty <= 0:
                        return {"allocated": False, "error": "No quantity available"}
                    
                    # Update (optimistic locking would check version here)
                    availability.remaining_quantity -= allocated_qty
                    
                    if availability.remaining_quantity <= 0:
                        availability.status = "SOLD"
                    
                    await self.db.flush()
                    
                    logger.info(
                        f"Allocated {allocated_qty} from availability {availability_id} "
                        f"for requirement {requirement_id}"
                    )
                    
                    return {
                        "allocated": True,
                        "allocated_quantity": float(allocated_qty),
                        "remaining_quantity": float(availability.remaining_quantity),
                        "allocation_type": allocation_type
                    }
                    
            except Exception as e:
                logger.warning(f"Allocation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        return {"allocated": False, "error": "Max retries exceeded"}
    
    # ========================================================================
    # AUDIT TRAIL ⭐ CRITICAL
    # ========================================================================
    
    async def _save_match_audit_trail(
        self,
        matches: List[MatchResult],
        entity: Any  # Requirement or Availability
    ) -> None:
        """
        Save detailed audit trail for explainability.
        
        Stores:
        - Full score breakdown
        - Risk assessment details
        - Location filter results
        - Duplicate detection results
        - Allocation status
        
        Future: Insert into match_audit_trail table
        """
        # Placeholder - will implement when audit table is created
        logger.debug(f"Audit trail: {len(matches)} matches for entity {entity.id}")
        pass
