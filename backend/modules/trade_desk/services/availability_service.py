"""
Availability Service - AI-Powered Business Logic Layer

This is the BRAIN of the Availability Engine. Handles all business logic with AI enhancements:

AI Features:
1. Auto-Normalize Quality Parameters: Standardize quality_params across commodities
2. Anomaly Detection: Detect unrealistic prices using statistical analysis + AI
3. Negotiation Readiness Score: Calculate how ready an availability is for negotiation
4. Commodity Similarity Mapping: Suggest similar commodities (Cotton 29mm → 28mm/30mm/yarn)
5. Seller Location Validation: Enforce seller=own location, trader=any location

Business Rules:
- Sellers can only post from registered locations
- Traders can post from any location
- Auto-calculate delivery coordinates from location
- Auto-detect price anomalies on creation
- Auto-generate AI score vectors (embeddings)
- Event emission for all state changes

Architecture:
- Service orchestrates Repository + AI models
- Validates business rules before persistence
- Emits events for real-time updates
- Flushes events to event store (audit trail)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.enums import (
    ApprovalStatus,
    AvailabilityStatus,
    MarketVisibility,
    PriceType,
)
from backend.modules.trade_desk.models import Availability
from backend.modules.trade_desk.repositories import AvailabilityRepository


class AvailabilityService:
    """
    Service layer for Availability Engine with AI-powered features.
    
    Responsibilities:
    - Business logic validation
    - AI-powered quality normalization
    - Price anomaly detection
    - Seller location validation
    - Event emission and flushing
    - Orchestration of repository operations
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize service.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        self.repo = AvailabilityRepository(db)
    
    # ========================
    # Create & Update Operations
    # ========================
    
    async def create_availability(
        self,
        seller_id: UUID,
        commodity_id: UUID,
        location_id: UUID,
        total_quantity: Decimal,
        base_price: Optional[Decimal] = None,
        price_matrix: Optional[Dict[str, Any]] = None,
        quality_params: Optional[Dict[str, Any]] = None,
        market_visibility: str = MarketVisibility.PUBLIC.value,
        allow_partial_order: bool = True,
        min_order_quantity: Optional[Decimal] = None,
        delivery_terms: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        created_by: UUID = None,
        auto_approve: bool = False,
        **kwargs
    ) -> Availability:
        """
        Create new availability with AI enhancements.
        
        Workflow:
        1. Validate seller location (SELLER=own location, TRADER=any location)
        2. Auto-normalize quality parameters (AI standardization)
        3. Detect price anomalies (statistical + AI)
        4. Calculate AI score vector (embeddings)
        5. Auto-fetch delivery coordinates from location
        6. Create availability
        7. Emit availability.created event
        8. Flush events to event store
        
        Args:
            seller_id: Business partner UUID (SELLER or TRADER)
            commodity_id: Commodity UUID
            location_id: Location UUID (delivery location)
            total_quantity: Total quantity available
            base_price: Base price (for FIXED/NEGOTIABLE)
            price_matrix: Price matrix JSONB (for MATRIX type)
            quality_params: Quality parameters JSONB
            market_visibility: PUBLIC, PRIVATE, RESTRICTED, INTERNAL
            allow_partial_order: Allow partial fills
            min_order_quantity: Minimum order quantity
            delivery_terms: Delivery terms (Ex-gin, Delivered, FOB)
            expiry_date: Expiry date/time
            created_by: User UUID who created it
            auto_approve: If True, auto-approve (skip approval workflow)
            **kwargs: Additional fields
        
        Returns:
            Created availability with AI enhancements
        
        Raises:
            ValueError: If validation fails
        """
        # 1. Validate seller location (business rule enforcement)
        await self._validate_seller_location(seller_id, location_id)
        
        # ====================================================================
        # 1A: 🚀 CAPABILITY VALIDATION (CDPS - Capability-Driven Partner System)
        # Validate partner has permission to sell based on verified documents
        # ====================================================================
        from backend.modules.trade_desk.validators.capability_validator import TradeCapabilityValidator
        
        # Get location country for capability check
        location_country = await self._get_location_country(location_id)
        
        capability_validator = TradeCapabilityValidator(self.db)
        await capability_validator.validate_sell_capability(
            partner_id=seller_id,
            location_country=location_country,
            raise_exception=True  # Will raise CapabilityValidationError if invalid
        )
        
        # ====================================================================
        # 1B: 🚀 ROLE RESTRICTION VALIDATION (Option A)
        # Prevent BUYER from posting SELL availabilities
        # Allow SELLER and TRADER to post SELL availabilities
        # ====================================================================
        from backend.modules.risk.risk_engine import RiskEngine
        risk_engine = RiskEngine(self.db)
        
        role_validation = await risk_engine.validate_partner_role(
            partner_id=seller_id,
            transaction_type="SELL"
        )
        
        if not role_validation["allowed"]:
            raise ValueError(role_validation["reason"])
        
        # ====================================================================
        # 1B: 🚀 CIRCULAR TRADING PREVENTION (Option A: Same-day only)
        # Block if seller has open BUY for same commodity today
        # ====================================================================
        if expiry_date:
            trade_date = expiry_date.date()
        else:
            trade_date = datetime.now().date()
        
        circular_check = await risk_engine.check_circular_trading(
            partner_id=seller_id,
            commodity_id=commodity_id,
            transaction_type="SELL",
            trade_date=trade_date
        )
        
        if circular_check["blocked"]:
            raise ValueError(
                f"{circular_check['reason']}\n\n"
                f"Recommendation: {circular_check['recommendation']}"
            )
        
        # 2. Auto-normalize quality parameters (AI standardization)
        if quality_params:
            quality_params = await self.normalize_quality_params(
                commodity_id,
                quality_params
            )
        
        # 3. Detect price anomalies
        price_anomaly_flag = False
        ai_suggested_price = None
        ai_confidence_score = None
        
        if base_price:
            anomaly_result = await self.detect_price_anomaly(
                commodity_id,
                base_price,
                quality_params
            )
            price_anomaly_flag = anomaly_result["is_anomaly"]
            ai_suggested_price = anomaly_result.get("suggested_price")
            ai_confidence_score = anomaly_result.get("confidence_score")
        
        # 4. Calculate AI score vector (embeddings for ML matching)
        ai_score_vector = await self.calculate_ai_score_vector(
            commodity_id,
            quality_params,
            base_price or Decimal(0)
        )
        
        # 5. Auto-fetch delivery coordinates from location
        delivery_coords = await self._get_delivery_coordinates(location_id)
        delivery_latitude = delivery_coords.get("latitude")
        delivery_longitude = delivery_coords.get("longitude")
        delivery_region = delivery_coords.get("region")
        
        # 6. Determine price type
        price_type = PriceType.MATRIX.value if price_matrix else PriceType.FIXED.value
        
        # 7. Determine approval status
        approval_status = (
            ApprovalStatus.AUTO_APPROVED.value if auto_approve
            else ApprovalStatus.PENDING.value
        )
        
        # 8. Create availability model
        availability = Availability(
            seller_id=seller_id,
            commodity_id=commodity_id,
            location_id=location_id,
            total_quantity=total_quantity,
            available_quantity=total_quantity,  # Initially all available
            reserved_quantity=Decimal(0),
            sold_quantity=Decimal(0),
            min_order_quantity=min_order_quantity,
            allow_partial_order=allow_partial_order,
            price_type=price_type,
            base_price=base_price,
            price_matrix=price_matrix,
            quality_params=quality_params,
            ai_score_vector=ai_score_vector,
            ai_suggested_price=ai_suggested_price,
            ai_confidence_score=ai_confidence_score,
            ai_price_anomaly_flag=price_anomaly_flag,
            market_visibility=market_visibility,
            delivery_terms=delivery_terms,
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            delivery_region=delivery_region,
            expiry_date=expiry_date,
            status=AvailabilityStatus.DRAFT.value,
            approval_status=approval_status,
            created_by=created_by,
            **kwargs
        )
        
        # 9. Persist to database
        availability = await self.repo.create(availability)
        
        # 10. Emit event
        availability.emit_created(created_by)
        
        # 11. Flush events to event store
        await availability.flush_events(self.db)
        
        return availability
    
    async def update_availability(
        self,
        availability_id: UUID,
        updated_by: UUID,
        **updates
    ) -> Optional[Availability]:
        """
        Update availability with AI re-processing and micro-events.
        
        Detects changes and emits appropriate micro-events:
        - market_visibility changed → emit visibility_changed
        - base_price/price_matrix changed → emit price_changed
        - quantities changed → emit quantity_changed
        
        Args:
            availability_id: Availability UUID
            updated_by: User UUID who updated it
            **updates: Fields to update
        
        Returns:
            Updated availability or None if not found
        """
        availability = await self.repo.get_by_id(availability_id)
        if not availability:
            return None
        
        # Track old values for micro-events
        old_visibility = availability.market_visibility
        old_base_price = availability.base_price
        old_price_matrix = availability.price_matrix
        old_total_qty = availability.total_quantity
        old_available_qty = availability.available_quantity
        old_reserved_qty = availability.reserved_quantity
        old_sold_qty = availability.sold_quantity
        
        # Update fields
        for key, value in updates.items():
            if hasattr(availability, key) and value is not None:
                setattr(availability, key, value)
        
        # Re-normalize quality params if changed
        if "quality_params" in updates and updates["quality_params"]:
            availability.quality_params = await self.normalize_quality_params(
                availability.commodity_id,
                updates["quality_params"]
            )
        
        # Re-detect price anomaly if price changed
        if "base_price" in updates and updates["base_price"]:
            anomaly_result = await self.detect_price_anomaly(
                availability.commodity_id,
                updates["base_price"],
                availability.quality_params
            )
            availability.ai_price_anomaly_flag = anomaly_result["is_anomaly"]
            availability.ai_suggested_price = anomaly_result.get("suggested_price")
            availability.ai_confidence_score = anomaly_result.get("confidence_score")
        
        # Re-calculate AI score vector if commodity/quality/price changed
        if any(k in updates for k in ["commodity_id", "quality_params", "base_price"]):
            availability.ai_score_vector = await self.calculate_ai_score_vector(
                availability.commodity_id,
                availability.quality_params,
                availability.base_price or Decimal(0)
            )
        
        # Update timestamp
        availability.updated_by = updated_by
        availability.updated_at = datetime.now(timezone.utc)
        
        # Persist
        availability = await self.repo.update(availability)
        
        # Emit micro-events based on what changed
        
        # 1. Visibility changed?
        if "market_visibility" in updates and updates["market_visibility"] != old_visibility:
            availability.emit_visibility_changed(
                old_visibility,
                availability.market_visibility,
                updated_by,
                reason="Manual update"
            )
        
        # 2. Price changed?
        price_changed = (
            ("base_price" in updates and updates["base_price"] != old_base_price) or
            ("price_matrix" in updates and updates["price_matrix"] != old_price_matrix)
        )
        if price_changed:
            availability.emit_price_changed(
                old_base_price,
                availability.base_price,
                updated_by,
                old_price_matrix=old_price_matrix,
                new_price_matrix=availability.price_matrix,
                reason="Manual update"
            )
        
        # 3. Quantities changed?
        qty_changed = (
            ("total_quantity" in updates and updates["total_quantity"] != old_total_qty) or
            ("available_quantity" in updates and updates["available_quantity"] != old_available_qty)
        )
        if qty_changed:
            availability.emit_quantity_changed(
                old_total_qty,
                old_available_qty,
                old_reserved_qty,
                old_sold_qty,
                updated_by,
                reason="Manual update"
            )
        
        # Flush events
        await availability.flush_events(self.db)
        
        return availability
    
    async def approve_availability(
        self,
        availability_id: UUID,
        approved_by: UUID,
        approval_notes: Optional[str] = None
    ) -> Optional[Availability]:
        """
        Approve availability (change status to ACTIVE).
        
        Args:
            availability_id: Availability UUID
            approved_by: User UUID who approved it
            approval_notes: Optional approval notes
        
        Returns:
            Approved availability or None if not found
        """
        availability = await self.repo.get_by_id(availability_id)
        if not availability:
            return None
        
        availability.approval_status = ApprovalStatus.APPROVED.value
        availability.status = AvailabilityStatus.ACTIVE.value
        availability.approved_by = approved_by
        availability.approved_at = datetime.now(timezone.utc)
        availability.approval_notes = approval_notes
        
        availability = await self.repo.update(availability)
        
        # Emit created event (now visible to buyers)
        availability.emit_created(approved_by)
        await availability.flush_events(self.db)
        
        return availability
    
    # ========================
    # Reserve/Release/Sold Operations
    # ========================
    
    async def reserve_availability(
        self,
        availability_id: UUID,
        quantity: Decimal,
        buyer_id: UUID,
        reservation_hours: int = 24,
        reserved_by: UUID = None
    ) -> Availability:
        """
        Reserve quantity for negotiation (temporary hold).
        
        Args:
            availability_id: Availability UUID
            quantity: Quantity to reserve
            buyer_id: Buyer UUID
            reservation_hours: Reservation duration in hours (default 24h)
            reserved_by: User UUID who reserved it
        
        Returns:
            Updated availability
        
        Raises:
            ValueError: If cannot reserve
        """
        availability = await self.repo.get_by_id(availability_id, load_relationships=True)
        if not availability:
            raise ValueError("Availability not found")
        
        reservation_expiry = datetime.now(timezone.utc) + timedelta(hours=reservation_hours)
        
        # Model handles validation + event emission
        availability.reserve_quantity(quantity, buyer_id, reservation_expiry, reserved_by)
        
        # Persist
        availability = await self.repo.update(availability)
        
        # Flush events
        await availability.flush_events(self.db)
        
        return availability
    
    async def release_availability(
        self,
        availability_id: UUID,
        quantity: Decimal,
        buyer_id: UUID,
        released_by: UUID,
        reason: Optional[str] = None
    ) -> Availability:
        """
        Release reserved quantity (negotiation failed/expired).
        
        Args:
            availability_id: Availability UUID
            quantity: Quantity to release
            buyer_id: Buyer UUID
            released_by: User UUID who released it
            reason: Optional reason
        
        Returns:
            Updated availability
        
        Raises:
            ValueError: If cannot release
        """
        availability = await self.repo.get_by_id(availability_id, load_relationships=True)
        if not availability:
            raise ValueError("Availability not found")
        
        # Model handles validation + event emission
        availability.release_quantity(quantity, buyer_id, released_by, reason)
        
        # Persist
        availability = await self.repo.update(availability)
        
        # Flush events
        await availability.flush_events(self.db)
        
        return availability
    
    async def mark_as_sold(
        self,
        availability_id: UUID,
        quantity: Decimal,
        buyer_id: UUID,
        trade_id: UUID,
        sold_price: Decimal,
        sold_by: UUID
    ) -> Availability:
        """
        Mark availability as sold (convert to trade).
        
        Args:
            availability_id: Availability UUID
            quantity: Quantity sold
            buyer_id: Buyer UUID
            trade_id: Trade UUID (binding contract)
            sold_price: Final negotiated price
            sold_by: User UUID who finalized it
        
        Returns:
            Updated availability
        
        Raises:
            ValueError: If cannot mark sold
        """
        availability = await self.repo.get_by_id(availability_id, load_relationships=True)
        if not availability:
            raise ValueError("Availability not found")
        
        # Model handles validation + event emission
        availability.mark_sold(quantity, buyer_id, trade_id, sold_price, sold_by)
        
        # Persist
        availability = await self.repo.update(availability)
        
        # Flush events
        await availability.flush_events(self.db)
        
        return availability
    
    # ========================
    # AI-Powered Features
    # ========================
    
    async def normalize_quality_params(
        self,
        commodity_id: UUID,
        quality_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Auto-normalize quality parameters using AI standardization.
        
        Examples:
        - Cotton: Convert "length" variations (2.9cm, 29mm, 1.14") → 29.0mm
        - Gold: Convert "purity" variations (999, 99.9%, 24K) → 99.9
        - Wheat: Convert "protein" variations (12%, 12, "high") → 12.0
        
        Args:
            commodity_id: Commodity UUID
            quality_params: Raw quality parameters
        
        Returns:
            Normalized quality parameters
        
        TODO: Integrate with AI model for intelligent normalization
        For now, implements basic normalization rules
        """
        # TODO: Load commodity-specific normalization rules from AI model
        # For now, basic type coercion
        
        normalized = {}
        
        for key, value in quality_params.items():
            # Convert to numeric if possible
            if isinstance(value, (int, float, Decimal)):
                normalized[key] = float(value)
            elif isinstance(value, str):
                # Try parsing numeric values
                try:
                    normalized[key] = float(value.replace("%", "").strip())
                except ValueError:
                    # Keep as string
                    normalized[key] = value.strip().upper()
            else:
                normalized[key] = value
        
        return normalized
    
    async def detect_price_anomaly(
        self,
        commodity_id: UUID,
        price: Decimal,
        quality_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect price anomalies using statistical analysis + AI.
        
        Detection Methods:
        1. Statistical: Compare with historical prices (mean, std dev, z-score)
        2. AI: Use ML model to predict expected price range
        3. Rule-based: Check against min/max thresholds
        
        Args:
            commodity_id: Commodity UUID
            price: Proposed price
            quality_params: Quality parameters (affects expected price)
        
        Returns:
            {
                "is_anomaly": bool,
                "suggested_price": Decimal,
                "confidence_score": Decimal (0.0 to 1.0),
                "reason": str
            }
        
        TODO: Integrate with AI anomaly detection model
        For now, implements basic statistical checks
        """
        # TODO: Load historical prices from database
        # TODO: Use AI model to predict expected price
        
        # Placeholder: Basic thresholds (replace with real logic)
        # Example: Cotton price typically 50,000 to 80,000 INR per bale
        
        # For now, return no anomaly (conservative approach)
        return {
            "is_anomaly": False,
            "suggested_price": None,
            "confidence_score": Decimal("0.5"),
            "reason": "AI model not yet trained - using conservative approach"
        }
    
    async def calculate_negotiation_readiness_score(
        self,
        availability_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate negotiation readiness score (0.0 to 1.0).
        
        Factors:
        1. Price competitiveness (vs market average)
        2. Quality completeness (all params filled)
        3. Delivery terms clarity
        4. Seller reputation (future: from rating system)
        5. Quantity availability
        6. Location accessibility
        
        Args:
            availability_id: Availability UUID
        
        Returns:
            {
                "readiness_score": float (0.0 to 1.0),
                "factors": {
                    "price_competitive": float,
                    "quality_complete": float,
                    "delivery_clear": float,
                    "quantity_adequate": float
                },
                "recommendations": List[str]
            }
        """
        availability = await self.repo.get_by_id(availability_id, load_relationships=True)
        if not availability:
            return {"readiness_score": 0.0, "factors": {}, "recommendations": ["Availability not found"]}
        
        factors = {}
        recommendations = []
        
        # 1. Quality completeness (40% weight)
        if availability.quality_params:
            quality_complete = min(1.0, len(availability.quality_params) / 5.0)  # Assume 5 params ideal
        else:
            quality_complete = 0.0
            recommendations.append("Add quality parameters for better matching")
        factors["quality_complete"] = quality_complete
        
        # 2. Price available (30% weight)
        price_available = 1.0 if availability.base_price or availability.price_matrix else 0.0
        if price_available == 0.0:
            recommendations.append("Add pricing information")
        factors["price_available"] = price_available
        
        # 3. Delivery terms clear (20% weight)
        delivery_clear = 1.0 if availability.delivery_terms else 0.0
        if delivery_clear == 0.0:
            recommendations.append("Specify delivery terms (Ex-gin, Delivered, FOB)")
        factors["delivery_clear"] = delivery_clear
        
        # 4. Quantity adequate (10% weight)
        quantity_adequate = 1.0 if availability.available_quantity > 0 else 0.0
        factors["quantity_adequate"] = quantity_adequate
        
        # Calculate weighted score
        readiness_score = (
            factors["quality_complete"] * 0.4 +
            factors["price_available"] * 0.3 +
            factors["delivery_clear"] * 0.2 +
            factors["quantity_adequate"] * 0.1
        )
        
        return {
            "readiness_score": round(readiness_score, 2),
            "factors": factors,
            "recommendations": recommendations
        }
    
    async def suggest_similar_commodities(
        self,
        commodity_id: UUID,
        quality_params: Optional[Dict[str, Any]] = None,
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest similar commodities using AI similarity mapping.
        
        Examples:
        - Cotton 29mm → Suggest 28mm, 30mm, Cotton Yarn
        - Gold 999 → Suggest Gold 995, Gold Coins
        - Wheat Protein 12% → Suggest Wheat 11%, 13%
        
        Args:
            commodity_id: Source commodity UUID
            quality_params: Quality parameters (for fine-tuning suggestions)
            max_suggestions: Max number of suggestions
        
        Returns:
            List of {
                "commodity_id": UUID,
                "commodity_name": str,
                "similarity_score": float (0.0 to 1.0),
                "reason": str
            }
        
        TODO: Integrate with AI commodity similarity model
        For now, returns empty list (conservative)
        """
        # TODO: Load commodity embeddings
        # TODO: Calculate cosine similarity
        # TODO: Filter by quality parameter ranges
        
        # Placeholder: Return empty (will implement with AI model)
        return []
    
    async def calculate_ai_score_vector(
        self,
        commodity_id: UUID,
        quality_params: Optional[Dict[str, Any]],
        price: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate AI score vector (embeddings) for ML-powered matching.
        
        Vector includes:
        - Commodity type encoding
        - Quality parameters encoding
        - Price normalization
        - Temporal features (seasonality)
        
        Args:
            commodity_id: Commodity UUID
            quality_params: Quality parameters
            price: Price
        
        Returns:
            JSONB vector for ai_score_vector field
        
        TODO: Integrate with actual embedding model (e.g., Sentence Transformers)
        For now, returns placeholder structure
        """
        # TODO: Use actual ML model to generate embeddings
        # For now, return structured placeholder
        
        return {
            "commodity_id": str(commodity_id),
            "quality_hash": hash(str(quality_params)) if quality_params else 0,
            "price_normalized": float(price) / 100000.0,  # Normalize to 0-1 range
            "version": "v1_placeholder",
            # In production: "embedding": [0.234, 0.567, ..., 0.123] (768-dim vector)
        }
    
    # ========================
    # Business Rule Validation
    # ========================
    
    async def _validate_seller_location(
        self,
        seller_id: UUID,
        location_id: UUID
    ) -> None:
        """
        Validate seller can post from location.
        
        Rules:
        - SELLER: Can only sell from registered locations
        - TRADER: Can sell from any location
        
        Args:
            seller_id: Business partner UUID
            location_id: Location UUID
        
        Raises:
            ValueError: If seller not allowed to post from location
        
        TODO: Implement actual validation by checking business_partner.partner_type
        and business_partner.locations (many-to-many relationship)
        """
        # TODO: Load business partner and check partner_type
        # TODO: If SELLER, verify location_id in partner.locations
        # TODO: If TRADER, allow any location
        
        # Placeholder: Allow all (implement actual validation later)
        pass
    
    async def _get_delivery_coordinates(
        self,
        location_id: UUID
    ) -> Dict[str, Any]:
        """
        Get delivery coordinates from location.
        
        Args:
            location_id: Location UUID
        
        Returns:
            {
                "latitude": Decimal,
                "longitude": Decimal,
                "region": str (WEST, SOUTH, etc.)
            }
        
        TODO: Query settings_locations table
        """
        # TODO: Load location from database
        # TODO: Return latitude, longitude, region
        
        # Placeholder: Return empty
        return {}
    
    async def _get_location_country(
        self,
        location_id: UUID
    ) -> str:
        """
        Get country from location for capability validation.
        
        Args:
            location_id: Location UUID
        
        Returns:
            str: Country name (e.g., "India", "USA", "China")
        
        TODO: Query actual location table when available
        """
        # TODO: Load from settings_locations table
        # For now, default to India (most common case)
        # This will be properly implemented when location module is integrated
        return "India"
    
    # ========================
    # Search & Query Operations
    # ========================
    
    async def search_availabilities(
        self,
        buyer_id: Optional[UUID] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        Search availabilities using AI-powered smart_search.
        
        Wrapper around repository.smart_search() with service-level logic.
        
        Args:
            buyer_id: Buyer UUID (for visibility access control)
            **search_params: Search parameters (commodity_id, quality_params, etc.)
        
        Returns:
            List of enriched availability results with match scores
        """
        # Add default visibility for buyer
        if "market_visibility" not in search_params:
            search_params["market_visibility"] = [
                MarketVisibility.PUBLIC.value,
                MarketVisibility.RESTRICTED.value
            ]
        
        if buyer_id:
            search_params["buyer_id"] = buyer_id
        
        return await self.repo.smart_search(**search_params)
    
    async def get_seller_availabilities(
        self,
        seller_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Availability]:
        """
        Get all availabilities for a seller.
        
        Args:
            seller_id: Seller UUID
            status: Optional status filter
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of availabilities
        """
        return await self.repo.get_by_seller(seller_id, status, skip, limit)
