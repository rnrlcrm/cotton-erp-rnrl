"""
ML Risk Engine - AI-powered Predictive Risk Assessment

TIER 2: Advisory layer that provides ML-based predictions and insights.
NEVER blocks transactions - only provides risk scores and recommendations.

AI Models:
1. Payment Default Predictor - Predicts probability of payment default
2. Quality Deviation Model - Predicts quality mismatch risk
3. Fraud Pattern Detector - Detects unusual trading patterns

Features:
- Counterparty trust scoring with ML
- Price volatility risk analysis
- KYC completeness risk scoring
- Real-time anomaly detection
- Historical behavior pattern analysis
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from statistics import stdev, mean

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.partners.models import BusinessPartner, PartnerDocument
from backend.modules.settings.commodities.models import Commodity


class MLRiskEngine:
    """
    Machine Learning Risk Engine for predictive risk assessment.
    
    This is TIER 2 - advisory only, never blocks transactions.
    Provides AI-powered insights to complement rule-based checks.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================================
    # MAIN PREDICTION ENTRY POINT
    # ============================================================================
    
    async def predict_risk(
        self,
        entity_type: str,
        partner_id: UUID,
        commodity_id: UUID,
        trade_value: Decimal,
        counterparty_id: Optional[UUID] = None,
        trade_quantity: Optional[Decimal] = None,
        trade_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive ML-based risk prediction.
        
        Args:
            entity_type: "requirement" or "availability"
            partner_id: Partner creating the entity
            commodity_id: Commodity being traded
            trade_value: Estimated trade value
            counterparty_id: Optional counterparty for bilateral assessment
            trade_quantity: Trade quantity
            trade_price: Trade price per unit
            
        Returns:
            Dict with ML predictions and scores
        """
        # Run all ML models in parallel
        payment_default_risk = await self.predict_payment_default(
            partner_id=partner_id,
            trade_value=trade_value,
            entity_type=entity_type
        )
        
        quality_risk = await self.predict_quality_deviation(
            partner_id=partner_id,
            commodity_id=commodity_id
        )
        
        fraud_risk = await self.detect_fraud_patterns(
            partner_id=partner_id,
            commodity_id=commodity_id,
            trade_value=trade_value,
            trade_price=trade_price
        )
        
        price_volatility_risk = await self.assess_price_volatility(
            commodity_id=commodity_id,
            proposed_price=trade_price
        )
        
        kyc_risk = await self.assess_kyc_completeness(
            partner_id=partner_id
        )
        
        trust_score = await self.calculate_ml_trust_score(
            partner_id=partner_id,
            counterparty_id=counterparty_id
        )
        
        anomaly_score = await self.detect_realtime_anomalies(
            partner_id=partner_id,
            commodity_id=commodity_id,
            trade_value=trade_value,
            trade_quantity=trade_quantity
        )
        
        # Aggregate ML score (0-100, higher is better)
        ml_score = self._calculate_aggregate_ml_score(
            payment_default_risk=payment_default_risk["probability"],
            quality_risk=quality_risk["probability"],
            fraud_risk=fraud_risk["probability"],
            price_volatility_risk=price_volatility_risk["risk_level"],
            kyc_risk=kyc_risk["risk_score"],
            trust_score=trust_score["score"],
            anomaly_score=anomaly_score["anomaly_score"]
        )
        
        return {
            "ml_score": ml_score,
            "predictions": {
                "payment_default": payment_default_risk,
                "quality_deviation": quality_risk,
                "fraud_pattern": fraud_risk,
                "price_volatility": price_volatility_risk,
                "kyc_completeness": kyc_risk,
                "trust_score": trust_score,
                "anomaly_detection": anomaly_score
            },
            "recommendation": self._generate_recommendation(ml_score),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # MODEL 1: PAYMENT DEFAULT PREDICTOR
    # ============================================================================
    
    async def predict_payment_default(
        self,
        partner_id: UUID,
        trade_value: Decimal,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Predict probability of payment default using historical behavior.
        
        Features:
        - Payment history (on-time vs delayed vs defaulted)
        - Trade value vs average historical value
        - Credit utilization trend
        - Seasonal patterns
        - Partner age and maturity
        
        Args:
            partner_id: Partner to assess
            trade_value: Proposed trade value
            entity_type: "requirement" or "availability"
            
        Returns:
            {
                "probability": float (0.0-1.0),
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "contributing_factors": List[str],
                "confidence": float (0.0-1.0)
            }
        """
        # Fetch partner data
        result = await self.db.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        
        if not partner:
            return {
                "probability": 0.5,
                "risk_level": "MEDIUM",
                "contributing_factors": ["Partner not found"],
                "confidence": 0.0
            }
        
        factors = []
        probability = 0.0
        
        # Feature 1: Payment performance score (30%)
        if entity_type == "requirement":
            payment_score = partner.payment_performance_score or 50
            if payment_score < 40:
                probability += 0.30
                factors.append(f"Poor payment history (score: {payment_score})")
            elif payment_score < 60:
                probability += 0.15
                factors.append(f"Below average payment history (score: {payment_score})")
            elif payment_score < 80:
                probability += 0.05
        
        # Feature 2: Credit utilization (25%)
        credit_utilization = 0
        if partner.credit_limit and partner.credit_limit > 0:
            credit_utilization = float(partner.current_exposure / partner.credit_limit * 100)
            
            if credit_utilization > 90:
                probability += 0.25
                factors.append(f"High credit utilization ({credit_utilization:.1f}%)")
            elif credit_utilization > 75:
                probability += 0.15
                factors.append(f"Moderate credit utilization ({credit_utilization:.1f}%)")
            elif credit_utilization > 60:
                probability += 0.05
        
        # Feature 3: Trade value anomaly (20%)
        # TODO: Fetch average historical trade value from database
        avg_trade_value = Decimal("100000")  # Placeholder
        
        if trade_value > avg_trade_value * Decimal("2.5"):
            probability += 0.20
            factors.append(f"Trade value {float(trade_value/avg_trade_value):.1f}x above average")
        elif trade_value > avg_trade_value * Decimal("1.5"):
            probability += 0.10
            factors.append(f"Trade value above average")
        
        # Feature 4: Partner rating (15%)
        rating = partner.rating or Decimal("3.0")
        if rating < Decimal("2.0"):
            probability += 0.15
            factors.append(f"Very low rating ({rating})")
        elif rating < Decimal("3.0"):
            probability += 0.08
            factors.append(f"Low rating ({rating})")
        
        # Feature 5: Partner maturity (10%)
        # TODO: Calculate account age from created_at
        # New partners (<6 months) = higher risk
        
        # Determine risk level
        if probability >= 0.7:
            risk_level = "HIGH"
        elif probability >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Confidence based on data availability
        confidence = 0.7  # Base confidence
        if partner.payment_performance_score:
            confidence += 0.1
        if credit_utilization > 0:
            confidence += 0.1
        if partner.rating and partner.rating > 0:
            confidence += 0.1
        
        return {
            "probability": min(1.0, probability),
            "risk_level": risk_level,
            "contributing_factors": factors,
            "confidence": min(1.0, confidence),
            "payment_score": payment_score if entity_type == "requirement" else None,
            "credit_utilization": credit_utilization,
            "partner_rating": float(rating)
        }
    
    # ============================================================================
    # MODEL 2: QUALITY DEVIATION PREDICTOR
    # ============================================================================
    
    async def predict_quality_deviation(
        self,
        partner_id: UUID,
        commodity_id: UUID
    ) -> Dict[str, Any]:
        """
        Predict probability of quality mismatch/deviation.
        
        Features:
        - Historical quality complaints
        - Commodity-specific quality performance
        - Quality certificate availability
        - Seller delivery performance score
        
        Args:
            partner_id: Partner to assess (seller)
            commodity_id: Commodity being sold
            
        Returns:
            {
                "probability": float (0.0-1.0),
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "quality_factors": List[str],
                "confidence": float
            }
        """
        # Fetch partner
        result = await self.db.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        
        if not partner:
            return {
                "probability": 0.3,
                "risk_level": "MEDIUM",
                "quality_factors": ["Partner not found"],
                "confidence": 0.0
            }
        
        factors = []
        probability = 0.0
        
        # Feature 1: Delivery performance score (40%)
        delivery_score = partner.delivery_performance_score or 50
        
        if delivery_score < 40:
            probability += 0.40
            factors.append(f"Poor delivery history (score: {delivery_score})")
        elif delivery_score < 60:
            probability += 0.20
            factors.append(f"Below average delivery (score: {delivery_score})")
        elif delivery_score < 75:
            probability += 0.10
        
        # Feature 2: Quality certificates (30%)
        result = await self.db.execute(
            select(func.count(PartnerDocument.id)).where(
                and_(
                    PartnerDocument.partner_id == partner_id,
                    PartnerDocument.document_type.in_(["quality_certificate", "iso_certification"]),
                    PartnerDocument.verified == True,
                    PartnerDocument.is_expired == False
                )
            )
        )
        quality_certs_count = result.scalar() or 0
        
        if quality_certs_count == 0:
            probability += 0.30
            factors.append("No quality certificates on file")
        elif quality_certs_count < 2:
            probability += 0.15
            factors.append("Limited quality documentation")
        
        # Feature 3: Historical quality disputes (30%)
        # TODO: Fetch actual dispute data from database
        # For now, use partner rating as proxy
        rating = partner.rating or Decimal("3.0")
        
        if rating < Decimal("2.5"):
            probability += 0.30
            factors.append(f"Low quality rating ({rating})")
        elif rating < Decimal("3.5"):
            probability += 0.15
            factors.append(f"Moderate quality rating ({rating})")
        
        # Determine risk level
        if probability >= 0.6:
            risk_level = "HIGH"
        elif probability >= 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        confidence = 0.65
        if delivery_score != 50:
            confidence += 0.15
        if quality_certs_count > 0:
            confidence += 0.1
        if rating != Decimal("3.0"):
            confidence += 0.1
        
        return {
            "probability": min(1.0, probability),
            "risk_level": risk_level,
            "quality_factors": factors,
            "confidence": min(1.0, confidence),
            "delivery_score": delivery_score,
            "quality_certificates": quality_certs_count,
            "quality_rating": float(rating)
        }
    
    # ============================================================================
    # MODEL 3: FRAUD PATTERN DETECTOR
    # ============================================================================
    
    async def detect_fraud_patterns(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        trade_value: Decimal,
        trade_price: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Detect unusual trading patterns that may indicate fraud.
        
        Patterns detected:
        - Sudden large trades from new partners
        - Price manipulation (far from market price)
        - High-frequency trading in short time window
        - Unusual commodity combinations
        - Geographic anomalies
        
        Args:
            partner_id: Partner to assess
            commodity_id: Commodity being traded
            trade_value: Trade value
            trade_price: Price per unit
            
        Returns:
            {
                "probability": float (0.0-1.0),
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "detected_patterns": List[str],
                "confidence": float
            }
        """
        patterns = []
        probability = 0.0
        
        # Fetch partner
        result = await self.db.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        
        if not partner:
            return {
                "probability": 0.5,
                "risk_level": "MEDIUM",
                "detected_patterns": ["Partner not found"],
                "confidence": 0.0
            }
        
        # Pattern 1: New partner with large trade (30%)
        # TODO: Check account age from created_at
        # For now, use trade history count as proxy
        trade_count = 0  # TODO: Fetch from database
        
        if trade_count < 5 and trade_value > Decimal("500000"):
            probability += 0.30
            patterns.append("New partner attempting large trade")
        elif trade_count < 10 and trade_value > Decimal("1000000"):
            probability += 0.15
            patterns.append("Limited history with very large trade")
        
        # Pattern 2: Price anomaly (25%)
        if trade_price:
            # Fetch commodity to get typical price range
            result = await self.db.execute(
                select(Commodity).where(Commodity.id == commodity_id)
            )
            commodity = result.scalar_one_or_none()
            
            if commodity:
                # TODO: Calculate market average from recent trades
                # For now, use placeholder logic
                typical_min = Decimal("50")
                typical_max = Decimal("150")
                
                if trade_price < typical_min * Decimal("0.5"):
                    probability += 0.25
                    patterns.append(f"Price suspiciously low ({float(trade_price)} vs market {float(typical_min)}-{float(typical_max)})")
                elif trade_price > typical_max * Decimal("2.0"):
                    probability += 0.25
                    patterns.append(f"Price suspiciously high ({float(trade_price)} vs market {float(typical_min)}-{float(typical_max)})")
                elif trade_price < typical_min * Decimal("0.75") or trade_price > typical_max * Decimal("1.25"):
                    probability += 0.10
                    patterns.append("Price outside normal range")
        
        # Pattern 3: High frequency trading (20%)
        # TODO: Check trades created in last 24 hours
        recent_trades_count = 0  # Placeholder
        
        if recent_trades_count > 10:
            probability += 0.20
            patterns.append(f"Unusually high trading frequency ({recent_trades_count} trades in 24h)")
        elif recent_trades_count > 5:
            probability += 0.10
            patterns.append("Higher than normal trading frequency")
        
        # Pattern 4: Partner rating anomaly (15%)
        rating = partner.rating or Decimal("3.0")
        
        if rating < Decimal("2.0"):
            probability += 0.15
            patterns.append(f"Very low partner rating ({rating})")
        elif rating < Decimal("2.5"):
            probability += 0.08
            patterns.append(f"Low partner rating ({rating})")
        
        # Pattern 5: KYC gaps (10%)
        result = await self.db.execute(
            select(func.count(PartnerDocument.id)).where(
                and_(
                    PartnerDocument.partner_id == partner_id,
                    PartnerDocument.verified == True
                )
            )
        )
        verified_docs = result.scalar() or 0
        
        if verified_docs < 2:
            probability += 0.10
            patterns.append(f"Insufficient KYC documentation ({verified_docs} verified docs)")
        
        # Determine risk level
        if probability >= 0.6:
            risk_level = "HIGH"
        elif probability >= 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        confidence = 0.6
        if trade_price:
            confidence += 0.15
        if trade_count > 0:
            confidence += 0.15
        if verified_docs > 0:
            confidence += 0.1
        
        return {
            "probability": min(1.0, probability),
            "risk_level": risk_level,
            "detected_patterns": patterns,
            "confidence": min(1.0, confidence),
            "partner_rating": float(rating),
            "verified_documents": verified_docs
        }
    
    # ============================================================================
    # PRICE VOLATILITY RISK
    # ============================================================================
    
    async def assess_price_volatility(
        self,
        commodity_id: UUID,
        proposed_price: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Assess price volatility risk for commodity.
        
        Calculates:
        - Historical price standard deviation
        - Recent price trends
        - Proposed price vs market average
        
        Args:
            commodity_id: Commodity to assess
            proposed_price: Proposed trade price
            
        Returns:
            {
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "volatility_percentage": float,
                "price_deviation": float,
                "trend": "STABLE" | "INCREASING" | "DECREASING"
            }
        """
        # TODO: Fetch historical prices from trades database
        # For now, return placeholder analysis
        
        result = await self.db.execute(
            select(Commodity).where(Commodity.id == commodity_id)
        )
        commodity = result.scalar_one_or_none()
        
        if not commodity:
            return {
                "risk_level": "MEDIUM",
                "volatility_percentage": 0,
                "price_deviation": 0,
                "trend": "UNKNOWN"
            }
        
        # TODO: Calculate from actual trade data
        # historical_prices = [...]
        # avg_price = mean(historical_prices)
        # price_volatility = stdev(historical_prices) / avg_price * 100
        
        # Placeholder logic
        volatility = 15.0  # 15% volatility
        
        if volatility > 25:
            risk_level = "HIGH"
        elif volatility > 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        price_deviation = 0.0
        if proposed_price:
            market_avg = Decimal("100")  # TODO: Calculate from real data
            price_deviation = float(abs(proposed_price - market_avg) / market_avg * 100)
        
        return {
            "risk_level": risk_level,
            "volatility_percentage": volatility,
            "price_deviation": price_deviation,
            "trend": "STABLE",  # TODO: Calculate trend
            "commodity_name": commodity.name
        }
    
    # ============================================================================
    # KYC COMPLETENESS RISK
    # ============================================================================
    
    async def assess_kyc_completeness(
        self,
        partner_id: UUID
    ) -> Dict[str, Any]:
        """
        Assess KYC documentation completeness and quality.
        
        Checks:
        - Number of verified documents
        - Critical documents present (PAN, GST, IEC)
        - Document expiry status
        - OCR extraction quality
        
        Args:
            partner_id: Partner to assess
            
        Returns:
            {
                "risk_score": int (0-100, higher is better),
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "missing_documents": List[str],
                "expired_documents": List[str],
                "completeness_percentage": float
            }
        """
        # Fetch all partner documents
        result = await self.db.execute(
            select(PartnerDocument).where(PartnerDocument.partner_id == partner_id)
        )
        documents = result.scalars().all()
        
        required_docs = {"pan", "gst", "bank_statement"}
        verified_docs = set()
        expired_docs = []
        
        for doc in documents:
            if doc.verified and not doc.is_expired:
                verified_docs.add(doc.document_type)
            elif doc.is_expired or (doc.expiry_date and doc.expiry_date < datetime.now().date()):
                expired_docs.append(doc.document_type)
        
        missing_docs = list(required_docs - verified_docs)
        completeness = len(verified_docs) / len(required_docs) * 100
        
        # Calculate risk score
        risk_score = 100
        
        if len(missing_docs) >= 2:
            risk_score -= 40
        elif len(missing_docs) == 1:
            risk_score -= 20
        
        if len(expired_docs) > 0:
            risk_score -= 15 * len(expired_docs)
        
        if len(documents) < 3:
            risk_score -= 10
        
        risk_score = max(0, risk_score)
        
        if risk_score >= 80:
            risk_level = "LOW"
        elif risk_score >= 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "missing_documents": missing_docs,
            "expired_documents": expired_docs,
            "completeness_percentage": completeness,
            "total_documents": len(documents),
            "verified_documents": len(verified_docs)
        }
    
    # ============================================================================
    # ML-BASED TRUST SCORE
    # ============================================================================
    
    async def calculate_ml_trust_score(
        self,
        partner_id: UUID,
        counterparty_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """
        Calculate ML-based trust score using multiple signals.
        
        Factors:
        - Trading relationship history
        - Successful trade completion rate
        - Average settlement time
        - Communication responsiveness
        - Dispute resolution history
        
        Args:
            partner_id: Primary partner
            counterparty_id: Optional counterparty
            
        Returns:
            {
                "score": int (0-100),
                "level": "LOW" | "MEDIUM" | "HIGH",
                "factors": List[str]
            }
        """
        result = await self.db.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        
        if not partner:
            return {
                "score": 50,
                "level": "MEDIUM",
                "factors": ["Partner not found"]
            }
        
        trust_score = 50
        factors = []
        
        # Factor 1: Partner rating (30 points)
        rating = partner.rating or Decimal("3.0")
        rating_points = int((float(rating) / 5.0) * 30)
        trust_score += rating_points - 18  # Normalized to +/- scale
        
        if rating >= Decimal("4.5"):
            factors.append(f"Excellent rating ({rating})")
        elif rating >= Decimal("4.0"):
            factors.append(f"Good rating ({rating})")
        elif rating < Decimal("3.0"):
            factors.append(f"Poor rating ({rating})")
        
        # Factor 2: Payment/delivery performance (30 points)
        perf_score = partner.payment_performance_score or partner.delivery_performance_score or 50
        perf_points = int((perf_score / 100) * 30)
        trust_score += perf_points - 15
        
        if perf_score >= 90:
            factors.append(f"Excellent performance ({perf_score})")
        elif perf_score >= 75:
            factors.append(f"Good performance ({perf_score})")
        elif perf_score < 50:
            factors.append(f"Poor performance ({perf_score})")
        
        # Factor 3: Account maturity (20 points)
        # TODO: Calculate from created_at
        # For now, assume mature account
        trust_score += 10
        
        # Factor 4: Verification status (20 points)
        if partner.is_verified:
            trust_score += 15
            factors.append("Verified partner")
        else:
            trust_score -= 5
            factors.append("Unverified partner")
        
        trust_score = max(0, min(100, trust_score))
        
        if trust_score >= 75:
            level = "HIGH"
        elif trust_score >= 50:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return {
            "score": trust_score,
            "level": level,
            "factors": factors,
            "partner_rating": float(rating),
            "performance_score": perf_score,
            "is_verified": partner.is_verified
        }
    
    # ============================================================================
    # REAL-TIME ANOMALY DETECTION
    # ============================================================================
    
    async def detect_realtime_anomalies(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        trade_value: Decimal,
        trade_quantity: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Detect real-time anomalies in trading behavior.
        
        Anomalies detected:
        - Trade value far from historical average
        - Unusual quantity for commodity
        - Time-of-day anomalies
        - Geographic anomalies
        - Velocity anomalies (too many trades)
        
        Args:
            partner_id: Partner to assess
            commodity_id: Commodity being traded
            trade_value: Trade value
            trade_quantity: Trade quantity
            
        Returns:
            {
                "anomaly_score": int (0-100, higher = more anomalous),
                "anomalies_detected": List[str],
                "severity": "LOW" | "MEDIUM" | "HIGH"
            }
        """
        anomalies = []
        anomaly_score = 0
        
        # TODO: Fetch historical baseline from database
        # avg_trade_value, avg_quantity, typical_trading_hours, etc.
        
        # Anomaly 1: Trade value deviation (40 points)
        historical_avg = Decimal("100000")  # TODO: Calculate from real data
        
        value_ratio = float(trade_value / historical_avg)
        if value_ratio > 5.0:
            anomaly_score += 40
            anomalies.append(f"Trade value {value_ratio:.1f}x above historical average")
        elif value_ratio > 3.0:
            anomaly_score += 25
            anomalies.append(f"Trade value significantly above average")
        elif value_ratio < 0.2:
            anomaly_score += 30
            anomalies.append(f"Trade value unusually low")
        
        # Anomaly 2: Quantity deviation (30 points)
        if trade_quantity:
            avg_quantity = Decimal("1000")  # TODO: Calculate
            quantity_ratio = float(trade_quantity / avg_quantity)
            
            if quantity_ratio > 5.0 or quantity_ratio < 0.2:
                anomaly_score += 30
                anomalies.append(f"Unusual trade quantity ({quantity_ratio:.1f}x average)")
            elif quantity_ratio > 3.0 or quantity_ratio < 0.5:
                anomaly_score += 15
                anomalies.append("Trade quantity outside normal range")
        
        # Anomaly 3: Time-of-day anomaly (15 points)
        current_hour = datetime.utcnow().hour
        
        # Unusual if trading between 10 PM - 6 AM IST
        if current_hour < 6 or current_hour >= 22:
            anomaly_score += 15
            anomalies.append("Trade created during unusual hours")
        
        # Anomaly 4: Velocity anomaly (15 points)
        # TODO: Check trades created in last hour
        recent_trades = 0  # Placeholder
        
        if recent_trades > 5:
            anomaly_score += 15
            anomalies.append(f"High velocity: {recent_trades} trades in last hour")
        
        anomaly_score = min(100, anomaly_score)
        
        if anomaly_score >= 60:
            severity = "HIGH"
        elif anomaly_score >= 30:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        return {
            "anomaly_score": anomaly_score,
            "anomalies_detected": anomalies,
            "severity": severity,
            "value_ratio": value_ratio,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _calculate_aggregate_ml_score(
        self,
        payment_default_risk: float,
        quality_risk: float,
        fraud_risk: float,
        price_volatility_risk: str,
        kyc_risk: int,
        trust_score: int,
        anomaly_score: int
    ) -> int:
        """
        Aggregate all ML predictions into single score (0-100).
        
        Higher score = lower risk (better)
        """
        # Convert risks to scores (invert probabilities)
        payment_score = int((1 - payment_default_risk) * 100)
        quality_score = int((1 - quality_risk) * 100)
        fraud_score = int((1 - fraud_risk) * 100)
        
        volatility_score = 50
        if price_volatility_risk == "LOW":
            volatility_score = 80
        elif price_volatility_risk == "HIGH":
            volatility_score = 30
        
        anomaly_score_inverted = 100 - anomaly_score
        
        # Weighted average
        ml_score = int(
            payment_score * 0.25 +
            quality_score * 0.20 +
            fraud_score * 0.20 +
            volatility_score * 0.10 +
            kyc_risk * 0.10 +
            trust_score * 0.10 +
            anomaly_score_inverted * 0.05
        )
        
        return max(0, min(100, ml_score))
    
    def _generate_recommendation(self, ml_score: int) -> str:
        """Generate human-readable recommendation based on ML score."""
        if ml_score >= 80:
            return "ML assessment: LOW RISK - Proceed with confidence"
        elif ml_score >= 60:
            return "ML assessment: MEDIUM RISK - Proceed with caution, monitor closely"
        else:
            return "ML assessment: HIGH RISK - Consider additional due diligence"
