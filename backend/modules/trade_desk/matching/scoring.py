"""
Match Scoring Algorithms

Multi-factor scoring for requirement-availability matching:
1. Quality compatibility (40% weight)
2. Price competitiveness (30% weight)
3. Delivery logistics (15% weight)
4. Risk assessment (15% weight)

CRITICAL: WARN risk status applies 10% GLOBAL penalty to final score.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from math import radians, sin, cos, sqrt, atan2

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.risk.risk_engine import RiskEngine
from backend.modules.trade_desk.config.matching_config import MatchingConfig, get_matching_config

logger = logging.getLogger(__name__)


class MatchScorer:
    """
    Calculates individual score components for requirement-availability matching.
    
    All scores range from 0.0 (worst) to 1.0 (perfect).
    """
    
    def __init__(self, config: Optional[MatchingConfig] = None):
        self.config = config or get_matching_config()
    
    # ========================================================================
    # COMBINED MATCH SCORE WITH WARN PENALTY ⭐ CRITICAL
    # ========================================================================
    
    async def calculate_match_score(
        self,
        requirement: Requirement,
        availability: Availability,
        risk_engine: Optional[RiskEngine] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive match score with breakdown.
        
        CRITICAL: WARN risk status applies 10% GLOBAL penalty.
        
        Returns:
        {
            "total_score": 0.765,          # After WARN penalty if applicable
            "base_score": 0.85,            # Before WARN penalty
            "warn_penalty_applied": True,
            "warn_penalty_value": 0.10,
            "breakdown": {
                "quality_score": 0.92,
                "price_score": 0.78,
                "delivery_score": 0.88,
                "risk_score": 0.5  # WARN maps to 0.5
            },
            "pass_fail": {...},
            "risk_details": {...},
            "blocked": False  # True if FAIL
        }
        """
        # Calculate individual scores
        quality_result = self.calculate_quality_score(requirement, availability)
        price_result = self.calculate_price_score(requirement, availability)
        delivery_result = self.calculate_delivery_score(requirement, availability)
        
        # Risk check with clear WARN semantics
        if risk_engine:
            risk_result = await self.calculate_risk_score(
                requirement, availability, risk_engine
            )
            
            # Map risk status to score
            risk_status = risk_result.get("risk_status", "UNKNOWN")
            if risk_status == "PASS":
                risk_score = 1.0
                warn_penalty = 0.0
            elif risk_status == "WARN":
                risk_score = 0.5  # For the 15% risk component
                warn_penalty = self.config.RISK_WARN_GLOBAL_PENALTY  # -10% global
            else:  # FAIL
                risk_score = 0.0
                warn_penalty = 0.0
                # Match blocked - return 0 score
                return {
                    "total_score": 0.0,
                    "base_score": 0.0,
                    "warn_penalty_applied": False,
                    "warn_penalty_value": 0.0,
                    "blocked": True,
                    "risk_details": risk_result,
                    "breakdown": {},
                    "pass_fail": {}
                }
        else:
            risk_score = 1.0
            risk_result = {"risk_status": "SKIPPED"}
            warn_penalty = 0.0
        
        # Get commodity-specific weights
        commodity_code = requirement.commodity.code if requirement.commodity else "default"
        weights = self.config.get_scoring_weights(commodity_code)
        
        # Calculate base score (weighted average)
        base_score = (
            quality_result["score"] * weights["quality"] +
            price_result["score"] * weights["price"] +
            delivery_result["score"] * weights["delivery"] +
            risk_score * weights["risk"]
        )
        
        # Apply WARN penalty (global -10%)
        final_score = base_score * (1.0 - warn_penalty)
        
        # ====================================================================
        # AI RECOMMENDATION BOOST (ENHANCEMENT #7)
        # ====================================================================
        ai_boost = 0.0
        ai_recommended = False
        
        if (
            self.config.ENABLE_AI_SCORE_BOOST and 
            requirement.ai_recommended_sellers
        ):
            # Check if this seller is in AI pre-scored recommendations
            from uuid import UUID
            recommended_seller_ids = [
                UUID(rec.get('seller_id')) 
                for rec in requirement.ai_recommended_sellers.get('recommendations', [])
                if rec.get('seller_id')
            ]
            
            if availability.party_id in recommended_seller_ids:
                ai_boost = self.config.AI_RECOMMENDATION_SCORE_BOOST
                final_score = min(1.0, final_score + ai_boost)  # Cap at 1.0
                ai_recommended = True
        
        # Generate recommendations
        if final_score >= 0.9:
            recommendation = "Excellent match - proceed with confidence"
        elif final_score >= 0.75:
            recommendation = "Good match - recommended"
        elif final_score >= 0.6:
            recommendation = "Acceptable match - review details"
        else:
            recommendation = "Below threshold - not recommended"
        
        if warn_penalty > 0:
            recommendation += f" (WARN penalty applied: -{int(warn_penalty * 100)}%)"
        
        if ai_recommended:
            recommendation += f" (AI-recommended seller: +{int(ai_boost * 100)}%)"
        
        return {
            "total_score": round(final_score, 4),
            "base_score": round(base_score, 4),
            "warn_penalty_applied": warn_penalty > 0,
            "warn_penalty_value": warn_penalty,
            "ai_boost_applied": ai_boost > 0,
            "ai_boost_value": ai_boost,
            "ai_recommended": ai_recommended,
            "breakdown": {
                "quality_score": round(quality_result["score"], 4),
                "price_score": round(price_result["score"], 4),
                "delivery_score": round(delivery_result["score"], 4),
                "risk_score": round(risk_score, 4)
            },
            "pass_fail": {
                "quality_pass": quality_result["pass"],
                "price_pass": price_result["pass"],
                "delivery_pass": delivery_result["pass"],
                "risk_pass": risk_result.get("risk_status") != "FAIL"
            },
            "risk_details": risk_result,
            "recommendations": recommendation,
            "blocked": False
        }
    
    # ========================================================================
    # QUALITY SCORING (40% weight) - STRICT PARAMETER MATCHING
    # ========================================================================
    
    def calculate_quality_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Compare quality parameters with STRICT tolerances.
        
        CRITICAL: Parameters must match closely - no lenient scoring.
        
        Algorithm:
        1. For each parameter in requirement quality_params:
           - If seller value EXACTLY matches buyer's target: score = 1.0
           - If seller value within buyer's min/max range BUT not exact: score = 0.8
           - If seller value outside range: score = 0.0 (BLOCKED)
        2. ALL parameters must pass for quality_pass = True
        3. Final score = average of all parameter scores
        2. Weight each parameter by importance (if specified)
        3. Return weighted average
        
        Returns:
        {
            "score": 0.92,
            "pass": True,
            "details": {
                "param_scores": {...},
                "missing_params": []
            }
        }
        """
        # Extract quality params from JSONB
        buyer_quality = requirement.quality_params or {}
        seller_quality = availability.quality_params or {}
        
        if not buyer_quality:
            # No quality requirements - perfect match
            return {
                "score": 1.0,
                "pass": True,
                "details": {"note": "No quality requirements specified"}
            }
        
        param_scores = {}
        total_score = 0.0
        param_count = 0
        
        for param_name, param_spec in buyer_quality.items():
            if not isinstance(param_spec, dict):
                continue
            
            seller_value = seller_quality.get(param_name)
            
            if seller_value is None:
                # Seller missing this parameter - score 0
                param_scores[param_name] = {
                    "score": 0.0,
                    "reason": "Missing from seller"
                }
                param_count += 1
                continue
            
            # Extract buyer's range and preferred
            buyer_min = param_spec.get("min")
            buyer_max = param_spec.get("max")
            buyer_preferred = param_spec.get("preferred")
            
            # Calculate parameter score
            if buyer_min is not None and buyer_max is not None:
                # Range check
                if buyer_min <= seller_value <= buyer_max:
                    # Within range - base score 1.0
                    score = 1.0
                    
                    # Bonus if close to preferred
                    if buyer_preferred is not None:
                        range_size = buyer_max - buyer_min
                        if range_size > 0:
                            distance_from_preferred = abs(seller_value - buyer_preferred)
                            # Closer to preferred = higher score (up to 1.0)
                            score = 1.0 - min(distance_from_preferred / range_size, 0.5)
                    
                    param_scores[param_name] = {
                        "score": score,
                        "seller_value": seller_value,
                        "buyer_range": [buyer_min, buyer_max],
                        "in_range": True
                    }
                else:
                    # Outside range - score 0
                    param_scores[param_name] = {
                        "score": 0.0,
                        "seller_value": seller_value,
                        "buyer_range": [buyer_min, buyer_max],
                        "in_range": False
                    }
                    score = 0.0
            else:
                # No range specified - exact match or pass
                score = 1.0 if seller_value == buyer_preferred else 0.8
                param_scores[param_name] = {
                    "score": score,
                    "seller_value": seller_value
                }
            
            total_score += score
            param_count += 1
        
        # Average score
        final_score = total_score / param_count if param_count > 0 else 1.0
        
        # Pass if score >= 0.6 (configurable threshold)
        passed = final_score >= 0.6
        
        return {
            "score": final_score,
            "pass": passed,
            "details": {
                "param_scores": param_scores,
                "params_checked": param_count
            }
        }
    
    # ========================================================================
    # PRICE SCORING (30% weight) - STRICT PRICE MATCHING
    # ========================================================================
    
    def calculate_price_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Compare seller price vs buyer budget with STRICT matching.
        
        CRITICAL: If buyer specifies price, match closely. Exact price = highest score.
        
        Algorithm:
        - If price EXACTLY matches buyer's target: score = 1.0 (perfect match)
        - If price within 2% of buyer's target: score = 0.95 (excellent)
        - If price within 5% of buyer's target: score = 0.85 (good)
        - If price within 10% of buyer's target: score = 0.70 (acceptable)
        - If price <= buyer's max budget: score = 0.60 (just acceptable)
        - If price > max budget: score = 0.0 (BLOCKED)
        
        Returns:
        {
            "score": 0.95,
            "pass": True,
            "details": {
                "seller_price": 48000,
                "buyer_target": 48500,
                "buyer_max": 50000,
                "variance_percent": 1.03,
                "price_match_quality": "EXCELLENT"
            }
        }
        """
        buyer_max_budget = requirement.max_budget
        buyer_target_price = requirement.preferred_budget  # Buyer's target/ideal price
        seller_price = availability.base_price
        
        if not seller_price:
            return {
                "score": 0.0,
                "pass": False,
                "details": {"error": "Seller price not specified"}
            }
        
        if not buyer_max_budget:
            # No price constraints - perfect match
            return {
                "score": 1.0,
                "pass": True,
                "details": {"note": "No price constraints specified"}
            }
        
        # Convert to Decimal for precision
        max_budget = Decimal(str(buyer_max_budget))
        seller_price_dec = Decimal(str(seller_price))
        
        # NOTE: Currency conversion is for DISPLAY only, not for scoring
        # Buyer and seller negotiate in their respective currencies
        # Price comparison assumes same currency or buyer understands conversion
        
        # Use target price if specified, otherwise assume 90% of max
        if buyer_target_price:
            target_price = Decimal(str(buyer_target_price))
        else:
            target_price = max_budget * Decimal("0.90")
        
        # Check if price exceeds budget (BLOCKED)
        if seller_price_dec > max_budget:
            score = 0.0
            passed = False
            price_match_quality = "REJECTED - Over Budget"
            variance_percent = 100.0
        else:
            # Calculate variance from target
            if target_price > 0:
                variance_percent = abs(float((seller_price_dec - target_price) / target_price * 100))
            else:
                variance_percent = 0.0
            
            # STRICT PRICE MATCHING TIERS (as per requirements)
            if seller_price_dec == target_price:
                score = 1.0
                price_match_quality = "PERFECT - Exact Match"
            elif variance_percent <= 2.0:
                score = 0.95
                price_match_quality = "EXCELLENT - Within 2%"
            elif variance_percent <= 5.0:
                score = 0.85
                price_match_quality = "GOOD - Within 5%"
            elif variance_percent <= 10.0:
                score = 0.70
                price_match_quality = "ACCEPTABLE - Within 10%"
            elif seller_price_dec <= max_budget:
                score = 0.60
                price_match_quality = "JUST ACCEPTABLE - Within Budget"
            else:
                score = 0.0
                price_match_quality = "REJECTED"
            
            passed = score >= 0.6
        
        savings = float(max_budget - seller_price_dec)
        variance_from_target = float(seller_price_dec - target_price)
        
        return {
            "score": max(0.0, min(1.0, score)),
            "pass": passed,
            "details": {
                "seller_price": float(seller_price_dec),
                "buyer_target_price": float(target_price),
                "buyer_max_budget": float(max_budget),
                "variance_percent": round(variance_percent, 2),
                "variance_from_target": variance_from_target,
                "savings": savings,
                "price_match_quality": price_match_quality,
                "over_budget": seller_price_dec > max_budget
            }
        }
    
    # ========================================================================
    # DELIVERY SCORING (15% weight)
    # ========================================================================
    
    def calculate_delivery_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Calculate logistics compatibility.
        
        Factors:
        1. Location match (already filtered, so score 1.0 if here)
        2. Delivery timeline compatibility
        3. Delivery terms matching
        4. Incoterm matching (international trade)
        5. Port distance (international trade)
        
        Returns:
        {
            "score": 0.90,
            "pass": True,
            "details": {...}
        }
        """
        # Location already matched (hard filter passed)
        location_score = 1.0
        
        # Timeline check (placeholder - would check delivery_window_start/end)
        timeline_score = 1.0
        
        # Delivery terms check (placeholder)
        terms_score = 1.0
        
        # Incoterm matching (international trade)
        incoterm_score = self._calculate_incoterm_match(requirement, availability)
        
        # Port distance (international trade)
        port_distance_score = self._calculate_port_distance_score(requirement, availability)
        
        # Weighted average
        # National trade: location (40%), timeline (30%), terms (30%)
        # International: location (25%), timeline (20%), terms (20%), incoterm (20%), port distance (15%)
        is_international = requirement.destination_country is not None
        
        if is_international:
            final_score = (
                location_score * 0.25 +
                timeline_score * 0.20 +
                terms_score * 0.20 +
                incoterm_score * 0.20 +
                port_distance_score * 0.15
            )
        else:
            final_score = (
                location_score * 0.40 +
                timeline_score * 0.30 +
                terms_score * 0.30
            )
        
        return {
            "score": final_score,
            "pass": final_score >= 0.6,
            "details": {
                "location_compatible": True,
                "timeline_compatible": True,
                "terms_compatible": True,
                "incoterm_score": incoterm_score if is_international else None,
                "port_distance_score": port_distance_score if is_international else None,
                "is_international": is_international
            }
        }
    
    def _calculate_incoterm_match(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> float:
        """
        Calculate incoterm compatibility score for international trade.
        
        Rules:
        - If requirement has NO preferred_incoterm: 1.0 (accept any)
        - If availability has NO supported_incoterms: 0.5 (partial score)
        - If preferred matches supported: 1.0 (perfect match)
        - If not matched: 0.3 (incompatible)
        
        Returns:
            Score between 0.0 and 1.0
        """
        req_incoterm = requirement.preferred_incoterm
        avail_incoterms = availability.supported_incoterms
        
        # No preference - accept any
        if not req_incoterm:
            return 1.0
        
        # Seller has no incoterms specified - partial score
        if not avail_incoterms or not isinstance(avail_incoterms, list):
            return 0.5
        
        # Check if preferred is supported
        if req_incoterm.upper() in [inc.upper() for inc in avail_incoterms]:
            return 1.0
        
        # No match - incompatible
        return 0.3
    
    def _calculate_port_distance_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> float:
        """
        Calculate port distance score for international trade.
        
        Uses simplified port distance estimation:
        - Same port: 1.0
        - Different ports: 0.7 (placeholder - would calculate actual distance)
        - Missing port info: 0.8 (neutral)
        
        TODO: Implement actual port-to-port distance calculation
        
        Returns:
            Score between 0.0 and 1.0
        """
        req_port = requirement.import_port
        avail_port = availability.export_port
        
        # No port info - neutral score
        if not req_port or not avail_port:
            return 0.8
        
        # Same port (likely transshipment scenario)
        if req_port.upper() == avail_port.upper():
            return 1.0
        
        # Different ports - would calculate distance
        # For now, return moderate score
        return 0.7
    
    # ========================================================================
    # QUANTITY SCORING (embedded in quality/delivery)
    # ========================================================================
    
    def calculate_quantity_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Check if seller has enough quantity.
        
        Algorithm:
        - If available >= preferred: score = 1.0
        - If available >= min and < preferred:
            score = (available - min) / (preferred - min)
        - If available < min: score = available / min (partial order)
        
        Returns:
        {
            "score": 1.0,
            "pass": True,
            "details": {...}
        }
        """
        buyer_min = requirement.min_quantity
        buyer_max = requirement.max_quantity
        buyer_preferred = requirement.preferred_quantity or buyer_min
        seller_available = availability.remaining_quantity or Decimal(0)
        
        if seller_available >= buyer_preferred:
            # Can fulfill preferred - perfect score
            score = 1.0
            can_fulfill = True
        elif seller_available >= buyer_min:
            # Can fulfill min but not preferred - partial score
            range_size = buyer_preferred - buyer_min
            if range_size > 0:
                score = float((seller_available - buyer_min) / range_size)
            else:
                score = 1.0
            can_fulfill = True
        else:
            # Below min - proportional score (allow partial matching)
            if buyer_min > 0:
                score = float(seller_available / buyer_min)
            else:
                score = 0.0
            can_fulfill = False
        
        # Check minimum partial threshold (10%)
        min_partial_pct = self.config.MIN_PARTIAL_QUANTITY_PERCENT
        meets_min_partial = (seller_available / buyer_min) >= Decimal(str(min_partial_pct)) if buyer_min > 0 else True
        
        return {
            "score": max(0.0, min(1.0, score)),
            "pass": meets_min_partial,
            "details": {
                "buyer_min": float(buyer_min),
                "buyer_preferred": float(buyer_preferred),
                "buyer_max": float(buyer_max) if buyer_max else None,
                "seller_available": float(seller_available),
                "can_fulfill_preferred": can_fulfill,
                "meets_min_partial_threshold": meets_min_partial
            }
        }
    
    # ========================================================================
    # RISK SCORING (15% weight) ⭐ CRITICAL
    # ========================================================================
    
    async def calculate_risk_score(
        self,
        requirement: Requirement,
        availability: Availability,
        risk_engine: RiskEngine
    ) -> Dict[str, Any]:
        """
        Integrate with Risk Engine for compliance checks.
        
        CRITICAL: WARN status will trigger 10% global penalty in parent function.
        
        Risk Score Mapping:
        - PASS (score >= 80): risk_score = 1.0
        - WARN (score 60-79): risk_score = 0.5 (for 15% component)
        - FAIL (score < 60): risk_score = 0.0 (blocks match)
        
        Returns:
        {
            "risk_status": "WARN",
            "risk_score": 75,
            "violations": [...],
            "warnings": [...],
            "details": {...}
        }
        """
        try:
            # Call risk engine
            risk_assessment = await risk_engine.assess_trade_risk(
                requirement=requirement,
                availability=availability,
                trade_quantity=min(
                    requirement.preferred_quantity or requirement.min_quantity,
                    availability.remaining_quantity or Decimal(0)
                ),
                trade_price=availability.base_price,
                buyer_data={"partner_id": requirement.buyer_partner_id},
                seller_data={"partner_id": availability.seller_id},
                user_id=None  # System matching
            )
            
            overall_status = risk_assessment.get("overall_status", "UNKNOWN")
            risk_score_value = risk_assessment.get("overall_risk_score", 100)
            
            return {
                "risk_status": overall_status,
                "risk_score": risk_score_value,
                "violations": risk_assessment.get("violations", []),
                "warnings": risk_assessment.get("warnings", []),
                "details": risk_assessment
            }
            
        except Exception as e:
            logger.error(f"Risk engine error: {e}")
            # Default to WARN on error (conservative)
            return {
                "risk_status": "WARN",
                "risk_score": 70,
                "violations": [],
                "warnings": [f"Risk engine error: {str(e)}"],
                "details": {}
            }
    
    # ========================================================================
    # WARN PENALTY HELPER (for testing)
    # ========================================================================
    
    def _apply_warn_penalty(
        self,
        base_score: float,
        risk_details: Dict[str, Any]
    ) -> tuple[float, bool, float]:
        """
        Apply WARN penalty to base score.
        
        Args:
            base_score: Score before penalty
            risk_details: Risk assessment details with risk_status
            
        Returns:
            Tuple of (final_score, penalty_applied, penalty_value)
        """
        risk_status = risk_details.get("risk_status", "UNKNOWN")
        
        if risk_status == "WARN":
            penalty_value = self.config.RISK_WARN_GLOBAL_PENALTY
            final_score = base_score * (1.0 - penalty_value)
            return (final_score, True, penalty_value)
        else:
            return (base_score, False, 0.0)
    
    # ========================================================================
    # AI BOOST HELPER (for testing)
    # ========================================================================
    
    def _apply_ai_boost(
        self,
        base_score: float,
        availability: Availability
    ) -> float:
        """
        Apply AI confidence boost to score.
        
        Args:
            base_score: Score before boost
            availability: Availability with ai_confidence_score
            
        Returns:
            Final score with boost applied (capped at 1.0)
        """
        if not self.config.ENABLE_AI_SCORE_BOOST:
            return base_score
        
        ai_confidence = availability.ai_confidence_score
        if ai_confidence is None:
            return base_score
        
        # Convert to float if Decimal
        confidence_value = float(ai_confidence) if isinstance(ai_confidence, Decimal) else ai_confidence
        
        # Apply boost if confidence >= 80%
        if confidence_value >= 0.8:
            boost = self.config.AI_RECOMMENDATION_SCORE_BOOST
            final_score = min(1.0, base_score + boost)
            return final_score
        
        return base_score
    
    # ========================================================================
    # HELPER: HAVERSINE DISTANCE
    # ========================================================================
    
    def calculate_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate Haversine distance between two coordinates.
        
        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth radius in km
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance

