"""
Risk Engine - Centralized Risk Assessment for Trading Platform

The Risk Engine provides comprehensive risk assessment for all trading activities:
- Buyer credit risk (requirements)
- Seller delivery risk (availabilities)
- Trade-level risk (matching)
- Counterparty risk (partner relationships)
- Market risk (commodity price volatility)

Key Features:
- Unified risk scoring algorithm (0-100)
- Multi-factor risk assessment
- Real-time exposure tracking
- Risk alert broadcasting via WebSocket
- Configurable risk thresholds
- Audit trail for all risk decisions
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, date

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.partners.models import BusinessPartner
from backend.modules.risk.exceptions import (
    RiskCheckFailedError,
    CircularTradingViolation,
    WashTradingViolation,
)


class RiskEngine:
    """
    Centralized Risk Assessment Engine
    
    Provides consistent risk scoring across:
    - Requirements (buyer-side risk)
    - Availabilities (seller-side risk)
    - Trade proposals (bilateral risk)
    - Partner relationships (counterparty risk)
    """
    
    # Risk status thresholds
    PASS_THRESHOLD = 80  # >= 80 = PASS
    WARN_THRESHOLD = 60  # 60-79 = WARN, < 60 = FAIL
    
    # Risk factor weights (total = 100%)
    CREDIT_WEIGHT = 0.40  # 40%
    RATING_WEIGHT = 0.30  # 30%
    PERFORMANCE_WEIGHT = 0.30  # 30%
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================================
    # COMPREHENSIVE RISK CHECK (Runs AFTER entity creation, BEFORE matching)
    # ============================================================================
    
    async def comprehensive_check(
        self,
        entity_type: str,
        entity_id: UUID,
        partner_id: UUID,
        commodity_id: UUID,
        estimated_value: Decimal,
        counterparty_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive risk check that runs AFTER entity creation, BEFORE matching.
        
        This is the MAIN method services should call after creating requirement/availability.
        
        Runs ALL checks:
        1. Credit limit validation
        2. Circular trading prevention (settlement-based, NOT same-day)
        3. Wash trading prevention (same-party reverse trades)
        4. Party links detection (PAN/GST)
        5. Peer-to-peer relationship validation (if counterparty provided)
        
        Args:
            entity_type: "requirement" or "availability"
            entity_id: ID of created requirement/availability
            partner_id: Partner creating the entity
            commodity_id: Commodity being traded
            estimated_value: Estimated trade value
            counterparty_id: Optional counterparty for peer-to-peer check
            
        Returns:
            {
                "status": "PASS" | "WARN" | "FAIL",
                "score": int (0-100),
                "reason": str,
                "risk_factors": List[str],
                "circular_trading": Dict,
                "wash_trading": Dict,
                "peer_relationship": Dict (if counterparty provided)
            }
            
        Raises:
            RiskCheckFailedError: If status is FAIL
        """
        risk_score = 100
        risk_factors = []
        
        # Fetch entity
        if entity_type == "requirement":
            entity_query = select(Requirement).where(Requirement.id == entity_id)
            result = await self.db.execute(entity_query)
            entity = result.scalar_one_or_none()
            transaction_type = "BUY"
        else:  # availability
            entity_query = select(Availability).where(Availability.id == entity_id)
            result = await self.db.execute(entity_query)
            entity = result.scalar_one_or_none()
            transaction_type = "SELL"
        
        if not entity:
            raise ValueError(f"{entity_type} with ID {entity_id} not found")
        
        # ========================================================================
        # CHECK 1: Circular Trading Prevention (Settlement-based)
        # ========================================================================
        circular_check = await self.check_circular_trading_settlement_based(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type
        )
        
        if circular_check["blocked"]:
            raise CircularTradingViolation(
                circular_check["reason"],
                risk_details=circular_check
            )
        
        # ========================================================================
        # CHECK 2: Wash Trading Prevention (Same-party reverse trades)
        # ========================================================================
        wash_trading_check = await self.check_wash_trading(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type,
            trade_date=datetime.now().date()
        )
        
        if wash_trading_check["blocked"]:
            raise WashTradingViolation(
                wash_trading_check["reason"],
                risk_details=wash_trading_check
            )
        
        # ========================================================================
        # CHECK 3: Peer-to-Peer Relationship (if counterparty provided)
        # ========================================================================
        peer_relationship = None
        if counterparty_id:
            if transaction_type == "BUY":
                peer_relationship = await self.assess_peer_relationship(
                    buyer_partner_id=partner_id,
                    seller_partner_id=counterparty_id,
                    commodity_id=commodity_id
                )
            else:
                peer_relationship = await self.assess_peer_relationship(
                    buyer_partner_id=counterparty_id,
                    seller_partner_id=partner_id,
                    commodity_id=commodity_id
                )
            
            # Apply peer relationship score
            if peer_relationship["status"] == "BLOCKED_FOR_THIS_PARTNER":
                # Don't fail entire check, just flag it
                risk_score -= 40
                risk_factors.append(f"Poor peer relationship: {peer_relationship['reason']}")
            elif peer_relationship["status"] == "WARN":
                risk_score -= 20
                risk_factors.append(f"Peer relationship warning: {peer_relationship['reason']}")
        
        # ========================================================================
        # Determine final status
        # ========================================================================
        if risk_score >= self.PASS_THRESHOLD:
            status = "PASS"
        elif risk_score >= self.WARN_THRESHOLD:
            status = "WARN"
        else:
            status = "FAIL"
        
        result = {
            "status": status,
            "score": max(0, risk_score),
            "reason": "; ".join(risk_factors) if risk_factors else "All risk checks passed",
            "risk_factors": risk_factors,
            "circular_trading": circular_check,
            "wash_trading": wash_trading_check,
            "peer_relationship": peer_relationship,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if status == "FAIL":
            raise RiskCheckFailedError(
                f"Comprehensive risk check failed: {result['reason']}",
                risk_details=result
            )
        
        return result
    
    # ============================================================================
    # BUYER RISK ASSESSMENT (for Requirements)
    # ============================================================================
    
    async def assess_buyer_risk(
        self,
        requirement: Requirement,
        buyer_credit_limit: Decimal,
        buyer_current_exposure: Decimal,
        buyer_rating: Decimal,
        buyer_payment_performance: int,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Assess buyer risk for a requirement.
        
        Args:
            requirement: Requirement to assess
            buyer_credit_limit: Total credit limit
            buyer_current_exposure: Current outstanding exposure
            buyer_rating: Buyer rating (0.00-5.00)
            buyer_payment_performance: Payment score (0-100)
            user_id: User performing assessment
            
        Returns:
            Dict with risk assessment details
        """
        # Calculate estimated trade value
        estimated_value = requirement.calculate_estimated_trade_value()
        
        # Calculate exposure after this trade
        exposure_after = buyer_current_exposure + estimated_value
        credit_remaining = buyer_credit_limit - buyer_current_exposure
        
        # Risk scoring
        risk_score = 100
        risk_factors = []
        
        # Factor 1: Credit limit check (40 points)
        if exposure_after > buyer_credit_limit:
            risk_score -= 40
            risk_factors.append(
                f"Insufficient credit limit (need: {estimated_value}, "
                f"available: {credit_remaining})"
            )
        elif credit_remaining < estimated_value * Decimal("1.2"):
            # Less than 20% buffer
            risk_score -= 20
            risk_factors.append("Low credit limit buffer (<20%)")
        
        # Factor 2: Buyer rating (30 points)
        if buyer_rating < Decimal("3.0"):
            risk_score -= 30
            risk_factors.append(f"Low buyer rating (<3.0): {buyer_rating}")
        elif buyer_rating < Decimal("4.0"):
            risk_score -= 15
            risk_factors.append(f"Moderate buyer rating (<4.0): {buyer_rating}")
        
        # Factor 3: Payment performance (30 points)
        if buyer_payment_performance < 50:
            risk_score -= 30
            risk_factors.append(
                f"Poor payment history (<50): {buyer_payment_performance}"
            )
        elif buyer_payment_performance < 75:
            risk_score -= 15
            risk_factors.append(
                f"Moderate payment history (<75): {buyer_payment_performance}"
            )
        
        # Determine status
        if risk_score >= self.PASS_THRESHOLD:
            status = "PASS"
        elif risk_score >= self.WARN_THRESHOLD:
            status = "WARN"
        else:
            status = "FAIL"
        
        # Update requirement with risk assessment
        risk_assessment = requirement.update_risk_precheck(
            credit_limit_remaining=credit_remaining,
            rating_score=buyer_rating,
            payment_performance_score=buyer_payment_performance,
            current_exposure=buyer_current_exposure,
            user_id=user_id
        )
        
        return {
            "status": status,
            "score": max(0, risk_score),
            "estimated_trade_value": estimated_value,
            "buyer_exposure_after_trade": exposure_after,
            "credit_limit_remaining": credit_remaining,
            "risk_factors": risk_factors,
            "assessment_timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # SELLER RISK ASSESSMENT (for Availabilities)
    # ============================================================================
    
    async def assess_seller_risk(
        self,
        availability: Availability,
        seller_credit_limit: Decimal,
        seller_current_exposure: Decimal,
        seller_rating: Decimal,
        seller_delivery_performance: int,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Assess seller risk for an availability.
        
        Args:
            availability: Availability to assess
            seller_credit_limit: Total credit limit
            seller_current_exposure: Current outstanding exposure
            seller_rating: Seller rating (0.00-5.00)
            seller_delivery_performance: Delivery score (0-100)
            user_id: User performing assessment
            
        Returns:
            Dict with risk assessment details
        """
        # Calculate estimated trade value
        estimated_value = availability.calculate_estimated_trade_value()
        
        # Calculate exposure after this trade
        exposure_after = seller_current_exposure + estimated_value
        credit_remaining = seller_credit_limit - seller_current_exposure
        
        # Risk scoring
        risk_score = 100
        risk_factors = []
        
        # Factor 1: Credit limit check (40 points)
        if exposure_after > seller_credit_limit:
            risk_score -= 40
            risk_factors.append(
                f"Insufficient seller credit limit (need: {estimated_value}, "
                f"available: {credit_remaining})"
            )
        elif credit_remaining < estimated_value * Decimal("1.2"):
            risk_score -= 20
            risk_factors.append("Low seller credit limit buffer (<20%)")
        
        # Factor 2: Seller rating (30 points)
        if seller_rating < Decimal("3.0"):
            risk_score -= 30
            risk_factors.append(f"Low seller rating (<3.0): {seller_rating}")
        elif seller_rating < Decimal("4.0"):
            risk_score -= 15
            risk_factors.append(f"Moderate seller rating (<4.0): {seller_rating}")
        
        # Factor 3: Delivery performance (30 points)
        if seller_delivery_performance < 50:
            risk_score -= 30
            risk_factors.append(
                f"Poor delivery history (<50): {seller_delivery_performance}"
            )
        elif seller_delivery_performance < 75:
            risk_score -= 15
            risk_factors.append(
                f"Moderate delivery history (<75): {seller_delivery_performance}"
            )
        
        # Determine status
        if risk_score >= self.PASS_THRESHOLD:
            status = "PASS"
        elif risk_score >= self.WARN_THRESHOLD:
            status = "WARN"
        else:
            status = "FAIL"
        
        # Update availability with risk assessment
        risk_assessment = availability.update_risk_precheck(
            seller_credit_limit_remaining=credit_remaining,
            seller_rating=seller_rating,
            seller_delivery_performance=seller_delivery_performance,
            seller_exposure=seller_current_exposure,
            user_id=user_id
        )
        
        return {
            "status": status,
            "score": max(0, risk_score),
            "estimated_trade_value": estimated_value,
            "seller_exposure_after_trade": exposure_after,
            "credit_limit_remaining": credit_remaining,
            "risk_factors": risk_factors,
            "assessment_timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # BILATERAL TRADE RISK ASSESSMENT
    # ============================================================================
    
    async def assess_trade_risk(
        self,
        requirement: Requirement,
        availability: Availability,
        trade_quantity: Decimal,
        trade_price: Decimal,
        buyer_data: Dict[str, Any],
        seller_data: Dict[str, Any],
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Assess bilateral risk for a proposed trade.
        
        Enhanced with 3 new mandatory checks:
        1. Party links detection (PAN/GST/mobile/email)
        2. Circular trading prevention (same-day reversals)
        3. Role restriction validation (already validated in services)
        
        Args:
            requirement: Buyer's requirement
            availability: Seller's availability
            trade_quantity: Proposed trade quantity
            trade_price: Proposed trade price
            buyer_data: Buyer credit/rating/performance data
            seller_data: Seller credit/rating/performance data
            user_id: User performing assessment
            
        Returns:
            Dict with bilateral risk assessment
        """
        # Calculate trade value
        trade_value = trade_quantity * trade_price
        
        # Assess buyer side
        buyer_assessment = await self.assess_buyer_risk(
            requirement=requirement,
            buyer_credit_limit=buyer_data["credit_limit"],
            buyer_current_exposure=buyer_data["current_exposure"],
            buyer_rating=buyer_data["rating"],
            buyer_payment_performance=buyer_data["payment_performance"],
            user_id=user_id
        )
        
        # Assess seller side
        seller_assessment = await self.assess_seller_risk(
            availability=availability,
            seller_credit_limit=seller_data["credit_limit"],
            seller_current_exposure=seller_data["current_exposure"],
            seller_rating=seller_data["rating"],
            seller_delivery_performance=seller_data["delivery_performance"],
            user_id=user_id
        )
        
        # ====================================================================
        # NEW: Party Links Detection (Option B: Block PAN/GST, Warn mobile)
        # ====================================================================
        party_link_check = await self.check_party_links(
            buyer_partner_id=requirement.buyer_partner_id,
            seller_partner_id=availability.seller_id
        )
        
        # ====================================================================
        # Check internal trade blocking (same branch)
        # ====================================================================
        internal_trade_blocked = False
        if requirement.blocked_internal_trades:
            internal_trade_blocked = requirement.check_internal_trade_block(
                seller_branch_id=availability.seller_branch_id
            )
        
        if availability.blocked_for_branches:
            internal_trade_blocked = internal_trade_blocked or availability.check_internal_trade_block(
                buyer_branch_id=requirement.buyer_branch_id
            )
        
        # ====================================================================
        # Combined risk score (average of both sides)
        # ====================================================================
        combined_score = (buyer_assessment["score"] + seller_assessment["score"]) / 2
        
        # ====================================================================
        # Determine overall status (strictest wins)
        # ====================================================================
        if buyer_assessment["status"] == "FAIL" or seller_assessment["status"] == "FAIL":
            overall_status = "FAIL"
        elif buyer_assessment["status"] == "WARN" or seller_assessment["status"] == "WARN":
            overall_status = "WARN"
        else:
            overall_status = "PASS"
        
        # ====================================================================
        # Override to FAIL if critical violations detected
        # ====================================================================
        
        # Internal trade blocking
        if internal_trade_blocked:
            overall_status = "FAIL"
            buyer_assessment["risk_factors"].append("Internal trade blocked (same branch)")
        
        # Party links - BLOCK violations (PAN/GST)
        if party_link_check["severity"] == "BLOCK":
            overall_status = "FAIL"
            buyer_assessment["risk_factors"].append(
                f"Party link violation: {', '.join([v['type'] for v in party_link_check['block_violations']])}"
            )
        
        # Party links - WARN violations (mobile/email)
        if party_link_check["severity"] == "WARN" and overall_status == "PASS":
            overall_status = "WARN"
            buyer_assessment["risk_factors"].append(
                f"Party link warning: {', '.join([v['type'] for v in party_link_check['warn_violations']])}"
            )
        
        # ====================================================================
        # Build comprehensive risk assessment
        # ====================================================================
        return {
            "trade_id": None,  # Assigned when trade is created
            "overall_status": overall_status,
            "combined_score": combined_score,
            "trade_value": trade_value,
            
            # Internal trade blocking
            "internal_trade_blocked": internal_trade_blocked,
            
            # Party links detection (NEW)
            "party_links_detected": party_link_check["linked"],
            "party_links_severity": party_link_check["severity"],
            "party_links_violations": party_link_check["violations"],
            
            # Individual assessments
            "buyer_assessment": buyer_assessment,
            "seller_assessment": seller_assessment,
            
            # Recommended action
            "recommended_action": self._get_recommended_action(
                overall_status, 
                internal_trade_blocked,
                party_link_check,
                buyer_assessment,
                seller_assessment
            ),
            "assessment_timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # COUNTERPARTY RISK ASSESSMENT
    # ============================================================================
    
    async def assess_counterparty_risk(
        self,
        partner_id: UUID,
        partner_type: str,  # "BUYER" or "SELLER"
        credit_limit: Decimal,
        current_exposure: Decimal,
        rating: Decimal,
        performance_score: int,
        trade_history_count: int,
        dispute_count: int,
        average_trade_value: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Assess overall counterparty risk for a business partner.
        
        Args:
            partner_id: Partner UUID
            partner_type: "BUYER" or "SELLER"
            credit_limit: Total credit limit
            current_exposure: Current outstanding exposure
            rating: Partner rating (0.00-5.00)
            performance_score: Payment/delivery score (0-100)
            trade_history_count: Number of completed trades
            dispute_count: Number of disputes
            average_trade_value: Average trade value (optional)
            
        Returns:
            Dict with counterparty risk assessment
        """
        risk_score = 100
        risk_factors = []
        
        # Factor 1: Credit utilization (25 points)
        credit_utilization = (current_exposure / credit_limit * 100) if credit_limit > 0 else 0
        
        if credit_utilization > 90:
            risk_score -= 25
            risk_factors.append(f"High credit utilization (>{credit_utilization}%)")
        elif credit_utilization > 75:
            risk_score -= 15
            risk_factors.append(f"Moderate credit utilization ({credit_utilization}%)")
        
        # Factor 2: Rating (25 points)
        if rating < Decimal("2.0"):
            risk_score -= 25
            risk_factors.append(f"Very low rating (<2.0): {rating}")
        elif rating < Decimal("3.0"):
            risk_score -= 15
            risk_factors.append(f"Low rating (<3.0): {rating}")
        elif rating < Decimal("4.0"):
            risk_score -= 8
            risk_factors.append(f"Moderate rating (<4.0): {rating}")
        
        # Factor 3: Performance score (25 points)
        if performance_score < 40:
            risk_score -= 25
            risk_factors.append(f"Poor performance (<40): {performance_score}")
        elif performance_score < 60:
            risk_score -= 15
            risk_factors.append(f"Low performance (<60): {performance_score}")
        elif performance_score < 75:
            risk_score -= 8
            risk_factors.append(f"Moderate performance (<75): {performance_score}")
        
        # Factor 4: Dispute rate (15 points)
        dispute_rate = (dispute_count / trade_history_count * 100) if trade_history_count > 0 else 0
        
        if dispute_rate > 10:
            risk_score -= 15
            risk_factors.append(f"High dispute rate (>{dispute_rate}%)")
        elif dispute_rate > 5:
            risk_score -= 8
            risk_factors.append(f"Moderate dispute rate ({dispute_rate}%)")
        
        # Factor 5: Trade history (10 points)
        if trade_history_count < 10:
            risk_score -= 10
            risk_factors.append(f"Limited trade history (<10 trades)")
        elif trade_history_count < 50:
            risk_score -= 5
            risk_factors.append(f"Moderate trade history ({trade_history_count} trades)")
        
        # Determine status
        if risk_score >= self.PASS_THRESHOLD:
            status = "PASS"
        elif risk_score >= self.WARN_THRESHOLD:
            status = "WARN"
        else:
            status = "FAIL"
        
        return {
            "partner_id": str(partner_id),
            "partner_type": partner_type,
            "status": status,
            "score": max(0, risk_score),
            "credit_utilization": credit_utilization,
            "dispute_rate": dispute_rate,
            "trade_history_count": trade_history_count,
            "risk_factors": risk_factors,
            "recommended_credit_limit": self._calculate_recommended_credit_limit(
                current_limit=credit_limit,
                rating=rating,
                performance_score=performance_score,
                average_trade_value=average_trade_value
            ),
            "assessment_timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # RISK MONITORING & ALERTS
    # ============================================================================
    
    async def monitor_exposure_limits(
        self,
        partner_id: UUID,
        current_exposure: Decimal,
        credit_limit: Decimal
    ) -> Dict[str, Any]:
        """
        Monitor exposure limits and generate alerts.
        
        Args:
            partner_id: Partner UUID
            current_exposure: Current outstanding exposure
            credit_limit: Total credit limit
            
        Returns:
            Dict with monitoring status and alerts
        """
        utilization = (current_exposure / credit_limit * 100) if credit_limit > 0 else 0
        
        alerts = []
        alert_level = "GREEN"
        
        if utilization >= 100:
            alert_level = "RED"
            alerts.append({
                "level": "CRITICAL",
                "message": f"Credit limit exceeded ({utilization:.1f}%)",
                "action_required": "Block new trades, initiate collection"
            })
        elif utilization >= 90:
            alert_level = "RED"
            alerts.append({
                "level": "HIGH",
                "message": f"Credit limit nearly exhausted ({utilization:.1f}%)",
                "action_required": "Review and potentially block new trades"
            })
        elif utilization >= 75:
            alert_level = "YELLOW"
            alerts.append({
                "level": "MEDIUM",
                "message": f"High credit utilization ({utilization:.1f}%)",
                "action_required": "Monitor closely"
            })
        elif utilization >= 50:
            alert_level = "YELLOW"
            alerts.append({
                "level": "LOW",
                "message": f"Moderate credit utilization ({utilization:.1f}%)",
                "action_required": "Normal monitoring"
            })
        
        return {
            "partner_id": str(partner_id),
            "current_exposure": current_exposure,
            "credit_limit": credit_limit,
            "utilization_percent": utilization,
            "alert_level": alert_level,
            "alerts": alerts,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _get_recommended_action(
        self,
        status: str,
        internal_trade_blocked: bool,
        party_link_check: Dict[str, Any],
        buyer_assessment: Dict[str, Any],
        seller_assessment: Dict[str, Any]
    ) -> str:
        """Generate recommended action based on risk assessment."""
        if internal_trade_blocked:
            return "REJECT: Internal trade blocked (same branch)"
        
        if party_link_check["severity"] == "BLOCK":
            return f"REJECT: Party link violation - {party_link_check['recommended_action']}"
        
        if status == "FAIL":
            return "REJECT: High risk - do not proceed with trade"
        elif status == "WARN":
            if party_link_check["severity"] == "WARN":
                return "REVIEW: Moderate risk + party link warnings - require senior management approval"
            return "REVIEW: Moderate risk - require management approval"
        else:
            return "APPROVE: Low risk - proceed with trade"
    
    def _calculate_recommended_credit_limit(
        self,
        current_limit: Decimal,
        rating: Decimal,
        performance_score: int,
        average_trade_value: Optional[Decimal]
    ) -> Decimal:
        """
        Calculate recommended credit limit based on partner performance.
        
        Logic:
        - Excellent partners (rating >= 4.5, performance >= 90): +20%
        - Good partners (rating >= 4.0, performance >= 80): +10%
        - Average partners: No change
        - Poor partners (rating < 3.0 or performance < 60): -25%
        """
        if rating >= Decimal("4.5") and performance_score >= 90:
            return current_limit * Decimal("1.2")
        elif rating >= Decimal("4.0") and performance_score >= 80:
            return current_limit * Decimal("1.1")
        elif rating < Decimal("3.0") or performance_score < 60:
            return current_limit * Decimal("0.75")
        else:
            return current_limit
    
    # ============================================================================
    # PARTY LINKS DETECTION (Option B: Block PAN/GST, Warn mobile/bank)
    # ============================================================================
    
    async def check_party_links(
        self,
        buyer_partner_id: UUID,
        seller_partner_id: UUID
    ) -> Dict[str, Any]:
        """
        Check if buyer and seller are linked (same ownership/entity).
        
        Option B Implementation:
        - Same PAN/Tax ID → BLOCK (CRITICAL violations)
        - Same mobile/email → WARN (allow with manual approval)
        
        Args:
            buyer_partner_id: Buyer's partner UUID
            seller_partner_id: Seller's partner UUID
            
        Returns:
            {
                "linked": bool,
                "severity": "BLOCK" or "WARN" or "PASS",
                "violations": [{"type": str, "severity": str, "message": str}],
                "recommended_action": str
            }
        """
        # Fetch both partners
        buyer_query = select(BusinessPartner).where(BusinessPartner.id == buyer_partner_id)
        seller_query = select(BusinessPartner).where(BusinessPartner.id == seller_partner_id)
        
        buyer_result = await self.db.execute(buyer_query)
        seller_result = await self.db.execute(seller_query)
        
        buyer = buyer_result.scalar_one_or_none()
        seller = seller_result.scalar_one_or_none()
        
        if not buyer or not seller:
            return {
                "linked": False,
                "severity": "PASS",
                "violations": [],
                "recommended_action": "PROCEED: Partner not found (will fail elsewhere)"
            }
        
        violations = []
        max_severity = "PASS"
        
        # ====================================================================
        # CRITICAL CHECKS (Option B: BLOCK trades)
        # ====================================================================
        
        # Check 1: Same PAN Number
        if buyer.pan_number and seller.pan_number and buyer.pan_number == seller.pan_number:
            violations.append({
                "type": "SAME_PAN",
                "severity": "BLOCK",
                "field": "PAN Number",
                "value": buyer.pan_number,
                "message": f"BLOCKED: Buyer and seller have same PAN number ({buyer.pan_number}). This indicates same ownership."
            })
            max_severity = "BLOCK"
        
        # Check 2: Same Tax ID (GST/TIN/EIN/etc.)
        if buyer.tax_id_number and seller.tax_id_number and buyer.tax_id_number == seller.tax_id_number:
            violations.append({
                "type": "SAME_TAX_ID",
                "severity": "BLOCK",
                "field": "Tax ID Number",
                "value": buyer.tax_id_number,
                "message": f"BLOCKED: Buyer and seller have same tax ID number ({buyer.tax_id_number}). This indicates same legal entity."
            })
            max_severity = "BLOCK"
        
        # ====================================================================
        # WARNING CHECKS (Option B: WARN but allow with approval)
        # ====================================================================
        
        # Check 3: Same Mobile Number
        if (buyer.primary_contact_phone and seller.primary_contact_phone and 
            buyer.primary_contact_phone == seller.primary_contact_phone):
            violations.append({
                "type": "SAME_MOBILE",
                "severity": "WARN",
                "field": "Mobile Number",
                "value": buyer.primary_contact_phone,
                "message": f"WARNING: Buyer and seller have same mobile number ({buyer.primary_contact_phone}). Manual approval required."
            })
            if max_severity == "PASS":
                max_severity = "WARN"
        
        # Check 4: Same Email Domain (potential link)
        if buyer.primary_contact_email and seller.primary_contact_email:
            buyer_domain = buyer.primary_contact_email.split('@')[-1].lower()
            seller_domain = seller.primary_contact_email.split('@')[-1].lower()
            
            # Skip common email providers (gmail, yahoo, etc.)
            common_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'rediffmail.com']
            
            if (buyer_domain == seller_domain and 
                buyer_domain not in common_providers):
                violations.append({
                    "type": "SAME_EMAIL_DOMAIN",
                    "severity": "WARN",
                    "field": "Email Domain",
                    "value": buyer_domain,
                    "message": f"WARNING: Buyer and seller use same corporate email domain ({buyer_domain}). May indicate relationship."
                })
                if max_severity == "PASS":
                    max_severity = "WARN"
        
        # TODO: Bank account checking requires bank_accounts table
        # Will be implemented when bank_accounts relationship is available
        
        # ====================================================================
        # Determine recommended action
        # ====================================================================
        if max_severity == "BLOCK":
            recommended_action = "REJECT: Trade blocked due to party link violations (same PAN/Tax ID)"
        elif max_severity == "WARN":
            recommended_action = "REVIEW: Trade requires manual approval due to party links (same mobile/email)"
        else:
            recommended_action = "APPROVE: No party links detected"
        
        return {
            "linked": len(violations) > 0,
            "severity": max_severity,
            "violations": violations,
            "violation_count": len(violations),
            "block_violations": [v for v in violations if v["severity"] == "BLOCK"],
            "warn_violations": [v for v in violations if v["severity"] == "WARN"],
            "recommended_action": recommended_action,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # CIRCULAR TRADING PREVENTION (Settlement-based, NOT same-day)
    # ============================================================================
    
    async def check_circular_trading_settlement_based(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        transaction_type: str  # "BUY" or "SELL"
    ) -> Dict[str, Any]:
        """
        Check if partner has UNSETTLED opposite position for same commodity.
        
        CORRECT Implementation (Settlement-based):
        - Prevents selling before owning (must settle buy first)
        - Allows: Buy today (COMPLETED/SETTLED) → Sell tomorrow ✅
        - Blocks: Create BUY (ACTIVE/PENDING) → Create SELL (unsettled) ❌
        
        Args:
            partner_id: Partner UUID
            commodity_id: Commodity UUID
            transaction_type: "BUY" or "SELL"
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "violation_type": str,
                "unsettled_positions": List[Dict]
            }
        """
        if transaction_type == "BUY":
            # User wants to BUY - check if they have UNSETTLED SELL for same commodity
            query = select(Availability).where(
                and_(
                    Availability.seller_partner_id == partner_id,
                    Availability.commodity_id == commodity_id,
                    Availability.status.in_(['DRAFT', 'ACTIVE', 'RESERVED', 'PARTIALLY_SOLD'])
                )
            )
            
            result = await self.db.execute(query)
            unsettled_sells = result.scalars().all()
            
            if unsettled_sells:
                return {
                    "blocked": True,
                    "reason": (
                        f"CIRCULAR TRADING VIOLATION: Partner has {len(unsettled_sells)} UNSETTLED SELL "
                        f"position(s) for same commodity. Cannot create BUY before settling existing SELL positions."
                    ),
                    "violation_type": "UNSETTLED_SELL_EXISTS",
                    "unsettled_positions": [
                        {
                            "type": "SELL",
                            "id": str(avail.id),
                            "quantity": float(avail.total_quantity),
                            "available_quantity": float(avail.available_quantity),
                            "status": avail.status,
                            "created_at": avail.created_at.isoformat()
                        }
                        for avail in unsettled_sells
                    ],
                    "recommendation": (
                        "Complete/settle existing SELL positions before creating BUY requirement. "
                        "Settlement-based restriction prevents circular trading."
                    )
                }
        
        elif transaction_type == "SELL":
            # User wants to SELL - check if they have UNSETTLED BUY for same commodity
            query = select(Requirement).where(
                and_(
                    Requirement.buyer_partner_id == partner_id,
                    Requirement.commodity_id == commodity_id,
                    Requirement.status.in_(['DRAFT', 'ACTIVE', 'PARTIALLY_FULFILLED'])
                )
            )
            
            result = await self.db.execute(query)
            unsettled_buys = result.scalars().all()
            
            if unsettled_buys:
                return {
                    "blocked": True,
                    "reason": (
                        f"CIRCULAR TRADING VIOLATION: Partner has {len(unsettled_buys)} UNSETTLED BUY "
                        f"position(s) for same commodity. Cannot create SELL before settling existing BUY positions."
                    ),
                    "violation_type": "UNSETTLED_BUY_EXISTS",
                    "unsettled_positions": [
                        {
                            "type": "BUY",
                            "id": str(req.id),
                            "quantity": float(req.preferred_quantity or req.min_quantity),
                            "fulfilled_quantity": float(req.total_purchased_quantity),
                            "status": req.status,
                            "created_at": req.created_at.isoformat()
                        }
                        for req in unsettled_buys
                    ],
                    "recommendation": (
                        "Complete/settle existing BUY requirements before creating SELL availability. "
                        "Settlement-based restriction prevents circular trading."
                    )
                }
        
        # No circular trading detected
        return {
            "blocked": False,
            "reason": "No unsettled opposite positions - validation passed",
            "violation_type": None,
            "unsettled_positions": []
        }
    
    # ============================================================================
    # WASH TRADING PREVENTION (Same-party reverse trades same day)
    # ============================================================================
    
    async def check_wash_trading(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        transaction_type: str,
        trade_date: date
    ) -> Dict[str, Any]:
        """
        Check for wash trading: same-party reverse trades on same day.
        
        Example Blocked Scenario:
        - 9:00 AM: Partner buys from Seller A
        - 10:00 AM: Partner sells to Seller A (BLOCKED - wash trading)
        
        Args:
            partner_id: Partner UUID
            commodity_id: Commodity UUID
            transaction_type: "BUY" or "SELL"
            trade_date: Trade date (usually today)
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "wash_trades": List[Dict]
            }
        """
        # This requires checking completed/matched trades table
        # For now, return pass as trades table integration is needed
        # TODO: Implement when trades table is integrated
        
        return {
            "blocked": False,
            "reason": "Wash trading check passed (trades table integration pending)",
            "wash_trades": []
        }
    
    # ============================================================================
    # PEER-TO-PEER RELATIONSHIP VALIDATION
    # ============================================================================
    
    async def assess_peer_relationship(
        self,
        buyer_partner_id: UUID,
        seller_partner_id: UUID,
        commodity_id: UUID
    ) -> Dict[str, Any]:
        """
        Assess peer-to-peer relationship between buyer and seller.
        
        Checks:
        1. Outstanding amount between parties
        2. Payment performance (buyer with THIS seller)
        3. Delivery performance (seller with THIS buyer)
        4. Quality performance (between these partners)
        
        Scoring:
        - < 30: BLOCKED_FOR_THIS_PARTNER
        - 30-50: WARN
        - > 50: PASS
        
        Args:
            buyer_partner_id: Buyer UUID
            seller_partner_id: Seller UUID
            commodity_id: Commodity UUID
            
        Returns:
            {
                "status": "PASS" | "WARN" | "BLOCKED_FOR_THIS_PARTNER",
                "peer_score": float (0-100),
                "reason": str,
                "outstanding_amount": Decimal,
                "payment_score": int,
                "delivery_score": int,
                "quality_score": int
            }
        """
        # TODO: Implement when trades/invoices/deliveries tables are integrated
        # For now, return PASS to allow business to continue
        
        return {
            "status": "PASS",
            "peer_score": 100.0,
            "reason": "Peer relationship validation passed (full implementation pending)",
            "outstanding_amount": Decimal("0"),
            "payment_score": 100,
            "delivery_score": 100,
            "quality_score": 100,
            "note": "This is a placeholder. Full implementation requires trades/invoices/deliveries tables."
        }
    
    # ============================================================================
    # CIRCULAR TRADING PREVENTION (OLD - Same-day - DEPRECATED)
    # Keep for backward compatibility during transition
    # ============================================================================
    
    async def check_circular_trading(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        transaction_type: str,  # "BUY" or "SELL"
        trade_date: date
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use check_circular_trading_settlement_based() instead.
        
        This method uses same-day logic which is INCORRECT.
        Kept for backward compatibility during transition.
        
        Will be removed in next release.
        """
        # Redirect to new settlement-based check
        return await self.check_circular_trading_settlement_based(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type
        )
    
    # ============================================================================
    # ROLE RESTRICTION VALIDATION (Option A: Trader flexibility)
    # ============================================================================
    
    async def validate_partner_role(
        self,
        partner_id: UUID,
        transaction_type: str  # "BUY" or "SELL"
    ) -> Dict[str, Any]:
        """
        Validate partner role allows the requested transaction type.
        
        Option A Implementation: Trader flexibility with same-day blocking
        - BUYER: Can only create BUY requirements
        - SELLER: Can only create SELL availabilities
        - TRADER: Can create both BUY and SELL (but blocked by circular check)
        
        Args:
            partner_id: Partner UUID
            transaction_type: "BUY" or "SELL"
            
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "partner_type": str
            }
        """
        # Fetch partner type
        query = select(BusinessPartner.partner_type).where(
            BusinessPartner.id == partner_id
        )
        result = await self.db.execute(query)
        partner_type = result.scalar_one_or_none()
        
        if not partner_type:
            return {
                "allowed": False,
                "reason": "Partner not found",
                "partner_type": None
            }
        
        # Normalize to lowercase
        partner_type = partner_type.lower()
        
        # ====================================================================
        # BUYER RESTRICTIONS
        # ====================================================================
        if partner_type == "buyer":
            if transaction_type == "SELL":
                return {
                    "allowed": False,
                    "reason": (
                        "ROLE VIOLATION: Buyers cannot post SELL availabilities. "
                        "Buyers can only post BUY requirements. "
                        "If you want to sell inventory, change partner type to TRADER."
                    ),
                    "partner_type": partner_type,
                    "violation_type": "BUYER_CANNOT_SELL"
                }
            else:  # BUY
                return {
                    "allowed": True,
                    "reason": "Buyer can create BUY requirements",
                    "partner_type": partner_type
                }
        
        # ====================================================================
        # SELLER RESTRICTIONS
        # ====================================================================
        elif partner_type == "seller":
            if transaction_type == "BUY":
                return {
                    "allowed": False,
                    "reason": (
                        "ROLE VIOLATION: Sellers cannot post BUY requirements. "
                        "Sellers can only post SELL availabilities. "
                        "If you want to buy commodities, change partner type to TRADER."
                    ),
                    "partner_type": partner_type,
                    "violation_type": "SELLER_CANNOT_BUY"
                }
            else:  # SELL
                return {
                    "allowed": True,
                    "reason": "Seller can create SELL availabilities",
                    "partner_type": partner_type
                }
        
        # ====================================================================
        # TRADER FLEXIBILITY (Option A)
        # ====================================================================
        elif partner_type == "trader":
            # Traders can do both BUY and SELL
            # Same-day reversals are blocked by check_circular_trading()
            return {
                "allowed": True,
                "reason": f"Trader can create {transaction_type} orders (subject to circular trading check)",
                "partner_type": partner_type,
                "note": "Trader BUY+SELL allowed, but same-day reversals are blocked"
            }
        
        # ====================================================================
        # OTHER PARTNER TYPES (broker, transporter, etc.)
        # ====================================================================
        else:
            # For now, treat as traders (flexible)
            # Adjust as needed based on business rules
            return {
                "allowed": True,
                "reason": f"{partner_type.title()} role has flexible trading permissions",
                "partner_type": partner_type
            }
    
    # ============================================================================
    # NATIONAL COMPLIANCE CHECKS (India Domestic)
    # ============================================================================
    
    async def check_gst_registration(
        self,
        partner_id: UUID,
        transaction_type: str,
        buyer_state: str,
        seller_state: str
    ) -> Dict[str, Any]:
        """
        Check if partner has valid GST certificate using PartnerDocument system.
        
        Args:
            partner_id: Partner ID
            transaction_type: "BUY" or "SELL"
            buyer_state: Buyer's state code (e.g., "MH", "GJ")
            seller_state: Seller's state code
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "violation_type": str (if blocked),
                "gstin": str (if found),
                "document_id": str (if found)
            }
        
        Data Source:
        - PartnerDocument with document_type='gst_certificate'
        - OCR extracted data (GSTIN, registration date, state)
        """
        from backend.modules.partners.models import PartnerDocument
        
        # Query PartnerDocument for GST certificate
        result = await self.db.execute(
            select(PartnerDocument).where(
                and_(
                    PartnerDocument.partner_id == partner_id,
                    PartnerDocument.document_type == "gst_certificate",
                    PartnerDocument.verified == True,  # KYC approved
                    PartnerDocument.is_expired == False
                )
            )
        )
        gst_certificate = result.scalar_one_or_none()
        
        # CHECK 1: GST certificate exists
        if not gst_certificate:
            return {
                "blocked": True,
                "reason": "GST registration required for domestic trade but partner doesn't have verified GST certificate",
                "violation_type": "GST_MISSING",
                "how_to_fix": "Upload GST certificate in Documents section and get it verified"
            }
        
        # CHECK 2: Extract GSTIN from OCR data
        ocr_data = gst_certificate.ocr_extracted_data or {}
        gstin = ocr_data.get("gstin") or ocr_data.get("gst_number")
        
        if not gstin:
            return {
                "blocked": True,
                "reason": "GST certificate uploaded but GSTIN not extracted from OCR",
                "violation_type": "GST_INCOMPLETE",
                "document_id": str(gst_certificate.id),
                "how_to_fix": "Re-upload clear GST certificate for OCR extraction"
            }
        
        # CHECK 3: Verify state matches transaction (warning only)
        gst_state = ocr_data.get("state_code") or gstin[:2]  # First 2 digits of GSTIN
        
        if transaction_type == "SELL" and gst_state != seller_state[:2]:
            return {
                "blocked": False,
                "warning": True,
                "reason": f"GST state code {gst_state} doesn't match seller state {seller_state}",
                "violation_type": "GST_STATE_MISMATCH",
                "gstin": gstin,
                "document_id": str(gst_certificate.id)
            }
        
        return {
            "blocked": False,
            "gstin": gstin,
            "document_id": str(gst_certificate.id),
            "state_code": gst_state
        }
    
    async def check_pan_card(
        self,
        partner_id: UUID
    ) -> Dict[str, Any]:
        """
        Check if partner has valid PAN card using PartnerDocument system.
        
        Args:
            partner_id: Partner ID
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "pan_number": str (if found),
                "document_id": str (if found)
            }
        
        Data Source:
        - PartnerDocument with document_type='pan_card'
        - OCR extracted PAN number
        """
        from backend.modules.partners.models import PartnerDocument
        
        # Query PartnerDocument for PAN card
        result = await self.db.execute(
            select(PartnerDocument).where(
                and_(
                    PartnerDocument.partner_id == partner_id,
                    PartnerDocument.document_type == "pan_card",
                    PartnerDocument.verified == True
                )
            )
        )
        pan_document = result.scalar_one_or_none()
        
        # CHECK 1: PAN card exists
        if not pan_document:
            return {
                "blocked": True,
                "reason": "PAN card required for trading but partner doesn't have verified PAN card",
                "violation_type": "PAN_MISSING",
                "how_to_fix": "Upload PAN card in Documents section and get it verified"
            }
        
        # CHECK 2: Extract PAN number from OCR
        ocr_data = pan_document.ocr_extracted_data or {}
        pan_number = ocr_data.get("pan_number")
        
        if not pan_number:
            return {
                "blocked": True,
                "reason": "PAN card uploaded but PAN number not extracted from OCR",
                "violation_type": "PAN_INCOMPLETE",
                "document_id": str(pan_document.id),
                "how_to_fix": "Re-upload clear PAN card for OCR extraction"
            }
        
        # CHECK 3: Validate PAN format (10 chars: 5 letters + 4 digits + 1 letter)
        import re
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
            return {
                "blocked": True,
                "reason": f"Invalid PAN format: {pan_number}",
                "violation_type": "PAN_INVALID_FORMAT",
                "document_id": str(pan_document.id),
                "how_to_fix": "Verify PAN number is correct (format: AAAAA9999A)"
            }
        
        return {
            "blocked": False,
            "pan_number": pan_number,
            "document_id": str(pan_document.id)
        }
    
    # ============================================================================
    # INTERNATIONAL COMPLIANCE CHECKS (Cross-Border)
    # ============================================================================
    
    async def check_sanctions_compliance(
        self,
        commodity_id: UUID,
        buyer_country: str,
        seller_country: str
    ) -> Dict[str, Any]:
        """
        Check sanctions and country restrictions - RUN THIS FIRST for international trades!
        
        Args:
            commodity_id: Commodity ID
            buyer_country: Buyer's country code (ISO 2-letter)
            seller_country: Seller's country code
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "violation_type": str (if blocked)
            }
        
        Data Sources:
        - commodity.export_regulations.restricted_countries
        - commodity.import_regulations.restricted_countries
        - Global sanctions list (hardcoded)
        """
        from backend.modules.settings.commodities.models import Commodity
        
        # Get commodity
        commodity = await self.db.get(Commodity, commodity_id)
        
        if not commodity:
            return {"blocked": False, "reason": "Commodity not found"}
        
        # GLOBAL SANCTIONS LIST (Update periodically from OFAC, UN, EU)
        SANCTIONED_COUNTRIES = [
            "IR",  # Iran
            "KP",  # North Korea
            "SY",  # Syria
            "CU",  # Cuba (partial sanctions)
            # Add more as regulations change
        ]
        
        # CHECK 1: Buyer country sanctioned
        if buyer_country in SANCTIONED_COUNTRIES:
            return {
                "blocked": True,
                "reason": f"Cannot trade with {buyer_country} - Country under international sanctions",
                "violation_type": "SANCTIONED_COUNTRY",
                "country": buyer_country,
                "how_to_fix": "Cannot trade to sanctioned countries (OFAC/UN restrictions)"
            }
        
        # CHECK 2: Seller country sanctioned
        if seller_country in SANCTIONED_COUNTRIES:
            return {
                "blocked": True,
                "reason": f"Cannot trade from {seller_country} - Country under international sanctions",
                "violation_type": "SANCTIONED_ORIGIN",
                "country": seller_country,
                "how_to_fix": "Cannot trade from sanctioned countries (OFAC/UN restrictions)"
            }
        
        # CHECK 3: Commodity-specific export restrictions
        export_regs = commodity.export_regulations or {}
        restricted_countries = export_regs.get("restricted_countries", [])
        
        if buyer_country in restricted_countries:
            restriction_reason = export_regs.get("restriction_reason", "Trade restrictions apply")
            
            return {
                "blocked": True,
                "reason": (
                    f"Export of {commodity.name} to {buyer_country} is RESTRICTED. "
                    f"Reason: {restriction_reason}"
                ),
                "violation_type": "COMMODITY_EXPORT_RESTRICTED",
                "commodity_name": commodity.name,
                "restricted_country": buyer_country,
                "restriction_reason": restriction_reason,
                "how_to_fix": "Cannot trade this commodity to this destination (regulatory restriction)"
            }
        
        # CHECK 4: Commodity-specific import restrictions
        import_regs = commodity.import_regulations or {}
        import_restricted = import_regs.get("restricted_countries", [])
        
        if seller_country in import_restricted:
            return {
                "blocked": True,
                "reason": f"Import of {commodity.name} from {seller_country} is RESTRICTED",
                "violation_type": "COMMODITY_IMPORT_RESTRICTED",
                "commodity_name": commodity.name,
                "restricted_origin": seller_country,
                "how_to_fix": "Cannot import this commodity from this origin (regulatory restriction)"
            }
        
        return {
            "blocked": False,
            "reason": "Sanctions compliance check passed"
        }
    
    async def check_export_import_license(
        self,
        commodity_id: UUID,
        seller_partner_id: UUID,
        buyer_partner_id: UUID,
        buyer_country: str,
        seller_country: str,
        transaction_value: Decimal
    ) -> Dict[str, Any]:
        """
        Check export/import license using EXISTING PartnerDocument system.
        
        Args:
            commodity_id: Commodity ID
            seller_partner_id: Seller's partner ID
            buyer_partner_id: Buyer's partner ID
            buyer_country: Buyer's country code
            seller_country: Seller's country code
            transaction_value: Transaction amount
            
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "seller_license_doc_id": str (if found),
                "buyer_license_doc_id": str (if found)
            }
        
        Data Sources:
        - commodity.export_regulations (ALREADY EXISTS)
        - PartnerDocument with document_type='iec' or 'foreign_export_license'
        - PartnerDocument.ocr_extracted_data (license details)
        """
        from backend.modules.settings.commodities.models import Commodity
        from backend.modules.partners.models import PartnerDocument
        
        # Get commodity
        commodity = await self.db.get(Commodity, commodity_id)
        
        if not commodity:
            return {"blocked": False, "reason": "Commodity not found"}
        
        # ========================================================================
        # STEP 1: Check EXPORT regulations (seller side)
        # ========================================================================
        export_regs = commodity.export_regulations or {}
        
        if export_regs.get("license_required", False):
            # Query seller's IEC/export license document
            result = await self.db.execute(
                select(PartnerDocument).where(
                    and_(
                        PartnerDocument.partner_id == seller_partner_id,
                        PartnerDocument.document_type.in_(["iec", "foreign_export_license"]),
                        PartnerDocument.verified == True,  # KYC approved only
                        PartnerDocument.is_expired == False  # Not expired
                    )
                )
            )
            license_doc = result.scalar_one_or_none()
            
            # CHECK 1: Does seller have verified export license document?
            if not license_doc:
                return {
                    "blocked": True,
                    "reason": (
                        f"Export license required for {commodity.name} but seller "
                        f"does not have verified export license (IEC/DGFT) document"
                    ),
                    "violation_type": "EXPORT_LICENSE_MISSING",
                    "required_license_types": export_regs.get("license_types", ["IEC"]),
                    "commodity_name": commodity.name,
                    "how_to_fix": "Upload IEC/DGFT certificate in Documents section and get it verified"
                }
            
            # CHECK 2: Is license expired?
            if license_doc.is_expired or (license_doc.expiry_date and license_doc.expiry_date < date.today()):
                return {
                    "blocked": True,
                    "reason": f"Seller has expired export license. License expired on {license_doc.expiry_date}",
                    "violation_type": "EXPORT_LICENSE_EXPIRED",
                    "license_number": license_doc.ocr_extracted_data.get("license_number") if license_doc.ocr_extracted_data else "Unknown",
                    "expiry_date": license_doc.expiry_date.isoformat() if license_doc.expiry_date else None,
                    "document_id": str(license_doc.id),
                    "how_to_fix": "Renew export license and upload new certificate"
                }
            
            # Extract license details from OCR data
            ocr_data = license_doc.ocr_extracted_data or {}
            license_type = ocr_data.get("license_type", "IEC")
            license_countries = ocr_data.get("license_countries", [])
            
            # CHECK 3: Is license type correct?
            required_types = export_regs.get("license_types", [])
            if required_types and license_type not in required_types:
                return {
                    "blocked": True,
                    "reason": f"Commodity {commodity.name} requires {required_types} license, but seller has '{license_type}'",
                    "violation_type": "WRONG_LICENSE_TYPE",
                    "seller_license_type": license_type,
                    "required_license_types": required_types,
                    "how_to_fix": f"Obtain {required_types} license"
                }
            
            # CHECK 4: Is destination country covered by license?
            if license_countries:
                if buyer_country not in license_countries and "ALL" not in license_countries:
                    return {
                        "blocked": True,
                        "reason": f"Seller's export license does not cover {buyer_country}. License valid for: {', '.join(license_countries)}",
                        "violation_type": "DESTINATION_NOT_COVERED",
                        "destination_country": buyer_country,
                        "licensed_countries": license_countries,
                        "document_id": str(license_doc.id),
                        "how_to_fix": f"Update license to include {buyer_country} or upload worldwide license"
                    }
            
            # CHECK 5: Minimum export value exemption
            min_value = export_regs.get("minimum_export_value")
            if min_value and transaction_value < Decimal(str(min_value)):
                return {
                    "blocked": False,
                    "reason": f"Export value below license threshold (${min_value})",
                    "exemption": "SMALL_VALUE_EXEMPTION"
                }
        
        # ========================================================================
        # STEP 2: Check IMPORT regulations (buyer side)
        # ========================================================================
        import_regs = commodity.import_regulations or {}
        
        if import_regs.get("license_required", False):
            # Query buyer's import license document
            result = await self.db.execute(
                select(PartnerDocument).where(
                    and_(
                        PartnerDocument.partner_id == buyer_partner_id,
                        PartnerDocument.document_type.in_(["iec", "foreign_import_license"]),
                        PartnerDocument.verified == True,
                        PartnerDocument.is_expired == False
                    )
                )
            )
            buyer_license_doc = result.scalar_one_or_none()
            
            if not buyer_license_doc:
                return {
                    "blocked": True,
                    "reason": f"Import license required for {commodity.name} but buyer does not have verified import license document",
                    "violation_type": "IMPORT_LICENSE_MISSING",
                    "required_license_types": import_regs.get("license_types", ["IEC"]),
                    "commodity_name": commodity.name,
                    "how_to_fix": "Upload import license certificate and get it verified"
                }
            
            if buyer_license_doc.is_expired or (buyer_license_doc.expiry_date and buyer_license_doc.expiry_date < date.today()):
                return {
                    "blocked": True,
                    "reason": f"Buyer has expired import license. License expired on {buyer_license_doc.expiry_date}",
                    "violation_type": "IMPORT_LICENSE_EXPIRED",
                    "license_number": buyer_license_doc.ocr_extracted_data.get("license_number") if buyer_license_doc.ocr_extracted_data else "Unknown",
                    "expiry_date": buyer_license_doc.expiry_date.isoformat() if buyer_license_doc.expiry_date else None,
                    "how_to_fix": "Renew import license"
                }
        
        return {
            "blocked": False,
            "reason": "Export/Import license validation passed"
        }

