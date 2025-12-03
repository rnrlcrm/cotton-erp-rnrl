"""
Matching Engine Validators with AI Integration

Validates match eligibility with comprehensive checks including:
- Hard requirement validation (commodity, quantity, price)
- Risk compliance (PASS/WARN/FAIL semantics)
- Internal branch trading prevention
- AI price alert validation
- AI confidence threshold checks
- Party status verification

Part of GLOBAL MULTI-COMMODITY Platform - works for Cotton, Gold, Wheat, Rice, Oil, ANY commodity.

Dependencies:
    - Requirement/Availability models
    - RiskEngine for compliance checks
    - MatchingConfig for thresholds
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.risk.risk_engine import RiskEngine


@dataclass
class ValidationResult:
    """Result of match validation with detailed failure reasons"""
    is_valid: bool
    reasons: List[str]
    warnings: List[str]
    ai_alerts: List[str]  # AI-specific alerts
    risk_status: Optional[str] = None
    risk_score: Optional[int] = None
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation passed with warnings"""
        return self.is_valid and len(self.warnings) > 0
    
    @property
    def has_ai_alerts(self) -> bool:
        """Check if AI flagged any concerns"""
        return len(self.ai_alerts) > 0


class MatchValidator:
    """
    Validates match eligibility with multi-layer checks
    
    Validation Order (fail-fast):
    1. Hard Requirements (commodity, quantity, price, status)
    2. AI Price Alerts (if enabled)
    3. AI Confidence Thresholds (if configured)
    4. Risk Compliance (PASS/WARN/FAIL)
    5. Internal Branch Trading (if blocked)
    6. Business Rules (expiry, location already checked)
    
    All 13 user iterations incorporated.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        risk_engine: RiskEngine,
        config: MatchingConfig
    ):
        self.db = db
        self.risk_engine = risk_engine
        self.config = config
    
    async def validate_match_eligibility(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> ValidationResult:
        """
        Comprehensive match validation with AI integration
        
        Args:
            requirement: Buyer requirement
            availability: Seller availability
        
        Returns:
            ValidationResult with is_valid flag and detailed reasons
        
        Note:
            Location filter assumed to have run BEFORE this (location-first architecture)
        """
        reasons: List[str] = []
        warnings: List[str] = []
        ai_alerts: List[str] = []
        
        # ====================================================================
        # STEP 1: Hard Requirements (FAIL-FAST)
        # ====================================================================
        
        # 1.1 Commodity Match
        if requirement.commodity_id != availability.commodity_id:
            reasons.append(
                f"Commodity mismatch: requirement wants {requirement.commodity_id}, "
                f"availability offers {availability.commodity_id}"
            )
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # 1.2 Quantity Sufficient (at least MIN_PARTIAL_QUANTITY_PERCENT)
        min_quantity = requirement.min_quantity or (
            requirement.preferred_quantity * Decimal('0.10')  # 10% default
        )
        if availability.available_quantity < min_quantity:
            reasons.append(
                f"Insufficient quantity: availability {availability.available_quantity}, "
                f"minimum required {min_quantity}"
            )
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # 1.3 Price Within Budget
        if availability.asking_price > requirement.max_budget:
            reasons.append(
                f"Price exceeds budget: asking {availability.asking_price}, "
                f"max budget {requirement.max_budget}"
            )
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # 1.4 Both Parties Active
        if requirement.status != "ACTIVE":
            reasons.append(f"Requirement not active: {requirement.status}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        if availability.status != "ACTIVE":
            reasons.append(f"Availability not active: {availability.status}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # 1.5 Not Expired
        now = datetime.utcnow()
        if requirement.expiry_date and requirement.expiry_date < now:
            reasons.append(f"Requirement expired: {requirement.expiry_date}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        if availability.expiry_date and availability.expiry_date < now:
            reasons.append(f"Availability expired: {availability.expiry_date}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # ====================================================================
        # STEP 1.6: 🚀 CAPABILITY VALIDATION (CDPS)
        # Validate both parties have required trading capabilities
        # ====================================================================
        from backend.modules.trade_desk.validators.capability_validator import TradeCapabilityValidator
        
        capability_validator = TradeCapabilityValidator(self.db)
        
        # Get countries (TODO: fetch from actual location data)
        buyer_delivery_country = "India"  # TODO: Get from requirement delivery location
        seller_location_country = "India"  # TODO: Get from availability location
        
        parties_valid, capability_error = await capability_validator.validate_trade_parties(
            buyer_id=requirement.buyer_id,
            seller_id=availability.seller_id,
            buyer_delivery_country=buyer_delivery_country,
            seller_location_country=seller_location_country,
            raise_exception=False
        )
        
        if not parties_valid:
            reasons.append(f"Capability violation: {capability_error}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # ====================================================================
        # STEP 1.7: 🚀 INSIDER TRADING PREVENTION (CDPS)
        # Block trading between related entities
        # ====================================================================
        from backend.core.validators.insider_trading import InsiderTradingValidator
        
        insider_validator = InsiderTradingValidator(self.db)
        
        insider_valid, insider_error = await insider_validator.validate_trade_parties(
            buyer_id=requirement.buyer_id,
            seller_id=availability.seller_id,
            raise_exception=False
        )
        
        if not insider_valid:
            reasons.append(f"Insider trading blocked: {insider_error}")
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts
            )
        
        # ====================================================================
        # STEP 2: AI Price Alert Validation (ENHANCEMENT #7)
        # ====================================================================
        
        if requirement.ai_price_alert_flag:
            ai_alerts.append(
                f"AI Price Alert: {requirement.ai_alert_reason or 'Unrealistic budget detected'}"
            )
            warnings.append(
                "AI flagged budget as potentially unrealistic - match may fail negotiation"
            )
        
        # ====================================================================
        # STEP 3: AI Confidence Threshold (ENHANCEMENT #7)
        # ====================================================================
        
        if requirement.ai_confidence_score is not None:
            min_confidence = getattr(
                self.config,
                'MIN_AI_CONFIDENCE_THRESHOLD',
                60  # Default 60%
            )
            if requirement.ai_confidence_score < min_confidence:
                ai_alerts.append(
                    f"Low AI confidence: {requirement.ai_confidence_score}% "
                    f"(threshold {min_confidence}%)"
                )
                warnings.append(
                    f"AI confidence below threshold - match quality uncertain"
                )
        
        # ====================================================================
        # STEP 4: AI Suggested Price Comparison (ENHANCEMENT #7)
        # ====================================================================
        
        if requirement.ai_suggested_max_price is not None:
            if availability.asking_price > requirement.ai_suggested_max_price:
                price_diff_pct = (
                    (availability.asking_price - requirement.ai_suggested_max_price) 
                    / requirement.ai_suggested_max_price * 100
                )
                ai_alerts.append(
                    f"Asking price {price_diff_pct:.1f}% above AI-suggested "
                    f"fair market price ({requirement.ai_suggested_max_price})"
                )
                warnings.append(
                    "Price above AI market recommendation - negotiation may be needed"
                )
        
        # ====================================================================
        # STEP 5: AI Recommended Sellers Check (ENHANCEMENT #7)
        # ====================================================================
        
        if requirement.ai_recommended_sellers:
            # Check if this seller is in AI pre-scored suggestions
            recommended_seller_ids = [
                UUID(rec.get('seller_id')) 
                for rec in requirement.ai_recommended_sellers.get('recommendations', [])
                if rec.get('seller_id')
            ]
            
            if availability.party_id in recommended_seller_ids:
                warnings.append(
                    "Seller is in AI pre-scored recommendations (high quality match)"
                )
            else:
                ai_alerts.append(
                    "Seller not in AI pre-scored recommendations - may be suboptimal match"
                )
        
        # ====================================================================
        # STEP 6: Risk Compliance (CRITICAL - ITERATION #3)
        # ====================================================================
        
        risk_result = await self.validate_risk_compliance(
            requirement,
            availability
        )
        
        if not risk_result.is_valid:
            # Risk FAIL blocks match entirely
            reasons.extend(risk_result.reasons)
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=warnings,
                ai_alerts=ai_alerts,
                risk_status=risk_result.risk_status,
                risk_score=risk_result.risk_score
            )
        
        # Risk PASS or WARN - add warnings if WARN
        if risk_result.has_warnings:
            warnings.extend(risk_result.warnings)
        
        # ====================================================================
        # STEP 7: Internal Branch Trading Check (ITERATION #8)
        # ====================================================================
        
        if self._is_internal_branch_trading_blocked():
            if self._is_same_organization(requirement, availability):
                reasons.append(
                    "Internal branch trading blocked: buyer and seller from same organization"
                )
                return ValidationResult(
                    is_valid=False,
                    reasons=reasons,
                    warnings=warnings,
                    ai_alerts=ai_alerts,
                    risk_status=risk_result.risk_status,
                    risk_score=risk_result.risk_score
                )
        
        # ====================================================================
        # ALL VALIDATIONS PASSED
        # ====================================================================
        
        return ValidationResult(
            is_valid=True,
            reasons=[],
            warnings=warnings,
            ai_alerts=ai_alerts,
            risk_status=risk_result.risk_status,
            risk_score=risk_result.risk_score
        )
    
    async def validate_risk_compliance(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> ValidationResult:
        """
        Validate risk assessment with PASS/WARN/FAIL semantics
        
        Risk Status Logic (ITERATION #3):
        - PASS (≥80): risk_score=1.0, no penalty, no warnings
        - WARN (60-79): risk_score=0.5, 10% global penalty, warning added
        - FAIL (<60): Block match entirely (is_valid=False)
        
        Args:
            requirement: Buyer requirement
            availability: Seller availability
        
        Returns:
            ValidationResult with risk status and warnings
        """
        reasons: List[str] = []
        warnings: List[str] = []
        
        # Call risk engine for assessment
        risk_assessment = await self.risk_engine.assess_trade_risk(
            requirement_id=requirement.id,
            availability_id=availability.id,
            buyer_id=requirement.party_id,
            seller_id=availability.party_id,
            commodity_id=requirement.commodity_id,
            quantity=min(
                requirement.preferred_quantity,
                availability.available_quantity
            ),
            price=availability.asking_price
        )
        
        risk_status = risk_assessment.get('risk_status', 'UNKNOWN')
        risk_score = risk_assessment.get('risk_score', 0)
        
        # FAIL: Block match entirely
        if risk_status == "FAIL" or risk_score < 60:
            reasons.append(
                f"Risk assessment FAILED: score {risk_score}/100 "
                f"(minimum 60 required)"
            )
            risk_flags = risk_assessment.get('risk_flags', [])
            if risk_flags:
                reasons.append(f"Risk flags: {', '.join(risk_flags)}")
            
            return ValidationResult(
                is_valid=False,
                reasons=reasons,
                warnings=[],
                ai_alerts=[],
                risk_status=risk_status,
                risk_score=risk_score
            )
        
        # WARN: Allow match with penalty
        if risk_status == "WARN" or (60 <= risk_score < 80):
            warnings.append(
                f"Risk assessment WARNING: score {risk_score}/100 "
                f"(10% penalty will apply to final match score)"
            )
            risk_flags = risk_assessment.get('risk_flags', [])
            if risk_flags:
                warnings.append(f"Risk concerns: {', '.join(risk_flags)}")
            
            return ValidationResult(
                is_valid=True,
                reasons=[],
                warnings=warnings,
                ai_alerts=[],
                risk_status=risk_status,
                risk_score=risk_score
            )
        
        # PASS: No warnings or penalties
        return ValidationResult(
            is_valid=True,
            reasons=[],
            warnings=[],
            ai_alerts=[],
            risk_status=risk_status,
            risk_score=risk_score
        )
    
    def _is_internal_branch_trading_blocked(self) -> bool:
        """
        Check if internal branch trading is blocked in configuration
        
        Returns:
            True if internal branch trading should be blocked
        """
        return getattr(
            self.config,
            'BLOCK_INTERNAL_BRANCH_TRADING',
            True  # Default to blocking for safety
        )
    
    def _is_same_organization(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> bool:
        """
        Check if buyer and seller belong to same organization
        
        Args:
            requirement: Buyer requirement
            availability: Seller availability
        
        Returns:
            True if same organization (internal branch trading)
        
        Note:
            Assumes party model has organization_id field
            TODO: Update when party model structure confirmed
        """
        # Check if both parties loaded (eager loading)
        if not hasattr(requirement, 'buyer') or not hasattr(availability, 'seller'):
            # Can't determine without party relationship loaded
            return False
        
        buyer_org_id = getattr(requirement.buyer, 'organization_id', None)
        seller_org_id = getattr(availability.seller, 'organization_id', None)
        
        if buyer_org_id is None or seller_org_id is None:
            return False
        
        return buyer_org_id == seller_org_id
    
    async def validate_quantity_availability(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> dict:
        """
        Validate if seller has sufficient quantity.
        
        Returns:
            Dict with is_available, available_quantity, requested_quantity, etc.
        """
        buyer_min = requirement.min_quantity
        buyer_preferred = requirement.preferred_quantity or buyer_min
        seller_available = availability.available_quantity or Decimal("0.000")
        
        # Check minimum partial threshold (10%)
        min_partial_pct = self.config.MIN_PARTIAL_QUANTITY_PERCENT
        min_acceptable = buyer_min * Decimal(str(min_partial_pct))
        
        can_fulfill_full = seller_available >= buyer_preferred
        meets_minimum = seller_available >= min_acceptable
        
        return {
            "is_available": meets_minimum,
            "available_quantity": seller_available,
            "requested_quantity": buyer_preferred,
            "can_fulfill_full": can_fulfill_full,
            "partial_match": seller_available < buyer_preferred and seller_available >= buyer_min,
            "below_minimum": seller_available < min_acceptable
        }
    
    async def validate_internal_branch_trading(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> dict:
        """
        Validate internal branch trading prevention.
        
        Returns:
            Dict with is_allowed, is_internal_trade, blocked_reason
        """
        # Check if blocking is enabled
        if not self._is_internal_branch_trading_blocked():
            return {
                "is_allowed": True,
                "is_internal_trade": False,
                "blocked_reason": None
            }
        
        # Check if same branch
        buyer_branch_id = getattr(requirement.buyer_partner, 'branch_id', None) if hasattr(requirement, 'buyer_partner') else None
        seller_branch_id = availability.seller_branch_id
        
        if buyer_branch_id is None or seller_branch_id is None:
            # Can't determine, allow by default
            return {
                "is_allowed": True,
                "is_internal_trade": False,
                "blocked_reason": None
            }
        
        is_same_branch = buyer_branch_id == seller_branch_id
        
        if is_same_branch:
            return {
                "is_allowed": False,
                "is_internal_trade": True,
                "blocked_reason": "Internal branch trading blocked by configuration"
            }
        
        return {
            "is_allowed": True,
            "is_internal_trade": False,
            "blocked_reason": None
        }
    
    async def validate_ai_requirements(
        self,
        availability: Availability
    ) -> dict:
        """
        Validate AI confidence requirements.
        
        Returns:
            Dict with meets_threshold, confidence_score, boost_eligible
        """
        ai_confidence = availability.ai_confidence_score
        
        if ai_confidence is None:
            return {
                "meets_threshold": False,
                "confidence_score": None,
                "boost_eligible": False
            }
        
        # Convert to float if Decimal
        confidence_value = float(ai_confidence) if isinstance(ai_confidence, Decimal) else ai_confidence
        
        # Check against threshold (60% default)
        min_threshold = self.config.AI_MIN_CONFIDENCE_THRESHOLD / 100.0
        meets_threshold = confidence_value >= min_threshold
        
        # Boost eligible if confidence >= 80%
        boost_eligible = confidence_value >= 0.8
        
        return {
            "meets_threshold": meets_threshold,
            "confidence_score": ai_confidence,
            "boost_eligible": boost_eligible
        }
    
    async def validate_batch_eligibility(
        self,
        requirement: Requirement,
        availabilities: List[Availability]
    ) -> List[Tuple[Availability, ValidationResult]]:
        """
        Validate multiple availabilities against one requirement
        
        Optimized for batch processing:
        - Pre-filters obvious failures
        - Reuses requirement validation checks
        - Returns only valid or interesting matches
        
        Args:
            requirement: Single buyer requirement
            availabilities: List of potential seller availabilities
        
        Returns:
            List of (availability, validation_result) tuples
            Only includes matches that passed or have warnings
        """
        results: List[Tuple[Availability, ValidationResult]] = []
        
        for availability in availabilities:
            validation = await self.validate_match_eligibility(
                requirement,
                availability
            )
            
            # Include if valid OR has interesting warnings/AI alerts
            if validation.is_valid or validation.has_warnings or validation.has_ai_alerts:
                results.append((availability, validation))
        
        return results


# ========================================================================
# CONFIGURATION ADDITIONS FOR AI
# ========================================================================

# Add to MatchingConfig class (for reference):
"""
class MatchingConfig:
    # ... existing config ...
    
    # AI-specific thresholds
    MIN_AI_CONFIDENCE_THRESHOLD: int = 60  # Minimum AI confidence %
    ENABLE_AI_PRICE_ALERTS: bool = True    # Honor AI price alerts
    ENABLE_AI_RECOMMENDATIONS: bool = True  # Use AI pre-scored sellers
    BLOCK_INTERNAL_BRANCH_TRADING: bool = True  # Prevent circular trades
"""
