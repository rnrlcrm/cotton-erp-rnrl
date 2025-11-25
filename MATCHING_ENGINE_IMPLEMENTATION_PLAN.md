# MATCHING ENGINE - IMPLEMENTATION PLAN

**Engine 3:** Bilateral Matching & Trade Proposal Generation  
**Status:** 🟡 AWAITING APPROVAL  
**Branch:** `feat/trade-desk-matching-engine`  
**Prerequisites:** ✅ Availability Engine, ✅ Requirement Engine, ✅ Risk Engine  
**Estimated Timeline:** 6-8 days

---

## 📋 EXECUTIVE SUMMARY

**Purpose:** The Matching Engine is the intelligent heart of the trading platform - it automatically matches buyers with sellers, scores compatibility, validates risk, and generates trade proposals ready for execution.

**What It Does:**
- **Bilateral Matching:** Finds compatible Requirement-Availability pairs
- **Multi-Factor Scoring:** Quality, price, location, risk, delivery timeline
- **Risk Integration:** Validates party links, circular trading, credit limits
- **Trade Proposal Generation:** Creates executable trade contracts
- **Real-Time Notifications:** Alerts both parties when good matches are found

**Key Innovation:** Unlike traditional matching that only checks "does it fit?", our engine scores "how well does it fit?" (0.0 to 1.0) and explains WHY, enabling intelligent prioritization.

---

## 🎯 BUSINESS REQUIREMENTS

### Core Functionality

1. **Location-First Hard Filtering** ⭐ CRITICAL
   - **BEFORE** any scoring, filter by exact location match
   - Buyer sees ONLY sellers in their selected location region
   - Sellers see ONLY buyers in their delivery area
   - NO cross-state/cross-region spam
   - NO random marketplace-like broadcasts
   - Location mismatch = immediate skip (no scoring needed)

2. **Event-Driven Auto-Matching** ⭐ CRITICAL
   - **Primary Trigger:** Real-time events
     - `requirement.created`
     - `requirement.updated` (location/qty/params changed)
     - `availability.created`
     - `availability.updated`
     - `risk_status.changed` (FAIL → PASS unlocks match)
   - **Safety Net:** Optional 15-30s cron (fallback only)
   - NO batch processing as primary mechanism

3. **Intelligent Scoring Algorithm**
   - Quality parameter compatibility (40%)
   - Price competitiveness (30%)
   - Delivery logistics (15%)
   - Risk assessment (15%)
   - Combined score: 0.0 (poor match) to 1.0 (perfect match)
   - **Configurable per commodity** (not hardcoded)

4. **Risk Integration with Clear WARN Semantics** ⭐ CRITICAL
   - **PASS** (score ≥ 80): risk_score = 1.0, proceed normally
   - **WARN** (score 60-79): Allow with warning + 10% global score penalty
   - **FAIL** (score < 60): Block match completely (risk_score = 0.0)
   - Risk checks:
     - Party links validation
     - Circular trading prevention
     - Role restrictions (buyer/seller/trader)
     - Credit limit validation
     - Internal branch trade blocking (if configured)

5. **Atomic Partial Matching** ⭐ CRITICAL
   - If seller has 10 tons, buyer wants 6 tons → match for 6
   - Remaining 4 tons stays available for OTHER buyers in SAME location
   - **Optimistic locking** prevents double-allocation
   - **Row-level DB transaction** ensures atomicity
   - Concurrent reservation tests required

6. **Trade Proposal Generation**
   - Create trade proposal from matched pair
   - Pre-fill terms (price, quantity, delivery)
   - Include risk assessment results
   - Ready for buyer/seller approval

7. **Smart Notifications with Rate Limiting** ⭐ CRITICAL
   - Notify ONLY location-matched parties
   - Top N matches (default: 5, user-configurable)
   - **Rate limiting:** Max 1 push per seller per minute (debounce)
   - **User preferences:** Opt-in/opt-out for push/email/SMS
   - Real-time WebSocket alerts
   - Dashboard badges for new matches

### Match Lifecycle ⭐ UPDATED WITH LOCATION-FIRST

```text
NEW REQUIREMENT/AVAILABILITY POSTED
            ↓
    Event Published (requirement.created/availability.created)
            ↓
    Matching Engine Triggered (Real-Time)
            ↓
    🔸 LOCATION-FIRST HARD FILTER 🔸
    (Skip if location doesn't match - NO SCORING)
            ↓
    Find Compatible Counterparts (Location-Matched Pool Only)
            ↓
    Calculate Match Scores (0.0-1.0)
            ↓
    Filter by Min Score (commodity-specific, default ≥0.6)
            ↓
    Validate Risk (Party Links, Circular Trading, Credit)
            ↓
    Apply WARN Penalty (if risk=WARN → -10% global score)
            ↓
    Sort by Score (Best First)
            ↓
    Check Duplicate Detection (5min window, 95% similarity)
            ↓
    Atomic Allocation (Optimistic Locking for Partial Qty)
            ↓
    Store Match Details (Audit Trail with Score Breakdown)
            ↓
    Notify Matched Parties (Rate-Limited, User Preferences)
            ↓
    READY FOR APPROVAL/NEGOTIATION
```

---

## 🏗️ TECHNICAL ARCHITECTURE

### Configuration System ⭐ NEW

**File:** `backend/modules/trade_desk/config/matching_config.py`

```python
class MatchingConfig:
    """
    Per-commodity configurable matching parameters.
    Runtime-tunable via admin settings.
    """
    
    # Scoring weights (per commodity)
    SCORING_WEIGHTS = {
        "default": {
            "quality": 0.40,
            "price": 0.30,
            "delivery": 0.15,
            "risk": 0.15
        },
        "COTTON": {  # Example override
            "quality": 0.45,  # Cotton quality more critical
            "price": 0.25,
            "delivery": 0.15,
            "risk": 0.15
        }
    }
    
    # Min score threshold (per commodity)
    MIN_SCORE_THRESHOLD = {
        "default": 0.6,
        "GOLD": 0.7,  # Higher bar for precious metals
        "WHEAT": 0.5  # More lenient for grains
    }
    
    # Duplicate detection
    DUPLICATE_TIME_WINDOW_MINUTES = 5
    DUPLICATE_SIMILARITY_THRESHOLD = 0.95  # 95% param match
    
    # Notification settings
    MAX_MATCHES_TO_NOTIFY = 5  # Top N only
    NOTIFICATION_RATE_LIMIT_SECONDS = 60  # Max 1 per user per minute
    
    # Partial matching
    ENABLE_PARTIAL_MATCHING = True
    MIN_PARTIAL_QUANTITY_PERCENT = 10  # Minimum 10% of required qty
    
    # Performance tuning
    MATCH_BATCH_SIZE = 100  # For high-volume scenarios
    MATCH_BATCH_DELAY_MS = 1000  # 1s micro-batching
    
    # Risk WARN penalty
    RISK_WARN_GLOBAL_PENALTY = 0.10  # -10% to final score
```

### Database Schema Changes

**No new tables needed!** Matching Engine operates on existing tables:

- ✅ `requirements` (Engine 2)
- ✅ `availabilities` (Engine 1)
- ✅ `business_partners` (existing)
- ✅ `commodities` (existing)
- ✅ `settings_locations` (existing)

**New Indexes for Performance:**

```sql
-- Location-first filtering optimization
CREATE INDEX idx_requirements_location_status 
ON requirements(delivery_location_id, status) 
WHERE status = 'ACTIVE';

CREATE INDEX idx_availabilities_location_status 
ON availabilities(location_id, status) 
WHERE status = 'AVAILABLE';

-- Concurrent allocation (optimistic locking)
ALTER TABLE availabilities ADD COLUMN version INTEGER DEFAULT 1;
CREATE INDEX idx_availabilities_version ON availabilities(version);
```

**Audit Trail Table (for match explainability):**

```sql
CREATE TABLE match_audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID REFERENCES requirements(id),
    availability_id UUID REFERENCES availabilities(id),
    match_score NUMERIC(5, 4),  -- 0.0000 to 1.0000
    score_breakdown JSONB NOT NULL,  -- Quality/Price/Delivery/Risk scores
    risk_assessment JSONB NOT NULL,  -- Risk engine full results
    location_filter_passed BOOLEAN,
    duplicate_detection_result JSONB,
    allocation_status VARCHAR(20),  -- SUCCESS, PARTIAL, FAILED
    allocated_quantity NUMERIC(15, 3),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_match_audit_requirement ON match_audit_trail(requirement_id);
CREATE INDEX idx_match_audit_availability ON match_audit_trail(availability_id);
```

**Future Enhancement (Engine 5 - Trade Execution):**
```sql
CREATE TABLE trade_proposals (
    id UUID PRIMARY KEY,
    requirement_id UUID REFERENCES requirements(id),
    availability_id UUID REFERENCES availabilities(id),
    match_score NUMERIC(5, 4),  -- 0.0000 to 1.0000
    match_details JSONB,         -- Breakdown of score components
    risk_assessment JSONB,       -- Risk engine results
    proposed_price NUMERIC(18, 2),
    proposed_quantity NUMERIC(15, 3),
    status VARCHAR(20),          -- DRAFT, PROPOSED, ACCEPTED, REJECTED, EXPIRED
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);
```
*Note: We'll implement this in Engine 5 (Trade Execution). For now, matching returns results in-memory.*

---

## 📁 FILE STRUCTURE

```
backend/modules/trade_desk/
├── matching/
│   ├── __init__.py
│   ├── matching_engine.py          # ⭐ CORE: Matching algorithm
│   ├── scoring.py                   # Score calculation logic
│   ├── validators.py                # Match validation rules
│   └── events.py                    # Match-related events
│
├── models/
│   ├── requirement.py               # ✅ EXISTS (add match methods)
│   └── availability.py              # ✅ EXISTS (add match methods)
│
├── repositories/
│   ├── requirement_repository.py    # ✅ EXISTS (add search_compatible_availabilities)
│   └── availability_repository.py   # ✅ EXISTS (add search_compatible_requirements)
│
├── services/
│   ├── requirement_service.py       # ✅ EXISTS (integrate matching)
│   ├── availability_service.py      # ✅ EXISTS (integrate matching)
│   └── matching_service.py          # NEW: High-level matching orchestration
│
├── routes/
│   ├── matching_router.py           # NEW: Matching API endpoints
│   ├── requirement_router.py        # UPDATE: Add find-matches endpoint
│   └── availability_router.py       # UPDATE: Add find-matches endpoint
│
└── tests/
    ├── test_matching_engine.py      # NEW: Core matching tests
    ├── test_matching_scoring.py     # NEW: Scoring algorithm tests
    └── test_matching_risk.py        # NEW: Risk integration tests
```

**Estimated New Files:** 8 new files  
**Estimated Updates:** 6 existing files  
**Total Lines of Code:** ~3,500 lines

---

## 🔧 IMPLEMENTATION PHASES

### Phase 1: Core Matching Engine (Days 1-2)

**File:** `backend/modules/trade_desk/matching/matching_engine.py`

#### Key Classes:

```python
class MatchingEngine:
    """
    Core matching engine for Requirement-Availability pairing.
    
    CRITICAL DESIGN PRINCIPLES:
    1. Location-First Hard Filter (before any scoring)
    2. Event-Driven Triggers (no cron as primary)
    3. Atomic Partial Allocation (optimistic locking)
    4. Audit Trail for Explainability
    
    Responsibilities:
    - Find compatible counterparts (bidirectional)
    - Calculate match scores (0.0-1.0)
    - Validate matches against risk rules
    - Sort and rank matches
    - Generate trade proposals (future)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        risk_engine: RiskEngine,
        requirement_repo: RequirementRepository,
        availability_repo: AvailabilityRepository,
        config: MatchingConfig
    ):
        self.db = db
        self.risk_engine = risk_engine
        self.requirement_repo = requirement_repo
        self.availability_repo = availability_repo
        self.config = config
    
    # ========================================================================
    # LOCATION-FIRST HARD FILTER ⭐ CRITICAL
    # ========================================================================
    
    def _location_matches(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> bool:
        """
        Hard location filter - BEFORE any scoring.
        
        Rules:
        - Buyer's delivery_location must match seller's location region
        - NO cross-state/cross-region matches
        - NO marketplace-like broadcasts
        
        Returns:
            True if locations compatible, False to skip immediately
        """
        # Exact location match OR same region/state
        if requirement.delivery_location_id == availability.location_id:
            return True
        
        # Check if both locations in same state/region
        req_location = requirement.delivery_location  # Eager loaded
        avail_location = availability.location
        
        if req_location.state_id == avail_location.state_id:
            # Within same state - check district/region rules
            return self._check_regional_compatibility(req_location, avail_location)
        
        return False  # Different states = NO MATCH
    
    # ========================================================================
    # BIDIRECTIONAL MATCHING
    # ========================================================================
    
    async def find_matches_for_requirement(
        self,
        requirement_id: UUID,
        min_score: Optional[float] = None,
        include_risk_check: bool = True,
        max_results: int = 50
    ) -> List[MatchResult]:
        """
        Find compatible availabilities for a requirement.
        
        CRITICAL FLOW:
        1. Fetch requirement with location data
        2. Query availabilities FILTERED BY LOCATION (DB-level)
        3. For each candidate, apply location hard filter
        4. ONLY THEN calculate scores
        5. Apply duplicate detection
        6. Validate risk
        7. Sort and return top matches
        
        Args:
            requirement_id: Requirement UUID
            min_score: Minimum match score (commodity-specific if None)
            include_risk_check: Whether to validate with risk engine
            max_results: Maximum number of matches to return
            
        Returns:
            List of MatchResult objects sorted by score (best first)
        """
        # Get requirement with location
        requirement = await self.requirement_repo.get_by_id(
            requirement_id,
            eager_load=["delivery_location", "commodity", "buyer_partner"]
        )
        
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        # Get commodity-specific min score
        if min_score is None:
            commodity_code = requirement.commodity.code
            min_score = self.config.get_min_score_threshold(commodity_code)
        
        # Step 1: LOCATION-FIRST FILTER (DB query level)
        candidate_availabilities = await self.availability_repo.search_by_location(
            location_id=requirement.delivery_location_id,
            commodity_id=requirement.commodity_id,
            status="AVAILABLE",
            eager_load=["location", "seller", "commodity"]
        )
        
        matches = []
        seen_duplicates = set()  # For duplicate detection
        
        for availability in candidate_availabilities:
            # Step 2: Hard location filter (application level)
            if not self._location_matches(requirement, availability):
                continue  # SKIP - no scoring needed
            
            # Step 3: Duplicate detection
            dup_key = self._generate_duplicate_key(requirement, availability)
            if self._is_duplicate(dup_key, seen_duplicates):
                continue  # SKIP duplicate
            
            # Step 4: Calculate match score
            score_result = await self.calculate_match_score(
                requirement=requirement,
                availability=availability,
                include_risk_check=include_risk_check
            )
            
            # Step 5: Filter by min score
            if score_result["total_score"] < min_score:
                continue
            
            # Step 6: Create match result with audit trail
            match = MatchResult(
                requirement_id=requirement.id,
                availability_id=availability.id,
                score=score_result["total_score"],
                score_breakdown=score_result["breakdown"],
                risk_assessment=score_result.get("risk_details"),
                location_filter_passed=True,
                duplicate_detection_key=dup_key
            )
            
            matches.append(match)
            seen_duplicates.add(dup_key)
        
        # Step 7: Sort by score (best first)
        matches.sort(key=lambda m: m.score, reverse=True)
        
        # Step 8: Store audit trail
        await self._save_match_audit_trail(matches, requirement)
        
        return matches[:max_results]
    
    async def find_matches_for_availability(
        self,
        availability_id: UUID,
        min_score: Optional[float] = None,
        include_risk_check: bool = True,
        max_results: int = 50
    ) -> List[MatchResult]:
        """
        Find compatible requirements for an availability.
        Same location-first logic as find_matches_for_requirement.
        """
        # Similar implementation with location-first filter
        pass
    
    # ========================================================================
    # MATCH SCORING WITH RISK WARN PENALTY ⭐ CRITICAL
    # ========================================================================
    
    async def calculate_match_score(
        self,
        requirement: Requirement,
        availability: Availability,
        include_risk_check: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive match score with breakdown.
        
        CRITICAL: WARN risk status applies 10% GLOBAL penalty
        
        Returns:
        {
            "total_score": 0.765,          # After WARN penalty if applicable
            "base_score": 0.85,            # Before WARN penalty
            "warn_penalty_applied": True,
            "breakdown": {
                "quality_score": 0.92,     # 40% weight
                "price_score": 0.78,       # 30% weight
                "delivery_score": 0.88,    # 15% weight
                "risk_score": 0.85         # 15% weight (WARN → affects this)
            },
            "pass_fail": {
                "quality_pass": True,
                "price_pass": True,
                "quantity_pass": True,
                "delivery_pass": True,
                "risk_pass": True          # WARN still passes
            },
            "risk_details": {
                "status": "WARN",
                "warnings": ["Same mobile number detected"],
                "global_penalty": 0.10     # -10% to final score
            },
            "gaps": [],
            "recommendations": "Good match but review warnings"
        }
        """
        # Calculate individual scores
        quality_result = await self.scorer.calculate_quality_score(
            requirement, availability
        )
        price_result = await self.scorer.calculate_price_score(
            requirement, availability
        )
        delivery_result = await self.scorer.calculate_delivery_score(
            requirement, availability
        )
        
        # Risk check with clear WARN semantics
        if include_risk_check:
            risk_result = await self.scorer.calculate_risk_score(
                requirement, availability, self.risk_engine
            )
            
            # Map risk status to score
            if risk_result["risk_status"] == "PASS":
                risk_score = 1.0
                warn_penalty = 0.0
            elif risk_result["risk_status"] == "WARN":
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
                    "blocked": True,
                    "risk_details": risk_result
                }
        else:
            risk_score = 1.0
            risk_result = {"risk_status": "SKIPPED"}
            warn_penalty = 0.0
        
        # Get commodity-specific weights
        commodity_code = requirement.commodity.code
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
        
        return {
            "total_score": round(final_score, 4),
            "base_score": round(base_score, 4),
            "warn_penalty_applied": warn_penalty > 0,
            "warn_penalty_value": warn_penalty,
            "breakdown": {
                "quality_score": quality_result["score"],
                "price_score": price_result["score"],
                "delivery_score": delivery_result["score"],
                "risk_score": risk_score
            },
            "pass_fail": {
                "quality_pass": quality_result["pass"],
                "price_pass": price_result["pass"],
                "quantity_pass": True,  # Checked in location filter
                "delivery_pass": delivery_result["pass"],
                "risk_pass": risk_result["risk_status"] != "FAIL"
            },
            "risk_details": risk_result,
            "gaps": [],
            "recommendations": self._generate_recommendations(
                final_score, risk_result["risk_status"]
            )
        }
    
    # ========================================================================
    # DUPLICATE DETECTION ⭐ CRITICAL
    # ========================================================================
    
    def _generate_duplicate_key(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> str:
        """
        Generate unique key for duplicate detection.
        
        Rules:
        - Same commodity
        - Same buyer-seller pair
        - Within 5-minute time window
        - 95%+ similar quality parameters
        """
        return f"{requirement.commodity_id}:{requirement.buyer_partner_id}:{availability.seller_id}"
    
    def _is_duplicate(
        self,
        dup_key: str,
        seen_duplicates: set,
        time_window_minutes: int = 5
    ) -> bool:
        """
        Check if match is duplicate within time window.
        
        Uses in-memory cache + DB check for recent duplicates.
        """
        if dup_key in seen_duplicates:
            return True
        
        # Check DB for recent duplicates (within time window)
        # Implementation in repository layer
        return False
    
    # ========================================================================
    # ATOMIC PARTIAL ALLOCATION ⭐ CRITICAL
    # ========================================================================
    
    async def allocate_quantity_atomic(
        self,
        availability_id: UUID,
        requested_quantity: Decimal,
        requirement_id: UUID
    ) -> Dict[str, Any]:
        """
        Atomically allocate quantity with optimistic locking.
        
        CRITICAL: Prevents double-allocation in concurrent scenarios.
        
        Algorithm:
        1. Read availability with current version
        2. Check if sufficient quantity available
        3. Update remaining_qty and increment version
        4. If version mismatch → retry
        
        Returns:
        {
            "allocated": True,
            "allocated_quantity": 6.0,
            "remaining_quantity": 4.0,
            "allocation_type": "PARTIAL",  # or "FULL"
            "version": 2
        }
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            async with self.db.begin():
                # Read with row-level lock
                availability = await self.db.execute(
                    select(Availability)
                    .where(Availability.id == availability_id)
                    .with_for_update()  # Pessimistic lock
                )
                availability = availability.scalar_one_or_none()
                
                if not availability:
                    return {"allocated": False, "error": "Availability not found"}
                
                # Check quantity
                if availability.remaining_quantity < requested_quantity:
                    # Partial allocation
                    allocated_qty = availability.remaining_quantity
                    allocation_type = "PARTIAL"
                else:
                    allocated_qty = requested_quantity
                    allocation_type = "FULL"
                
                if allocated_qty == 0:
                    return {"allocated": False, "error": "No quantity available"}
                
                # Optimistic locking check
                current_version = availability.version
                
                # Update
                availability.remaining_quantity -= allocated_qty
                availability.version += 1
                
                if availability.remaining_quantity == 0:
                    availability.status = "SOLD"
                
                await self.db.flush()
                
                return {
                    "allocated": True,
                    "allocated_quantity": float(allocated_qty),
                    "remaining_quantity": float(availability.remaining_quantity),
                    "allocation_type": allocation_type,
                    "version": availability.version
                }
        
        return {"allocated": False, "error": "Max retries exceeded"}
    
    # ========================================================================
    # AUDIT TRAIL ⭐ CRITICAL
    # ========================================================================
    
    async def _save_match_audit_trail(
        self,
        matches: List[MatchResult],
        entity: Union[Requirement, Availability]
    ) -> None:
        """
        Save detailed audit trail for explainability.
        
        Stores:
        - Full score breakdown
        - Risk assessment details
        - Location filter results
        - Duplicate detection results
        - Allocation status
        """
        # Implementation saves to match_audit_trail table
        pass
```

**Estimated Lines:** ~800 lines

---

### Phase 2: Scoring Algorithms (Days 2-3)

**File:** `backend/modules/trade_desk/matching/scoring.py`

#### Scoring Components:

```python
class MatchScorer:
    """
    Calculates individual score components for requirement-availability matching.
    
    Score Range: All scores are 0.0 (worst) to 1.0 (perfect)
    """
    
    # ========================================================================
    # QUALITY SCORING (40% weight)
    # ========================================================================
    
    @staticmethod
    def calculate_quality_score(
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Compare quality parameters with tolerances.
        
        Example (Cotton):
        - Requirement: staple_length min=28, max=32, preferred=30
        - Availability: staple_length=29
        - Score: 0.95 (very close to preferred)
        
        Algorithm:
        1. For each parameter in requirement:
           - If seller value within min/max range: score = 1.0
           - If seller value near preferred: bonus score
           - If seller value outside range: score = 0.0
        2. Weight each parameter by importance
        3. Return weighted average
        
        Returns:
        {
            "score": 0.92,
            "details": {
                "staple_length": {"score": 0.95, "pass": True},
                "micronaire": {"score": 0.88, "pass": True},
                "strength": {"score": 0.93, "pass": True}
            },
            "pass": True
        }
        """
    
    # ========================================================================
    # PRICE SCORING (30% weight)
    # ========================================================================
    
    @staticmethod
    def calculate_price_score(
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Compare seller price vs buyer budget.
        
        Example:
        - Buyer max budget: ₹61,000/bale
        - Buyer preferred price: ₹59,500/bale
        - Seller asking: ₹60,000/bale
        
        Algorithm:
        - If price <= preferred: score = 1.0
        - If price between preferred and max: 
            score = (max - price) / (max - preferred)
            score = (61000 - 60000) / (61000 - 59500) = 0.67
        - If price > max: score = 0.0
        
        Returns:
        {
            "score": 0.67,
            "pass": True,
            "details": {
                "seller_price": 60000,
                "buyer_max_budget": 61000,
                "buyer_preferred_price": 59500,
                "savings_vs_budget": 1000,
                "premium_vs_preferred": 500
            }
        }
        """
    
    # ========================================================================
    # DELIVERY SCORING (15% weight)
    # ========================================================================
    
    @staticmethod
    def calculate_delivery_score(
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Calculate logistics compatibility.
        
        Factors:
        1. Distance between delivery locations (Haversine formula)
        2. Delivery timeline compatibility
        3. Delivery terms matching (FOB, CIF, Ex-gin, etc.)
        
        Example:
        - Buyer location: Mumbai
        - Seller location: Ahmedabad (450 km away)
        - Buyer max distance: 500 km
        - Score: 1.0 - (450/500) = 0.90
        
        Returns:
        {
            "score": 0.90,
            "pass": True,
            "details": {
                "distance_km": 450,
                "buyer_max_distance": 500,
                "timeline_compatible": True,
                "terms_match": True
            }
        }
        """
    
    # ========================================================================
    # QUANTITY SCORING (Embedded in quality score)
    # ========================================================================
    
    @staticmethod
    def calculate_quantity_score(
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Check if seller has enough quantity.
        
        Example:
        - Buyer needs: min=200, max=500, preferred=300 bales
        - Seller has: 320 bales available
        
        Algorithm:
        - If available >= preferred: score = 1.0
        - If available >= min and < preferred:
            score = (available - min) / (preferred - min)
        - If available < min: score = available / min (partial order)
        
        Returns:
        {
            "score": 1.0,
            "pass": True,
            "details": {
                "buyer_preferred": 300,
                "buyer_min": 200,
                "buyer_max": 500,
                "seller_available": 320,
                "can_fulfill_preferred": True
            }
        }
        """
    
    # ========================================================================
    # RISK SCORING (15% weight)
    # ========================================================================
    
    async def calculate_risk_score(
        self,
        requirement: Requirement,
        availability: Availability,
        risk_engine: RiskEngine
    ) -> Dict[str, Any]:
        """
        Integrate with Risk Engine for compliance checks.
        
        Checks:
        1. Party links detection (same PAN/GST/mobile)
        2. Circular trading prevention (same-day reversals)
        3. Role restrictions (buyer can only buy, seller only sell)
        4. Credit limit validation
        5. Internal trade blocking (same branch)
        
        Risk Score Mapping:
        - PASS (score >= 80): risk_score = 1.0
        - WARN (score 60-79): risk_score = 0.5
        - FAIL (score < 60): risk_score = 0.0
        
        Returns:
        {
            "score": 1.0,
            "pass": True,
            "risk_status": "PASS",
            "risk_details": {
                "party_links": False,
                "circular_trading": False,
                "role_valid": True,
                "credit_ok": True,
                "internal_trade_blocked": False
            },
            "recommended_action": "APPROVE"
        }
        """
    
    # ========================================================================
    # COMBINED SCORE
    # ========================================================================
    
    @staticmethod
    def calculate_combined_score(
        quality_score: float,
        price_score: float,
        delivery_score: float,
        risk_score: float
    ) -> float:
        """
        Weighted average of all score components.
        
        Weights:
        - Quality: 40%
        - Price: 30%
        - Delivery: 15%
        - Risk: 15%
        
        Formula:
        combined = (quality * 0.40) + (price * 0.30) + 
                   (delivery * 0.15) + (risk * 0.15)
        
        Returns:
            Combined score from 0.0 to 1.0
        """
        return (
            quality_score * 0.40 +
            price_score * 0.30 +
            delivery_score * 0.15 +
            risk_score * 0.15
        )
```

**Estimated Lines:** ~600 lines

---

### Phase 3: Match Validation & Risk Integration (Day 3)

**File:** `backend/modules/trade_desk/matching/validators.py`

```python
class MatchValidator:
    """
    Validates match eligibility and applies business rules.
    """
    
    def __init__(self, risk_engine: RiskEngine):
        self.risk_engine = risk_engine
    
    # ========================================================================
    # PRE-MATCH VALIDATION
    # ========================================================================
    
    async def validate_match_eligibility(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Check if match is even possible (hard requirements).
        
        Hard Rules (must pass):
        1. Commodity must match
        2. Seller must have enough quantity (≥ min_quantity)
        3. Price must be within budget (≤ max_budget)
        4. Both parties active/approved
        5. Market visibility allows matching
        
        Returns:
        {
            "eligible": True/False,
            "reasons": []  # List of blocking reasons if ineligible
        }
        """
    
    # ========================================================================
    # RISK VALIDATION
    # ========================================================================
    
    async def validate_risk_compliance(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> Dict[str, Any]:
        """
        Call Risk Engine for comprehensive risk checks.
        
        Risk Checks:
        1. Party Links Detection
           - BLOCK if same PAN/GST
           - WARN if same mobile/email
        
        2. Circular Trading Prevention
           - BLOCK if same partner has opposite position same day
        
        3. Role Restrictions
           - BLOCK if buyer trying to sell or seller trying to buy
           - ALLOW traders to do both (but block same-day reversals)
        
        4. Credit Limit Validation
           - Check if both parties have sufficient credit
        
        5. Internal Trade Blocking
           - BLOCK if same branch (if configured)
        
        Returns:
        {
            "valid": True/False,
            "risk_status": "PASS/WARN/FAIL",
            "violations": [],
            "recommended_action": "APPROVE/REVIEW/REJECT"
        }
        """
        
        # Party links check
        party_link_result = await self.risk_engine.check_party_links(
            buyer_partner_id=requirement.buyer_partner_id,
            seller_partner_id=availability.seller_id
        )
        
        # Circular trading check (if trader)
        circular_trading_result = await self.risk_engine.check_circular_trading(
            partner_id=requirement.buyer_partner_id,
            commodity_id=requirement.commodity_id,
            transaction_type="BUY",
            trade_date=datetime.now().date()
        )
        
        # Role validation
        role_validation_result = await self.risk_engine.validate_partner_role(
            partner_id=requirement.buyer_partner_id,
            transaction_type="BUY"
        )
        
        # Combine results and determine overall status
        # ...
```

**Estimated Lines:** ~400 lines

---

### Phase 4: Matching Service (Days 4-5)

**File:** `backend/modules/trade_desk/services/matching_service.py`

```python
class MatchingService:
    """
    High-level orchestration for matching operations.
    
    CRITICAL DESIGN:
    1. Event-Driven Matching (no cron as primary)
    2. Rate-Limited Notifications (1 per user per minute)
    3. User Notification Preferences
    4. Throttling & Backpressure Handling
    
    Responsibilities:
    - Coordinate matching engine, scoring, and validation
    - Handle match notifications with rate limits
    - Manage match history/analytics
    - Integration point for other modules
    """
    
    def __init__(
        self,
        db: AsyncSession,
        matching_engine: MatchingEngine,
        event_publisher: EventPublisher,
        notification_service: NotificationService,
        config: MatchingConfig
    ):
        self.db = db
        self.matching_engine = matching_engine
        self.event_publisher = event_publisher
        self.notification_service = notification_service
        self.config = config
        self._notification_rate_limiter = {}  # user_id -> last_notified_at
        self._match_queue = asyncio.Queue()  # For throttling
    
    # ========================================================================
    # EVENT-DRIVEN MATCHING ⭐ CRITICAL
    # ========================================================================
    
    async def on_requirement_created(self, event: RequirementCreatedEvent) -> None:
        """
        Event handler: requirement.created
        
        Triggered immediately when new requirement posted.
        Finds matches and notifies sellers in matched location.
        """
        await self._enqueue_match_request(
            entity_type="requirement",
            entity_id=event.requirement_id,
            priority="HIGH"
        )
    
    async def on_requirement_updated(self, event: RequirementUpdatedEvent) -> None:
        """
        Event handler: requirement.updated
        
        Triggered when requirement location/qty/params change.
        Re-runs matching with new criteria.
        """
        # Check if location/qty/quality params changed
        if self._requires_rematch(event.changed_fields):
            await self._enqueue_match_request(
                entity_type="requirement",
                entity_id=event.requirement_id,
                priority="MEDIUM"
            )
    
    async def on_availability_created(self, event: AvailabilityCreatedEvent) -> None:
        """
        Event handler: availability.created
        
        Triggered immediately when new availability posted.
        Finds matches and notifies buyers in matched location.
        """
        await self._enqueue_match_request(
            entity_type="availability",
            entity_id=event.availability_id,
            priority="HIGH"
        )
    
    async def on_risk_status_changed(self, event: RiskStatusChangedEvent) -> None:
        """
        Event handler: risk_status.changed
        
        Triggered when risk status changes (e.g., FAIL → PASS).
        Re-runs matching for previously blocked pairs.
        """
        if event.new_status == "PASS" and event.old_status == "FAIL":
            # Previously blocked, now allowed - retry matching
            await self._enqueue_match_request(
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                priority="LOW"
            )
    
    # ========================================================================
    # THROTTLING & BACKPRESSURE ⭐ CRITICAL
    # ========================================================================
    
    async def _enqueue_match_request(
        self,
        entity_type: str,
        entity_id: UUID,
        priority: str
    ) -> None:
        """
        Enqueue match request with priority.
        
        Prevents overwhelming system when thousands of postings arrive.
        Processes prioritized queue (HIGH > MEDIUM > LOW).
        """
        request = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "priority": priority,
            "enqueued_at": datetime.utcnow()
        }
        
        await self._match_queue.put(request)
    
    async def _process_match_queue(self) -> None:
        """
        Background worker that processes match queue.
        
        Runs continuously, processes requests with throttling.
        Uses micro-batching (1-3s delay) for high volume.
        """
        while True:
            try:
                # Get batch of requests (up to MATCH_BATCH_SIZE)
                batch = []
                timeout = self.config.MATCH_BATCH_DELAY_MS / 1000
                
                try:
                    request = await asyncio.wait_for(
                        self._match_queue.get(),
                        timeout=timeout
                    )
                    batch.append(request)
                except asyncio.TimeoutError:
                    pass
                
                if not batch:
                    continue
                
                # Process batch
                for request in batch:
                    await self._execute_match_request(request)
                    
            except Exception as e:
                logger.error(f"Match queue processing error: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _execute_match_request(self, request: Dict) -> None:
        """Execute single match request from queue."""
        if request["entity_type"] == "requirement":
            await self.auto_match_on_new_post(
                entity_type="requirement",
                entity_id=request["entity_id"]
            )
        else:
            await self.auto_match_on_new_post(
                entity_type="availability",
                entity_id=request["entity_id"]
            )
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    async def find_and_notify_matches(
        self,
        requirement_id: Optional[UUID] = None,
        availability_id: Optional[UUID] = None,
        notify: bool = True,
        min_score: Optional[float] = None
    ) -> List[MatchResult]:
        """
        Find matches and optionally notify parties.
        
        CRITICAL: Only notifies location-matched parties with rate limiting.
        
        Use Cases:
        1. Buyer posts requirement → find availabilities, notify sellers
        2. Seller posts availability → find requirements, notify buyers
        3. Manual search → find matches without notifications
        
        Args:
            requirement_id: Search for this requirement
            availability_id: Search for this availability
            notify: Send notifications if True
            min_score: Minimum match score threshold
            
        Returns:
            List of MatchResult objects
        """
        if requirement_id:
            matches = await self.matching_engine.find_matches_for_requirement(
                requirement_id=requirement_id,
                min_score=min_score,
                include_risk_check=True
            )
            entity_type = "requirement"
            entity_id = requirement_id
        elif availability_id:
            matches = await self.matching_engine.find_matches_for_availability(
                availability_id=availability_id,
                min_score=min_score,
                include_risk_check=True
            )
            entity_type = "availability"
            entity_id = availability_id
        else:
            raise ValueError("Must provide requirement_id or availability_id")
        
        # Notify with rate limiting and user preferences
        if notify and matches:
            await self._notify_matches_with_rate_limit(
                matches=matches,
                entity_type=entity_type
            )
        
        return matches
    
    # ========================================================================
    # NOTIFICATION WITH RATE LIMITING & PREFERENCES ⭐ CRITICAL
    # ========================================================================
    
    async def _notify_matches_with_rate_limit(
        self,
        matches: List[MatchResult],
        entity_type: str
    ) -> None:
        """
        Send notifications with rate limiting and user preferences.
        
        CRITICAL RULES:
        1. Max 1 notification per user per minute (debounce)
        2. Only notify top N matches (user-configurable, default 5)
        3. Respect user opt-in/opt-out preferences
        4. Only notify location-matched parties
        """
        # Get top N matches (user-configurable)
        top_matches = matches[:self.config.MAX_MATCHES_TO_NOTIFY]
        
        for match in top_matches:
            # Determine who to notify
            if entity_type == "requirement":
                # Notify seller about buyer
                user_id = match.availability.seller_id
                notification_type = "BUYER_MATCH_FOUND"
                message = f"Buyer found in your area (score: {match.score:.1%})"
            else:
                # Notify buyer about seller
                user_id = match.requirement.buyer_partner_id
                notification_type = "SELLER_MATCH_FOUND"
                message = f"Seller found in your delivery area (score: {match.score:.1%})"
            
            # Check user notification preferences
            preferences = await self._get_user_notification_preferences(user_id)
            if not preferences.get("notify_on_match", True):
                continue  # User opted out
            
            # Rate limiting check
            if not self._can_notify_user(user_id):
                continue  # User notified recently, skip
            
            # Send notification
            await self.notification_service.send(
                user_id=user_id,
                title="New Match Found!",
                message=message,
                notification_type=notification_type,
                channels=preferences.get("channels", ["PUSH"]),  # PUSH/EMAIL/SMS
                metadata={
                    "requirement_id": match.requirement_id,
                    "availability_id": match.availability_id,
                    "match_score": match.score,
                    "location_matched": True
                }
            )
            
            # Update rate limiter
            self._notification_rate_limiter[user_id] = datetime.utcnow()
    
    def _can_notify_user(self, user_id: UUID) -> bool:
        """
        Check if user can be notified (rate limit check).
        
        Returns True if:
        - User never notified before, OR
        - Last notification was > 60 seconds ago
        """
        last_notified = self._notification_rate_limiter.get(user_id)
        
        if not last_notified:
            return True
        
        elapsed = (datetime.utcnow() - last_notified).total_seconds()
        return elapsed >= self.config.NOTIFICATION_RATE_LIMIT_SECONDS
    
    async def _get_user_notification_preferences(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get user notification preferences.
        
        Returns:
        {
            "notify_on_match": True,  # Opt-in/opt-out
            "max_matches_to_notify": 5,  # User-specific override
            "channels": ["PUSH", "EMAIL"],  # SMS opt-out
            "quiet_hours": {"start": "22:00", "end": "08:00"}  # Future
        }
        """
        # Query user_settings table
        # Default to safe defaults if not configured
        return {
            "notify_on_match": True,
            "max_matches_to_notify": 5,
            "channels": ["PUSH"]
        }
    
    async def auto_match_on_new_post(
        self,
        entity_type: str,  # "requirement" or "availability"
        entity_id: UUID
    ) -> int:
        """
        Automatically run matching when new requirement/availability posted.
        
        Called by event handlers.
        
        Returns:
            Number of matches found
        """
        matches = await self.find_and_notify_matches(
            requirement_id=entity_id if entity_type == "requirement" else None,
            availability_id=entity_id if entity_type == "availability" else None,
            notify=True
        )
        
        return len(matches)
```

**Estimated Lines:** ~500 lines

---

### Phase 5: REST API Endpoints (Days 5-6)

**File:** `backend/modules/trade_desk/routes/matching_router.py`

```python
@router.post("/requirements/{id}/find-matches", response_model=MatchListResponse)
async def find_matches_for_requirement(
    id: UUID,
    filters: MatchFilters = Body(...),
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service)
):
    """
    Find compatible availabilities for a requirement.
    
    Request Body:
    {
        "min_score": 0.7,
        "max_results": 20,
        "include_risk_check": true,
        "filters": {
            "max_distance_km": 500,
            "max_price_variance": 5  // percent
        }
    }
    
    Response:
    {
        "matches": [
            {
                "availability_id": "uuid",
                "match_score": 0.85,
                "score_breakdown": {...},
                "risk_status": "PASS",
                "availability_details": {...}
            }
        ],
        "total_matches": 15,
        "best_match_score": 0.92
    }
    """

@router.post("/availabilities/{id}/find-matches", response_model=MatchListResponse)
async def find_matches_for_availability(
    id: UUID,
    filters: MatchFilters = Body(...),
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service)
):
    """
    Find compatible requirements for an availability.
    """

@router.get("/matches/{requirement_id}/{availability_id}", response_model=MatchDetailResponse)
async def get_match_details(
    requirement_id: UUID,
    availability_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service)
):
    """
    Get detailed match analysis for specific pair.
    """
```

**Estimated Lines:** ~400 lines

---

### Phase 6: Integration with Existing Engines (Day 6)

#### Update: `requirement_repository.py`

```python
# Add to RequirementRepository class

async def search_compatible_availabilities(
    self,
    requirement_id: UUID,
    min_score: float = 0.6,
    max_results: int = 50
) -> List[Tuple[Availability, float]]:
    """
    Search for compatible availabilities.
    
    This method is called by MatchingEngine.
    Returns raw query results for matching engine to score.
    """
    # Implementation using existing query patterns
```

#### Update: `availability_repository.py`

```python
# Add to AvailabilityRepository class

async def search_compatible_requirements(
    self,
    availability_id: UUID,
    min_score: float = 0.6,
    max_results: int = 50
) -> List[Tuple[Requirement, float]]:
    """
    Search for compatible requirements.
    
    This method is called by MatchingEngine.
    Returns raw query results for matching engine to score.
    """
    # Implementation using existing query patterns
```

#### Update: `requirement_service.py`

```python
# Add to RequirementService class

async def auto_match_on_create(
    self,
    requirement: Requirement
) -> int:
    """
    Automatically find matches after requirement creation.
    
    Called at end of create() method.
    """
    from backend.modules.trade_desk.services.matching_service import get_matching_service
    
    matching_service = get_matching_service(self.db)
    match_count = await matching_service.auto_match_on_new_post(
        entity_type="requirement",
        entity_id=requirement.id
    )
    
    return match_count
```

---

### Phase 7: Event System & Notifications (Day 7)

**File:** `backend/modules/trade_desk/matching/events.py`

```python
class MatchFoundEvent(DomainEvent):
    """
    Emitted when a good match (score >= threshold) is found.
    
    Subscribers:
    - NotificationService (email/SMS alerts)
    - WebSocketService (real-time updates)
    - AnalyticsService (track match quality)
    """
    
    event_type = "match.found"
    
    requirement_id: UUID
    availability_id: UUID
    match_score: float
    score_breakdown: Dict[str, Any]
    buyer_id: UUID
    seller_id: UUID


class MatchRejectedEvent(DomainEvent):
    """
    Emitted when match fails risk validation.
    """
    
    event_type = "match.rejected"
    
    requirement_id: UUID
    availability_id: UUID
    rejection_reason: str
    risk_violations: List[str]
```

---

### Phase 8: Comprehensive Testing (Days 7-8) ⭐ UPDATED

**Test Files:**

1. **`test_matching_engine.py`** (~800 lines)
   - ✅ Location-first hard filter tests
   - ✅ Bidirectional matching
   - ✅ Score calculation accuracy
   - ✅ Filtering by commodity-specific min_score
   - ✅ Result sorting (best first)
   - ✅ Duplicate detection (5min window, 95% similarity)

2. **`test_matching_scoring.py`** (~600 lines)
   - ✅ Quality scoring algorithm
   - ✅ Price scoring algorithm
   - ✅ Delivery scoring algorithm
   - ✅ Quantity scoring
   - ✅ Combined scoring with commodity-specific weights
   - ✅ WARN risk penalty (10% global reduction)

3. **`test_matching_risk.py`** (~500 lines)
   - ✅ Party links integration (PASS/WARN/FAIL)
   - ✅ Circular trading checks
   - ✅ Role restriction validation
   - ✅ Credit limit checks
   - ✅ Internal trade blocking (if configured)
   - ✅ WARN semantics: allowed with penalty vs blocked

4. **`test_matching_concurrency.py`** (~400 lines) ⭐ NEW
   - ✅ Race conditions for partial matches
   - ✅ Optimistic locking tests
   - ✅ Concurrent allocation scenarios
   - ✅ Double-allocation prevention
   - ✅ Version conflict handling

5. **`test_matching_location.py`** (~300 lines) ⭐ NEW
   - ✅ Location-first filter accuracy
   - ✅ Same state/region matching
   - ✅ Cross-state blocking
   - ✅ Location change recompute
   - ✅ Multi-branch seller scenarios

6. **`test_matching_events.py`** (~400 lines) ⭐ NEW
   - ✅ requirement.created event trigger
   - ✅ availability.created event trigger
   - ✅ requirement.updated location change
   - ✅ risk_status.changed FAIL→PASS
   - ✅ Event ordering and idempotency

7. **`test_matching_notifications.py`** (~400 lines) ⭐ NEW
   - ✅ Rate limiting (1 per user per minute)
   - ✅ User preference opt-in/opt-out
   - ✅ Top N matches notification
   - ✅ Location-matched parties only
   - ✅ Multi-channel preferences (PUSH/EMAIL/SMS)

8. **`test_matching_integration.py`** (~600 lines)
   - ✅ End-to-end matching workflows
   - ✅ Real requirement/availability data
   - ✅ Multi-commodity scenarios (Cotton, Gold, Wheat, Rice, Oil)
   - ✅ Notification triggers
   - ✅ Event publishing
   - ✅ Audit trail verification

9. **`test_matching_performance.py`** (~300 lines) ⭐ NEW
   - ✅ High-volume scenarios (10K+ postings)
   - ✅ Throttling & backpressure
   - ✅ Micro-batching performance
   - ✅ Query performance with indexes
   - ✅ Response time SLAs (<1s for search)

**Total Test Coverage:** ~4,300 lines
**Minimum Coverage Target:** 95% for core matching logic

---

## 📊 MATCHING ALGORITHM DETAILS

### Quality Score Calculation

**Scenario:** Cotton matching

```python
Requirement:
{
    "staple_length": {"min": 28, "max": 32, "preferred": 30},
    "micronaire": {"min": 3.5, "max": 4.5, "preferred": 4.0},
    "strength": {"min": 26, "max": 30}
}

Availability:
{
    "staple_length": 29.5,
    "micronaire": 4.1,
    "strength": 28
}

Calculation:
1. Staple Length:
   - Within range [28, 32]: ✓
   - Distance from preferred: |29.5 - 30| = 0.5
   - Score: 1.0 - (0.5 / 2) = 0.875

2. Micronaire:
   - Within range [3.5, 4.5]: ✓
   - Distance from preferred: |4.1 - 4.0| = 0.1
   - Score: 1.0 - (0.1 / 0.5) = 0.80

3. Strength:
   - Within range [26, 30]: ✓
   - No preferred specified, in middle of range
   - Score: 1.0

Quality Score = (0.875 + 0.80 + 1.0) / 3 = 0.892
```

### Price Score Calculation

```python
Buyer Budget:
- Max: ₹61,000/bale
- Preferred: ₹59,500/bale

Seller Price: ₹60,000/bale

Calculation:
- Price within budget: ✓
- Price > preferred: premium of ₹500
- Score: (max - price) / (max - preferred)
- Score: (61000 - 60000) / (61000 - 59500)
- Score: 1000 / 1500 = 0.667
```

### Delivery Score Calculation

```python
Buyer Location: Mumbai (19.0760°N, 72.8777°E)
Seller Location: Ahmedabad (23.0225°N, 72.5714°E)

Distance Calculation (Haversine):
distance = 450 km

Buyer Max Distance: 500 km

Score Calculation:
- Within max distance: ✓
- Score: 1.0 - (distance / max_distance)
- Score: 1.0 - (450 / 500)
- Score: 0.90
```

### Combined Score

```python
Quality Score: 0.892 (weight: 40%)
Price Score: 0.667 (weight: 30%)
Delivery Score: 0.90 (weight: 15%)
Risk Score: 1.0 (weight: 15%)  // PASS from risk engine

Combined Score:
= (0.892 × 0.40) + (0.667 × 0.30) + (0.90 × 0.15) + (1.0 × 0.15)
= 0.357 + 0.200 + 0.135 + 0.150
= 0.842

Final Match Score: 0.842 (84.2%) - EXCELLENT MATCH
```

---

## 🔗 INTEGRATION POINTS

### With Risk Engine

```python
# In MatchingEngine.calculate_match_score()

# Call risk engine for validation
risk_assessment = await self.risk_engine.assess_trade_risk(
    requirement=requirement,
    availability=availability,
    trade_quantity=min(requirement.preferred_quantity, availability.available_quantity),
    trade_price=availability.base_price,
    buyer_data={...},
    seller_data={...},
    user_id=current_user.id
)

# Extract risk score
if risk_assessment["overall_status"] == "PASS":
    risk_score = 1.0
elif risk_assessment["overall_status"] == "WARN":
    risk_score = 0.5
else:  # FAIL
    risk_score = 0.0
```

### With Requirement/Availability Services

```python
# In RequirementService.create()

# After creating requirement
requirement = await self.repo.create(requirement_data)

# Auto-match with existing availabilities
from backend.modules.trade_desk.services.matching_service import MatchingService

matching_service = MatchingService(self.db, ...)
matches = await matching_service.auto_match_on_new_post(
    entity_type="requirement",
    entity_id=requirement.id
)

# Emit event with match count
requirement.emit_event(RequirementMatchesFoundEvent(
    requirement_id=requirement.id,
    match_count=len(matches)
))
```

### With Notification Service

```python
# In MatchingService.find_and_notify_matches()

if notify and matches:
    for match in matches[:5]:  # Top 5 matches only
        # Notify buyer
        await self.notification_service.send(
            user_id=requirement.buyer_id,
            title="New Match Found!",
            message=f"Found compatible availability (score: {match.score:.1%})",
            notification_type="MATCH_FOUND",
            metadata={
                "requirement_id": requirement.id,
                "availability_id": match.availability_id,
                "match_score": match.score
            }
        )
        
        # Notify seller
        await self.notification_service.send(
            user_id=availability.seller_id,
            title="Potential Buyer Found!",
            message=f"Your availability matches a buyer requirement (score: {match.score:.1%})",
            notification_type="MATCH_FOUND",
            metadata={...}
        )
```

---

## 🎯 SUCCESS CRITERIA

1. ✅ **Bidirectional Matching Works**
   - Find availabilities for requirements
   - Find requirements for availabilities
   - Results are symmetric

2. ✅ **Scoring Algorithm Accurate**
   - Quality scoring validated against manual calculations
   - Price scoring handles all edge cases
   - Delivery scoring uses correct Haversine formula
   - Combined scoring weights correct

3. ✅ **Risk Integration Complete**
   - Party links blocking works
   - Circular trading prevention works
   - Role restrictions enforced
   - Credit limits validated

4. ✅ **Performance Acceptable**
   - Match search <1 second
   - Score calculation <100ms per pair
   - Handles 10K+ active requirements/availabilities

5. ✅ **Notifications Working**
   - Real-time WebSocket updates
   - Email/SMS alerts (if enabled)
   - Event publishing functional

6. ✅ **Tests Passing**
   - 100% test coverage on core algorithms
   - All integration tests passing
   - Edge cases handled

---

## 📈 ESTIMATED EFFORT ⭐ UPDATED

| Phase | Duration | Lines of Code | Key Deliverables |
|-------|----------|---------------|------------------|
| Configuration System | 0.5 days | ~200 lines | Per-commodity config, rate limiting |
| Core Matching Engine | 2 days | ~1,000 lines | Location-first filter, atomic allocation |
| Scoring Algorithms | 1.5 days | ~700 lines | WARN penalty, commodity weights |
| Validation & Risk | 1 day | ~500 lines | Risk integration, duplicate detection |
| Matching Service | 1.5 days | ~700 lines | Event-driven triggers, notifications |
| REST API | 1 day | ~400 lines | Location-aware endpoints |
| Integration Updates | 1 day | ~400 lines | Event handlers, repository queries |
| Events & Notifications | 0.5 days | ~300 lines | Rate limiting, user preferences |
| Database Schema | 0.5 days | ~100 lines | Indexes, audit trail table |
| Comprehensive Testing | 2 days | ~4,300 lines | 9 test suites, 95% coverage |
| **TOTAL** | **10 days** | **~8,600 lines** | Production-ready matching engine |

**Breakdown:**
- **Production Code:** ~4,300 lines
- **Test Code:** ~4,300 lines
- **Test Coverage Target:** 95%+ for core logic

---

## 🎯 SUCCESS CRITERIA ⭐ UPDATED

1. ✅ **Location-First Filtering**
   - ✅ Location hard filter runs BEFORE scoring
   - ✅ NO cross-state matches appear
   - ✅ Database queries optimized with location indexes
   - ✅ Location change triggers rematch

2. ✅ **Event-Driven Architecture**
   - ✅ requirement.created triggers immediate matching
   - ✅ availability.created triggers immediate matching
   - ✅ risk_status.changed FAIL→PASS unlocks matches
   - ✅ Safety cron as fallback only (15-30s)

3. ✅ **Bidirectional Matching Works**
   - ✅ Find availabilities for requirements
   - ✅ Find requirements for availabilities
   - ✅ Results are symmetric

4. ✅ **Scoring Algorithm Accurate**
   - ✅ Quality scoring validated against manual calculations
   - ✅ Price scoring handles all edge cases
   - ✅ Delivery scoring uses correct Haversine formula
   - ✅ Combined scoring uses commodity-specific weights
   - ✅ WARN penalty applied correctly (10% global)

5. ✅ **Risk Integration Complete**
   - ✅ PASS → risk_score = 1.0, no penalty
   - ✅ WARN → risk_score = 0.5, -10% global penalty
   - ✅ FAIL → match blocked (score = 0.0)
   - ✅ Party links blocking works
   - ✅ Circular trading prevention works
   - ✅ Role restrictions enforced
   - ✅ Credit limits validated

6. ✅ **Atomic Partial Allocation**
   - ✅ Optimistic locking prevents double-allocation
   - ✅ Concurrent reservation tests pass
   - ✅ Version conflicts handled gracefully
   - ✅ Remaining quantity accurate

7. ✅ **Duplicate Detection Working**
   - ✅ 5-minute time window enforced
   - ✅ 95% similarity threshold accurate
   - ✅ In-memory + DB duplicate check

8. ✅ **Notifications Smart & Rate-Limited**
   - ✅ Only location-matched parties notified
   - ✅ Top N matches (user-configurable)
   - ✅ Rate limiting (1 per user per minute)
   - ✅ User preferences respected (opt-in/opt-out)
   - ✅ Multi-channel support (PUSH/EMAIL/SMS)
   - ✅ Real-time WebSocket updates
   - ✅ Event publishing functional

9. ✅ **Performance Acceptable**
   - ✅ Match search <1 second (with location filter)
   - ✅ Score calculation <100ms per pair
   - ✅ Handles 10K+ active requirements/availabilities
   - ✅ Throttling works under high load
   - ✅ Micro-batching reduces database pressure

10. ✅ **Audit Trail Complete**
    - ✅ Every match logged with full breakdown
    - ✅ Risk details stored for compliance
    - ✅ Location filter results tracked
    - ✅ Duplicate detection recorded
    - ✅ Allocation status audited

11. ✅ **Tests Passing**
    - ✅ 95%+ test coverage on core algorithms
    - ✅ All integration tests passing
    - ✅ Concurrency tests pass (race conditions)
    - ✅ Location filter tests pass
    - ✅ WARN/PASS/FAIL scenarios tested
    - ✅ Duplicate detection tests pass
    - ✅ Edge cases handled

12. ✅ **Security & Privacy**
    - ✅ Match results shown ONLY to matched parties
    - ✅ NO count leakage to non-matched users
    - ✅ NO partial info visible to non-participants
    - ✅ Internal branch trading blocked (if configured)

---

## 📝 QUESTIONS FOR APPROVAL ⭐ UPDATED

**Before starting implementation, please confirm:**

### 1. **Scoring Weights (Per Commodity)**

Default configuration:
- Quality: 40%
- Price: 30%
- Delivery: 15%
- Risk: 15%

**Question:** Accept defaults OR provide custom weights per commodity?

Example custom:
```
COTTON: Quality 45%, Price 25%, Delivery 15%, Risk 15%
GOLD: Quality 30%, Price 40%, Delivery 10%, Risk 20%
```

**Your Decision:** ___________________

---

### 2. **Min Score Threshold (Per Commodity)** ⭐ UPDATED

Default: 0.6 (60%) for all commodities  
Now supports per-commodity configuration:

**Question:** Use 0.6 global default OR different thresholds per commodity?

Example:
```
COTTON: 0.6 (standard)
GOLD: 0.7 (higher bar for precious metals)
WHEAT: 0.5 (more lenient for grains)
```

**Your Decision:** ___________________

---

### 3. **Risk WARN Semantics** ⭐ UPDATED

Current design: WARN = allowed with 10% global score penalty

Example:
- Base score: 0.85
- Risk status: WARN (same mobile detected)
- Penalty: -10%
- Final score: 0.765

**Question:** Accept 10% penalty OR different penalty %? OR block WARN completely?

**Your Decision:** ___________________

---

### 4. **Auto-Match Trigger Mechanism** ⭐ UPDATED

**Primary:** Event-driven (requirement.created, availability.created, risk_status.changed)  
**Safety Net:** Optional 15-30s cron as fallback

**Question:** Approve event-driven as primary? Cron interval preference?

**Your Decision:** ___________________

---

### 5. **Notification Settings** ⭐ UPDATED

Current design:
- Top 5 matches notified (default, user-configurable)
- Rate limit: 1 notification per user per minute
- User preferences: opt-in/opt-out, channel selection (PUSH/EMAIL/SMS)

**Question:** Accept top 5 default OR different number? Accept 60s rate limit?

**Your Decision:** ___________________

---

### 6. **Location Matching Rules** ⭐ NEW

**Question:** Should matching allow:
- ✅ Exact location match (same city/district)?
- ✅ Same state match?
- ❌ Cross-state match?
- ❓ Distance-based (within X km)?

**Your Decision:** ___________________

---

### 7. **Duplicate Detection Tolerances** ⭐ NEW

Current design:
- Time window: 5 minutes
- Similarity threshold: 95% quality param match

**Question:** Accept 5min/95% OR different values?

**Your Decision:** ___________________

---

### 8. **Partial Matching Rules** ⭐ NEW

Current design:
- If seller has 10 tons, buyer wants 6 → match for 6
- Remaining 4 stays available for OTHER buyers in SAME location
- Minimum partial quantity: 10% of requested

**Question:** Accept 10% minimum OR different %? (e.g., 25% minimum partial)

**Your Decision:** ___________________

---

### 9. **Internal Branch Trading** ⭐ NEW

**Question:** Block trades between same company branches?

Options:
- ✅ BLOCK (prevent internal circular trades)
- ❌ ALLOW (permit internal transfers)
- ⚙️ CONFIGURABLE (admin setting)

**Your Decision:** ___________________

---

### 10. **Safety Cron Fallback Interval** ⭐ NEW

Events are primary trigger, but safety cron checks for missed matches.

**Question:** Cron interval preference?

Options:
- 15 seconds (more responsive)
- 30 seconds (balanced)
- 60 seconds (lighter load)
- Disabled (events only)

**Your Decision:** ___________________

---

## ✅ CRITICAL CONFIRMATIONS

Please confirm understanding:

1. ✅ **Location-First Design**
   - Buyer sees ONLY sellers in matched location
   - Seller sees ONLY buyers in their delivery region
   - NO cross-state broadcasts
   - NO marketplace-like spam

   **Confirmed:** _____ (Y/N)

2. ✅ **Event-Driven Architecture**
   - Real-time matching on requirement.created / availability.created
   - No batch processing as primary mechanism
   - Safety cron only as fallback

   **Confirmed:** _____ (Y/N)

3. ✅ **Risk Integration**
   - PASS → proceed normally (risk_score = 1.0)
   - WARN → allow with 10% penalty
   - FAIL → block completely
   - Party links, circular trading, role checks integrated

   **Confirmed:** _____ (Y/N)

4. ✅ **Atomic Partial Allocation**
   - Optimistic locking prevents double-allocation
   - Concurrent reservation tests included
   - Remaining quantity stays available for others

   **Confirmed:** _____ (Y/N)

5. ✅ **Multi-Commodity Platform**
   - JSONB quality_params work for Cotton, Gold, Wheat, Rice, Oil, ANY commodity
   - Per-commodity configurable weights and thresholds
   - NOT cotton-specific

   **Confirmed:** _____ (Y/N)

6. ✅ **Audit Trail & Explainability**
   - Every match stores full score breakdown
   - Risk assessment details logged
   - Location filter results tracked
   - Duplicate detection recorded

   **Confirmed:** _____ (Y/N)

7. ✅ **Security & Privacy**
   - Match results shown ONLY to matched parties
   - NO count leakage to non-matched users
   - NO partial info visible to non-participants

   **Confirmed:** _____ (Y/N)

---

## 🎯 WHY THIS DESIGN?

### Separation of Concerns
- **Matching Engine:** Pure matching logic (no I/O)
- **Matching Service:** Orchestration & side effects
- **Validators:** Business rules & compliance

### Testability
- Each component independently testable
- Mock-friendly interfaces
- Clear input/output contracts

### Performance
- Async/await throughout
- Efficient database queries
- Score calculation optimized
- Caching opportunities (future)

### Extensibility
- Easy to add new scoring factors
- Pluggable validators
- Event-driven for integrations

---

## 🚀 NEXT STEPS AFTER APPROVAL

1. ✅ **Get Approval** - Answer 10 configuration questions above
2. ✅ **Create Feature Branch** - `feat/trade-desk-matching-engine`
3. ✅ **Implement Phases 1-9** - Systematic implementation (10 days)
4. ✅ **Run All Tests** - 95%+ coverage, all suites passing
5. ✅ **Code Review** - Internal team review
6. ✅ **Merge to Main** - After approval and tests passing

---

## 📋 FINAL SUMMARY - WHAT WILL BE BUILT

### Core Features

**1. Location-First Intelligent Matching**
- Hard location filter BEFORE any scoring (no wasted computation)
- Buyer sees ONLY sellers in their delivery region
- Seller sees ONLY buyers in their location area
- NO cross-state spam, NO marketplace-like broadcasts
- Location change triggers automatic rematch

**2. Event-Driven Real-Time Architecture**
- `requirement.created` → immediate matching
- `availability.created` → immediate matching
- `requirement.updated` (location change) → rematch
- `risk_status.changed` (FAIL→PASS) → unlock matches
- Safety cron (15-30s) as fallback only

**3. Multi-Factor Scoring System**
- Quality compatibility (40% weight, configurable)
- Price competitiveness (30% weight)
- Delivery logistics (15% weight)
- Risk assessment (15% weight)
- **Per-commodity configurable** (Cotton, Gold, Wheat, Rice, Oil, etc.)
- **Min score threshold** per commodity (default 0.6)

**4. Risk-First Validation**
- **PASS** (score ≥ 80): Proceed normally, risk_score = 1.0
- **WARN** (score 60-79): Allow with 10% global penalty + warning
- **FAIL** (score < 60): Block match completely
- Party links detection (same PAN/GST/mobile)
- Circular trading prevention
- Role restrictions (buyer/seller/trader)
- Credit limit validation
- Internal branch blocking (configurable)

**5. Atomic Partial Matching**
- Seller has 10 tons, buyer wants 6 → match 6, leave 4 for others
- **Optimistic locking** prevents double-allocation
- **Row-level DB transaction** ensures atomicity
- Concurrent reservation handling with version control
- Remaining quantity stays in SAME location pool

**6. Smart Notifications with Rate Limiting**
- Notify ONLY location-matched parties (no spam)
- Top N matches (default 5, user-configurable)
- **Rate limiting:** Max 1 notification per user per minute
- **User preferences:** Opt-in/opt-out, channel selection
- Multi-channel: PUSH, EMAIL, SMS (user choice)
- Real-time WebSocket updates

**7. Duplicate Detection**
- 5-minute time window (configurable)
- 95% quality param similarity threshold (configurable)
- Prevents same buyer-seller pair duplicate matches
- In-memory + database duplicate check

**8. Throttling & Backpressure**
- High-volume scenarios handled gracefully
- Priority queue (HIGH → MEDIUM → LOW)
- Micro-batching (1-3s) for database efficiency
- Max batch size configurable (default 100)
- No system overload even with thousands of postings

**9. Complete Audit Trail**
- Every match logged with full score breakdown
- Risk assessment details stored
- Location filter results tracked
- Duplicate detection recorded
- Allocation status audited
- Explainability for compliance & debugging

**10. Security & Privacy**
- Match results shown ONLY to matched parties
- NO count leakage to non-matched users
- NO partial info visible to non-participants
- Prevent data snooping and market manipulation

---

### Technical Deliverables

**New Files (9 files):**
1. `matching_config.py` - Per-commodity configuration
2. `matching_engine.py` - Core matching logic (location-first)
3. `scoring.py` - Multi-factor scoring algorithms
4. `validators.py` - Risk integration & validation
5. `matching_service.py` - Event-driven orchestration
6. `matching_router.py` - REST API endpoints
7. `events.py` - Domain events
8. `match_audit_trail` table - Explainability & compliance
9. `test_matching_*.py` (9 test suites) - Comprehensive testing

**Updated Files (6 files):**
1. `requirement_repository.py` - Location-aware queries
2. `availability_repository.py` - Location-aware queries
3. `requirement_service.py` - Event handler integration
4. `availability_service.py` - Event handler integration
5. `requirement_router.py` - Find matches endpoint
6. `availability_router.py` - Find matches endpoint

**Database Changes:**
- 2 new indexes (location-first optimization)
- 1 audit trail table (explainability)
- 1 version column (optimistic locking)

**Total Code:**
- Production: ~4,300 lines
- Tests: ~4,300 lines
- Coverage: 95%+ target

---

### Business Impact

**For Buyers:**
- ✅ See ONLY relevant sellers in their delivery area
- ✅ Get instant match notifications (< 1 second)
- ✅ Understand WHY matches scored well (score breakdown)
- ✅ Trust system (risk checks prevent fraud)
- ✅ No spam from irrelevant sellers

**For Sellers:**
- ✅ See ONLY relevant buyers in their location
- ✅ Get instant match notifications (< 1 second)
- ✅ Partial qty matching (sell 6 tons, keep 4 available)
- ✅ No allocation conflicts (atomic locking)
- ✅ No spam from irrelevant buyers

**For Platform:**
- ✅ Reduced manual matching work
- ✅ Faster time-to-trade (real-time vs batch)
- ✅ Fraud prevention (risk integration)
- ✅ Audit compliance (full trail)
- ✅ Scalable (handles 10K+ postings)
- ✅ Multi-commodity ready (not just cotton)

---

## ⚠️ CRITICAL DEPENDENCIES

Before starting implementation:

1. ✅ **Risk Engine** - Must be complete and merged to main
2. ✅ **Requirement Engine** - Must have location field
3. ✅ **Availability Engine** - Must have location field
4. ✅ **Event System** - Event publisher infrastructure
5. ✅ **Notification Service** - For match alerts
6. ⏸️ **User Settings** - For notification preferences (can mock initially)

---

## 🎯 WHY THIS DESIGN?

### Separation of Concerns

- **Matching Engine:** Pure matching logic (no I/O)
- **Matching Service:** Orchestration & side effects
- **Validators:** Business rules & compliance

### Testability

- Each component independently testable
- Mock-friendly interfaces
- Clear input/output contracts

### Performance

- Async/await throughout
- Efficient database queries (location-first indexes)
- Score calculation optimized
- Caching opportunities (future)
- Throttling prevents overload

### Extensibility

- Easy to add new scoring factors
- Pluggable validators
- Event-driven for integrations
- Per-commodity configuration

### Risk-First

- Risk engine integrated at core
- No matches proceed without validation
- Audit trail for all decisions
- Compliance-ready from day 1

### Location-Centric

- Hard filter prevents wasted computation
- Database-level optimization
- NO cross-region spam
- Privacy-preserving (only matched parties see results)

---

## 📊 COMPARISON: BEFORE vs AFTER

| Aspect | Before Matching Engine | After Matching Engine |
|--------|------------------------|----------------------|
| **Match Discovery** | Manual search by buyers/sellers | Automatic real-time matching |
| **Match Speed** | Hours/days (manual review) | < 1 second (event-driven) |
| **Location Filtering** | Manual check | Automatic hard filter |
| **Risk Validation** | Manual PAN/GST check | Automatic risk engine integration |
| **Scoring** | Subjective human judgment | Objective 4-factor algorithm |
| **Notifications** | None (manual follow-up) | Real-time push/email/SMS |
| **Partial Matching** | Not supported | Atomic partial allocation |
| **Duplicate Prevention** | Manual tracking | Automatic 5min/95% detection |
| **Audit Trail** | None | Complete explainability log |
| **Scalability** | Limited by human capacity | 10K+ postings handled |
| **Multi-Commodity** | Cotton-only assumptions | Any commodity supported |

---

**END OF IMPLEMENTATION PLAN**

---

## ✅ READY FOR APPROVAL

Please review this comprehensive plan and answer the 10 configuration questions above.

Once approved, implementation will begin systematically on feature branch `feat/trade-desk-matching-engine`.

Estimated completion: **10 days** from approval.

**No code will be committed to main until:**
1. All phases complete
2. All tests passing (95%+ coverage)
3. Code review approved
4. Final approval given

---

*Last Updated: 2025-11-25*  
*Version: 2.0 (Location-First, Event-Driven, Risk-Integrated)*
