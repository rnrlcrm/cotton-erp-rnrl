"""
Availability Repository - AI-Optimized Data Access Layer

Features:
- smart_search(): AI vector embedding search for commodity similarity
- Quality tolerance matching (e.g., 28mm cotton → also show 29mm/30mm)
- Price tolerance filtering (within budget range)
- Region-based proximity scoring (geo-spatial)
- Market visibility access control
- Real-time matching queries for Matching Engine (Engine 3)

AI-Powered Queries:
1. Vector Similarity: Find similar commodities using ai_score_vector
2. Quality Fuzzy Match: Tolerance-based quality parameter matching
3. Price Range Search: With anomaly detection filtering
4. Geo-Proximity: Distance-based location scoring
5. Multi-Criteria Ranking: Combined score for best matches

Architecture:
- AsyncSession for high concurrency (millions of trades)
- JSONB GIN indexes for fast quality_params search
- Geo-spatial indexes for location-based queries
- Event-driven: Returns data for real-time WebSocket updates
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.trade_desk.enums import AvailabilityStatus, MarketVisibility
from backend.modules.trade_desk.models import Availability


class AvailabilityRepository:
    """
    AI-optimized repository for Availability Engine.
    
    Uses AsyncSession for high performance and AI-powered search capabilities.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    # ========================
    # Basic CRUD Operations
    # ========================
    
    async def get_by_id(
        self,
        availability_id: UUID,
        load_relationships: bool = False
    ) -> Optional[Availability]:
        """
        Get availability by ID.
        
        Args:
            availability_id: Availability UUID
            load_relationships: If True, eager load commodity, location, seller
        
        Returns:
            Availability if found, None otherwise
        """
        query = select(Availability).where(
            and_(
                Availability.id == availability_id,
                Availability.is_deleted == False  # noqa: E712
            )
        )
        
        if load_relationships:
            query = query.options(
                joinedload(Availability.commodity),
                joinedload(Availability.location),
                joinedload(Availability.seller)
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_seller(
        self,
        seller_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Availability]:
        """
        Get all availabilities for a seller.
        
        Args:
            seller_id: Seller business partner UUID
            status: Optional status filter (ACTIVE, DRAFT, etc.)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of availabilities
        """
        query = select(Availability).where(
            and_(
                Availability.seller_id == seller_id,
                Availability.is_deleted == False  # noqa: E712
            )
        )
        
        if status:
            query = query.where(Availability.status == status)
        
        query = query.order_by(desc(Availability.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, availability: Availability) -> Availability:
        """
        Create new availability.
        
        Args:
            availability: Availability model instance
        
        Returns:
            Created availability
        """
        self.db.add(availability)
        await self.db.flush()
        await self.db.refresh(availability)
        return availability
    
    async def update(self, availability: Availability) -> Availability:
        """
        Update availability (already modified in-memory).
        
        Args:
            availability: Modified availability instance
        
        Returns:
            Updated availability
        """
        await self.db.flush()
        await self.db.refresh(availability)
        return availability
    
    async def soft_delete(self, availability_id: UUID, deleted_by: UUID) -> bool:
        """
        Soft delete availability (GDPR compliance).
        
        Args:
            availability_id: Availability UUID
            deleted_by: User UUID who deleted it
        
        Returns:
            True if deleted, False if not found
        """
        availability = await self.get_by_id(availability_id)
        if not availability:
            return False
        
        availability.is_deleted = True
        availability.deleted_by = deleted_by
        availability.deleted_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        return True
    
    # ========================
    # AI-Powered Search
    # ========================
    
    async def smart_search(
        self,
        query_vector: Optional[Dict[str, Any]] = None,
        commodity_id: Optional[UUID] = None,
        quality_params: Optional[Dict[str, Any]] = None,
        quality_tolerance: Optional[Dict[str, float]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        price_tolerance_pct: Optional[float] = None,
        location_id: Optional[UUID] = None,
        delivery_region: Optional[str] = None,
        max_distance_km: Optional[float] = None,
        buyer_latitude: Optional[float] = None,
        buyer_longitude: Optional[float] = None,
        min_quantity: Optional[Decimal] = None,
        allow_partial: Optional[bool] = None,
        market_visibility: Optional[List[str]] = None,
        buyer_id: Optional[UUID] = None,
        exclude_anomalies: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        AI-powered smart search with multi-criteria ranking.
        
        This is the HEART of the Matching Engine - finds compatible availabilities
        using AI vector embeddings, quality tolerance, price range, and geo-proximity.
        
        Args:
            query_vector: AI embedding vector for commodity similarity (JSONB)
            commodity_id: Exact commodity filter
            quality_params: Desired quality parameters
            quality_tolerance: Tolerance for each quality param (e.g., {"length": 0.5})
            min_price: Minimum acceptable price
            max_price: Maximum acceptable price
            price_tolerance_pct: Price tolerance percentage (e.g., 10.0 for ±10%)
            location_id: Exact location filter
            delivery_region: Region filter (WEST, SOUTH, etc.)
            max_distance_km: Maximum distance from buyer location
            buyer_latitude: Buyer latitude for distance calculation
            buyer_longitude: Buyer longitude for distance calculation
            min_quantity: Minimum available quantity required
            allow_partial: Filter by allow_partial_order
            market_visibility: List of visibility levels (PUBLIC, PRIVATE, etc.)
            buyer_id: Buyer UUID for PRIVATE/RESTRICTED access check
            exclude_anomalies: If True, exclude price anomalies (ai_price_anomaly_flag)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of dicts with availability + match_score + distance_km
            
        Example:
            # Find cotton 29mm within 10% price tolerance and 200km radius
            results = await repo.smart_search(
                commodity_id=cotton_uuid,
                quality_params={"length": 29.0, "strength": 26.0},
                quality_tolerance={"length": 1.0, "strength": 2.0},
                max_price=70000,
                price_tolerance_pct=10.0,
                buyer_latitude=23.0225,
                buyer_longitude=72.5714,
                max_distance_km=200.0,
                exclude_anomalies=True
            )
        """
        # Base query: ACTIVE availabilities with available quantity
        query = select(Availability).where(
            and_(
                Availability.status == AvailabilityStatus.ACTIVE.value,
                Availability.available_quantity > 0,
                Availability.is_deleted == False,  # noqa: E712
                # Expiry check
                or_(
                    Availability.expiry_date.is_(None),
                    Availability.expiry_date > datetime.now(timezone.utc)
                )
            )
        )
        
        # Commodity filter
        if commodity_id:
            query = query.where(Availability.commodity_id == commodity_id)
        
        # Quantity filter
        if min_quantity:
            query = query.where(Availability.available_quantity >= min_quantity)
        
        # Partial order filter
        if allow_partial is not None:
            query = query.where(Availability.allow_partial_order == allow_partial)
        
        # Price range filter
        if min_price or max_price:
            if min_price:
                query = query.where(Availability.base_price >= min_price)
            if max_price:
                query = query.where(Availability.base_price <= max_price)
        
        # Region filter
        if delivery_region:
            query = query.where(Availability.delivery_region == delivery_region)
        
        # Location filter
        if location_id:
            query = query.where(Availability.location_id == location_id)
        
        # Market visibility access control
        if market_visibility:
            visibility_conditions = [Availability.market_visibility.in_(market_visibility)]
            
            # If buyer_id provided, check restricted_buyers JSONB
            if buyer_id and MarketVisibility.RESTRICTED.value in market_visibility:
                visibility_conditions.append(
                    and_(
                        Availability.market_visibility == MarketVisibility.RESTRICTED.value,
                        Availability.restricted_buyers.contains(
                            func.jsonb_build_array(str(buyer_id))
                        )
                    )
                )
            
            query = query.where(or_(*visibility_conditions))
        else:
            # Default: PUBLIC only
            query = query.where(Availability.market_visibility == MarketVisibility.PUBLIC.value)
        
        # Exclude price anomalies (AI-detected unrealistic prices)
        if exclude_anomalies:
            query = query.where(Availability.ai_price_anomaly_flag == False)  # noqa: E712
        
        # Quality parameters matching (JSONB fuzzy search with tolerance)
        if quality_params and quality_tolerance:
            quality_conditions = []
            
            for param_name, param_value in quality_params.items():
                if param_name in quality_tolerance:
                    tolerance = quality_tolerance[param_name]
                    min_val = param_value - tolerance
                    max_val = param_value + tolerance
                    
                    # JSONB numeric range query
                    # Cast JSONB value to numeric and check range
                    quality_conditions.append(
                        and_(
                            text(f"(quality_params->>'{param_name}')::numeric >= :min_{param_name}"),
                            text(f"(quality_params->>'{param_name}')::numeric <= :max_{param_name}")
                        )
                    )
                    query = query.params(**{
                        f"min_{param_name}": float(min_val),
                        f"max_{param_name}": float(max_val)
                    })
            
            if quality_conditions:
                query = query.where(and_(*quality_conditions))
        
        # Geo-spatial distance filter (if buyer location provided)
        if buyer_latitude and buyer_longitude and max_distance_km:
            # PostgreSQL ST_Distance calculation (Haversine formula)
            # Distance in kilometers using earth_distance extension
            query = query.where(
                and_(
                    Availability.delivery_latitude.isnot(None),
                    Availability.delivery_longitude.isnot(None),
                    text("""
                        earth_distance(
                            ll_to_earth(:buyer_lat, :buyer_lng),
                            ll_to_earth(delivery_latitude, delivery_longitude)
                        ) <= :max_distance
                    """)
                )
            ).params(
                buyer_lat=buyer_latitude,
                buyer_lng=buyer_longitude,
                max_distance=max_distance_km * 1000  # Convert km to meters
            )
        
        # Eager load relationships for performance
        query = query.options(
            joinedload(Availability.commodity),
            joinedload(Availability.location),
            joinedload(Availability.seller)
        )
        
        # Order by created_at (newest first) - AI scoring happens post-query
        query = query.order_by(desc(Availability.created_at))
        
        # Pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await self.db.execute(query)
        availabilities = list(result.scalars().all())
        
        # Post-processing: Calculate match scores and distances
        enriched_results = []
        
        for availability in availabilities:
            match_score = await self._calculate_match_score(
                availability,
                query_vector=query_vector,
                quality_params=quality_params,
                quality_tolerance=quality_tolerance,
                target_price=max_price,
                price_tolerance_pct=price_tolerance_pct
            )
            
            distance_km = None
            if buyer_latitude and buyer_longitude:
                distance_km = await self._calculate_distance(
                    availability,
                    buyer_latitude,
                    buyer_longitude
                )
            
            enriched_results.append({
                "availability": availability,
                "match_score": match_score,
                "distance_km": distance_km,
                "ai_confidence": availability.ai_confidence_score,
                "ai_suggested_price": availability.ai_suggested_price
            })
        
        # Sort by match_score (highest first)
        enriched_results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return enriched_results
    
    async def _calculate_match_score(
        self,
        availability: Availability,
        query_vector: Optional[Dict[str, Any]] = None,
        quality_params: Optional[Dict[str, Any]] = None,
        quality_tolerance: Optional[Dict[str, float]] = None,
        target_price: Optional[Decimal] = None,
        price_tolerance_pct: Optional[float] = None
    ) -> float:
        """
        Calculate AI match score (0.0 to 1.0).
        
        Combines:
        1. Vector similarity (if query_vector provided)
        2. Quality parameter closeness
        3. Price competitiveness
        4. AI confidence score
        
        Args:
            availability: Availability instance
            query_vector: AI embedding vector for similarity
            quality_params: Desired quality parameters
            quality_tolerance: Tolerance dict
            target_price: Target price for scoring
            price_tolerance_pct: Price tolerance percentage
        
        Returns:
            Match score from 0.0 (worst) to 1.0 (best)
        """
        scores = []
        
        # 1. Vector similarity score (if AI embeddings available)
        if query_vector and availability.ai_score_vector:
            vector_score = await self._cosine_similarity(
                query_vector,
                availability.ai_score_vector
            )
            scores.append(("vector", vector_score, 0.4))  # 40% weight
        
        # 2. Quality parameter closeness score
        if quality_params and quality_tolerance and availability.quality_params:
            quality_score = self._quality_match_score(
                quality_params,
                quality_tolerance,
                availability.quality_params
            )
            scores.append(("quality", quality_score, 0.3))  # 30% weight
        
        # 3. Price competitiveness score
        if target_price and availability.base_price:
            price_score = self._price_competitiveness_score(
                availability.base_price,
                target_price,
                price_tolerance_pct or 10.0
            )
            scores.append(("price", price_score, 0.2))  # 20% weight
        
        # 4. AI confidence score (if available)
        if availability.ai_confidence_score:
            scores.append(("ai_confidence", float(availability.ai_confidence_score), 0.1))  # 10% weight
        
        # Calculate weighted average
        if not scores:
            return 0.5  # Default neutral score
        
        total_weight = sum(weight for _, _, weight in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    async def _cosine_similarity(
        self,
        vector_a: Dict[str, Any],
        vector_b: Dict[str, Any]
    ) -> float:
        """
        Calculate cosine similarity between two JSONB vectors.
        
        Args:
            vector_a: First vector (JSONB dict)
            vector_b: Second vector (JSONB dict)
        
        Returns:
            Similarity score 0.0 to 1.0
        """
        # TODO: Implement proper vector similarity using pgvector extension
        # For now, return placeholder score
        # In production: Use pgvector's <=> operator for embeddings
        return 0.75  # Placeholder
    
    def _quality_match_score(
        self,
        desired_params: Dict[str, Any],
        tolerances: Dict[str, float],
        actual_params: Dict[str, Any]
    ) -> float:
        """
        Calculate quality parameter match score.
        
        Args:
            desired_params: Desired quality parameters
            tolerances: Tolerance for each parameter
            actual_params: Availability's actual quality parameters
        
        Returns:
            Score 0.0 (no match) to 1.0 (perfect match)
        """
        if not desired_params or not actual_params:
            return 0.5
        
        match_scores = []
        
        for param_name, desired_value in desired_params.items():
            if param_name not in actual_params:
                continue
            
            actual_value = actual_params[param_name]
            tolerance = tolerances.get(param_name, 0.0)
            
            if tolerance == 0:
                # Exact match required
                match_scores.append(1.0 if actual_value == desired_value else 0.0)
            else:
                # Tolerance-based scoring
                diff = abs(float(actual_value) - float(desired_value))
                if diff <= tolerance:
                    # Linear scoring: closer = higher score
                    score = 1.0 - (diff / tolerance)
                    match_scores.append(score)
                else:
                    match_scores.append(0.0)
        
        return sum(match_scores) / len(match_scores) if match_scores else 0.5
    
    def _price_competitiveness_score(
        self,
        actual_price: Decimal,
        target_price: Decimal,
        tolerance_pct: float
    ) -> float:
        """
        Calculate price competitiveness score.
        
        Lower price = higher score (more competitive)
        
        Args:
            actual_price: Availability's price
            target_price: Buyer's target/max price
            tolerance_pct: Price tolerance percentage
        
        Returns:
            Score 0.0 (too expensive) to 1.0 (best price)
        """
        if actual_price <= target_price:
            # Within budget: score based on how much cheaper
            price_diff_pct = ((target_price - actual_price) / target_price) * 100
            # Max score at 10% cheaper, linear decay
            return min(1.0, 0.5 + (price_diff_pct / 20.0))
        else:
            # Over budget: score based on tolerance
            price_diff_pct = ((actual_price - target_price) / target_price) * 100
            if price_diff_pct <= tolerance_pct:
                # Within tolerance: linear penalty
                return 0.5 * (1.0 - (price_diff_pct / tolerance_pct))
            else:
                # Outside tolerance: very low score
                return 0.1
    
    async def _calculate_distance(
        self,
        availability: Availability,
        buyer_latitude: float,
        buyer_longitude: float
    ) -> Optional[float]:
        """
        Calculate distance in kilometers using Haversine formula.
        
        Args:
            availability: Availability with delivery coordinates
            buyer_latitude: Buyer latitude
            buyer_longitude: Buyer longitude
        
        Returns:
            Distance in km, or None if coordinates missing
        """
        if not availability.delivery_latitude or not availability.delivery_longitude:
            return None
        
        # Use PostgreSQL earth_distance function
        query = select(
            text("""
                earth_distance(
                    ll_to_earth(:lat1, :lng1),
                    ll_to_earth(:lat2, :lng2)
                ) / 1000.0
            """)
        ).params(
            lat1=buyer_latitude,
            lng1=buyer_longitude,
            lat2=float(availability.delivery_latitude),
            lng2=float(availability.delivery_longitude)
        )
        
        result = await self.db.execute(query)
        distance_km = result.scalar()
        
        return float(distance_km) if distance_km else None
    
    # ========================
    # Bulk Operations
    # ========================
    
    async def get_active_count_by_commodity(
        self,
        commodity_id: UUID
    ) -> int:
        """
        Get count of active availabilities for a commodity.
        
        Args:
            commodity_id: Commodity UUID
        
        Returns:
            Count of active availabilities
        """
        query = select(func.count(Availability.id)).where(
            and_(
                Availability.commodity_id == commodity_id,
                Availability.status == AvailabilityStatus.ACTIVE.value,
                Availability.is_deleted == False  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def mark_expired(self) -> int:
        """
        Mark expired availabilities (batch job).
        
        Returns:
            Number of availabilities marked as expired
        """
        # Find active availabilities past expiry_date
        query = select(Availability).where(
            and_(
                Availability.status == AvailabilityStatus.ACTIVE.value,
                Availability.expiry_date.isnot(None),
                Availability.expiry_date < datetime.now(timezone.utc),
                Availability.is_deleted == False  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        availabilities = list(result.scalars().all())
        
        for availability in availabilities:
            availability.status = AvailabilityStatus.EXPIRED.value
            # Note: Event emission happens in service layer
        
        await self.db.flush()
        
        return len(availabilities)
    
    # ========================================================================
    # LOCATION-AWARE QUERIES (FOR MATCHING ENGINE)
    # ========================================================================
    
    async def search_by_location(
        self,
        location_id: UUID,
        commodity_id: Optional[UUID] = None,
        status: str = "ACTIVE",
        skip: int = 0,
        limit: int = 100
    ) -> List[Availability]:
        """
        Find availabilities at a specific location.
        
        Used by matching engine to find sellers for a buyer's requirement.
        Direct location_id filter.
        
        Args:
            location_id: Location UUID
            commodity_id: Optional commodity filter
            status: Availability status (default ACTIVE)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of availabilities at this location
        """
        query = select(Availability).where(
            and_(
                Availability.location_id == location_id,
                Availability.status == status,
                Availability.is_deleted == False  # noqa: E712
            )
        )
        
        if commodity_id:
            query = query.where(Availability.commodity_id == commodity_id)
        
        query = query.order_by(desc(Availability.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
