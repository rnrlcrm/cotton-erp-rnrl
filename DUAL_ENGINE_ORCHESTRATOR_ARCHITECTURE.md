# DUAL ENGINE + ORCHESTRATOR ARCHITECTURE

**Date**: December 3, 2025  
**Architecture**: Rule Engine + ML Engine + Orchestrator  
**Status**: RECOMMENDED APPROACH ✅

---

## EXECUTIVE SUMMARY

**Decision**: Keep TWO separate engines, orchestrated by ONE unified entry point.

```
┌─────────────────────────────────────────────────────────────┐
│  UnifiedRiskOrchestrator (Single Entry Point)               │
│  • Coordinates both engines                                 │
│  • Enforces execution order (Rules FIRST, ML SECOND)        │
│  • Fusion layer combines outputs                            │
│  • Circuit breaker for ML failures                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌───────────────────┐               ┌───────────────────┐
│  RuleEngine       │               │  MLRiskEngine     │
│  (Deterministic)  │               │  (AI Predictions) │
├───────────────────┤               ├───────────────────┤
│ • Circular trade  │               │ • Default predict │
│ • Wash trading    │               │ • Credit optimize │
│ • Party links     │               │ • Fraud detect    │
│ • Sanctions       │               │ • Pattern learn   │
│ • Credit limits   │               │                   │
│                   │               │                   │
│ ✅ 100% reliable  │               │ ⚠️ Can fail       │
│ ✅ Auditable      │               │ ⚠️ Non-deterministic│
│ ✅ Regulatory OK  │               │ ⚠️ Advisory only  │
└───────────────────┘               └───────────────────┘
```

---

## ARCHITECTURE OVERVIEW

### File Structure (CORRECT APPROACH)

```
backend/modules/risk/
│
├── __init__.py
│
├── orchestrator/                    # ⭐ NEW - Single entry point
│   ├── __init__.py
│   ├── unified_risk_orchestrator.py # Main orchestrator
│   ├── fusion_layer.py              # Combines rule + ML outputs
│   └── circuit_breaker.py           # ML failure handling
│
├── rule_engine/                     # ⭐ KEEP EXISTING (rename)
│   ├── __init__.py
│   ├── risk_engine.py               # Current rule-based engine
│   ├── circular_trading.py          # Extracted rules
│   ├── wash_trading.py
│   ├── party_links.py
│   ├── credit_validation.py
│   └── sanctions.py
│
├── ml_engine/                       # ⭐ KEEP EXISTING (rename)
│   ├── __init__.py
│   ├── ml_risk_model.py             # Current ML engine
│   ├── payment_default_model.py     # Extracted models
│   ├── credit_optimizer.py
│   ├── fraud_detector.py
│   ├── model_trainer.py
│   └── actual_data_collector.py     # Real performance data
│
├── schemas.py                       # API request/response schemas
├── routes.py                        # API endpoints
└── services/
    └── risk_service.py              # FastAPI service layer
```

---

## 1. UNIFIED RISK ORCHESTRATOR (Entry Point)

### Purpose
- **Single entry point** for all risk checks
- **Coordinates** RuleEngine + MLRiskEngine
- **Enforces** execution order (rules first, ML second)
- **Handles** ML failures gracefully
- **Combines** outputs via fusion layer

### Implementation

```python
# backend/modules/risk/orchestrator/unified_risk_orchestrator.py

from typing import Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.risk.rule_engine.risk_engine import RuleEngine
from backend.modules.risk.ml_engine.ml_risk_model import MLRiskEngine
from backend.modules.risk.orchestrator.fusion_layer import FusionLayer
from backend.modules.risk.orchestrator.circuit_breaker import CircuitBreaker


class UnifiedRiskOrchestrator:
    """
    Single entry point for all risk assessments.
    
    Orchestrates RuleEngine (deterministic) + MLRiskEngine (AI predictions)
    
    Execution Flow:
    1. RuleEngine executes FIRST (instant blocking rules)
    2. If blocked → Return immediately (ML never runs)
    3. If passed → MLRiskEngine executes (advisory predictions)
    4. FusionLayer combines both outputs
    5. Return unified risk assessment
    
    Guarantees:
    - Rules ALWAYS execute (100% reliable)
    - ML MAY execute (can fail gracefully)
    - If ML fails → Rules-only result returned
    - Zero downtime even if ML crashes
    """
    
    def __init__(
        self,
        db: AsyncSession,
        enable_ml: bool = True,
        ml_weight: float = 0.30  # 30% ML, 70% Rules
    ):
        self.db = db
        self.enable_ml = enable_ml
        self.ml_weight = ml_weight
        
        # Initialize engines
        self.rule_engine = RuleEngine(db)
        self.ml_engine = MLRiskEngine(db) if enable_ml else None
        
        # Initialize fusion layer
        self.fusion = FusionLayer(ml_weight=ml_weight)
        
        # Circuit breaker for ML failures
        self.ml_circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # Open after 5 failures
            timeout_seconds=300   # Reset after 5 minutes
        )
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    
    async def comprehensive_check(
        self,
        partner_id: UUID,
        transaction_type: str,  # "BUY" or "SELL"
        commodity_id: UUID,
        amount: Decimal,
        counterparty_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive risk check using both engines.
        
        TIER 1: RuleEngine (ALWAYS executes)
        - Instant blocking rules (circular, wash, party links, sanctions)
        - If violation → INSTANT BLOCK (ML never runs)
        
        TIER 2: MLRiskEngine (CONDITIONALLY executes)
        - AI predictions (default risk, fraud, credit optimization)
        - If ML fails → Graceful degradation (rules-only)
        
        TIER 3: FusionLayer
        - Combines rule + ML outputs
        - Weighted scoring (30% ML + 70% Rules)
        
        Args:
            partner_id: Partner creating transaction
            transaction_type: "BUY" or "SELL"
            commodity_id: Commodity being traded
            amount: Transaction amount
            counterparty_id: Optional counterparty (for bilateral checks)
        
        Returns:
            Unified risk assessment with combined score
        """
        
        # ====================================================================
        # TIER 1: RULE ENGINE (ALWAYS EXECUTES FIRST)
        # ====================================================================
        
        rule_result = await self.rule_engine.comprehensive_check(
            partner_id=partner_id,
            transaction_type=transaction_type,
            commodity_id=commodity_id,
            amount=amount,
            counterparty_id=counterparty_id
        )
        
        # If rules BLOCKED the trade → Return immediately (ML never runs)
        if rule_result.get("blocked", False):
            return {
                "score": 0,
                "status": "FAIL",
                "blocked": True,
                "blocking_reason": rule_result["blocking_reason"],
                "violation_type": rule_result["violation_type"],
                "engine": "RuleEngine",
                "tier": "TIER_1_INSTANT_BLOCK",
                "method": "rules_only",
                "confidence": "absolute",
                "rule_result": rule_result,
                "ml_result": None,  # ML didn't run
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
        
        # ====================================================================
        # TIER 2: ML ENGINE (CONDITIONALLY EXECUTES)
        # ====================================================================
        
        ml_result = None
        ml_execution_status = "skipped"
        
        if self.enable_ml and not self.ml_circuit_breaker.is_open():
            try:
                # Try to get ML predictions
                ml_result = await self.ml_engine.predict_risk(
                    partner_id=partner_id,
                    transaction_type=transaction_type,
                    amount=amount
                )
                
                ml_execution_status = "success"
                self.ml_circuit_breaker.record_success()
                
            except Exception as e:
                # ML failed → Record failure, but continue with rules-only
                ml_execution_status = "failed"
                self.ml_circuit_breaker.record_failure()
                
                # Log error but don't crash
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"ML Engine failed: {e}")
                logger.warning("Falling back to rules-only scoring")
        
        elif self.ml_circuit_breaker.is_open():
            ml_execution_status = "circuit_breaker_open"
        
        # ====================================================================
        # TIER 3: FUSION LAYER (COMBINE OUTPUTS)
        # ====================================================================
        
        unified_result = self.fusion.combine(
            rule_result=rule_result,
            ml_result=ml_result
        )
        
        # Add metadata
        unified_result.update({
            "engine": "UnifiedOrchestrator",
            "engines_used": {
                "rule_engine": "success",
                "ml_engine": ml_execution_status
            },
            "ml_weight": self.ml_weight if ml_result else 0.0,
            "rule_weight": 1.0 - self.ml_weight if ml_result else 1.0,
            "circuit_breaker_status": "open" if self.ml_circuit_breaker.is_open() else "closed",
            "assessment_timestamp": datetime.utcnow().isoformat()
        })
        
        return unified_result
    
    # ========================================================================
    # INDIVIDUAL ENGINE ACCESS (for testing/debugging)
    # ========================================================================
    
    async def check_rules_only(self, **kwargs) -> Dict[str, Any]:
        """Run RuleEngine only (skip ML)."""
        return await self.rule_engine.comprehensive_check(**kwargs)
    
    async def check_ml_only(self, **kwargs) -> Dict[str, Any]:
        """Run MLRiskEngine only (skip rules - for testing)."""
        if not self.ml_engine:
            raise RuntimeError("ML Engine not enabled")
        return await self.ml_engine.predict_risk(**kwargs)
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    def set_ml_weight(self, weight: float):
        """Adjust ML weight (0.0-1.0)."""
        if not 0.0 <= weight <= 1.0:
            raise ValueError("ML weight must be between 0.0 and 1.0")
        self.ml_weight = weight
        self.fusion.ml_weight = weight
    
    def enable_ml_engine(self, enable: bool):
        """Enable/disable ML engine."""
        self.enable_ml = enable
        if enable and not self.ml_engine:
            self.ml_engine = MLRiskEngine(self.db)
    
    def reset_circuit_breaker(self):
        """Manually reset ML circuit breaker."""
        self.ml_circuit_breaker.reset()
```

---

## 2. FUSION LAYER (Combine Outputs)

### Purpose
- **Combines** RuleEngine + MLRiskEngine outputs
- **Weighted scoring**: 30% ML + 70% Rules (configurable)
- **Graceful degradation**: Falls back to rules-only if ML fails

### Implementation

```python
# backend/modules/risk/orchestrator/fusion_layer.py

from typing import Dict, Any, Optional


class FusionLayer:
    """
    Combines RuleEngine + MLRiskEngine outputs into unified assessment.
    
    Fusion Strategies:
    1. Weighted Average (default): 30% ML + 70% Rules
    2. Conservative: Take lower of (rule_score, ml_score)
    3. Optimistic: Take higher of (rule_score, ml_score)
    4. Rules-Only: Ignore ML (fallback mode)
    """
    
    def __init__(self, ml_weight: float = 0.30):
        self.ml_weight = ml_weight
        self.rule_weight = 1.0 - ml_weight
    
    def combine(
        self,
        rule_result: Dict[str, Any],
        ml_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Combine rule + ML results into unified assessment.
        
        Args:
            rule_result: Output from RuleEngine
            ml_result: Output from MLRiskEngine (None if failed)
        
        Returns:
            Unified risk assessment
        """
        
        # Extract rule score
        rule_score = rule_result.get("score", 0)
        rule_status = rule_result.get("status", "FAIL")
        
        # If ML unavailable → Return rules-only
        if ml_result is None:
            return {
                "score": rule_score,
                "status": rule_status,
                "blocked": False,
                "blocking_reason": None,
                "method": "rules_only",
                "confidence": "medium",
                "rule_score": rule_score,
                "ml_score": None,
                "risk_factors": rule_result.get("risk_factors", []),
                "rule_result": rule_result,
                "ml_result": None
            }
        
        # Extract ML score
        ml_score = ml_result.get("score", 0)
        
        # ====================================================================
        # FUSION STRATEGY: Weighted Average
        # ====================================================================
        
        combined_score = (
            (rule_score * self.rule_weight) +
            (ml_score * self.ml_weight)
        )
        
        # Determine combined status
        combined_status = self._determine_status(combined_score)
        
        # ====================================================================
        # RISK FACTOR AGGREGATION
        # ====================================================================
        
        risk_factors = []
        
        # Add rule-based factors
        risk_factors.extend(rule_result.get("risk_factors", []))
        
        # Add ML-based factors
        if ml_result.get("high_default_risk"):
            risk_factors.append("High payment default probability (ML prediction)")
        
        if ml_result.get("fraud_detected"):
            risk_factors.append("Anomalous trading pattern (ML fraud detector)")
        
        if ml_result.get("credit_limit_exceeded"):
            risk_factors.append("Recommended credit limit exceeded (ML optimizer)")
        
        # ====================================================================
        # BUILD UNIFIED RESULT
        # ====================================================================
        
        return {
            "score": round(combined_score, 2),
            "status": combined_status,
            "blocked": False,
            "blocking_reason": None,
            "method": "hybrid_ml_rules",
            "confidence": "high",
            
            # Individual scores
            "rule_score": rule_score,
            "ml_score": ml_score,
            
            # Weights used
            "rule_weight": self.rule_weight,
            "ml_weight": self.ml_weight,
            
            # Combined risk factors
            "risk_factors": risk_factors,
            
            # Full engine outputs (for debugging)
            "rule_result": rule_result,
            "ml_result": ml_result
        }
    
    def _determine_status(self, score: float) -> str:
        """Determine status from combined score."""
        if score >= 80:
            return "PASS"
        elif score >= 60:
            return "WARN"
        else:
            return "FAIL"
```

---

## 3. CIRCUIT BREAKER (ML Failure Handling)

### Purpose
- **Prevents** repeated calls to failing ML engine
- **Opens** after N consecutive failures
- **Resets** after timeout period
- **Protects** system from ML cascading failures

### Implementation

```python
# backend/modules/risk/orchestrator/circuit_breaker.py

from datetime import datetime, timedelta
from typing import Optional


class CircuitBreaker:
    """
    Circuit breaker for ML Engine failures.
    
    States:
    - CLOSED: Normal operation (ML engine called)
    - OPEN: Too many failures (ML engine NOT called)
    - HALF_OPEN: Testing if ML recovered (single retry)
    
    Example:
    - ML fails 5 times in a row
    - Circuit opens (ML engine stopped)
    - System uses rules-only for 5 minutes
    - Circuit half-opens (test single call)
    - If success → Close, if fail → Open again
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 300  # 5 minutes
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        
        # State tracking
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit is open (blocking ML calls)."""
        
        if self.state == "CLOSED":
            return False
        
        if self.state == "OPEN":
            # Check if timeout expired
            if self._timeout_expired():
                self.state = "HALF_OPEN"
                return False  # Allow one retry
            return True
        
        # HALF_OPEN state
        return False
    
    def record_failure(self):
        """Record ML failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"🚨 Circuit Breaker OPENED: ML Engine failed {self.failure_count} times. "
                f"Switching to rules-only mode for {self.timeout_seconds} seconds."
            )
    
    def record_success(self):
        """Record ML success (reset failures)."""
        if self.state == "HALF_OPEN":
            # Success in half-open state → Close circuit
            self.reset()
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info("✅ Circuit Breaker CLOSED: ML Engine recovered.")
        
        # Reset failure count on any success
        self.failure_count = 0
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def _timeout_expired(self) -> bool:
        """Check if timeout period has expired."""
        if not self.last_failure_time:
            return True
        
        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout_seconds
    
    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "timeout_seconds": self.timeout_seconds,
            "is_open": self.is_open()
        }
```

---

## 4. RULE ENGINE (Keep Existing)

### Changes Required
- **Move** `backend/modules/risk/risk_engine.py` → `backend/modules/risk/rule_engine/risk_engine.py`
- **No code changes** - Keep implementation exactly as-is
- **Add** `__init__.py` for module

```python
# backend/modules/risk/rule_engine/__init__.py

from backend.modules.risk.rule_engine.risk_engine import RuleEngine

__all__ = ["RuleEngine"]
```

### Existing Implementation (Keep)
```python
# backend/modules/risk/rule_engine/risk_engine.py
# NO CHANGES - Keep existing 1,273 lines exactly as-is

class RuleEngine:
    async def comprehensive_check(...):
        # Instant blocking rules
        circular = await self.check_circular_trading_settlement_based(...)
        wash = await self.check_wash_trading(...)
        party_links = await self.check_party_links(...)
        
        # Credit validation
        credit_check = await self.assess_buyer_risk(...)
        
        # Return deterministic result
        return {
            "score": ...,
            "status": ...,
            "blocked": ...,
            "risk_factors": ...
        }
```

---

## 5. ML ENGINE (Keep Existing)

### Changes Required
- **Move** `backend/modules/risk/ml_risk_model.py` → `backend/modules/risk/ml_engine/ml_risk_model.py`
- **Rename class** `MLRiskModel` → `MLRiskEngine` (for consistency)
- **Add** actual performance data collection

```python
# backend/modules/risk/ml_engine/__init__.py

from backend.modules.risk.ml_engine.ml_risk_model import MLRiskEngine

__all__ = ["MLRiskEngine"]
```

### Implementation (Rename + Enhance)
```python
# backend/modules/risk/ml_engine/ml_risk_model.py

class MLRiskEngine:  # Renamed from MLRiskModel
    """
    ML-based risk prediction engine.
    
    Models:
    - Payment default predictor (RandomForest)
    - Credit limit optimizer (GradientBoosting)
    - Fraud detector (IsolationForest)
    
    Training:
    - Uses actual performance data from production
    - Auto-retrains weekly on new data
    - Tracks prediction accuracy
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Load pre-trained models
        self.payment_default_model = ...
        self.credit_limit_model = ...
        self.fraud_detector = ...
    
    async def predict_risk(
        self,
        partner_id: UUID,
        transaction_type: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Generate ML-based risk predictions.
        
        Returns:
            {
                "score": 0-100,
                "default_probability": 0.0-1.0,
                "recommended_credit_limit": Decimal,
                "fraud_score": 0.0-1.0,
                "high_default_risk": bool,
                "fraud_detected": bool,
                "credit_limit_exceeded": bool
            }
        """
        
        # Get partner features
        features = await self._extract_features(partner_id)
        
        # Run ML predictions
        default_prob = self.payment_default_model.predict_proba(features)[0][1]
        credit_limit = self.credit_limit_model.predict(features)[0]
        fraud_score = self.fraud_detector.score_samples(features)[0]
        
        # Calculate ML score (0-100)
        ml_score = self._calculate_ml_score(
            default_prob=default_prob,
            fraud_score=fraud_score,
            credit_limit=credit_limit,
            amount=amount
        )
        
        return {
            "score": ml_score,
            "default_probability": default_prob,
            "recommended_credit_limit": Decimal(str(credit_limit)),
            "fraud_score": fraud_score,
            "high_default_risk": default_prob > 0.15,  # 15% threshold
            "fraud_detected": fraud_score < -0.5,  # Anomaly threshold
            "credit_limit_exceeded": amount > Decimal(str(credit_limit))
        }
```

---

## 6. SERVICE LAYER INTEGRATION

### Update Risk Service to Use Orchestrator

```python
# backend/modules/risk/services/risk_service.py

from backend.modules.risk.orchestrator.unified_risk_orchestrator import (
    UnifiedRiskOrchestrator
)


class RiskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Use orchestrator as single entry point
        self.orchestrator = UnifiedRiskOrchestrator(
            db=db,
            enable_ml=True,
            ml_weight=0.30  # 30% ML, 70% Rules
        )
    
    async def assess_risk(self, **kwargs):
        """Main risk assessment endpoint."""
        return await self.orchestrator.comprehensive_check(**kwargs)
    
    async def assess_rules_only(self, **kwargs):
        """Rules-only assessment (skip ML)."""
        return await self.orchestrator.check_rules_only(**kwargs)
    
    async def get_circuit_breaker_status(self):
        """Get ML circuit breaker status."""
        return self.orchestrator.ml_circuit_breaker.get_status()
```

---

## 7. ADVANTAGES OF THIS ARCHITECTURE

### ✅ Separation of Concerns
```
RuleEngine:
- Handles regulatory/compliance rules
- 100% deterministic
- Auditable by regulators
- Never changes (stable)

MLRiskEngine:
- Handles AI predictions
- Non-deterministic
- Advisory only
- Frequently updated (model retraining)

Orchestrator:
- Coordinates both
- Handles failures
- Combines outputs
- Single entry point
```

### ✅ Zero Downtime
```
If ML crashes:
┌─────────────────────┐
│ ML Engine Failed ❌ │
└─────────────────────┘
         ↓
┌─────────────────────┐
│ Circuit Opens       │
│ ML calls stopped    │
└─────────────────────┘
         ↓
┌─────────────────────┐
│ RuleEngine continues│
│ Rules-only mode ✅  │
└─────────────────────┘
         ↓
System still works!
```

### ✅ Independent Evolution
```
Update RuleEngine:
- Add new compliance rule
- No ML retraining needed
- Deploy independently

Update MLRiskEngine:
- Retrain models on new data
- No rule changes needed
- Test in shadow mode first
- Deploy independently
```

### ✅ Regulatory Compliance
```
Auditor asks: "How do you block wash trading?"

Answer: 
"RuleEngine.check_wash_trading() - Line 1042
 Deterministic SQL query, no AI involved."

Auditor: ✅ Approved

vs.

"ML model predicts wash trading risk"

Auditor: ❌ Not acceptable (black box)
```

### ✅ Testing & Debugging
```
# Test rules only
result = await orchestrator.check_rules_only(...)

# Test ML only
result = await orchestrator.check_ml_only(...)

# Test combined
result = await orchestrator.comprehensive_check(...)

# Compare outputs
assert rule_result["score"] != ml_result["score"]
```

---

## 8. MIGRATION PLAN

### Phase 1: Create Orchestrator (Week 1)
```bash
# Create new directories
mkdir -p backend/modules/risk/orchestrator
mkdir -p backend/modules/risk/rule_engine
mkdir -p backend/modules/risk/ml_engine

# Create orchestrator files
touch backend/modules/risk/orchestrator/__init__.py
touch backend/modules/risk/orchestrator/unified_risk_orchestrator.py
touch backend/modules/risk/orchestrator/fusion_layer.py
touch backend/modules/risk/orchestrator/circuit_breaker.py
```

### Phase 2: Move Existing Engines (Week 1)
```bash
# Move rule engine
mv backend/modules/risk/risk_engine.py \
   backend/modules/risk/rule_engine/risk_engine.py

# Move ML engine
mv backend/modules/risk/ml_risk_model.py \
   backend/modules/risk/ml_engine/ml_risk_model.py

# Update imports across codebase
# (automated with IDE refactoring)
```

### Phase 3: Update Services (Week 2)
```python
# OLD: Direct engine usage
from backend.modules.risk.risk_engine import RiskEngine

risk_engine = RiskEngine(db)
result = await risk_engine.comprehensive_check(...)

# NEW: Orchestrator usage
from backend.modules.risk.orchestrator import UnifiedRiskOrchestrator

orchestrator = UnifiedRiskOrchestrator(db)
result = await orchestrator.comprehensive_check(...)
```

### Phase 4: Parallel Run (Week 3)
```python
# Run OLD and NEW side-by-side
old_result = await old_risk_engine.comprehensive_check(...)
new_result = await orchestrator.comprehensive_check(...)

# Compare results
if old_result["score"] != new_result["score"]:
    logger.warning(f"Score mismatch: OLD={old_result['score']}, NEW={new_result['score']}")
```

### Phase 5: Full Cutover (Week 4)
```python
# Remove old code
# Use orchestrator everywhere
orchestrator = UnifiedRiskOrchestrator(db)
```

---

## 9. CONFIGURATION OPTIONS

### ML Weight Adjustment
```python
# Conservative: 90% Rules, 10% ML
orchestrator.set_ml_weight(0.10)

# Balanced: 70% Rules, 30% ML (default)
orchestrator.set_ml_weight(0.30)

# Aggressive: 50% Rules, 50% ML
orchestrator.set_ml_weight(0.50)

# Rules-only: 100% Rules, 0% ML
orchestrator.enable_ml_engine(False)
```

### Circuit Breaker Tuning
```python
# Sensitive: Open after 3 failures
orchestrator.ml_circuit_breaker.failure_threshold = 3

# Tolerant: Open after 10 failures
orchestrator.ml_circuit_breaker.failure_threshold = 10

# Quick recovery: Reset after 1 minute
orchestrator.ml_circuit_breaker.timeout_seconds = 60

# Slow recovery: Reset after 30 minutes
orchestrator.ml_circuit_breaker.timeout_seconds = 1800
```

---

## 10. MONITORING & METRICS

### Dashboard Metrics
```python
{
    "orchestrator": {
        "total_checks": 12847,
        "rule_engine": {
            "executions": 12847,
            "failures": 0,
            "avg_latency_ms": 45,
            "blocks": 234  # Instant blocks
        },
        "ml_engine": {
            "executions": 12613,  # 234 skipped (instant blocks)
            "failures": 12,
            "success_rate": 0.999,
            "avg_latency_ms": 287,
            "circuit_breaker_state": "CLOSED"
        },
        "fusion_layer": {
            "weighted_avg_scores": 12613,
            "avg_combined_score": 82.5,
            "ml_weight": 0.30,
            "rule_weight": 0.70
        }
    }
}
```

### Alerting Rules
```yaml
alerts:
  - name: "ML Circuit Breaker Open"
    condition: "ml_circuit_breaker.state == 'OPEN'"
    severity: "warning"
    action: "Check ML engine logs, retrain models"
  
  - name: "High ML Failure Rate"
    condition: "ml_failure_rate > 0.05"  # >5%
    severity: "warning"
    action: "Investigate ML model quality"
  
  - name: "Rule Engine Failure"
    condition: "rule_engine_failures > 0"
    severity: "critical"
    action: "Page oncall (rules should never fail)"
```

---

## 11. COMPARISON: Merged vs Orchestrated

| Aspect | Merged Engine ❌ | Dual Engine + Orchestrator ✅ |
|--------|------------------|-------------------------------|
| **Separation** | Rules + ML mixed together | Clear separation (rule_engine/, ml_engine/) |
| **Testing** | Hard to test separately | Easy to test each engine |
| **ML Failure** | Whole engine affected | Only ML disabled, rules continue |
| **Regulatory** | Auditors see ML + rules | Auditors see pure rules (RuleEngine) |
| **Updates** | Change affects both | Update independently |
| **Debugging** | Hard to isolate issues | Clear which engine caused issue |
| **Evolution** | Coupled evolution | Independent evolution |
| **Complexity** | High coupling | Low coupling, high cohesion |

---

## 12. CONCLUSION

### Your Proposal: ✅ CORRECT APPROACH

```
backend/modules/risk/
├── orchestrator/
│   └── unified_risk_orchestrator.py   ← Single entry point
├── rule_engine/
│   └── risk_engine.py                 ← Deterministic checks
└── ml_engine/
    └── ml_risk_model.py               ← AI predictions
```

### Why This is Better:

1. **Keeps both engines intact** (no risky merging)
2. **Clear separation** (rules vs predictions)
3. **Independent testing** (test each engine separately)
4. **Graceful degradation** (ML fails → rules continue)
5. **Regulatory approved** (rules are auditable)
6. **Future-proof** (easy to update either engine)
7. **Zero downtime** (circuit breaker protects system)

### Next Steps:

1. ✅ **Approve this architecture**
2. Create orchestrator files (Week 1)
3. Move existing engines to subdirectories (Week 1)
4. Update service layer to use orchestrator (Week 2)
5. Parallel run testing (Week 3)
6. Full cutover (Week 4)

---

**Status**: RECOMMENDED ARCHITECTURE ✅  
**Timeline**: 4 weeks implementation  
**Risk**: LOW (keeps existing code, adds orchestration layer)  
**Benefit**: HIGH (best of both worlds - rules + AI)
