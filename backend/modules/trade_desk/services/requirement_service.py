"""
Requirement Service - AI-Powered Business Logic Layer for Buyer Requirements

🚀 2035-READY ENHANCEMENTS - 12-STEP AI PIPELINE:

This is the BRAIN of the Requirement Engine with autonomous AI decision-making.

AI Pipeline (12 Steps):
1. Validate buyer permissions & location constraints
2. Auto-normalize quality requirements (standardization)
3. AI price suggestion based on market data
4. Calculate buyer priority score (trust weighting)
5. Detect unrealistic budget constraints
6. Generate market context embedding (1536-dim vector)
7. 🚀 Market sentiment adjustment (real-time pricing)
8. 🚀 Dynamic tolerance recommendation (quality flexibility)
9. Create requirement with all enhancements
10. Emit requirement.created event
11. Auto-match with availabilities (if intent=DIRECT_BUY)
12. Route to correct engine based on intent_type

Enhanced Features:
1. Intent Layer: Routes to Matching/Negotiation/Auction engines
2. AI Market Context Embedding: Semantic similarity search
3. Dynamic Delivery Flexibility: Logistics optimization
4. Multi-Commodity Conversion: Cross-commodity intelligence
5. Negotiation Preferences: Self-negotiating system
6. Buyer Trust Score: Anti-spam & priority weighting
7. AI Adjustment Events: Explainability & audit trail

Business Rules:
- Buyers can specify delivery to registered locations only
- Traders can specify delivery to any location (no restriction)
- Auto-calculate buyer_priority_score from historical performance
- Auto-generate AI market_context_embedding
- Auto-suggest commodity equivalents
- Event emission for all state changes
- Intent-based routing to trade engines

Architecture:
- Service orchestrates Repository + AI models
- Validates business rules before persistence
- Emits events for real-time updates
- Flushes events to event store (audit trail)
- Routes to downstream engines based on intent
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.enums import (
    IntentType,
    MarketVisibility,
    RequirementStatus,
    UrgencyLevel,
)
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.repositories.requirement_repository import (
    RequirementRepository,
)


class RequirementService:
    """
    Service layer for Requirement Engine with AI-powered 12-step pipeline.
    
    Responsibilities:
    - Business logic validation
    - 12-step AI pipeline execution
    - Intent-based routing
    - AI market context embedding generation
    - Buyer priority score calculation
    - Event emission and flushing
    - WebSocket broadcasting for real-time updates
    - Orchestration of repository operations
    - Cross-commodity matching
    """
    
    def __init__(self, db: AsyncSession, ws_service=None):
        """
        Initialize service.
        
        Args:
            db: Async SQLAlchemy session
            ws_service: Optional WebSocket service for real-time broadcasts
        """
        self.db = db
        self.repo = RequirementRepository(db)
        self.ws_service = ws_service  # Injected WebSocket service
    
    # ========================================================================
    # 🚀 12-STEP AI PIPELINE: CREATE REQUIREMENT
    # ========================================================================
    
    async def create_requirement(
        self,
        buyer_id: UUID,
        commodity_id: UUID,
        min_quantity: Decimal,
        max_quantity: Decimal,
        quantity_unit: str,
        max_budget_per_unit: Decimal,
        quality_requirements: Dict[str, Any],
        valid_from: datetime,
        valid_until: datetime,
        created_by: UUID,
        # 🚀 ENHANCEMENT #1: Intent Layer
        intent_type: str = IntentType.DIRECT_BUY.value,
        # Standard fields
        variety_id: Optional[UUID] = None,
        preferred_quantity: Optional[Decimal] = None,
        preferred_price_per_unit: Optional[Decimal] = None,
        total_budget: Optional[Decimal] = None,
        currency_code: str = "INR",
        preferred_payment_terms: Optional[List[UUID]] = None,
        preferred_delivery_terms: Optional[List[UUID]] = None,
        delivery_locations: Optional[List[Dict[str, Any]]] = None,
        # 🚀 Risk Management
        buyer_branch_id: Optional[UUID] = None,
        blocked_internal_trades: bool = True,
        # 🚀 ENHANCEMENT #3: Dynamic Delivery Flexibility
        delivery_window_start: Optional[datetime] = None,
        delivery_window_end: Optional[datetime] = None,
        delivery_flexibility_hours: int = 168,  # Default 7 days
        market_visibility: str = MarketVisibility.PUBLIC.value,
        invited_seller_ids: Optional[List[UUID]] = None,
        urgency_level: str = UrgencyLevel.NORMAL.value,
        # 🚀 ENHANCEMENT #4: Multi-Commodity Conversion
        commodity_equivalents: Optional[Dict[str, Any]] = None,
        # 🚀 ENHANCEMENT #5: Negotiation Preferences
        negotiation_preferences: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        auto_publish: bool = False,
        **kwargs
    ) -> Requirement:
        """
        🚀 Create new requirement with 12-step AI pipeline.
        
        12-STEP AI PIPELINE WORKFLOW:
        
        Step 1: Validate buyer permissions & location constraints
        Step 2: 🚀 Risk precheck (credit limit, buyer rating, payment performance)
        Step 3: Auto-normalize quality requirements (AI standardization)
        Step 4: AI price suggestion based on market data
        Step 5: Calculate buyer priority score (trust weighting)
        Step 6: Detect unrealistic budget constraints
        Step 7: Generate market context embedding (1536-dim vector)
        Step 8: 🚀 Market sentiment adjustment (real-time pricing)
        Step 9: 🚀 Dynamic tolerance recommendation (quality flexibility)
        Step 10: Create requirement with all enhancements
        Step 11: Emit requirement.created event
        Step 12: Route to correct engine based on intent_type
        
        Args:
            buyer_id: Business partner UUID (BUYER or TRADER)
            commodity_id: Commodity UUID
            min_quantity: Minimum acceptable quantity
            max_quantity: Maximum desired quantity
            quantity_unit: Unit (bales, kg, MT, etc.)
            max_budget_per_unit: Maximum price willing to pay
            quality_requirements: Quality parameters with min/max/preferred/exact
            valid_from: Requirement valid from date
            valid_until: Requirement valid until date
            created_by: User UUID who created it
            intent_type: 🚀 DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY
            variety_id: Optional commodity variety
            preferred_quantity: Target/ideal quantity
            preferred_price_per_unit: Target/desired price
            total_budget: Overall budget limit
            currency_code: Currency (ISO 4217)
            preferred_payment_terms: Array of payment term UUIDs
            preferred_delivery_terms: Array of delivery term UUIDs
            delivery_locations: Multiple delivery locations with proximity
            delivery_window_start: 🚀 Earliest delivery date
            delivery_window_end: 🚀 Latest delivery date
            delivery_flexibility_hours: 🚀 Flexibility window (hours)
            market_visibility: PUBLIC, PRIVATE, RESTRICTED, INTERNAL
            invited_seller_ids: Seller UUIDs for RESTRICTED visibility
            urgency_level: URGENT, NORMAL, PLANNING
            commodity_equivalents: 🚀 Acceptable substitutes with conversion ratios
            negotiation_preferences: 🚀 Self-negotiation settings
            notes: Buyer internal notes
            attachments: Specification files
            auto_publish: If True, publish immediately (DRAFT → ACTIVE)
            **kwargs: Additional fields
        
        Returns:
            Created requirement with AI enhancements
        
        Raises:
            ValueError: If validation fails
        """
        # ====================================================================
        # STEP 1: Validate buyer permissions & location constraints
        # ====================================================================
        await self._validate_buyer_locations(buyer_id, delivery_locations)
        
        # ====================================================================
        # STEP 1A: 🚀 CAPABILITY VALIDATION (CDPS - Capability-Driven Partner System)
        # Validate partner has permission to buy based on verified documents
        # ====================================================================
        from backend.modules.trade_desk.validators.capability_validator import TradeCapabilityValidator
        
        # Get delivery country for capability check
        delivery_country = await self._get_delivery_country(delivery_locations)
        
        capability_validator = TradeCapabilityValidator(self.db)
        await capability_validator.validate_buy_capability(
            partner_id=buyer_id,
            delivery_country=delivery_country,
            raise_exception=True  # Will raise CapabilityValidationError if invalid
        )
        
        # ====================================================================
        # STEP 1B: 🚀 ROLE RESTRICTION VALIDATION (Option A)
        # Prevent SELLER from posting BUY requirements
        # Allow BUYER and TRADER to post BUY requirements
        # ====================================================================
        from backend.modules.risk.risk_engine import RiskEngine
        risk_engine = RiskEngine(self.db)
        
        role_validation = await risk_engine.validate_partner_role(
            partner_id=buyer_id,
            transaction_type="BUY"
        )
        
        if not role_validation["allowed"]:
            raise ValueError(role_validation["reason"])
        
        # ====================================================================
        # STEP 1B: 🚀 CIRCULAR TRADING PREVENTION (Option A: Same-day only)
        # Block if buyer has open SELL for same commodity today
        # ====================================================================
        circular_check = await risk_engine.check_circular_trading(
            partner_id=buyer_id,
            commodity_id=commodity_id,
            transaction_type="BUY",
            trade_date=valid_from.date()
        )
        
        if circular_check["blocked"]:
            raise ValueError(
                f"{circular_check['reason']}\n\n"
                f"Recommendation: {circular_check['recommendation']}"
            )
        
        # ====================================================================
        # STEP 2: 🚀 Risk precheck (credit limit, buyer rating, payment performance)
        # ====================================================================
        # Fetch buyer credit & performance data (placeholder - integrate with credit module)
        buyer_credit_limit_remaining = await self._fetch_buyer_credit_limit(buyer_id)
        buyer_rating_score = await self._fetch_buyer_rating(buyer_id)
        buyer_payment_performance_score = await self._fetch_payment_performance(buyer_id)
        
        # Calculate estimated trade value upfront
        estimated_trade_value = None
        if preferred_quantity and max_budget_per_unit:
            estimated_trade_value = preferred_quantity * max_budget_per_unit
        elif min_quantity and max_budget_per_unit:
            estimated_trade_value = min_quantity * max_budget_per_unit
        
        # ====================================================================
        # STEP 3: Auto-normalize quality requirements (AI standardization)
        # ====================================================================
        quality_requirements = await self.normalize_quality_requirements(
            commodity_id,
            quality_requirements
        )
        
        # ====================================================================
        # STEP 3: AI price suggestion based on market data
        # ====================================================================
        ai_price_result = await self.suggest_market_price(
            commodity_id,
            quality_requirements,
            min_quantity,
            max_quantity,
            urgency_level
        )
        
        ai_suggested_max_price = ai_price_result.get("suggested_max_price")
        ai_confidence_score = ai_price_result.get("confidence_score")
        ai_price_alert_flag = ai_price_result.get("is_unrealistic", False)
        ai_alert_reason = ai_price_result.get("alert_reason")
        
        # ====================================================================
        # STEP 4: 🚀 Calculate buyer priority score (trust weighting)
        # ====================================================================
        buyer_priority_score = await self.calculate_buyer_priority_score(
            buyer_id
        )
        
        # ====================================================================
        # STEP 5: Detect unrealistic budget constraints
        # ====================================================================
        if max_budget_per_unit and ai_suggested_max_price:
            budget_validation = await self.validate_budget_realism(
                max_budget_per_unit,
                ai_suggested_max_price,
                commodity_id
            )
            
            if budget_validation["is_unrealistic"]:
                ai_price_alert_flag = True
                ai_alert_reason = budget_validation["reason"]
        
        # ====================================================================
        # STEP 6: 🚀 Generate market context embedding (1536-dim vector)
        # ====================================================================
        market_context_embedding = await self.generate_market_context_embedding(
            commodity_id,
            quality_requirements,
            urgency_level,
            intent_type,
            max_budget_per_unit,
            notes
        )
        
        # ====================================================================
        # STEP 7: 🚀 ENHANCEMENT - Market sentiment adjustment
        # ====================================================================
        sentiment_adjustment = await self.adjust_for_market_sentiment(
            commodity_id,
            max_budget_per_unit,
            urgency_level,
            quality_requirements
        )
        
        # Apply sentiment adjustment to AI suggested price
        if ai_suggested_max_price and sentiment_adjustment["adjustment_factor"] != 1.0:
            adjusted_price = ai_suggested_max_price * Decimal(str(sentiment_adjustment["adjustment_factor"]))
            ai_suggested_max_price = adjusted_price
            
            # Log sentiment adjustment for explainability
            if not ai_alert_reason:
                ai_alert_reason = ""
            ai_alert_reason += f" | Market Sentiment: {sentiment_adjustment['sentiment']} ({sentiment_adjustment['reason']})"
        
        # ====================================================================
        # STEP 8: 🚀 ENHANCEMENT - Dynamic tolerance recommendation
        # ====================================================================
        tolerance_recommendations = await self.recommend_quality_tolerances(
            commodity_id,
            quality_requirements,
            urgency_level,
            market_visibility
        )
        
        # Inject tolerance recommendations into quality_requirements
        for param_name, tolerance_info in tolerance_recommendations.items():
            if param_name in quality_requirements:
                # Add tolerance metadata (AI-suggested)
                if isinstance(quality_requirements[param_name], dict):
                    quality_requirements[param_name]["ai_suggested_tolerance"] = tolerance_info["tolerance"]
                    quality_requirements[param_name]["ai_tolerance_reason"] = tolerance_info["reason"]
        
        # ====================================================================
        # STEP 9: Auto-suggest commodity equivalents (if not provided)
        # ====================================================================
        if not commodity_equivalents:
            commodity_equivalents = await self.suggest_commodity_equivalents(
                commodity_id,
                quality_requirements
            )
        
        # ====================================================================
        # STEP 10: Auto-suggest negotiation preferences (if not provided)
        # ====================================================================
        if not negotiation_preferences and intent_type in [IntentType.NEGOTIATION.value, IntentType.DIRECT_BUY.value]:
            negotiation_preferences = await self.suggest_negotiation_preferences(
                buyer_id,
                max_budget_per_unit,
                urgency_level
            )
        
        # ====================================================================
        # STEP 11: Generate AI-recommended sellers (pre-scoring)
        # ====================================================================
        ai_recommended_sellers = await self.recommend_sellers(
            commodity_id,
            quality_requirements,
            delivery_locations,
            max_budget_per_unit
        )
        
        # ====================================================================
        # STEP 12: Build AI score vector for ML matching
        # ====================================================================
        ai_score_vector = await self.calculate_ai_score_vector(
            commodity_id,
            quality_requirements,
            max_budget_per_unit,
            urgency_level,
            intent_type
        )
        
        # ====================================================================
        # CREATE REQUIREMENT MODEL
        # ====================================================================
        requirement = Requirement(
            buyer_partner_id=buyer_id,
            commodity_id=commodity_id,
            variety_id=variety_id,
            created_by_user_id=created_by,
            # Quantity
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            quantity_unit=quantity_unit,
            preferred_quantity=preferred_quantity,
            # Quality
            quality_requirements=quality_requirements,
            # Budget & Pricing
            max_budget_per_unit=max_budget_per_unit,
            preferred_price_per_unit=preferred_price_per_unit,
            total_budget=total_budget,
            currency_code=currency_code,
            # 🚀 Risk Management & Credit Control
            estimated_trade_value=estimated_trade_value,
            buyer_credit_limit_remaining=buyer_credit_limit_remaining,
            buyer_rating_score=buyer_rating_score,
            buyer_payment_performance_score=buyer_payment_performance_score,
            buyer_branch_id=buyer_branch_id,
            blocked_internal_trades=blocked_internal_trades,
            # Payment & Delivery
            preferred_payment_terms=preferred_payment_terms,
            preferred_delivery_terms=preferred_delivery_terms,
            delivery_locations=delivery_locations,
            # 🚀 ENHANCEMENT #3: Delivery Flexibility
            delivery_window_start=delivery_window_start,
            delivery_window_end=delivery_window_end,
            delivery_flexibility_hours=delivery_flexibility_hours,
            # Market Visibility
            market_visibility=market_visibility,
            invited_seller_ids=invited_seller_ids,
            # Lifecycle
            status=RequirementStatus.DRAFT.value,
            valid_from=valid_from,
            valid_until=valid_until,
            urgency_level=urgency_level,
            # 🚀 ENHANCEMENT #1: Intent Layer
            intent_type=intent_type,
            # Fulfillment Tracking
            total_matched_quantity=Decimal('0'),
            total_purchased_quantity=Decimal('0'),
            total_spent=Decimal('0'),
            active_negotiation_count=0,
            # 🚀 ENHANCEMENT #2: AI Market Context Embedding
            market_context_embedding=market_context_embedding,
            # AI Features
            ai_suggested_max_price=ai_suggested_max_price,
            ai_confidence_score=ai_confidence_score,
            ai_score_vector=ai_score_vector,
            ai_price_alert_flag=ai_price_alert_flag,
            ai_alert_reason=ai_alert_reason,
            ai_recommended_sellers=ai_recommended_sellers,
            # 🚀 ENHANCEMENT #4: Commodity Equivalents
            commodity_equivalents=commodity_equivalents,
            # 🚀 ENHANCEMENT #5: Negotiation Preferences
            negotiation_preferences=negotiation_preferences,
            # 🚀 ENHANCEMENT #6: Buyer Priority Score
            buyer_priority_score=buyer_priority_score,
            # Metadata
            notes=notes,
            attachments=attachments,
            **kwargs
        )
        
        # ====================================================================
        # PERSIST TO DATABASE
        # ====================================================================
        requirement = await self.repo.create(requirement)
        
        # ====================================================================
        # 🚀 UPDATE RISK PRECHECK (after creation with calculated values)
        # ====================================================================
        if buyer_credit_limit_remaining or buyer_rating_score or buyer_payment_performance_score:
            requirement.update_risk_precheck(
                credit_limit_remaining=buyer_credit_limit_remaining,
                rating_score=buyer_rating_score,
                payment_performance_score=buyer_payment_performance_score
            )
            # Update DB with risk assessment
            await self.repo.update(requirement)
        
        # ====================================================================
        # EMIT EVENTS
        # ====================================================================
        requirement.emit_created(created_by)
        
        # If auto-publish, immediately publish
        if auto_publish:
            requirement.publish(created_by)
            requirement.emit_published(created_by)
        
        await requirement.flush_events(self.db)
        
        # ====================================================================
        # 🚀 WEBSOCKET BROADCASTING (Real-time updates)
        # ====================================================================
        if self.ws_service:
            # Broadcast requirement.created
            await self.ws_service.broadcast_requirement_created(
                requirement_id=requirement.id,
                buyer_id=requirement.buyer_partner_id,
                commodity_id=requirement.commodity_id,
                intent_type=requirement.intent_type,
                urgency_level=requirement.urgency_level,
                data={
                    "min_quantity": float(requirement.min_quantity),
                    "max_quantity": float(requirement.max_quantity),
                    "max_budget_per_unit": float(requirement.max_budget_per_unit),
                    "status": requirement.status,
                    "market_visibility": requirement.market_visibility,
                }
            )
            
            # If published, broadcast requirement.published (🚀 triggers intent routing)
            if auto_publish:
                await self.ws_service.broadcast_requirement_published(
                    requirement_id=requirement.id,
                    buyer_id=requirement.buyer_partner_id,
                    commodity_id=requirement.commodity_id,
                    intent_type=requirement.intent_type,
                    urgency_level=requirement.urgency_level,
                    data={
                        "min_quantity": float(requirement.min_quantity),
                        "max_quantity": float(requirement.max_quantity),
                        "max_budget_per_unit": float(requirement.max_budget_per_unit),
                        "quality_requirements": requirement.quality_requirements,
                        "buyer_priority_score": requirement.buyer_priority_score,
                    }
                )
        
        # ====================================================================
        # 🚀 STEP 13: INTENT-BASED ROUTING
        # ====================================================================
        if auto_publish:
            await self._route_by_intent(requirement)
        
        return requirement
    
    # ========================================================================
    # UPDATE & LIFECYCLE OPERATIONS
    # ========================================================================
    
    async def update_requirement(
        self,
        requirement_id: UUID,
        updated_by: UUID,
        **updates
    ) -> Optional[Requirement]:
        """
        Update requirement with AI re-processing and micro-events.
        
        Detects changes and emits appropriate micro-events:
        - max_budget_per_unit changed → emit budget_changed
        - quality_requirements changed → emit quality_changed
        - market_visibility changed → emit visibility_changed
        
        Args:
            requirement_id: Requirement UUID
            updated_by: User UUID who updated it
            **updates: Fields to update
        
        Returns:
            Updated requirement or None if not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            return None
        
        if not requirement.can_update():
            raise ValueError(f"Cannot update requirement with status {requirement.status}")
        
        # Track old values for micro-events
        old_max_budget = requirement.max_budget_per_unit
        old_preferred_price = requirement.preferred_price_per_unit
        old_quality_requirements = requirement.quality_requirements
        old_visibility = requirement.market_visibility
        
        # Update fields
        for key, value in updates.items():
            if hasattr(requirement, key) and value is not None:
                setattr(requirement, key, value)
        
        # Re-normalize quality requirements if changed
        if "quality_requirements" in updates and updates["quality_requirements"]:
            requirement.quality_requirements = await self.normalize_quality_requirements(
                requirement.commodity_id,
                updates["quality_requirements"]
            )
        
        # Re-suggest price if budget changed or quality changed
        if "max_budget_per_unit" in updates or "quality_requirements" in updates:
            ai_price_result = await self.suggest_market_price(
                requirement.commodity_id,
                requirement.quality_requirements,
                requirement.min_quantity,
                requirement.max_quantity,
                requirement.urgency_level
            )
            requirement.ai_suggested_max_price = ai_price_result.get("suggested_max_price")
            requirement.ai_confidence_score = ai_price_result.get("confidence_score")
        
        # Re-calculate market context embedding if significant changes
        if any(k in updates for k in ["quality_requirements", "max_budget_per_unit", "urgency_level"]):
            requirement.market_context_embedding = await self.generate_market_context_embedding(
                requirement.commodity_id,
                requirement.quality_requirements,
                requirement.urgency_level,
                requirement.intent_type,
                requirement.max_budget_per_unit,
                requirement.notes
            )
        
        # Persist
        requirement = await self.repo.update(requirement)
        
        # Emit micro-events
        
        # 1. Budget changed?
        if ("max_budget_per_unit" in updates and updates["max_budget_per_unit"] != old_max_budget) or \
           ("preferred_price_per_unit" in updates and updates.get("preferred_price_per_unit") != old_preferred_price):
            requirement.emit_budget_changed(
                updated_by,
                old_max_budget,
                requirement.max_budget_per_unit,
                old_preferred_price,
                requirement.preferred_price_per_unit,
                reason="Manual update"
            )
        
        # 2. Quality changed?
        if "quality_requirements" in updates and updates["quality_requirements"] != old_quality_requirements:
            requirement.emit_quality_changed(
                updated_by,
                old_quality_requirements,
                requirement.quality_requirements,
                reason="Manual update"
            )
        
        # 3. Visibility changed?
        if "market_visibility" in updates and updates["market_visibility"] != old_visibility:
            requirement.emit_visibility_changed(
                updated_by,
                old_visibility,
                requirement.market_visibility,
                reason="Manual update"
            )
        
        # Flush events
        await requirement.flush_events(self.db)
        
        return requirement
    
    async def publish_requirement(
        self,
        requirement_id: UUID,
        published_by: UUID
    ) -> Optional[Requirement]:
        """
        Publish requirement (DRAFT → ACTIVE).
        
        Args:
            requirement_id: Requirement UUID
            published_by: User UUID who published it
        
        Returns:
            Published requirement or None if not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            return None
        
        requirement.publish(published_by)
        requirement = await self.repo.update(requirement)
        
        await requirement.flush_events(self.db)
        
        # 🚀 WebSocket: Broadcast requirement.published (triggers intent routing)
        if self.ws_service:
            await self.ws_service.broadcast_requirement_published(
                requirement_id=requirement.id,
                buyer_id=requirement.buyer_partner_id,
                commodity_id=requirement.commodity_id,
                intent_type=requirement.intent_type,
                urgency_level=requirement.urgency_level,
                data={
                    "min_quantity": float(requirement.min_quantity),
                    "max_quantity": float(requirement.max_quantity),
                    "max_budget_per_unit": float(requirement.max_budget_per_unit),
                    "quality_requirements": requirement.quality_requirements,
                    "buyer_priority_score": requirement.buyer_priority_score,
                }
            )
        
        # 🚀 Intent-based routing
        await self._route_by_intent(requirement)
        
        return requirement
    
    async def cancel_requirement(
        self,
        requirement_id: UUID,
        cancelled_by: UUID,
        reason: str
    ) -> Optional[Requirement]:
        """
        Cancel requirement.
        
        Args:
            requirement_id: Requirement UUID
            cancelled_by: User UUID who cancelled it
            reason: Cancellation reason
        
        Returns:
            Cancelled requirement or None if not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            return None
        
        requirement.cancel(cancelled_by, reason)
        requirement = await self.repo.update(requirement)
        
        await requirement.flush_events(self.db)
        
        # 🚀 WebSocket: Broadcast requirement.cancelled
        if self.ws_service:
            await self.ws_service.broadcast_requirement_cancelled(
                requirement_id=requirement.id,
                buyer_id=requirement.buyer_partner_id,
                data={
                    "reason": reason,
                    "unfulfilled_quantity": float(requirement.max_quantity - requirement.total_purchased_quantity),
                }
            )
        
        return requirement
    
    async def update_fulfillment(
        self,
        requirement_id: UUID,
        purchased_quantity: Decimal,
        amount_spent: Decimal,
        updated_by: UUID,
        trade_id: Optional[UUID] = None
    ) -> Optional[Requirement]:
        """
        Update requirement fulfillment (when buyer purchases).
        
        Args:
            requirement_id: Requirement UUID
            purchased_quantity: Quantity purchased
            amount_spent: Amount spent
            updated_by: User UUID who made purchase
            trade_id: Optional trade ID reference
        
        Returns:
            Updated requirement or None if not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            return None
        
        requirement.update_fulfillment(
            purchased_quantity,
            amount_spent,
            updated_by,
            trade_id
        )
        
        requirement = await self.repo.update(requirement)
        await requirement.flush_events(self.db)
        
        # 🚀 WebSocket: Broadcast requirement.fulfillment_updated
        if self.ws_service:
            is_fulfilled = requirement.status == RequirementStatus.FULFILLED.value
            
            if is_fulfilled:
                await self.ws_service.broadcast_requirement_fulfilled(
                    requirement_id=requirement.id,
                    buyer_id=requirement.buyer_partner_id,
                    data={
                        "total_purchased_quantity": float(requirement.total_purchased_quantity),
                        "total_spent": float(requirement.total_spent),
                        "avg_price_per_unit": float(requirement.total_spent / requirement.total_purchased_quantity),
                    }
                )
            else:
                await self.ws_service.broadcast_fulfillment_updated(
                    requirement_id=requirement.id,
                    buyer_id=requirement.buyer_partner_id,
                    data={
                        "purchased_quantity": float(purchased_quantity),
                        "amount_spent": float(amount_spent),
                        "total_purchased_quantity": float(requirement.total_purchased_quantity),
                        "total_spent": float(requirement.total_spent),
                        "remaining_quantity": float(requirement.max_quantity - requirement.total_purchased_quantity),
                    }
                )
        
        return requirement
    
    # ========================================================================
    # 🚀 ENHANCEMENT #7: AI ADJUSTMENT WITH EXPLAINABILITY
    # ========================================================================
    
    async def apply_ai_adjustment(
        self,
        requirement_id: UUID,
        adjustment_type: str,
        new_value: Any,
        ai_confidence: float,
        ai_reasoning: str,
        market_context: Optional[Dict[str, Any]] = None,
        expected_impact: Optional[str] = None,
        auto_apply: bool = False
    ) -> Optional[Requirement]:
        """
        🚀 Apply AI-suggested adjustment with full explainability.
        
        Critical for transparency and trust in autonomous AI decisions.
        
        Adjustment Types:
        - "budget": Adjust max_budget_per_unit
        - "quality": Adjust quality_requirements tolerance
        - "delivery_window": Adjust delivery_window_start/end
        - "commodity_equivalents": Add/remove acceptable substitutes
        
        Args:
            requirement_id: Requirement UUID
            adjustment_type: Type of adjustment
            new_value: New value to apply
            ai_confidence: AI confidence score (0.0 to 1.0)
            ai_reasoning: Human-readable explanation
            market_context: Market data used for decision
            expected_impact: Expected impact description
            auto_apply: If True, apply immediately. If False, suggest only.
        
        Returns:
            Updated requirement or None if not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            return None
        
        # Get old value
        old_value = None
        if adjustment_type == "budget":
            old_value = requirement.max_budget_per_unit
            if auto_apply:
                requirement.max_budget_per_unit = Decimal(str(new_value))
        elif adjustment_type == "quality":
            old_value = requirement.quality_requirements
            if auto_apply:
                requirement.quality_requirements = new_value
        elif adjustment_type == "delivery_window":
            old_value = {
                "start": requirement.delivery_window_start,
                "end": requirement.delivery_window_end
            }
            if auto_apply:
                requirement.delivery_window_start = new_value.get("start")
                requirement.delivery_window_end = new_value.get("end")
        elif adjustment_type == "commodity_equivalents":
            old_value = requirement.commodity_equivalents
            if auto_apply:
                requirement.commodity_equivalents = new_value
        
        # Emit AI adjustment event (always emit, even if not auto-applied)
        requirement.emit_ai_adjusted(
            adjustment_type=adjustment_type,
            old_value=old_value,
            new_value=new_value,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            market_context=market_context,
            expected_impact=expected_impact,
            adjusted_by_system=auto_apply
        )
        
        if auto_apply:
            requirement = await self.repo.update(requirement)
        
        await requirement.flush_events(self.db)
        
        # 🚀 WebSocket: Broadcast requirement.ai_adjusted
        if self.ws_service:
            await self.ws_service.broadcast_ai_adjusted(
                requirement_id=requirement.id,
                buyer_id=requirement.buyer_partner_id,
                data={
                    "adjustment_type": adjustment_type,
                    "old_value": str(old_value),
                    "new_value": str(new_value),
                    "ai_confidence": ai_confidence,
                    "ai_reasoning": ai_reasoning,
                    "auto_applied": auto_apply,
                }
            )
        
        return requirement
    
    # ========================================================================
    # AI-POWERED FEATURES (12-STEP PIPELINE COMPONENTS)
    # ========================================================================
    
    async def normalize_quality_requirements(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Auto-normalize quality requirements using AI standardization.
        
        Handles range-based requirements:
        - {"staple_length": {"min": 28, "max": 30, "preferred": 29}}
        - {"micronaire": {"exact": 4.2}}
        - {"strength": {"min": 26, "accepted": [26, 27, 28]}}
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Raw quality requirements
        
        Returns:
            Normalized quality requirements
        
        TODO: Integrate with AI model for intelligent normalization
        """
        # TODO: Load commodity-specific normalization rules
        
        normalized = {}
        
        for key, value in quality_requirements.items():
            if isinstance(value, dict):
                # Already structured (min/max/preferred/exact)
                normalized[key] = value
            elif isinstance(value, (int, float, Decimal)):
                # Convert to exact match
                normalized[key] = {"exact": float(value)}
            elif isinstance(value, str):
                # Try parsing
                try:
                    num_val = float(value.replace("%", "").strip())
                    normalized[key] = {"exact": num_val}
                except ValueError:
                    normalized[key] = {"exact": value.strip().upper()}
            else:
                normalized[key] = value
        
        return normalized
    
    async def suggest_market_price(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any],
        min_quantity: Decimal,
        max_quantity: Decimal,
        urgency_level: str
    ) -> Dict[str, Any]:
        """
        AI-powered market price suggestion.
        
        Uses:
        - Historical price data
        - Current market availability
        - Quality parameter impact
        - Quantity impact (bulk discounts)
        - Urgency impact (premium for urgent)
        - Seasonality patterns
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Quality parameters
            min_quantity: Minimum quantity
            max_quantity: Maximum quantity
            urgency_level: URGENT, NORMAL, PLANNING
        
        Returns:
            {
                "suggested_max_price": Decimal,
                "confidence_score": int (0-100),
                "is_unrealistic": bool,
                "alert_reason": str,
                "price_range": {"min": Decimal, "max": Decimal, "avg": Decimal}
            }
        
        TODO: Integrate with AI pricing model
        """
        # TODO: Load historical prices
        # TODO: Use ML model to predict price
        
        # Placeholder: Return conservative suggestion
        return {
            "suggested_max_price": None,
            "confidence_score": 50,
            "is_unrealistic": False,
            "alert_reason": None,
            "price_range": None
        }
    
    async def calculate_buyer_priority_score(
        self,
        buyer_id: UUID
    ) -> float:
        """
        🚀 ENHANCEMENT #6: Calculate buyer priority/trust score.
        
        Scoring Factors:
        - Historical fulfillment rate (completed vs cancelled)
        - Payment track record (on-time vs delays)
        - Dispute rate (clean record vs frequent disputes)
        - Account age (new vs established)
        - Trade volume (small vs large buyer)
        
        Score Scale:
        - 0.5: New/unverified buyers
        - 1.0: Standard buyers (default)
        - 1.5: Repeat buyers with good track record
        - 2.0: Premium/VIP buyers
        
        Args:
            buyer_id: Buyer business partner UUID
        
        Returns:
            Priority score (0.5 to 2.0)
        
        TODO: Implement actual scoring using historical data
        """
        # TODO: Load buyer history from trades, payments, disputes
        # TODO: Calculate weighted score
        
        # Placeholder: Return default score
        return 1.0
    
    async def validate_budget_realism(
        self,
        budget: Decimal,
        ai_suggested_price: Decimal,
        commodity_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate if buyer's budget is realistic.
        
        Prevents spam requirements with unrealistic budgets.
        
        Args:
            budget: Buyer's max budget per unit
            ai_suggested_price: AI-suggested market price
            commodity_id: Commodity UUID
        
        Returns:
            {
                "is_unrealistic": bool,
                "reason": str,
                "budget_vs_market_pct": float
            }
        """
        if not ai_suggested_price or ai_suggested_price == 0:
            return {"is_unrealistic": False, "reason": None, "budget_vs_market_pct": 0}
        
        # Calculate deviation
        deviation_pct = ((budget - ai_suggested_price) / ai_suggested_price) * 100
        
        # Flag if budget is >30% below market (unrealistic low)
        if deviation_pct < -30:
            return {
                "is_unrealistic": True,
                "reason": f"Budget {abs(deviation_pct):.1f}% below market price. Consider increasing budget.",
                "budget_vs_market_pct": deviation_pct
            }
        
        return {
            "is_unrealistic": False,
            "reason": None,
            "budget_vs_market_pct": deviation_pct
        }
    
    async def generate_market_context_embedding(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any],
        urgency_level: str,
        intent_type: str,
        budget: Optional[Decimal],
        notes: Optional[str]
    ) -> Optional[List[float]]:
        """
        🚀 ENHANCEMENT #2: Generate 1536-dim market context embedding.
        
        Uses OpenAI ada-002 compatible embedding model.
        
        Encoding Context:
        - Commodity type
        - Quality parameters (semantic)
        - Urgency level
        - Intent type
        - Budget range
        - Buyer notes (semantic)
        
        Enables:
        - Semantic similarity search
        - Cross-commodity pattern detection
        - Market sentiment analysis
        - Predictive matching
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Quality parameters
            urgency_level: URGENT, NORMAL, PLANNING
            intent_type: DIRECT_BUY, NEGOTIATION, etc.
            budget: Max budget per unit
            notes: Buyer notes
        
        Returns:
            1536-dim vector or None
        
        TODO: Integrate with OpenAI or local embedding model
        """
        # TODO: Generate text representation of requirement
        # TODO: Call embedding model (OpenAI ada-002 or local)
        # TODO: Return 1536-dim vector
        
        # Placeholder: Return None (will implement with AI model)
        return None
    
    async def adjust_for_market_sentiment(
        self,
        commodity_id: UUID,
        budget: Decimal,
        urgency_level: str,
        quality_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🚀 ENHANCEMENT #7: Adjust pricing based on real-time market sentiment.
        
        Sentiment Factors:
        - Supply/demand ratio
        - Recent price trends (rising/falling)
        - Seasonal patterns
        - News sentiment (bullish/bearish)
        - Inventory levels
        
        Args:
            commodity_id: Commodity UUID
            budget: Current budget per unit
            urgency_level: URGENT, NORMAL, PLANNING
            quality_requirements: Quality parameters
        
        Returns:
            {
                "sentiment": str ("bullish", "bearish", "neutral"),
                "adjustment_factor": float (0.9 to 1.1),
                "reason": str,
                "confidence": float (0.0 to 1.0)
            }
        
        TODO: Integrate with market sentiment analysis
        """
        # TODO: Load recent market data
        # TODO: Analyze supply/demand trends
        # TODO: Calculate sentiment score
        
        # Placeholder: Return neutral sentiment
        return {
            "sentiment": "neutral",
            "adjustment_factor": 1.0,
            "reason": "Market sentiment analysis not yet implemented",
            "confidence": 0.5
        }
    
    async def recommend_quality_tolerances(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any],
        urgency_level: str,
        market_visibility: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        🚀 ENHANCEMENT #8: Recommend dynamic quality tolerances.
        
        Tolerance Factors:
        - Market availability (low availability = higher tolerance)
        - Urgency level (urgent = higher tolerance)
        - Quality parameter criticality (critical params = lower tolerance)
        - Historical matching success rates
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Current quality requirements
            urgency_level: URGENT, NORMAL, PLANNING
            market_visibility: PUBLIC, PRIVATE, etc.
        
        Returns:
            {
                "param_name": {
                    "tolerance": float,
                    "reason": str,
                    "confidence": float
                }
            }
        
        TODO: Integrate with AI tolerance recommendation model
        """
        # TODO: Load market availability data
        # TODO: Analyze historical matching patterns
        # TODO: Calculate optimal tolerances
        
        # Placeholder: Return conservative tolerances
        recommendations = {}
        
        for param_name in quality_requirements.keys():
            # Default tolerance based on urgency
            if urgency_level == UrgencyLevel.URGENT.value:
                tolerance = 2.0  # Higher tolerance for urgent
            elif urgency_level == UrgencyLevel.PLANNING.value:
                tolerance = 0.5  # Lower tolerance for planning
            else:
                tolerance = 1.0  # Standard tolerance
            
            recommendations[param_name] = {
                "tolerance": tolerance,
                "reason": f"Based on {urgency_level} urgency level",
                "confidence": 0.6
            }
        
        return recommendations
    
    async def suggest_commodity_equivalents(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        🚀 ENHANCEMENT #4: Suggest acceptable commodity equivalents.
        
        Examples:
        - Cotton → Cotton Yarn (conversion ratio 0.85)
        - Paddy → Rice (conversion ratio 0.65)
        - Wheat → Flour (conversion ratio 0.75)
        
        Args:
            commodity_id: Source commodity UUID
            quality_requirements: Quality parameters
        
        Returns:
            {
                "acceptable_substitutes": [
                    {
                        "commodity_id": UUID,
                        "conversion_ratio": float,
                        "quality_mapping": {"source_param": "target_param"}
                    }
                ]
            }
        
        TODO: Integrate with commodity conversion knowledge base
        """
        # TODO: Load commodity conversion rules
        # TODO: Calculate conversion ratios
        # TODO: Map quality parameters
        
        # Placeholder: Return None
        return None
    
    async def suggest_negotiation_preferences(
        self,
        buyer_id: UUID,
        budget: Decimal,
        urgency_level: str
    ) -> Dict[str, Any]:
        """
        🚀 ENHANCEMENT #5: Suggest negotiation preferences.
        
        Auto-configure self-negotiation settings based on:
        - Buyer's historical negotiation patterns
        - Urgency level
        - Budget flexibility
        
        Args:
            buyer_id: Buyer UUID
            budget: Max budget per unit
            urgency_level: URGENT, NORMAL, PLANNING
        
        Returns:
            {
                "allow_auto_negotiation": bool,
                "max_rounds": int,
                "price_tolerance_percent": float,
                "quantity_tolerance_percent": float,
                "auto_accept_if_score": float,
                "escalate_to_human_if_score": float
            }
        
        TODO: Load buyer's historical negotiation preferences
        """
        # Default preferences based on urgency
        if urgency_level == UrgencyLevel.URGENT.value:
            return {
                "allow_auto_negotiation": True,
                "max_rounds": 3,
                "price_tolerance_percent": 5.0,
                "quantity_tolerance_percent": 15.0,
                "auto_accept_if_score": 0.85,
                "escalate_to_human_if_score": 0.60
            }
        elif urgency_level == UrgencyLevel.PLANNING.value:
            return {
                "allow_auto_negotiation": True,
                "max_rounds": 7,
                "price_tolerance_percent": 2.0,
                "quantity_tolerance_percent": 5.0,
                "auto_accept_if_score": 0.95,
                "escalate_to_human_if_score": 0.70
            }
        else:  # NORMAL
            return {
                "allow_auto_negotiation": True,
                "max_rounds": 5,
                "price_tolerance_percent": 3.0,
                "quantity_tolerance_percent": 10.0,
                "auto_accept_if_score": 0.90,
                "escalate_to_human_if_score": 0.65
            }
    
    async def recommend_sellers(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any],
        delivery_locations: Optional[List[Dict[str, Any]]],
        budget: Decimal
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Pre-score and recommend sellers.
        
        Scoring Factors:
        - Quality match
        - Price competitiveness
        - Delivery proximity
        - Seller rating
        - Historical reliability
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Quality parameters
            delivery_locations: Delivery locations
            budget: Max budget per unit
        
        Returns:
            [
                {
                    "seller_id": UUID,
                    "match_score": float,
                    "reason": str
                }
            ]
        
        TODO: Integrate with seller recommendation engine
        """
        # TODO: Search availabilities
        # TODO: Score sellers
        # TODO: Return top recommendations
        
        # Placeholder: Return None
        return None
    
    async def calculate_ai_score_vector(
        self,
        commodity_id: UUID,
        quality_requirements: Dict[str, Any],
        budget: Decimal,
        urgency_level: str,
        intent_type: str
    ) -> Dict[str, Any]:
        """
        Calculate AI score vector (JSONB) for ML matching.
        
        Vector includes:
        - Commodity encoding
        - Quality parameters encoding
        - Budget normalization
        - Urgency encoding
        - Intent encoding
        
        Args:
            commodity_id: Commodity UUID
            quality_requirements: Quality parameters
            budget: Max budget per unit
            urgency_level: URGENT, NORMAL, PLANNING
            intent_type: DIRECT_BUY, NEGOTIATION, etc.
        
        Returns:
            JSONB vector
        
        TODO: Use actual ML embeddings
        """
        return {
            "commodity_id": str(commodity_id),
            "quality_hash": hash(str(quality_requirements)),
            "budget_normalized": float(budget) / 100000.0,
            "urgency_encoded": {
                UrgencyLevel.URGENT.value: 3,
                UrgencyLevel.NORMAL.value: 2,
                UrgencyLevel.PLANNING.value: 1
            }.get(urgency_level, 2),
            "intent_encoded": {
                IntentType.DIRECT_BUY.value: 4,
                IntentType.NEGOTIATION.value: 3,
                IntentType.AUCTION_REQUEST.value: 2,
                IntentType.PRICE_DISCOVERY_ONLY.value: 1
            }.get(intent_type, 3),
            "version": "v1_placeholder"
        }
    
    # ========================================================================
    # BUSINESS RULE VALIDATION
    # ========================================================================
    
    async def _validate_buyer_locations(
        self,
        buyer_id: UUID,
        delivery_locations: Optional[List[Dict[str, Any]]]
    ) -> None:
        """
        Validate buyer can specify delivery locations.
        
        Rules:
        - BUYER: Can only specify registered locations
        - TRADER: Can specify any location (no restriction)
        
        Args:
            buyer_id: Business partner UUID
            delivery_locations: Delivery locations list
        
        Raises:
            ValueError: If buyer not allowed to use locations
        
        TODO: Implement actual validation
        """
        # TODO: Load business partner and check partner_type
        # TODO: If BUYER, verify all location_ids in partner.locations
        # TODO: If TRADER, allow any location
        
        # Placeholder: Allow all
        pass
    
    async def _get_delivery_country(
        self,
        delivery_locations: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Get delivery country from delivery locations for capability validation.
        
        Args:
            delivery_locations: Delivery locations list
        
        Returns:
            str: Country name (e.g., "India", "USA", "China")
        
        TODO: Query actual location table when available
        """
        # TODO: Load from settings_locations table
        # For now, default to India (most common case)
        # This will be properly implemented when location module is integrated
        return "India"
    
    # ========================================================================
    # 🚀 RISK MANAGEMENT HELPERS
    # ========================================================================
    
    async def _fetch_buyer_credit_limit(self, buyer_id: UUID) -> Optional[Decimal]:
        """
        Fetch buyer's remaining credit limit from credit module.
        
        Args:
            buyer_id: Buyer UUID
        
        Returns:
            Remaining credit limit or None if not available
        
        TODO: Integrate with credit management module
        """
        # Placeholder: Return None (will be populated by credit module)
        return None
    
    async def _fetch_buyer_rating(self, buyer_id: UUID) -> Optional[Decimal]:
        """
        Fetch buyer rating from rating module.
        
        Args:
            buyer_id: Buyer UUID
        
        Returns:
            Buyer rating (0.00-5.00) or None if not available
        
        TODO: Integrate with rating module
        """
        # Placeholder: Return None (will be populated by rating module)
        return None
    
    async def _fetch_payment_performance(self, buyer_id: UUID) -> Optional[int]:
        """
        Fetch buyer payment performance score from history.
        
        Args:
            buyer_id: Buyer UUID
        
        Returns:
            Payment performance score (0-100) or None if not available
        
        TODO: Integrate with payment history module
        """
        # Placeholder: Return None (will be populated by payment module)
        return None
    
    async def update_risk_precheck(
        self,
        requirement_id: UUID,
        credit_limit_remaining: Optional[Decimal] = None,
        rating_score: Optional[Decimal] = None,
        payment_performance_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update risk precheck for a requirement.
        
        Args:
            requirement_id: Requirement UUID
            credit_limit_remaining: Buyer's remaining credit limit
            rating_score: Buyer rating (0-5.00)
            payment_performance_score: Payment performance (0-100)
        
        Returns:
            Risk assessment details
        
        Raises:
            ValueError: If requirement not found
        """
        requirement = await self.repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        # Call model method
        risk_assessment = requirement.update_risk_precheck(
            credit_limit_remaining,
            rating_score,
            payment_performance_score
        )
        
        # Save to database
        await self.repo.update(requirement)
        
        # 🚀 WebSocket: Broadcast risk alert if status changed or score is concerning
        if self.ws_service and (risk_assessment["risk_precheck_status"] != "PASS"):
            await self.ws_service.broadcast_risk_alert(
                requirement_id=requirement.id,
                buyer_id=requirement.buyer_partner_id,
                risk_status=risk_assessment["risk_precheck_status"],
                risk_score=risk_assessment["risk_precheck_score"],
                risk_factors=risk_assessment["risk_factors"],
                data={
                    "estimated_trade_value": float(risk_assessment.get("estimated_trade_value") or 0),
                    "buyer_exposure_after_trade": float(risk_assessment.get("buyer_exposure_after_trade") or 0),
                }
            )
        
        return risk_assessment
    
    # ========================================================================
    # ROUTING & INTENT PROCESSING
    # ========================================================================
    
    async def _route_by_intent(
        self,
        requirement: Requirement
    ) -> None:
        """
        🚀 Route requirement to correct engine based on intent_type.
        
        Routing Logic:
        - DIRECT_BUY → Matching Engine (Engine 3) for immediate matching
        - NEGOTIATION → Negotiation Queue (Engine 4) for multi-round negotiation
        - AUCTION_REQUEST → Reverse Auction Module (Engine 5)
        - PRICE_DISCOVERY_ONLY → Market Insights (no trade execution)
        
        Args:
            requirement: Published requirement
        
        TODO: Implement actual routing to downstream engines
        """
        # TODO: Based on intent_type, trigger downstream engines
        # - DIRECT_BUY: Call matching_service.match_requirement()
        # - NEGOTIATION: Call negotiation_service.queue_requirement()
        # - AUCTION_REQUEST: Call auction_service.create_reverse_auction()
        # - PRICE_DISCOVERY_ONLY: No action (insights only)
        
        # Placeholder: Log routing (implement actual routing later)
        pass
    
    # ========================================================================
    # SEARCH & QUERY OPERATIONS
    # ========================================================================
    
    async def search_requirements(
        self,
        seller_id: Optional[UUID] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        Search requirements using AI-powered smart_search.
        
        Args:
            seller_id: Seller UUID (for visibility access control)
            **search_params: Search parameters
        
        Returns:
            List of enriched requirement results with match scores
        """
        # Add default visibility for seller
        if "market_visibility" not in search_params:
            search_params["market_visibility"] = [
                MarketVisibility.PUBLIC.value,
                MarketVisibility.RESTRICTED.value
            ]
        
        if seller_id:
            search_params["seller_id"] = seller_id
        
        return await self.repo.smart_search(**search_params)
    
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
        🚀 Search requirements by intent type.
        
        Args:
            intent_type: IntentType enum value
            commodity_id: Optional commodity filter
            urgency_level: Optional urgency filter
            min_priority_score: Minimum buyer priority score
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements
        """
        return await self.repo.search_by_intent(
            intent_type,
            commodity_id,
            urgency_level,
            min_priority_score,
            skip,
            limit
        )
    
    async def get_buyer_requirements(
        self,
        buyer_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Requirement]:
        """
        Get all requirements for a buyer.
        
        Args:
            buyer_id: Buyer UUID
            status: Optional status filter
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of requirements
        """
        return await self.repo.get_by_buyer(buyer_id, status, skip, limit)
    
    async def get_total_demand(
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
            Demand statistics
        """
        return await self.repo.get_total_demand_by_commodity(commodity_id, days)
