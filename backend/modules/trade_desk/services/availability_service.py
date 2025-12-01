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

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.outbox import OutboxRepository

from backend.modules.trade_desk.enums import (
    ApprovalStatus,
    AvailabilityStatus,
    MarketVisibility,
    PriceType,
)
from backend.modules.trade_desk.models import Availability
from backend.modules.trade_desk.repositories import AvailabilityRepository
from backend.modules.settings.commodities.unit_converter import UnitConverter
from backend.modules.settings.commodities.models import Commodity, CommodityParameter
from backend.modules.settings.locations.models import Location
from backend.modules.partners.validators.insider_trading import InsiderTradingValidator
from backend.modules.partners.cdps.capability_detection import CapabilityDetectionService


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
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        """
        Initialize service.
        
        Args:
            db: Async SQLAlchemy session
            redis_client: Redis client for idempotency
        """
        self.db = db
        self.redis = redis_client
        self.repo = AvailabilityRepository(db)
        self.outbox_repo = OutboxRepository(db)
    
    # ========================
    # Create & Update Operations
    # ========================
    
    async def create_availability(
        self,
        seller_id: UUID,
        commodity_id: UUID,
        location_id: Optional[UUID] = None,  # 🔥 OPTIONAL: registered OR ad-hoc
        total_quantity: Decimal = None,
        quantity_unit: Optional[str] = None,  # 🔥 AUTO-POPULATED from commodity.trade_unit
        base_price: Optional[Decimal] = None,
        price_unit: Optional[str] = None,  # 🔥 AUTO-POPULATED from commodity.rate_unit
        price_matrix: Optional[Dict[str, Any]] = None,
        quality_params: Optional[Dict[str, Any]] = None,
        test_report_url: Optional[str] = None,  # 🔥 NEW: Test report PDF/Image
        media_urls: Optional[Dict[str, List[str]]] = None,  # 🔥 NEW: Photos/videos
        market_visibility: str = MarketVisibility.PUBLIC.value,
        allow_partial_order: bool = True,
        min_order_quantity: Optional[Decimal] = None,
        delivery_terms: Optional[str] = None,
        delivery_address: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: UUID = None,
        auto_approve: bool = False,
        # 🔥 AD-HOC LOCATION (Google Maps coordinates)
        location_address: Optional[str] = None,
        location_latitude: Optional[Decimal] = None,
        location_longitude: Optional[Decimal] = None,
        location_pincode: Optional[str] = None,
        location_region: Optional[str] = None,
        **kwargs
    ) -> Availability:
        """
        Create new availability with AI enhancements + Unit Conversion + Quality Validation.
        
        Workflow:
        0. Auto-populate quantity_unit and price_unit from commodity master
        1. Validate seller location (ALL sellers can sell from ANY location)
        2. Validate commodity parameters (min/max/mandatory checking)
        3. Auto-convert quantity_unit → commodity base_unit (CANDY → 355.6222 KG)
        4. Auto-convert price_unit → price per base_unit
        5. Extract parameters from test_report_url if provided (AI OCR)
        6. Validate quality_params against CommodityParameter constraints
        7. Auto-normalize quality parameters (AI standardization)
        8. Detect price anomalies (statistical + AI)
        9. Calculate AI score vector (embeddings)
        10. Auto-fetch delivery coordinates from location
        11. Create availability
        12. Emit availability.created event
        13. Flush events to event store
        
        Args:
            seller_id: Business partner UUID (SELLER or TRADER)
            commodity_id: Commodity UUID
            location_id: Location UUID (OPTIONAL - use this OR ad-hoc location)
            location_address: Ad-hoc location address (if location_id not provided)
            location_latitude: Ad-hoc latitude from Google Maps
            location_longitude: Ad-hoc longitude from Google Maps
            location_pincode: Ad-hoc pincode (optional)
            location_region: Ad-hoc region/state (optional)
            total_quantity: Total quantity available (in trade_unit from commodity)
            quantity_unit: AUTO-POPULATED from commodity.trade_unit (DO NOT SEND)
            base_price: Base price (for FIXED/NEGOTIABLE)
            price_unit: AUTO-POPULATED from commodity.rate_unit (DO NOT SEND)
            price_matrix: Price matrix JSONB (for MATRIX type)
            quality_params: Quality parameters JSONB (manually entered)
            test_report_url: URL to test report PDF/Image (AI will extract parameters)
            media_urls: Photo/video URLs (AI will detect quality): {"photos": [...], "videos": [...]}
            market_visibility: PUBLIC, PRIVATE, RESTRICTED, INTERNAL
            allow_partial_order: Allow partial fills
            min_order_quantity: Minimum order quantity
            delivery_terms: Delivery terms (Ex-gin, Delivered, FOB)
            expiry_date: Expiry date/time
            created_by: User UUID who created it
            auto_approve: If True, auto-approve (skip approval workflow)
            **kwargs: Additional fields
        
        Returns:
            Created availability with AI enhancements + unit conversion
        
        Raises:
            ValueError: If validation fails (location, parameters, mandatory fields)
        """
        # 0. AUTO-POPULATE UNITS FROM COMMODITY MASTER
        from sqlalchemy import select
        commodity_result = await self.db.execute(
            select(Commodity).where(Commodity.id == commodity_id)
        )
        commodity = commodity_result.scalar_one_or_none()
        if not commodity:
            raise ValueError(f"Commodity {commodity_id} not found")
        
        # Auto-populate quantity_unit from commodity.trade_unit (fallback to base_unit)
        if not quantity_unit:
            quantity_unit = commodity.trade_unit or commodity.base_unit
            if not quantity_unit:
                raise ValueError(
                    f"Commodity {commodity.name} has no trade_unit or base_unit configured. "
                    "Please update commodity master data."
                )
        
        # Auto-populate price_unit from commodity.rate_unit (fallback to trade_unit)
        if base_price and not price_unit:
            price_unit = commodity.rate_unit or commodity.trade_unit or commodity.base_unit
            if not price_unit:
                raise ValueError(
                    f"Commodity {commodity.name} has no rate_unit configured. "
                    "Please update commodity master data."
                )
        
        # 1. Validate and resolve location (registered OR ad-hoc)
        actual_location_id = None
        delivery_latitude = None
        delivery_longitude = None
        delivery_region = None
        
        if location_id:
            # SCENARIO 1: Using registered location from settings table
            await self._validate_seller_location(seller_id, location_id)
            actual_location_id = location_id
            
            # Fetch coordinates from registered location
            delivery_coords = await self._get_delivery_coordinates(location_id)
            delivery_latitude = delivery_coords.get("latitude")
            delivery_longitude = delivery_coords.get("longitude")
            delivery_region = delivery_coords.get("region")
        else:
            # SCENARIO 2: Using ad-hoc location (Google Maps coordinates)
            if not all([location_address, location_latitude is not None, location_longitude is not None]):
                raise ValueError(
                    "Ad-hoc location requires: location_address, location_latitude, location_longitude"
                )
            
            # Use ad-hoc coordinates directly (no location_id stored)
            actual_location_id = None  # NULL in database
            delivery_latitude = location_latitude
            delivery_longitude = location_longitude
            delivery_region = location_region  # May be None
            
            # Update delivery_address if not provided
            if not delivery_address:
                delivery_address = location_address
        
        # ====================================================================
        # 1A: 🚀 CAPABILITY VALIDATION (CDPS - Capability-Driven Partner System)
        # Validate partner has SELL capability based on verified documents
        # Uses partner.capabilities JSONB (NOT deprecated partner_type)
        # ====================================================================
        from backend.modules.trade_desk.validators.capability_validator import TradeCapabilityValidator
        
        # Get location country for capability check
        if actual_location_id:
            location_country = await self._get_location_country(actual_location_id)
        else:
            # Ad-hoc location: derive country from region or default to India
            location_country = location_region if location_region else "India"
        
        capability_validator = TradeCapabilityValidator(self.db)
        await capability_validator.validate_sell_capability(
            partner_id=seller_id,
            location_country=location_country,
            raise_exception=True  # Will raise CapabilityValidationError if invalid
        )
        # Capability validation checks:
        # ✅ Service providers blocked (entity_class="service_provider")
        # ✅ Indian entities need domestic_sell_india=True (from GST+PAN)
        # ✅ Foreign entities need domestic_sell_home_country=True (from tax docs)
        # ✅ Foreign entities CANNOT sell in India (must establish Indian entity)
        # ✅ Export requires export_allowed=True (from IEC+GST+PAN or foreign license)
        
        # ====================================================================
        # 1B: 🚀 CIRCULAR TRADING PREVENTION
        # Block if seller has open BUY for same commodity today
        # ====================================================================
        from backend.modules.risk.risk_engine import RiskEngine
        risk_engine = RiskEngine(self.db)
        
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
        
        # ====================================================================
        # 2A: 🚀 UNIT CONVERSION (Integrate with Commodity Master)
        # Convert seller's trade_unit → commodity's base_unit
        # Example: CANDY (355.6222) → KG, BALE (170 KG) → KG
        # ====================================================================
        # Commodity already fetched in step 0 for auto-unit population
        
        # Convert quantity to base_unit
        quantity_in_base_unit = None
        if commodity.base_unit and quantity_unit:
            quantity_in_base_unit = UnitConverter.convert(
                value=float(total_quantity),
                from_unit=quantity_unit,
                to_unit=commodity.base_unit
            )
            quantity_in_base_unit = Decimal(str(quantity_in_base_unit))
        
        # Convert price to price_per_base_unit
        price_per_base_unit = None
        if base_price and price_unit and commodity.base_unit:
            # Price is per price_unit, need to convert to per base_unit
            # Example: ₹8000 per CANDY → ₹8000 / 355.6222 = ₹22.50 per KG
            conversion_factor = UnitConverter.get_conversion_factor(
                from_unit=price_unit.replace("per ", ""),
                to_unit=commodity.base_unit
            )
            price_per_base_unit = base_price / Decimal(str(conversion_factor))
        
        # ====================================================================
        # 2B: 🚀 QUALITY PARAMETER VALIDATION (Against CommodityParameter)
        # Validate min_value, max_value, is_mandatory constraints
        # ====================================================================
        test_report_data = None
        ai_detected_params = None
        manual_override_params = False
        
        # Extract parameters from test_report if provided
        if test_report_url:
            # TODO: Implement AI OCR extraction from test report PDF/Image
            # This will be implemented in Phase 2 with AI integration
            test_report_data = {"source": "manual", "note": "AI OCR not yet implemented"}
        
        # Detect quality from media if provided
        if media_urls and (media_urls.get("photos") or media_urls.get("videos")):
            # TODO: Implement AI computer vision quality detection
            # This will be implemented in Phase 2 with AI integration
            ai_detected_params = {"source": "manual", "note": "AI CV not yet implemented"}
        
        # Validate quality_params against CommodityParameter constraints
        if quality_params:
            await self._validate_quality_params(commodity_id, quality_params)
            
            # Check if user manually overrode AI-detected parameters
            if ai_detected_params:
                manual_override_params = True
        else:
            # If no quality_params provided, check if commodity has mandatory parameters
            mandatory_params = await self._get_mandatory_parameters(commodity_id)
            if mandatory_params:
                raise ValueError(
                    f"Quality parameters are mandatory for this commodity. "
                    f"Required parameters: {', '.join(mandatory_params)}"
                )
        
        # 2C. Auto-normalize quality parameters (AI standardization)
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
        
        # 5. Delivery coordinates already fetched in step 1 (registered or ad-hoc)
        # delivery_latitude, delivery_longitude, delivery_region are ready
        
        # 6. Determine price type
        price_type = PriceType.MATRIX.value if price_matrix else PriceType.FIXED.value
        
        # 7. Determine approval status
        approval_status = (
            ApprovalStatus.AUTO_APPROVED.value if auto_approve
            else ApprovalStatus.PENDING.value
        )
        
        # 8. Create availability model
        availability = Availability(
            seller_partner_id=seller_id,
            commodity_id=commodity_id,
            location_id=actual_location_id,  # NULL for ad-hoc locations
            total_quantity=total_quantity,
            quantity_unit=quantity_unit,
            quantity_in_base_unit=quantity_in_base_unit,
            available_quantity=total_quantity,  # Initially all available
            reserved_quantity=Decimal(0),
            sold_quantity=Decimal(0),
            min_order_quantity=min_order_quantity,
            allow_partial_order=allow_partial_order,
            price_type=price_type,
            base_price=base_price,
            price_unit=price_unit,
            price_per_base_unit=price_per_base_unit,
            price_matrix=price_matrix,
            quality_params=quality_params,
            test_report_url=test_report_url,
            test_report_verified=False,
            test_report_data=test_report_data,
            media_urls=media_urls,
            ai_detected_params=ai_detected_params,
            manual_override_params=manual_override_params,
            ai_score_vector=ai_score_vector,
            ai_suggested_price=ai_suggested_price,
            ai_confidence_score=ai_confidence_score,
            ai_price_anomaly_flag=price_anomaly_flag,
            market_visibility=market_visibility,
            delivery_terms=delivery_terms,
            delivery_address=delivery_address,  # 🔥 Ad-hoc or registered
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            delivery_region=delivery_region,
            expiry_date=expiry_date,
            notes=notes,
            tags=tags,
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
        approval_notes: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Optional[Availability]:
        """
        Approve availability (change status to ACTIVE).
        
        Args:
            availability_id: Availability UUID
            approved_by: User UUID who approved it
            approval_notes: Optional approval notes
            idempotency_key: Idempotency key for deduplication
        
        Returns:
            Approved availability or None if not found
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        
        availability = await self.repo.get_by_id(availability_id)
        if not availability:
            return None
        
        availability.approval_status = ApprovalStatus.APPROVED.value
        availability.status = AvailabilityStatus.ACTIVE.value
        availability.approved_by = approved_by
        availability.approved_at = datetime.now(timezone.utc)
        availability.approval_notes = approval_notes
        
        availability = await self.repo.update(availability)
        
        # Emit event through outbox (transactional)
        await self.outbox_repo.add_event(
            aggregate_id=availability.id,
            aggregate_type="Availability",
            event_type="AvailabilityApproved",
            payload={
                "availability_id": str(availability.id),
                "seller_id": str(availability.seller_id),
                "commodity_id": str(availability.commodity_id),
                "quantity": float(availability.total_quantity),
                "approved_by": str(approved_by),
                "approved_at": availability.approved_at.isoformat()
            },
            topic_name="availability-events",
            metadata={"user_id": str(approved_by)},
            idempotency_key=idempotency_key
        )
        
        # Commit transaction
        await self.db.commit()
        
        # Cache result for idempotency
        if idempotency_key and self.redis:
            result_dict = {
                "id": str(availability.id),
                "status": availability.status,
                "approval_status": availability.approval_status
            }
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,
                json.dumps(result_dict)
            )
        
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
        
        INSIDER TRADING VALIDATION:
        - Validates buyer != seller (same entity check)
        - Validates master-branch relationships
        - Validates corporate group membership
        - Validates same GST number
        
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
            InsiderTradingError: If buyer and seller are corporate insiders
        """
        availability = await self.repo.get_by_id(availability_id, load_relationships=True)
        if not availability:
            raise ValueError("Availability not found")
        
        # ====================================================================
        # 🚀 INSIDER TRADING VALIDATION
        # Prevent buyer from reserving if they are corporate insiders with seller
        # ====================================================================
        insider_validator = InsiderTradingValidator(self.db)
        
        try:
            is_valid, error_msg = await insider_validator.validate_trade_parties(
                buyer_id=buyer_id,
                seller_id=availability.seller_partner_id,
                raise_exception=True  # Will raise InsiderTradingError
            )
        except Exception as e:
            # Emit rejection event
            availability.emit_event(
                event_type="reservation.rejected.insider_trading",
                event_data={
                    "availability_id": str(availability_id),
                    "buyer_id": str(buyer_id),
                    "seller_id": str(availability.seller_partner_id),
                    "reason": str(e),
                    "rejected_by": "insider_trading_validator",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await availability.flush_events(self.db)
            raise  # Re-raise the exception
        
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
        
        UPDATED RULE (Nov 2024):
        - ALL SELLERS: Can sell from ANY location (no restriction)
        - Reason: Traders may source from multiple locations, sellers may have temporary stock
        - Validation: Only check if location exists in settings_locations table
        
        Args:
            seller_id: Business partner UUID
            location_id: Location UUID
        
        Raises:
            ValueError: If location does not exist
        """
        from sqlalchemy import select
        
        # Check if location exists in settings_locations table
        location_result = await self.db.execute(
            select(Location).where(Location.id == location_id)
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            raise ValueError(
                f"Location {location_id} does not exist in settings_locations table. "
                "Please create the location first or use ad-hoc location with coordinates."
            )
        
        # Validation passed - all sellers can sell from any registered location
        return None
    
    async def _get_delivery_coordinates(
        self,
        location_id: UUID
    ) -> Dict[str, Any]:
        """
        Get delivery coordinates from location master.
        
        Args:
            location_id: Location UUID
        
        Returns:
            {
                "latitude": Decimal or None,
                "longitude": Decimal or None,
                "region": str or None
            }
        """
        from sqlalchemy import select
        from decimal import Decimal as D
        
        # Query location from settings_locations table
        location_result = await self.db.execute(
            select(Location).where(Location.id == location_id)
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            # Return empty dict if location not found
            return {}
        
        # Extract coordinates with proper type conversion
        latitude = D(str(location.latitude)) if location.latitude is not None else None
        longitude = D(str(location.longitude)) if location.longitude is not None else None
        region = getattr(location, 'region', None) or getattr(location, 'state', None)
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "region": region
        }
    
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
        """
        from sqlalchemy import select
        
        # Query location from settings_locations table
        location_result = await self.db.execute(
            select(Location).where(Location.id == location_id)
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            # Default to India if location not found (most common case)
            return "India"
        
        # Try to get country from location model
        # Location model may have: country, country_code, or derive from region
        country = getattr(location, "country", None)
        
        if not country:
            # Fallback: derive from country_code or default to India
            country_code = getattr(location, "country_code", None)
            if country_code == "IN" or country_code == "IND":
                country = "India"
            elif country_code == "US" or country_code == "USA":
                country = "United States"
            else:
                country = "India"  # Default fallback
        
        return country
    
    async def _validate_quality_params(
        self,
        commodity_id: UUID,
        quality_params: Dict[str, Any]
    ) -> None:
        """
        Validate quality parameters against CommodityParameter constraints.
        
        Checks:
        - min_value <= value <= max_value
        - All mandatory parameters are provided
        
        Args:
            commodity_id: Commodity UUID
            quality_params: Quality parameters to validate
        
        Raises:
            ValueError: If validation fails
        """
        from sqlalchemy import select
        
        # Fetch commodity parameters
        params_result = await self.db.execute(
            select(CommodityParameter).where(
                CommodityParameter.commodity_id == commodity_id
            )
        )
        commodity_params = params_result.scalars().all()
        
        if not commodity_params:
            # No parameters defined for commodity, nothing to validate
            return
        
        # Build validation map
        param_map = {param.parameter_name: param for param in commodity_params}
        
        # Check mandatory parameters
        for param in commodity_params:
            if param.is_mandatory and param.parameter_name not in quality_params:
                raise ValueError(
                    f"Mandatory parameter '{param.parameter_name}' is missing. "
                    f"Expected value between {param.min_value} and {param.max_value}"
                )
        
        # Validate min/max constraints
        for param_name, param_value in quality_params.items():
            if param_name not in param_map:
                # Parameter not defined for commodity, skip validation
                continue
            
            param_config = param_map[param_name]
            
            try:
                value = float(param_value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Parameter '{param_name}' must be a numeric value. "
                    f"Got: {param_value}"
                )
            
            if param_config.min_value is not None and value < float(param_config.min_value):
                raise ValueError(
                    f"Parameter '{param_name}' value {value} is below minimum {param_config.min_value}"
                )
            
            if param_config.max_value is not None and value > float(param_config.max_value):
                raise ValueError(
                    f"Parameter '{param_name}' value {value} exceeds maximum {param_config.max_value}"
                )
    
    async def _get_mandatory_parameters(
        self,
        commodity_id: UUID
    ) -> List[str]:
        """
        Get list of mandatory parameter names for commodity.
        
        Args:
            commodity_id: Commodity UUID
        
        Returns:
            List of mandatory parameter names
        """
        from sqlalchemy import select
        
        # Fetch mandatory parameters
        params_result = await self.db.execute(
            select(CommodityParameter.parameter_name).where(
                CommodityParameter.commodity_id == commodity_id,
                CommodityParameter.is_mandatory == True
            )
        )
        
        return [row[0] for row in params_result.all()]
    
    # ========================
    # Search & Query Operations
    # ========================
    
    async def search_availabilities(
        self,
        buyer_id: Optional[UUID] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        Search availabilities using AI-powered smart_search with INSIDER TRADING PRE-FILTER.
        
        PRE-FILTER LOGIC:
        - If buyer_id provided, excludes availabilities where seller is corporate insider
        - Prevents insider trading at search level (proactive blocking)
        - Uses InsiderTradingValidator to get all blocked seller_ids
        
        Wrapper around repository.smart_search() with service-level logic.
        
        Args:
            buyer_id: Buyer UUID (for visibility access control + insider trading filter)
            **search_params: Search parameters (commodity_id, quality_params, etc.)
        
        Returns:
            List of enriched availability results with match scores (insider traders excluded)
        """
        # Add default visibility for buyer
        if "market_visibility" not in search_params:
            search_params["market_visibility"] = [
                MarketVisibility.PUBLIC.value,
                MarketVisibility.RESTRICTED.value
            ]
        
        if buyer_id:
            search_params["buyer_id"] = buyer_id
            
            # ====================================================================
            # 🚀 INSIDER TRADING PRE-FILTER
            # Get all seller_ids that are corporate insiders with buyer
            # Exclude them from search results
            # ====================================================================
            insider_validator = InsiderTradingValidator(self.db)
            
            insider_relationships = await insider_validator.get_all_insider_relationships(
                partner_id=buyer_id
            )
            
            # Collect all blocked seller_ids
            blocked_seller_ids = set()
            blocked_seller_ids.update(insider_relationships.get("same_entity", []))
            blocked_seller_ids.update(insider_relationships.get("master_branch", []))
            blocked_seller_ids.update(insider_relationships.get("corporate_group", []))
            blocked_seller_ids.update(insider_relationships.get("same_gst", []))
            
            # Add to search params (repository will exclude these)
            if blocked_seller_ids:
                search_params["excluded_seller_ids"] = list(blocked_seller_ids)
        
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
