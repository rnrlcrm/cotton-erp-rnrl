"""
Risk Engine Service - Business logic layer for risk assessments

Integrates with:
- Partner module (credit limits, ratings)
- Trade Desk module (requirements, availabilities)
- WebSocket manager (risk alert broadcasting)
"""

import json
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.outbox import OutboxRepository
from backend.modules.risk.risk_engine import RiskEngine
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.core.websocket.manager import ConnectionManager
from backend.ai.orchestrators.factory import get_orchestrator


class RiskService:
    """Service layer for Risk Engine operations"""
    
    def __init__(
        self,
        db: AsyncSession,
        ws_manager: Optional[ConnectionManager] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.db = db
        self.ws_manager = ws_manager
        self.redis = redis_client
        self.outbox_repo = OutboxRepository(db)
        self.risk_engine = RiskEngine(db)
        
        # AI orchestrator for AI-enhanced risk scoring
        try:
            self.ai_orchestrator = get_orchestrator()
        except Exception:
            self.ai_orchestrator = None  # Fallback to rule-based only
    
    # ============================================================================
    # REQUIREMENT RISK ASSESSMENT
    # ============================================================================
    
    async def assess_requirement_risk(
        self,
        requirement_id: UUID,
        user_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess risk for a requirement and broadcast alerts if needed.
        
        Args:
            requirement_id: Requirement UUID
            user_id: User performing assessment
            idempotency_key: Optional idempotency key
            
        Returns:
            Risk assessment result
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        
        # Get requirement
        stmt = select(Requirement).where(Requirement.id == requirement_id)
        result = await self.db.execute(stmt)
        requirement = result.scalar_one_or_none()
        
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        # Get buyer data (from partner module)
        buyer_data = await self._get_buyer_data(requirement.buyer_partner_id)
        
        # Perform risk assessment
        assessment = await self.risk_engine.assess_buyer_risk(
            requirement=requirement,
            buyer_credit_limit=buyer_data["credit_limit"],
            buyer_current_exposure=buyer_data["current_exposure"],
            buyer_rating=buyer_data["rating"],
            buyer_payment_performance=buyer_data["payment_performance"],
            user_id=user_id
        )
        
        # Broadcast risk alert if FAIL
        if assessment["status"] == "FAIL" and self.ws_manager:
            await self._broadcast_risk_alert(
                entity_type="requirement",
                entity_id=requirement_id,
                assessment=assessment
            )
        
        # Emit event to outbox (transactional)
        await self.outbox_repo.add_event(
            event_type="risk.requirement_assessed",
            aggregate_type="requirement",
            aggregate_id=str(requirement_id),
            payload={
                "requirement_id": str(requirement_id),
                "buyer_partner_id": str(requirement.buyer_partner_id),
                "assessment": assessment,
                "user_id": str(user_id),
                "status": assessment["status"]
            },
            user_id=user_id
        )
        
        # Commit changes to database
        await self.db.commit()
        
        # Cache result for idempotency
        if idempotency_key and self.redis:
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,  # 24 hours
                json.dumps(assessment)
            )
        
        return assessment
    
    # ============================================================================
    # AVAILABILITY RISK ASSESSMENT
    # ============================================================================
    
    async def assess_availability_risk(
        self,
        availability_id: UUID,
        user_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess risk for an availability and broadcast alerts if needed.
        
        Args:
            availability_id: Availability UUID
            user_id: User performing assessment
            idempotency_key: Optional idempotency key
            
        Returns:
            Risk assessment result
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        
        # Get availability
        stmt = select(Availability).where(Availability.id == availability_id)
        result = await self.db.execute(stmt)
        availability = result.scalar_one_or_none()
        
        if not availability:
            raise ValueError(f"Availability {availability_id} not found")
        
        # Get seller data (from partner module)
        seller_data = await self._get_seller_data(availability.seller_id)
        
        # Perform risk assessment
        assessment = await self.risk_engine.assess_seller_risk(
            availability=availability,
            seller_credit_limit=seller_data["credit_limit"],
            seller_current_exposure=seller_data["current_exposure"],
            seller_rating=seller_data["rating"],
            seller_delivery_performance=seller_data["delivery_performance"],
            user_id=user_id
        )
        
        # Broadcast risk alert if FAIL
        if assessment["status"] == "FAIL" and self.ws_manager:
            await self._broadcast_risk_alert(
                entity_type="availability",
                entity_id=availability_id,
                assessment=assessment
            )
        
        # Emit event to outbox
        await self.outbox_repo.add_event(
            event_type="risk.availability_assessed",
            aggregate_type="availability",
            aggregate_id=str(availability_id),
            payload={
                "availability_id": str(availability_id),
                "seller_id": str(availability.seller_id),
                "assessment": assessment,
                "user_id": str(user_id),
                "status": assessment["status"]
            },
            user_id=user_id
        )
        
        # Commit changes to database
        await self.db.commit()
        
        # Cache for idempotency
        if idempotency_key and self.redis:
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,
                json.dumps(assessment)
            )
        
        return assessment
    
    # ============================================================================
    # TRADE RISK ASSESSMENT
    # ============================================================================
    
    async def assess_trade_risk(
        self,
        requirement_id: UUID,
        availability_id: UUID,
        trade_quantity: Decimal,
        trade_price: Decimal,
        user_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess bilateral risk for a proposed trade.
        
        Args:
            requirement_id: Requirement UUID
            availability_id: Availability UUID
            trade_quantity: Proposed quantity
            trade_price: Proposed price per unit
            user_id: User performing assessment
            idempotency_key: Optional idempotency key
            
        Returns:
            Bilateral risk assessment
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        # Get requirement and availability
        req_stmt = select(Requirement).where(Requirement.id == requirement_id)
        avail_stmt = select(Availability).where(Availability.id == availability_id)
        
        req_result = await self.db.execute(req_stmt)
        avail_result = await self.db.execute(avail_stmt)
        
        requirement = req_result.scalar_one_or_none()
        availability = avail_result.scalar_one_or_none()
        
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        if not availability:
            raise ValueError(f"Availability {availability_id} not found")
        
        # Get buyer and seller data
        buyer_data = await self._get_buyer_data(requirement.buyer_partner_id)
        seller_data = await self._get_seller_data(availability.seller_id)
        
        # Perform bilateral risk assessment
        assessment = await self.risk_engine.assess_trade_risk(
            requirement=requirement,
            availability=availability,
            trade_quantity=trade_quantity,
            trade_price=trade_price,
            buyer_data=buyer_data,
            seller_data=seller_data,
            user_id=user_id
        )
        
        # Broadcast if high risk
        if assessment["overall_status"] == "FAIL" and self.ws_manager:
            await self._broadcast_trade_risk_alert(
                requirement_id=requirement_id,
                availability_id=availability_id,
                assessment=assessment
            )
        
        # Emit event to outbox
        await self.outbox_repo.add_event(
            event_type="risk.trade_assessed",
            aggregate_type="trade",
            aggregate_id=f"{requirement_id}_{availability_id}",
            payload={
                "requirement_id": str(requirement_id),
                "availability_id": str(availability_id),
                "trade_quantity": str(trade_quantity),
                "trade_price": str(trade_price),
                "assessment": assessment,
                "user_id": str(user_id),
                "overall_status": assessment["overall_status"]
            },
            user_id=user_id
        )
        
        # Commit changes
        await self.db.commit()
        
        # Cache for idempotency
        if idempotency_key and self.redis:
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,
                json.dumps(assessment)
            )
        
        return assessment
    
    # ============================================================================
    # COUNTERPARTY RISK ASSESSMENT
    # ============================================================================
    
    async def assess_partner_risk(
        self,
        partner_id: UUID,
        partner_type: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess overall counterparty risk for a partner.
        
        Args:
            partner_id: Partner UUID
            partner_type: "BUYER" or "SELLER"
            idempotency_key: Optional idempotency key
            
        Returns:
            Counterparty risk assessment
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        if partner_type == "BUYER":
            partner_data = await self._get_buyer_data(partner_id)
            performance_score = partner_data["payment_performance"]
        else:
            partner_data = await self._get_seller_data(partner_id)
            performance_score = partner_data["delivery_performance"]
        
        # Get trade history
        trade_history = await self._get_trade_history(partner_id)
        
        # Perform assessment
        assessment = await self.risk_engine.assess_counterparty_risk(
            partner_id=partner_id,
            partner_type=partner_type,
            credit_limit=partner_data["credit_limit"],
            current_exposure=partner_data["current_exposure"],
            rating=partner_data["rating"],
            performance_score=performance_score,
            trade_history_count=trade_history["total_trades"],
            dispute_count=trade_history["dispute_count"],
            average_trade_value=trade_history["average_trade_value"]
        )
        
        # Emit event
        await self.outbox_repo.add_event(
            event_type="risk.partner_assessed",
            aggregate_type="partner",
            aggregate_id=str(partner_id),
            payload={
                "partner_id": str(partner_id),
                "partner_type": partner_type,
                "assessment": assessment
            }
        )
        
        # Commit
        await self.db.commit()
        
        # Cache for idempotency
        if idempotency_key and self.redis:
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,
                json.dumps(assessment)
            )
        
        return assessment
    
    # ============================================================================
    # EXPOSURE MONITORING
    # ============================================================================
    
    async def monitor_partner_exposure(
        self,
        partner_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monitor partner exposure and generate alerts.
        
        Args:
            partner_id: Partner UUID
            idempotency_key: Optional idempotency key
            
        Returns:
            Exposure monitoring result with alerts
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        # Get partner data
        partner_data = await self._get_buyer_data(partner_id)
        
        # Monitor exposure
        monitoring = await self.risk_engine.monitor_exposure_limits(
            partner_id=partner_id,
            current_exposure=partner_data["current_exposure"],
            credit_limit=partner_data["credit_limit"]
        )
        
        # Broadcast alerts if RED or YELLOW
        if monitoring["alert_level"] in ["RED", "YELLOW"] and self.ws_manager:
            await self._broadcast_exposure_alert(
                partner_id=partner_id,
                monitoring=monitoring
            )
        
        # Emit event
        await self.outbox_repo.add_event(
            event_type="risk.exposure_monitored",
            aggregate_type="partner",
            aggregate_id=str(partner_id),
            payload={
                "partner_id": str(partner_id),
                "monitoring": monitoring,
                "alert_level": monitoring["alert_level"]
            }
        )
        
        # Commit
        await self.db.commit()
        
        # Cache for idempotency
        if idempotency_key and self.redis:
            await self.redis.setex(
                f"idempotency:{idempotency_key}",
                86400,
                json.dumps(monitoring)
            )
        
        return monitoring
    
    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================
    
    async def assess_all_active_requirements(
        self,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Assess risk for all active requirements."""
        stmt = select(Requirement).where(Requirement.status == "ACTIVE")
        result = await self.db.execute(stmt)
        requirements = result.scalars().all()
        
        assessments = []
        for requirement in requirements:
            try:
                assessment = await self.assess_requirement_risk(
                    requirement_id=requirement.id,
                    user_id=user_id
                )
                assessments.append({
                    "requirement_id": str(requirement.id),
                    "assessment": assessment
                })
            except Exception as e:
                assessments.append({
                    "requirement_id": str(requirement.id),
                    "error": str(e)
                })
        
        return assessments
    
    async def assess_all_active_availabilities(
        self,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Assess risk for all active availabilities."""
        stmt = select(Availability).where(Availability.status == "ACTIVE")
        result = await self.db.execute(stmt)
        availabilities = result.scalars().all()
        
        assessments = []
        for availability in availabilities:
            try:
                assessment = await self.assess_availability_risk(
                    availability_id=availability.id,
                    user_id=user_id
                )
                assessments.append({
                    "availability_id": str(availability.id),
                    "assessment": assessment
                })
            except Exception as e:
                assessments.append({
                    "availability_id": str(availability.id),
                    "error": str(e)
                })
        
        return assessments
    
    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================
    
    async def _get_buyer_data(self, buyer_id: UUID) -> Dict[str, Any]:
        """Get buyer credit and performance data."""
        # TODO: Integrate with Partner module
        # For now, return mock data
        return {
            "credit_limit": Decimal("100000000"),
            "current_exposure": Decimal("20000000"),
            "rating": Decimal("4.2"),
            "payment_performance": 85
        }
    
    async def _get_seller_data(self, seller_id: UUID) -> Dict[str, Any]:
        """Get seller credit and performance data."""
        # TODO: Integrate with Partner module
        # For now, return mock data
        return {
            "credit_limit": Decimal("50000000"),
            "current_exposure": Decimal("10000000"),
            "rating": Decimal("4.5"),
            "delivery_performance": 92
        }
    
    async def _get_trade_history(self, partner_id: UUID) -> Dict[str, Any]:
        """Get partner trade history."""
        # TODO: Integrate with Trade module
        # For now, return mock data
        return {
            "total_trades": 150,
            "dispute_count": 3,
            "average_trade_value": Decimal("500000")
        }
    
    async def _broadcast_risk_alert(
        self,
        entity_type: str,
        entity_id: UUID,
        assessment: Dict[str, Any]
    ) -> None:
        """Broadcast risk alert via WebSocket."""
        if not self.ws_manager:
            return
        
        message_data = {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "risk_status": assessment["status"],
            "risk_score": assessment["score"],
            "risk_factors": assessment["risk_factors"],
            "timestamp": assessment["assessment_timestamp"]
        }
        
        # Broadcast to risk alerts channel
        await self.ws_manager.broadcast_to_channel(
            channel="risk:alerts",
            event="risk.alert",
            data=message_data
        )
    
    async def _broadcast_trade_risk_alert(
        self,
        requirement_id: UUID,
        availability_id: UUID,
        assessment: Dict[str, Any]
    ) -> None:
        """Broadcast trade risk alert via WebSocket."""
        if not self.ws_manager:
            return
        
        message_data = {
            "requirement_id": str(requirement_id),
            "availability_id": str(availability_id),
            "overall_status": assessment["overall_status"],
            "combined_score": assessment["combined_score"],
            "internal_trade_blocked": assessment["internal_trade_blocked"],
            "recommended_action": assessment["recommended_action"],
            "timestamp": assessment["assessment_timestamp"]
        }
        
        # Broadcast to trade risk channel
        await self.ws_manager.broadcast_to_channel(
            channel="risk:trade_alerts",
            event="risk.trade_alert",
            data=message_data
        )
    
    async def _broadcast_exposure_alert(
        self,
        partner_id: UUID,
        monitoring: Dict[str, Any]
    ) -> None:
        """Broadcast exposure alert via WebSocket."""
        if not self.ws_manager:
            return
        
        message_data = {
            "partner_id": str(partner_id),
            "alert_level": monitoring["alert_level"],
            "utilization_percent": monitoring["utilization_percent"],
            "alerts": monitoring["alerts"],
            "timestamp": monitoring["checked_at"]
        }
        
        # Broadcast to exposure alerts channel
        await self.ws_manager.broadcast_to_channel(
            channel="risk:exposure_alerts",
            event="risk.exposure_alert",
            data=message_data
        )
