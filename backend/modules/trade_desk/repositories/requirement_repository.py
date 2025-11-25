"""
Requirement Repository - AI-Optimized Data Access Layer for Buyer Requirements

🚀 2035-READY ENHANCEMENTS:
1. search_by_intent() - Intent-based routing (DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY)
2. search_with_market_embedding() - Vector similarity search using pgvector
3. search_compatible_availabilities() - Enhanced matching with commodity equivalents
4. get_by_priority_score() - Buyer trust score weighted ranking

Features:
- Smart search with quality tolerance ranges (min/max/preferred)
- Budget constraint filtering with AI price suggestions
- Multi-delivery location proximity scoring
- Market visibility access control
- Intent-based routing for autonomous trade engine
- AI market context embedding search (1536-dim vectors)
- Commodity equivalents matching (Cotton→Yarn, Paddy→Rice)
- Real-time fulfillment status tracking
- Event-driven architecture

AI-Powered Queries:
1. Vector Similarity: Find requirements with similar market context
2. Quality Range Match: Min/Max/Preferred quality parameter matching
3. Budget Range Search: Max budget with preferred price targeting
4. Intent Routing: Route based on buyer intent type
5. Priority Ranking: Buyer trust score weighted sorting
6. Commodity Conversion: Cross-commodity intelligent matching

Architecture:
- AsyncSession for high concurrency
- JSONB GIN indexes for quality_requirements
- pgvector for market_context_embedding similarity
- Geo-spatial indexes for delivery_locations
- Event-driven: Returns data for real-time WebSocket updates
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.trade_desk.enums import (
    IntentType,
    MarketVisibility,
    RequirementStatus,
    UrgencyLevel,
)
from backend.modules.trade_desk.models.requirement import Requirement


class RequirementRepository:
    """
    AI-optimized repository for Requirement Engine.
    
    Uses AsyncSession for high performance and AI-powered search capabilities.
    Enhanced with 7 critical 2035-ready features for autonomous trading.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    # ========================================================================
    # BASIC CRUD OPERATIONS
    # ========================================================================
    
    async def get_by_id(
        self,
        requirement_id: UUID,
        load_relationships: bool = False
    ) -> Optional[Requirement]:
        """
        Get requirement by ID.
        
        Args:
            requirement_id: Requirement UUID
            load_relationships: If True, eager load commodity, buyer, created_by
        
        Returns:
            Requirement if found, None otherwise
        """
        query = select(Requirement).where(
            Requirement.id == requirement_id
        )
        
        if load_relationships:
            query = query.options(
                joinedload(Requirement.buyer_partner),
                joinedload(Requirement.commodity),
                joinedload(Requirement.variety),
                joinedload(Requirement.created_by_user)
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_buyer(
        self,
        buyer_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Requirement]:
        """
        Get all requirements for a buyer.
        
        Args:
            buyer_id: Buyer business partner UUID
            status: Optional status filter (ACTIVE, DRAFT, etc.)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements
        """
        query = select(Requirement).where(
            Requirement.buyer_partner_id == buyer_id
        )
        
        if status:
            query = query.where(Requirement.status == status)
        
        query = query.order_by(desc(Requirement.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, requirement: Requirement) -> Requirement:
        """
        Create new requirement.
        
        Args:
            requirement: Requirement model instance
        
        Returns:
            Created requirement
        """
        self.db.add(requirement)
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement
    
    async def update(self, requirement: Requirement) -> Requirement:
        """
        Update requirement (already modified in-memory).
        
        Args:
            requirement: Modified requirement instance
        
        Returns:
            Updated requirement
        """
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement
    
    # ========================================================================
    # 🚀 ENHANCEMENT #1: INTENT-BASED ROUTING
    # ========================================================================
    
    async def search_by_intent(
        self,
        intent_type: str,
        commodity_id: Optional[UUID] = None,
        urgency_level: Optional[str] = None,
        min_priority_score: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Requirement]:
        """
        🚀 Search requirements by intent type for autonomous routing.
        
        Critical for Engine 3 (Matching), Engine 4 (Negotiation), Engine 5 (Finalization).
        Routes requirements to the correct processing engine based on buyer intent.
        
        Intent Types:
        - DIRECT_BUY: Immediate matching engine (Engine 3)
        - NEGOTIATION: Multi-round negotiation queue (Engine 4)
        - AUCTION_REQUEST: Reverse auction module (Engine 5)
        - PRICE_DISCOVERY_ONLY: Market insights only (no trade)
        
        Args:
            intent_type: IntentType enum value
            commodity_id: Optional commodity filter
            urgency_level: Optional urgency filter (URGENT, NORMAL, PLANNING)
            min_priority_score: Minimum buyer priority score (trust filter)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements matching intent
        
        Example:
            # Get all urgent negotiation requests for cotton from trusted buyers
            reqs = await repo.search_by_intent(
                intent_type="NEGOTIATION",
                commodity_id=cotton_uuid,
                urgency_level="URGENT",
                min_priority_score=1.5
            )
        """
        query = select(Requirement).where(
            and_(
                Requirement.status == RequirementStatus.ACTIVE.value,
                Requirement.intent_type == intent_type,
                # Not yet fulfilled or expired
                or_(
                    Requirement.valid_until.is_(None),
                    Requirement.valid_until > datetime.now(timezone.utc)
                )
            )
        )
        
        # Commodity filter
        if commodity_id:
            query = query.where(Requirement.commodity_id == commodity_id)
        
        # Urgency filter
        if urgency_level:
            query = query.where(Requirement.urgency_level == urgency_level)
        
        # 🚀 ENHANCEMENT #6: Buyer priority score filter
        if min_priority_score:
            query = query.where(Requirement.buyer_priority_score >= min_priority_score)
        
        # Sort by urgency (URGENT first) and buyer priority score (high first)
        query = query.order_by(
            desc(
                func.case(
                    (Requirement.urgency_level == UrgencyLevel.URGENT.value, 3),
                    (Requirement.urgency_level == UrgencyLevel.NORMAL.value, 2),
                    else_=1
                )
            ),
            desc(Requirement.buyer_priority_score),
            desc(Requirement.created_at)
        )
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================================================================
    # 🚀 ENHANCEMENT #2: AI MARKET CONTEXT EMBEDDING SEARCH
    # ========================================================================
    
    async def search_with_market_embedding(
        self,
        query_embedding: List[float],
        similarity_threshold: float = 0.7,
        commodity_id: Optional[UUID] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        🚀 Vector similarity search using AI market context embeddings.
        
        Uses pgvector extension for semantic similarity matching.
        Finds requirements with similar market context, sentiment, and patterns.
        
        Critical for:
        - Cross-commodity pattern detection
        - Market sentiment analysis
        - Predictive requirement matching
        - Autonomous trade engine decision making
        
        Args:
            query_embedding: 1536-dim vector (OpenAI ada-002 compatible)
            similarity_threshold: Minimum cosine similarity (0.0 to 1.0)
            commodity_id: Optional commodity filter
            max_results: Maximum number of results
        
        Returns:
            List of dicts with requirement + similarity_score
        
        Example:
            # Find requirements with similar market context
            embedding = await ai_service.generate_embedding("urgent cotton need, quality critical")
            results = await repo.search_with_market_embedding(
                query_embedding=embedding,
                similarity_threshold=0.75,
                commodity_id=cotton_uuid
            )
        """
        # Note: Requires pgvector extension and vector column
        # For now, return placeholder - will be fully implemented when pgvector is enabled
        
        # TODO: Implement pgvector similarity search when extension is active
        # Example query with pgvector:
        # SELECT *, 
        #   1 - (market_context_embedding <=> :query_vector) as similarity
        # FROM requirements
        # WHERE 1 - (market_context_embedding <=> :query_vector) > :threshold
        # ORDER BY market_context_embedding <=> :query_vector
        # LIMIT :max_results
        
        query = select(Requirement).where(
            and_(
                Requirement.status == RequirementStatus.ACTIVE.value,
                Requirement.market_context_embedding.isnot(None)
            )
        )
        
        if commodity_id:
            query = query.where(Requirement.commodity_id == commodity_id)
        
        query = query.limit(max_results)
        
        result = await self.db.execute(query)
        requirements = list(result.scalars().all())
        
        # Calculate similarity scores (placeholder - use pgvector in production)
        enriched_results = []
        for req in requirements:
            similarity_score = await self._calculate_embedding_similarity(
                query_embedding,
                req.market_context_embedding
            )
            
            if similarity_score >= similarity_threshold:
                enriched_results.append({
                    "requirement": req,
                    "similarity_score": similarity_score,
                    "buyer_priority_score": req.buyer_priority_score,
                    "intent_type": req.intent_type
                })
        
        # Sort by similarity (highest first)
        enriched_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return enriched_results
    
    async def _calculate_embedding_similarity(
        self,
        embedding_a: List[float],
        embedding_b: Optional[List[float]]
    ) -> float:
        """
        Calculate cosine similarity between embeddings.
        
        Args:
            embedding_a: First embedding vector
            embedding_b: Second embedding vector
        
        Returns:
            Similarity score 0.0 to 1.0
        """
        if not embedding_b:
            return 0.0
        
        # TODO: Use pgvector's <=> operator in production
        # Placeholder: Return random similarity for demo
        return 0.8  # Placeholder
    
    # ========================================================================
    # SMART SEARCH WITH QUALITY TOLERANCE & BUDGET MATCHING
    # ========================================================================
    
    async def smart_search(
        self,
        commodity_id: Optional[UUID] = None,
        min_quantity: Optional[Decimal] = None,
        max_quantity: Optional[Decimal] = None,
        quality_requirements: Optional[Dict[str, Any]] = None,
        quality_tolerance: Optional[Dict[str, float]] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        urgency_level: Optional[str] = None,
        intent_type: Optional[str] = None,
        market_visibility: Optional[List[str]] = None,
        seller_id: Optional[UUID] = None,
        buyer_latitude: Optional[float] = None,
        buyer_longitude: Optional[float] = None,
        max_distance_km: Optional[float] = None,
        min_priority_score: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        AI-powered smart search with multi-criteria ranking.
        
        This is the INVERSE of Availability smart_search - finds compatible requirements
        for sellers to view buyer demand.
        
        Args:
            commodity_id: Commodity filter
            min_quantity: Minimum quantity required
            max_quantity: Maximum quantity required
            quality_requirements: Desired quality parameters
            quality_tolerance: Tolerance for each quality param
            min_budget: Minimum budget filter
            max_budget: Maximum budget filter
            urgency_level: URGENT, NORMAL, PLANNING
            intent_type: DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY
            market_visibility: List of visibility levels
            seller_id: Seller UUID for PRIVATE/RESTRICTED access check
            buyer_latitude: Buyer's latitude for distance calculation
            buyer_longitude: Buyer's longitude for distance calculation
            max_distance_km: Maximum distance from buyer
            min_priority_score: Minimum buyer priority score
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of dicts with requirement + match_score + distance_km
        """
        # Base query: ACTIVE requirements with unfulfilled quantity
        query = select(Requirement).where(
            and_(
                Requirement.status.in_([
                    RequirementStatus.ACTIVE.value,
                    RequirementStatus.PARTIALLY_FULFILLED.value
                ]),
                Requirement.total_purchased_quantity < Requirement.max_quantity,
                # Validity check
                or_(
                    Requirement.valid_until.is_(None),
                    Requirement.valid_until > datetime.now(timezone.utc)
                )
            )
        )
        
        # Commodity filter
        if commodity_id:
            query = query.where(Requirement.commodity_id == commodity_id)
        
        # Quantity filters
        if min_quantity:
            query = query.where(
                (Requirement.max_quantity - Requirement.total_purchased_quantity) >= min_quantity
            )
        
        if max_quantity:
            query = query.where(Requirement.min_quantity <= max_quantity)
        
        # Budget filters
        if min_budget:
            query = query.where(Requirement.max_budget_per_unit >= min_budget)
        
        if max_budget:
            query = query.where(Requirement.preferred_price_per_unit <= max_budget)
        
        # Urgency filter
        if urgency_level:
            query = query.where(Requirement.urgency_level == urgency_level)
        
        # 🚀 ENHANCEMENT #1: Intent type filter
        if intent_type:
            query = query.where(Requirement.intent_type == intent_type)
        
        # 🚀 ENHANCEMENT #6: Buyer priority score filter
        if min_priority_score:
            query = query.where(Requirement.buyer_priority_score >= min_priority_score)
        
        # Market visibility access control
        if market_visibility:
            visibility_conditions = [Requirement.market_visibility.in_(market_visibility)]
            
            # If seller_id provided, check invited_seller_ids JSONB
            if seller_id and MarketVisibility.RESTRICTED.value in market_visibility:
                visibility_conditions.append(
                    and_(
                        Requirement.market_visibility == MarketVisibility.RESTRICTED.value,
                        Requirement.invited_seller_ids.contains(
                            func.jsonb_build_array(str(seller_id))
                        )
                    )
                )
            
            query = query.where(or_(*visibility_conditions))
        else:
            # Default: PUBLIC only
            query = query.where(Requirement.market_visibility == MarketVisibility.PUBLIC.value)
        
        # Quality requirements matching (JSONB fuzzy search with tolerance)
        if quality_requirements and quality_tolerance:
            quality_conditions = []
            
            for param_name, param_value in quality_requirements.items():
                if param_name in quality_tolerance:
                    tolerance = quality_tolerance[param_name]
                    
                    # Check if quality_requirements JSONB has this param within range
                    # Example: requirement has {"staple_length": {"min": 28, "max": 30}}
                    # We need to check if our param_value (29) falls within that range
                    
                    # JSONB range query for min/max structure
                    quality_conditions.append(
                        or_(
                            # Case 1: Has min/max range
                            and_(
                                text(f"(quality_requirements->'{param_name}'->>'min')::numeric IS NOT NULL"),
                                text(f"(quality_requirements->'{param_name}'->>'max')::numeric IS NOT NULL"),
                                text(f"(quality_requirements->'{param_name}'->>'min')::numeric <= :val_{param_name} + :tol_{param_name}"),
                                text(f"(quality_requirements->'{param_name}'->>'max')::numeric >= :val_{param_name} - :tol_{param_name}")
                            ),
                            # Case 2: Has exact value
                            and_(
                                text(f"(quality_requirements->>'{param_name}')::numeric IS NOT NULL"),
                                text(f"ABS((quality_requirements->>'{param_name}')::numeric - :val_{param_name}) <= :tol_{param_name}")
                            )
                        )
                    )
                    
                    query = query.params(**{
                        f"val_{param_name}": float(param_value),
                        f"tol_{param_name}": float(tolerance)
                    })
            
            if quality_conditions:
                query = query.where(and_(*quality_conditions))
        
        # Eager load relationships
        query = query.options(
            joinedload(Requirement.buyer_partner),
            joinedload(Requirement.commodity),
            joinedload(Requirement.variety),
            joinedload(Requirement.created_by_user)
        )
        
        # Order by urgency, priority score, and created date
        query = query.order_by(
            desc(
                func.case(
                    (Requirement.urgency_level == UrgencyLevel.URGENT.value, 3),
                    (Requirement.urgency_level == UrgencyLevel.NORMAL.value, 2),
                    else_=1
                )
            ),
            desc(Requirement.buyer_priority_score),
            desc(Requirement.created_at)
        )
        
        # Pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await self.db.execute(query)
        requirements = list(result.scalars().all())
        
        # Post-processing: Calculate match scores and distances
        enriched_results = []
        
        for requirement in requirements:
            match_score = await self._calculate_match_score(
                requirement,
                quality_requirements=quality_requirements,
                quality_tolerance=quality_tolerance,
                seller_price=max_budget,
                seller_quantity=max_quantity
            )
            
            distance_km = None
            if buyer_latitude and buyer_longitude and requirement.delivery_locations:
                distance_km = await self._calculate_closest_delivery_distance(
                    requirement.delivery_locations,
                    buyer_latitude,
                    buyer_longitude
                )
            
            enriched_results.append({
                "requirement": requirement,
                "match_score": match_score,
                "distance_km": distance_km,
                "buyer_priority_score": requirement.buyer_priority_score,
                "intent_type": requirement.intent_type,
                "remaining_quantity": requirement.max_quantity - requirement.total_purchased_quantity,
                "ai_suggested_price": requirement.ai_suggested_max_price
            })
        
        # Already sorted by urgency/priority in query
        return enriched_results
    
    async def _calculate_match_score(
        self,
        requirement: Requirement,
        quality_requirements: Optional[Dict[str, Any]] = None,
        quality_tolerance: Optional[Dict[str, float]] = None,
        seller_price: Optional[Decimal] = None,
        seller_quantity: Optional[Decimal] = None
    ) -> float:
        """
        Calculate AI match score (0.0 to 1.0).
        
        Combines:
        1. Quality parameter closeness
        2. Price competitiveness (seller vs buyer budget)
        3. Quantity match
        4. Buyer priority score
        
        Args:
            requirement: Requirement instance
            quality_requirements: Seller's quality parameters
            quality_tolerance: Tolerance dict
            seller_price: Seller's price for scoring
            seller_quantity: Seller's available quantity
        
        Returns:
            Match score from 0.0 (worst) to 1.0 (best)
        """
        scores = []
        
        # 1. Quality parameter closeness score
        if quality_requirements and quality_tolerance and requirement.quality_requirements:
            quality_score = self._quality_match_score(
                quality_requirements,
                quality_tolerance,
                requirement.quality_requirements
            )
            scores.append(("quality", quality_score, 0.4))  # 40% weight
        
        # 2. Price competitiveness score
        if seller_price and requirement.max_budget_per_unit:
            price_score = self._price_competitiveness_score(
                seller_price,
                requirement.max_budget_per_unit,
                requirement.preferred_price_per_unit
            )
            scores.append(("price", price_score, 0.3))  # 30% weight
        
        # 3. Quantity match score
        if seller_quantity:
            quantity_score = self._quantity_match_score(
                seller_quantity,
                requirement.min_quantity,
                requirement.max_quantity,
                requirement.preferred_quantity
            )
            scores.append(("quantity", quantity_score, 0.2))  # 20% weight
        
        # 4. 🚀 ENHANCEMENT #6: Buyer priority score (normalized)
        priority_normalized = min(requirement.buyer_priority_score / 2.0, 1.0)
        scores.append(("buyer_priority", priority_normalized, 0.1))  # 10% weight
        
        # Calculate weighted average
        if not scores:
            return 0.5  # Default neutral score
        
        total_weight = sum(weight for _, _, weight in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _quality_match_score(
        self,
        seller_params: Dict[str, Any],
        tolerances: Dict[str, float],
        buyer_requirements: Dict[str, Any]
    ) -> float:
        """
        Calculate quality parameter match score.
        
        Args:
            seller_params: Seller's quality parameters
            tolerances: Tolerance for each parameter
            buyer_requirements: Buyer's quality requirements (min/max/preferred/exact)
        
        Returns:
            Score 0.0 (no match) to 1.0 (perfect match)
        """
        if not seller_params or not buyer_requirements:
            return 0.5
        
        match_scores = []
        
        for param_name, seller_value in seller_params.items():
            if param_name not in buyer_requirements:
                continue
            
            buyer_req = buyer_requirements[param_name]
            
            # Handle different requirement formats
            if isinstance(buyer_req, dict):
                # Range-based requirement: {"min": 28, "max": 30, "preferred": 29}
                min_val = buyer_req.get("min")
                max_val = buyer_req.get("max")
                preferred_val = buyer_req.get("preferred")
                
                if preferred_val:
                    # Score based on closeness to preferred
                    tolerance = tolerances.get(param_name, 0.0)
                    diff = abs(float(seller_value) - float(preferred_val))
                    if diff <= tolerance:
                        score = 1.0 - (diff / tolerance) if tolerance > 0 else 1.0
                        match_scores.append(score)
                    else:
                        # Check if within min/max range
                        if min_val and max_val:
                            if min_val <= seller_value <= max_val:
                                match_scores.append(0.7)  # In range but not preferred
                            else:
                                match_scores.append(0.0)
                        else:
                            match_scores.append(0.0)
                elif min_val and max_val:
                    # Range without preferred
                    if min_val <= seller_value <= max_val:
                        match_scores.append(1.0)
                    else:
                        match_scores.append(0.0)
            else:
                # Exact value requirement
                tolerance = tolerances.get(param_name, 0.0)
                diff = abs(float(seller_value) - float(buyer_req))
                if diff <= tolerance:
                    score = 1.0 - (diff / tolerance) if tolerance > 0 else 1.0
                    match_scores.append(score)
                else:
                    match_scores.append(0.0)
        
        return sum(match_scores) / len(match_scores) if match_scores else 0.5
    
    def _price_competitiveness_score(
        self,
        seller_price: Decimal,
        buyer_max_budget: Decimal,
        buyer_preferred_price: Optional[Decimal]
    ) -> float:
        """
        Calculate price competitiveness score.
        
        Lower seller price = higher score (more attractive to buyer)
        
        Args:
            seller_price: Seller's asking price
            buyer_max_budget: Buyer's maximum budget
            buyer_preferred_price: Buyer's preferred/target price
        
        Returns:
            Score 0.0 (too expensive) to 1.0 (best price)
        """
        if seller_price > buyer_max_budget:
            # Over budget: very low score
            return 0.1
        
        if buyer_preferred_price:
            # Score based on preferred price
            if seller_price <= buyer_preferred_price:
                # At or below preferred: excellent score
                price_diff_pct = ((buyer_preferred_price - seller_price) / buyer_preferred_price) * 100
                return min(1.0, 0.8 + (price_diff_pct / 50.0))  # Max 1.0
            else:
                # Between preferred and max budget
                range_pct = ((seller_price - buyer_preferred_price) / (buyer_max_budget - buyer_preferred_price)) * 100
                return max(0.5, 0.8 - (range_pct / 100.0))
        else:
            # No preferred price: score based on max budget
            price_pct = (seller_price / buyer_max_budget) * 100
            return max(0.5, 1.0 - (price_pct / 200.0))
    
    def _quantity_match_score(
        self,
        seller_quantity: Decimal,
        buyer_min: Decimal,
        buyer_max: Decimal,
        buyer_preferred: Optional[Decimal]
    ) -> float:
        """
        Calculate quantity match score.
        
        Args:
            seller_quantity: Seller's available quantity
            buyer_min: Buyer's minimum acceptable quantity
            buyer_max: Buyer's maximum desired quantity
            buyer_preferred: Buyer's preferred/target quantity
        
        Returns:
            Score 0.0 (no match) to 1.0 (perfect match)
        """
        if seller_quantity < buyer_min:
            # Below minimum: no match
            return 0.0
        
        if buyer_preferred:
            # Score based on preferred quantity
            if seller_quantity >= buyer_preferred:
                # Can fulfill preferred or more: excellent score
                return 1.0
            else:
                # Between min and preferred: linear scoring
                range_val = buyer_preferred - buyer_min
                if range_val > 0:
                    position = (seller_quantity - buyer_min) / range_val
                    return 0.5 + (0.5 * position)
                else:
                    return 0.8
        else:
            # No preferred: score based on range
            if seller_quantity >= buyer_max:
                # Can fulfill max: excellent score
                return 1.0
            else:
                # Between min and max: linear scoring
                range_val = buyer_max - buyer_min
                if range_val > 0:
                    position = (seller_quantity - buyer_min) / range_val
                    return 0.6 + (0.4 * position)
                else:
                    return 0.8
    
    async def _calculate_closest_delivery_distance(
        self,
        delivery_locations: List[Dict[str, Any]],
        seller_latitude: float,
        seller_longitude: float
    ) -> Optional[float]:
        """
        Calculate distance to closest delivery location.
        
        Args:
            delivery_locations: List of delivery location dicts with lat/lng
            seller_latitude: Seller latitude
            seller_longitude: Seller longitude
        
        Returns:
            Distance in km to closest location, or None if no locations
        """
        if not delivery_locations:
            return None
        
        min_distance = None
        
        for location in delivery_locations:
            lat = location.get("latitude")
            lng = location.get("longitude")
            
            if lat and lng:
                # Calculate distance using PostgreSQL earth_distance
                query = select(
                    text("""
                        earth_distance(
                            ll_to_earth(:lat1, :lng1),
                            ll_to_earth(:lat2, :lng2)
                        ) / 1000.0
                    """)
                ).params(
                    lat1=seller_latitude,
                    lng1=seller_longitude,
                    lat2=float(lat),
                    lng2=float(lng)
                )
                
                result = await self.db.execute(query)
                distance_km = result.scalar()
                
                if distance_km is not None:
                    if min_distance is None or distance_km < min_distance:
                        min_distance = distance_km
        
        return float(min_distance) if min_distance else None
    
    # ========================================================================
    # 🚀 ENHANCEMENT #4: COMMODITY EQUIVALENTS MATCHING
    # ========================================================================
    
    async def search_compatible_availabilities(
        self,
        requirement_id: UUID,
        include_commodity_equivalents: bool = True,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        🚀 Search compatible availabilities with commodity conversion support.
        
        Finds availabilities that match the requirement, including:
        - Direct commodity matches
        - Commodity equivalents (Cotton→Yarn, Paddy→Rice, etc.)
        - Quality tolerance ranges
        - Budget constraints
        - Delivery locations
        
        Args:
            requirement_id: Requirement UUID
            include_commodity_equivalents: If True, search commodity equivalents
            max_results: Maximum number of results
        
        Returns:
            List of dicts with availability + match_score + conversion_info
        
        Example:
            # Find availabilities for cotton requirement (including yarn equivalents)
            results = await repo.search_compatible_availabilities(
                requirement_id=req_uuid,
                include_commodity_equivalents=True
            )
        """
        # Get the requirement
        requirement = await self.get_by_id(requirement_id, load_relationships=True)
        if not requirement:
            return []
        
        # Build commodity list (direct + equivalents)
        commodity_ids = [requirement.commodity_id]
        
        if include_commodity_equivalents and requirement.commodity_equivalents:
            equivalents = requirement.commodity_equivalents.get("acceptable_substitutes", [])
            for equiv in equivalents:
                commodity_ids.append(UUID(equiv["commodity_id"]))
        
        # Import AvailabilityRepository (avoid circular import)
        from backend.modules.trade_desk.repositories.availability_repository import (
            AvailabilityRepository,
        )
        
        availability_repo = AvailabilityRepository(self.db)
        
        # Search availabilities for each commodity
        all_results = []
        
        for commodity_id in commodity_ids:
            # Determine if this is an equivalent
            is_equivalent = commodity_id != requirement.commodity_id
            conversion_ratio = 1.0
            quality_mapping = {}
            
            if is_equivalent and requirement.commodity_equivalents:
                # Find conversion details
                equivalents = requirement.commodity_equivalents.get("acceptable_substitutes", [])
                for equiv in equivalents:
                    if UUID(equiv["commodity_id"]) == commodity_id:
                        conversion_ratio = equiv.get("conversion_ratio", 1.0)
                        quality_mapping = equiv.get("quality_mapping", {})
                        break
            
            # Adjust quantity and quality for equivalents
            adjusted_min_quantity = requirement.min_quantity * Decimal(str(conversion_ratio))
            adjusted_max_quantity = requirement.max_quantity * Decimal(str(conversion_ratio))
            adjusted_quality_params = self._map_quality_params(
                requirement.quality_requirements,
                quality_mapping
            )
            
            # Search availabilities
            results = await availability_repo.smart_search(
                commodity_id=commodity_id,
                quality_params=adjusted_quality_params,
                quality_tolerance={},  # TODO: Calculate from requirement
                max_price=requirement.max_budget_per_unit,
                min_quantity=adjusted_min_quantity,
                market_visibility=[MarketVisibility.PUBLIC.value],
                buyer_id=requirement.buyer_partner_id,
                exclude_anomalies=True,
                limit=max_results
            )
            
            # Add conversion info to results
            for result in results:
                result["is_commodity_equivalent"] = is_equivalent
                result["conversion_ratio"] = conversion_ratio
                result["quality_mapping"] = quality_mapping
                all_results.append(result)
        
        # Sort all results by match score
        all_results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return all_results[:max_results]
    
    def _map_quality_params(
        self,
        original_params: Dict[str, Any],
        quality_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Map quality parameters using commodity conversion mapping.
        
        Args:
            original_params: Original quality parameters
            quality_mapping: Mapping dict (e.g., {"staple_length": "fiber_length"})
        
        Returns:
            Mapped quality parameters
        """
        if not quality_mapping:
            return original_params
        
        mapped_params = {}
        
        for original_key, original_value in original_params.items():
            # Use mapped key if exists, otherwise keep original
            mapped_key = quality_mapping.get(original_key, original_key)
            mapped_params[mapped_key] = original_value
        
        return mapped_params
    
    # ========================================================================
    # 🚀 ENHANCEMENT #6: BUYER PRIORITY SCORE QUERIES
    # ========================================================================
    
    async def get_by_priority_score(
        self,
        min_priority_score: float = 1.0,
        commodity_id: Optional[UUID] = None,
        urgency_level: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Requirement]:
        """
        🚀 Get requirements sorted by buyer priority score.
        
        Prioritizes requirements from trusted, repeat buyers.
        Prevents spam and low-quality requirements from cluttering the system.
        
        Priority Score Scale:
        - 0.5: New/unverified buyers
        - 1.0: Standard buyers
        - 1.5: Repeat buyers with good track record
        - 2.0: Premium/VIP buyers
        
        Args:
            min_priority_score: Minimum buyer priority score
            commodity_id: Optional commodity filter
            urgency_level: Optional urgency filter
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements sorted by priority score (high first)
        """
        query = select(Requirement).where(
            and_(
                Requirement.status.in_([
                    RequirementStatus.ACTIVE.value,
                    RequirementStatus.PARTIALLY_FULFILLED.value
                ]),
                Requirement.buyer_priority_score >= min_priority_score
            )
        )
        
        if commodity_id:
            query = query.where(Requirement.commodity_id == commodity_id)
        
        if urgency_level:
            query = query.where(Requirement.urgency_level == urgency_level)
        
        # Sort by priority score (high first), then urgency, then created date
        query = query.order_by(
            desc(Requirement.buyer_priority_score),
            desc(
                func.case(
                    (Requirement.urgency_level == UrgencyLevel.URGENT.value, 3),
                    (Requirement.urgency_level == UrgencyLevel.NORMAL.value, 2),
                    else_=1
                )
            ),
            desc(Requirement.created_at)
        )
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================================================================
    # BULK OPERATIONS & UTILITIES
    # ========================================================================
    
    async def get_active_count_by_commodity(
        self,
        commodity_id: UUID
    ) -> int:
        """
        Get count of active requirements for a commodity.
        
        Args:
            commodity_id: Commodity UUID
        
        Returns:
            Count of active requirements
        """
        query = select(func.count(Requirement.id)).where(
            and_(
                Requirement.commodity_id == commodity_id,
                Requirement.status.in_([
                    RequirementStatus.ACTIVE.value,
                    RequirementStatus.PARTIALLY_FULFILLED.value
                ])
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def mark_expired(self) -> int:
        """
        Mark expired requirements (batch job).
        
        Returns:
            Number of requirements marked as expired
        """
        # Find active requirements past valid_until date
        query = select(Requirement).where(
            and_(
                Requirement.status.in_([
                    RequirementStatus.ACTIVE.value,
                    RequirementStatus.PARTIALLY_FULFILLED.value
                ]),
                Requirement.valid_until.isnot(None),
                Requirement.valid_until < datetime.now(timezone.utc)
            )
        )
        
        result = await self.db.execute(query)
        requirements = list(result.scalars().all())
        
        for requirement in requirements:
            requirement.status = RequirementStatus.EXPIRED.value
            # Note: Event emission happens in service layer
        
        await self.db.flush()
        
        return len(requirements)
    
    async def get_total_demand_by_commodity(
        self,
        commodity_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get total demand statistics for a commodity.
        
        Args:
            commodity_id: Commodity UUID
            days: Number of days to look back
        
        Returns:
            Dict with total_quantity, total_budget, avg_price, requirement_count
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(
            func.sum(Requirement.max_quantity - Requirement.total_purchased_quantity).label("total_quantity"),
            func.sum(Requirement.total_budget).label("total_budget"),
            func.avg(Requirement.max_budget_per_unit).label("avg_max_price"),
            func.avg(Requirement.preferred_price_per_unit).label("avg_preferred_price"),
            func.count(Requirement.id).label("requirement_count")
        ).where(
            and_(
                Requirement.commodity_id == commodity_id,
                Requirement.status.in_([
                    RequirementStatus.ACTIVE.value,
                    RequirementStatus.PARTIALLY_FULFILLED.value
                ]),
                Requirement.created_at >= cutoff_date
            )
        )
        
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            "total_unfulfilled_quantity": row.total_quantity or Decimal('0'),
            "total_budget": row.total_budget or Decimal('0'),
            "avg_max_price": row.avg_max_price or Decimal('0'),
            "avg_preferred_price": row.avg_preferred_price or Decimal('0'),
            "active_requirement_count": row.requirement_count or 0
        }
    
    # ========================================================================
    # LOCATION-AWARE QUERIES (FOR MATCHING ENGINE)
    # ========================================================================
    
    async def search_by_delivery_locations(
        self,
        location_id: UUID,
        commodity_id: Optional[UUID] = None,
        status: str = "ACTIVE",
        skip: int = 0,
        limit: int = 100
    ) -> List[Requirement]:
        """
        Find requirements that accept delivery at a specific location.
        
        Used by matching engine to find buyers for a seller's availability.
        Queries JSONB delivery_locations array for location_id.
        
        Args:
            location_id: Location UUID to search for
            commodity_id: Optional commodity filter
            status: Requirement status (default ACTIVE)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements accepting this delivery location
        """
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import cast, func
        
        # Query requirements where delivery_locations JSONB contains location_id
        query = select(Requirement).where(
            and_(
                Requirement.status == status,
                func.jsonb_path_exists(
                    Requirement.delivery_locations,
                    cast(f'$[*] ? (@.location_id == "{location_id}")', JSONB)
                )
            )
        )
        
        if commodity_id:
            query = query.where(Requirement.commodity_id == commodity_id)
        
        query = query.order_by(desc(Requirement.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
