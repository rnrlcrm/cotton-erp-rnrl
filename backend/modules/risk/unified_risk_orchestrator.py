"""
Unified Risk Orchestrator - Coordinates RuleEngine + MLRiskEngine

Architecture:
    UnifiedRiskOrchestrator (Entry Point)
    ├── RuleEngine (Deterministic, NO ML) - TIER 1
    │   ├── National Compliance (GST, PAN, IEC)
    │   ├── International Compliance (Sanctions, Export/Import License)
    │   ├── Circular Trading Detection
    │   ├── Wash Trading Prevention
    │   └── Party Links Detection
    │
    ├── MLRiskEngine (AI Predictions, Advisory) - TIER 2
    │   ├── Payment Default Predictor
    │   ├── Credit Limit Optimizer
    │   └── Fraud Detector
    │
    ├── FusionLayer (Combines outputs: 30% ML + 70% Rules)
    └── CircuitBreaker (ML failure handling)

Execution Flow:
    1. TIER 1: RuleEngine executes FIRST (<200ms, instant blocking)
    2. If blocked → Return immediately (ML never runs)
    3. If passed → TIER 2: MLRiskEngine executes (200-500ms, scoring)
    4. FusionLayer combines: 30% ML + 70% Rules
    5. Return unified result
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.risk.risk_engine import RiskEngine
from backend.modules.risk.ml_risk_engine import MLRiskEngine


class CircuitBreaker:
    """
    Circuit breaker to handle ML engine failures gracefully.
    
    If ML engine fails, system continues with rules-only mode.
    """
    
    def __init__(self):
        self.failure_count = 0
        self.max_failures = 5
        self.is_open = False
    
    def record_success(self):
        """Record successful ML execution."""
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        """Record ML execution failure."""
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.is_open = True
    
    def should_skip_ml(self) -> bool:
        """Check if ML should be skipped due to circuit breaker."""
        return self.is_open


class FusionLayer:
    """
    Fusion layer that combines RuleEngine and MLRiskEngine outputs.
    
    Weighting:
    - Rules: 70% (deterministic, regulatory compliance)
    - ML: 30% (predictive, risk insights)
    """
    
    RULE_WEIGHT = 0.70
    ML_WEIGHT = 0.30
    
    @staticmethod
    def combine_scores(
        rule_score: int,
        ml_score: Optional[int],
        rule_blocked: bool
    ) -> Dict[str, Any]:
        """
        Combine rule and ML scores into unified result.
        
        Args:
            rule_score: Score from RuleEngine (0-100)
            ml_score: Score from MLRiskEngine (0-100), None if ML failed
            rule_blocked: Whether RuleEngine blocked the transaction
            
        Returns:
            {
                "final_score": int,
                "rule_contribution": int,
                "ml_contribution": int,
                "ml_available": bool
            }
        """
        if rule_blocked:
            # If rules block, ML contribution is irrelevant
            return {
                "final_score": 0,
                "rule_contribution": rule_score,
                "ml_contribution": 0,
                "ml_available": False,
                "reason": "Blocked by RuleEngine (compliance violation)"
            }
        
        if ml_score is None:
            # ML failed - use rules only
            return {
                "final_score": rule_score,
                "rule_contribution": rule_score,
                "ml_contribution": 0,
                "ml_available": False,
                "reason": "ML unavailable, using rules-only score"
            }
        
        # Both available - combine with weights
        rule_contribution = int(rule_score * FusionLayer.RULE_WEIGHT)
        ml_contribution = int(ml_score * FusionLayer.ML_WEIGHT)
        final_score = rule_contribution + ml_contribution
        
        return {
            "final_score": final_score,
            "rule_contribution": rule_contribution,
            "ml_contribution": ml_contribution,
            "ml_available": True,
            "reason": f"Combined score: {FusionLayer.RULE_WEIGHT*100}% rules + {FusionLayer.ML_WEIGHT*100}% ML"
        }


class UnifiedRiskOrchestrator:
    """
    Unified Risk Orchestrator - Entry point for all risk assessments.
    
    Coordinates RuleEngine (TIER 1) and MLRiskEngine (TIER 2).
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RiskEngine(db)
        self.ml_engine = MLRiskEngine(db)
        self.circuit_breaker = CircuitBreaker()
        self.fusion_layer = FusionLayer()
    
    async def comprehensive_check(
        self,
        partner_id: UUID,
        transaction_type: str,  # "BUY" or "SELL"
        commodity_id: UUID,
        amount: Decimal,
        counterparty_id: Optional[UUID] = None,
        
        # Geographic details
        buyer_country: str = "IN",  # Default India
        seller_country: str = "IN",
        buyer_state: Optional[str] = None,
        seller_state: Optional[str] = None,
        
        # International trade details
        proposed_currency: Optional[str] = None,
        payment_term_id: Optional[UUID] = None,
        quality_standard: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        COMPLETE trade compliance check: National + International + Internal rules + ML.
        
        Execution Order:
        1. TIER 1: RuleEngine (Deterministic checks)
           - Sanctions compliance (international only)
           - GST/PAN validation (national only)
           - Export/Import license (international only)
           - Circular trading, wash trading, party links
        2. If blocked by rules → Return immediately (ML never runs)
        3. TIER 2: MLRiskEngine (Predictive scoring)
           - Payment default prediction
           - Fraud detection
           - Credit risk scoring
        4. FusionLayer combines both scores
        
        Args:
            partner_id: Partner creating the transaction
            transaction_type: "BUY" or "SELL"
            commodity_id: Commodity ID
            amount: Transaction amount
            counterparty_id: Optional counterparty
            buyer_country: Buyer's country code (ISO 2-letter)
            seller_country: Seller's country code
            buyer_state: Buyer's state (for India domestic)
            seller_state: Seller's state (for India domestic)
            proposed_currency: Currency for international trades
            payment_term_id: Payment terms
            quality_standard: Quality standard for international
            
        Returns:
            {
                "status": "PASS" | "WARN" | "FAIL",
                "final_score": int (0-100),
                "blocked": bool,
                "blocking_reason": str (if blocked),
                "tier_1_rule_engine": {...},
                "tier_2_ml_engine": {...},
                "fusion_result": {...},
                "compliance_checks": {...}
            }
        """
        
        # ====================================================================
        # STEP 1: Determine if National or International
        # ====================================================================
        is_international = buyer_country != seller_country
        
        compliance_checks = {
            "trade_type": "INTERNATIONAL" if is_international else "NATIONAL",
            "national_checks": [],
            "international_checks": [],
            "internal_checks": []
        }
        
        # ====================================================================
        # TIER 1: RULE ENGINE (Deterministic, Instant Blocking)
        # ====================================================================
        
        tier_1_start = datetime.utcnow()
        
        # --------------------------------------------------------------------
        # INTERNATIONAL: Sanctions Check FIRST (Highest Priority)
        # --------------------------------------------------------------------
        if is_international:
            sanctions_check = await self.rule_engine.check_sanctions_compliance(
                commodity_id=commodity_id,
                buyer_country=buyer_country,
                seller_country=seller_country
            )
            compliance_checks["international_checks"].append({
                "check": "sanctions_compliance",
                **sanctions_check
            })
            
            # INSTANT BLOCK if sanctioned
            if sanctions_check.get("blocked"):
                return self._create_blocked_response(
                    reason=sanctions_check["reason"],
                    violation_type=sanctions_check["violation_type"],
                    tier="SANCTIONS_COMPLIANCE",
                    compliance_checks=compliance_checks,
                    tier_1_duration_ms=self._duration_ms(tier_1_start)
                )
            
            # Export/Import License Check
            license_check = await self.rule_engine.check_export_import_license(
                commodity_id=commodity_id,
                seller_partner_id=partner_id if transaction_type == "SELL" else counterparty_id,
                buyer_partner_id=counterparty_id if transaction_type == "SELL" else partner_id,
                buyer_country=buyer_country,
                seller_country=seller_country,
                transaction_value=amount
            )
            compliance_checks["international_checks"].append({
                "check": "export_import_license",
                **license_check
            })
            
            # INSTANT BLOCK if license missing/invalid
            if license_check.get("blocked"):
                return self._create_blocked_response(
                    reason=license_check["reason"],
                    violation_type=license_check["violation_type"],
                    tier="EXPORT_IMPORT_LICENSE",
                    compliance_checks=compliance_checks,
                    tier_1_duration_ms=self._duration_ms(tier_1_start)
                )
        
        else:
            # --------------------------------------------------------------------
            # NATIONAL (India Domestic): GST + PAN Checks
            # --------------------------------------------------------------------
            
            # GST Certificate Check (BLOCKING)
            if buyer_state and seller_state:
                gst_check = await self.rule_engine.check_gst_registration(
                    partner_id=partner_id,
                    transaction_type=transaction_type,
                    buyer_state=buyer_state,
                    seller_state=seller_state
                )
                compliance_checks["national_checks"].append({
                    "check": "gst_registration",
                    **gst_check
                })
                
                if gst_check.get("blocked"):
                    return self._create_blocked_response(
                        reason=gst_check["reason"],
                        violation_type=gst_check["violation_type"],
                        tier="GST_COMPLIANCE",
                        compliance_checks=compliance_checks,
                        tier_1_duration_ms=self._duration_ms(tier_1_start)
                    )
            
            # PAN Card Check (BLOCKING)
            pan_check = await self.rule_engine.check_pan_card(
                partner_id=partner_id
            )
            compliance_checks["national_checks"].append({
                "check": "pan_card",
                **pan_check
            })
            
            if pan_check.get("blocked"):
                return self._create_blocked_response(
                    reason=pan_check["reason"],
                    violation_type=pan_check["violation_type"],
                    tier="PAN_COMPLIANCE",
                    compliance_checks=compliance_checks,
                    tier_1_duration_ms=self._duration_ms(tier_1_start)
                )
        
        # --------------------------------------------------------------------
        # INTERNAL TRADING RULES (Applies to BOTH National + International)
        # --------------------------------------------------------------------
        
        # Circular Trading Check
        circular = await self.rule_engine.check_circular_trading_settlement_based(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type
        )
        compliance_checks["internal_checks"].append({
            "check": "circular_trading",
            **circular
        })
        
        if circular.get("blocked"):
            return self._create_blocked_response(
                reason=circular["reason"],
                violation_type="CIRCULAR_TRADING",
                tier="INTERNAL_RULES",
                compliance_checks=compliance_checks,
                tier_1_duration_ms=self._duration_ms(tier_1_start)
            )
        
        # Wash Trading Check
        wash = await self.rule_engine.check_wash_trading(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type,
            trade_date=datetime.now().date()
        )
        compliance_checks["internal_checks"].append({
            "check": "wash_trading",
            **wash
        })
        
        if wash.get("blocked"):
            return self._create_blocked_response(
                reason=wash["reason"],
                violation_type="WASH_TRADING",
                tier="INTERNAL_RULES",
                compliance_checks=compliance_checks,
                tier_1_duration_ms=self._duration_ms(tier_1_start)
            )
        
        # Party Links Check (BOTH National + International)
        if counterparty_id:
            party_links = await self.rule_engine.check_party_links(
                partner_id=partner_id,
                counterparty_id=counterparty_id
            )
            compliance_checks["internal_checks"].append({
                "check": "party_links",
                **party_links
            })
            
            if party_links.get("blocked"):
                return self._create_blocked_response(
                    reason=party_links["reason"],
                    violation_type="PARTY_LINKS",
                    tier="INTERNAL_RULES",
                    compliance_checks=compliance_checks,
                    tier_1_duration_ms=self._duration_ms(tier_1_start),
                    note="Party links check applies to both national and international trades"
                )
        
        tier_1_duration = self._duration_ms(tier_1_start)
        
        # --------------------------------------------------------------------
        # TIER 1 PASSED - Calculate rule score
        # --------------------------------------------------------------------
        rule_score = 85  # Base score if all rules passed
        
        tier_1_result = {
            "status": "PASS",
            "score": rule_score,
            "duration_ms": tier_1_duration,
            "checks_passed": len(compliance_checks["national_checks"]) + 
                           len(compliance_checks["international_checks"]) + 
                           len(compliance_checks["internal_checks"])
        }
        
        # ====================================================================
        # TIER 2: ML RISK ENGINE (Predictive Scoring)
        # ====================================================================
        
        ml_score = None
        tier_2_result = None
        
        if self.ml_engine and not self.circuit_breaker.should_skip_ml():
            tier_2_start = datetime.utcnow()
            
            try:
                # Call real ML engine
                ml_result = await self.ml_engine.predict_risk(
                    entity_type=transaction_type,
                    partner_id=partner_id,
                    commodity_id=commodity_id,
                    trade_value=amount,
                    counterparty_id=counterparty_id,
                    trade_quantity=None,  # TODO: Pass if available
                    trade_price=None  # TODO: Pass if available
                )
                
                ml_score = ml_result.get("ml_score")
                tier_2_result = {
                    "status": "PASS",
                    "score": ml_score,
                    "duration_ms": self._duration_ms(tier_2_start),
                    "predictions": ml_result.get("predictions"),
                    "recommendation": ml_result.get("recommendation")
                }
                
                self.circuit_breaker.record_success()
                
            except Exception as e:
                # ML failed - circuit breaker kicks in
                self.circuit_breaker.record_failure()
                tier_2_result = {
                    "status": "FAILED",
                    "error": str(e),
                    "duration_ms": self._duration_ms(tier_2_start),
                    "note": "ML engine unavailable, using rules-only mode"
                }
        else:
            tier_2_result = {
                "status": "SKIPPED",
                "reason": "ML engine not available or circuit breaker open"
            }
        
        # ====================================================================
        # FUSION LAYER: Combine Rule + ML Scores
        # ====================================================================
        
        fusion_result = self.fusion_layer.combine_scores(
            rule_score=rule_score,
            ml_score=ml_score,
            rule_blocked=False
        )
        
        final_score = fusion_result["final_score"]
        
        # Determine final status
        if final_score >= 80:
            status = "PASS"
        elif final_score >= 60:
            status = "WARN"
        else:
            status = "FAIL"
        
        # ====================================================================
        # RETURN UNIFIED RESULT
        # ====================================================================
        
        return {
            "status": status,
            "final_score": final_score,
            "blocked": False,
            "tier_1_rule_engine": tier_1_result,
            "tier_2_ml_engine": tier_2_result,
            "fusion_result": fusion_result,
            "compliance_checks": compliance_checks,
            "trade_type": compliance_checks["trade_type"],
            "checked_at": datetime.utcnow().isoformat(),
            "total_duration_ms": tier_1_duration + (tier_2_result.get("duration_ms", 0) if tier_2_result else 0)
        }
    
    def _create_blocked_response(
        self,
        reason: str,
        violation_type: str,
        tier: str,
        compliance_checks: Dict,
        tier_1_duration_ms: int,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized blocked response."""
        response = {
            "status": "FAIL",
            "final_score": 0,
            "blocked": True,
            "blocking_reason": reason,
            "violation_type": violation_type,
            "blocked_at_tier": tier,
            "tier_1_rule_engine": {
                "status": "BLOCKED",
                "duration_ms": tier_1_duration_ms
            },
            "tier_2_ml_engine": {
                "status": "SKIPPED",
                "reason": "Blocked by TIER 1 rules, ML never executed"
            },
            "compliance_checks": compliance_checks,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if note:
            response["note"] = note
        
        return response
    
    @staticmethod
    def _duration_ms(start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)
