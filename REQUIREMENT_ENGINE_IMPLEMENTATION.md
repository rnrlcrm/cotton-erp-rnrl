# REQUIREMENT ENGINE - IMPLEMENTATION PLAN

**Branch:** `feat/trade-desk-requirement-engine`  
**Started:** November 24, 2025  
**Status:** Planning Phase - Awaiting Approval ⏳

---

## 🚀 **7 CRITICAL ENHANCEMENTS ADDED (2035-READY)**

This plan is **100% future-proof** with autonomous AI, real-time intent matching, and cross-commodity intelligence:

1. **🎯 Requirement Intent Layer** - `intent_type` field (DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY)
   - Matching Engine routes based on buyer intent
   - Autonomous trade engine decision making

2. **🧠 AI Market Context Embedding** - `market_context_embedding VECTOR(1536)`
   - Vector similarity search for semantic matching
   - Cross-commodity pattern detection
   - Market sentiment alignment
   - Predictive trade analytics

3. **📅 Dynamic Delivery Flexibility Window** - `delivery_window_start/end`, `delivery_flexibility_hours`
   - Logistics optimization
   - Delivery feasibility scoring
   - Supply chain coordination

4. **🔄 Multi-Commodity Conversion Rules** - `commodity_equivalents JSONB`
   - Intelligent substitutions (Cotton → Yarn, Paddy → Rice, Soybean → Oil+DOC)
   - Cross-commodity matching
   - Value chain integration

5. **🤝 Negotiation Preferences Block** - `negotiation_preferences JSONB`
   - Self-negotiating system
   - Auto-accept thresholds
   - Escalation rules
   - AI-powered negotiation

6. **⭐ Buyer Trust Score Weighting** - `buyer_priority_score FLOAT`
   - Prioritize serious buyers
   - Prevent spam requirements
   - Reward loyalty

7. **🔍 AI Adjustment Event & Explainability** - `requirement.ai_adjusted` event
   - Transparent AI decisions
   - Audit trail for AI modifications
   - Market sentiment adjustments
   - Dynamic tolerance recommendations

**Result:** **12-step AI pipeline** (enhanced from 10), **11 events** (enhanced from 10), **11 REST endpoints** (enhanced from 9), **5 WebSocket channels** (enhanced from 4)

---

## 🎯 OVERVIEW

The Requirement Engine is the **second of 5 core engines** powering the 2035 Global Multi-Commodity Trading Platform:

1. **Availability Engine** ✅ (COMPLETE - Merged to Main)
2. **Requirement Engine** 🚧 (Planning Now)
3. Matching Engine (AI-Powered)
4. Negotiation Engine (AI-Assisted)
5. Trade Finalization Engine

---

## 📋 WHAT IS REQUIREMENT ENGINE?

**Purpose:** Buyers post their commodity requirements (inverse of Availability)

**Core Concept:**
- **Availability Engine:** Sellers say "I HAVE this commodity to sell"
- **Requirement Engine:** Buyers say "I NEED this commodity to buy"

**Key Differences from Availability:**
1. **Quantity Ranges:** Buyers specify min/max quantity (flexible)
2. **Budget Constraints:** Max price buyer willing to pay
3. **Quality Tolerances:** Acceptable quality parameter ranges
4. **Delivery Preferences:** Multiple delivery locations acceptable
5. **Auto-Matching:** System suggests compatible availabilities
6. **Requirement Visibility:** Control who can see your requirement

---

## 🏗️ IMPLEMENTATION PHASES

### **PHASE 1: DATABASE SCHEMA** (Day 1)

**Migration:** `create_requirement_engine_tables.py`

**Table: `requirements`**

#### **Core Identification:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
requirement_number VARCHAR(50) UNIQUE NOT NULL -- REQ-2025-000001
buyer_partner_id UUID NOT NULL REFERENCES partners(id)
commodity_id UUID NOT NULL REFERENCES commodities(id)
variety_id UUID REFERENCES commodity_varieties(id)
created_by_user_id UUID NOT NULL REFERENCES users(id)
```

#### **Quantity Requirements (Min/Max Ranges):**
```sql
min_quantity DECIMAL(15, 3) NOT NULL
max_quantity DECIMAL(15, 3) NOT NULL
quantity_unit VARCHAR(20) NOT NULL -- bales, kg, MT, grams
preferred_quantity DECIMAL(15, 3) -- Ideal quantity
```

#### **Quality Requirements (JSONB - Flexible Tolerances):**
```sql
quality_requirements JSONB NOT NULL
-- Example for Cotton:
{
  "staple_length": {"min": 28, "max": 30, "preferred": 29},
  "micronaire": {"min": 3.8, "max": 4.5, "preferred": 4.2},
  "moisture": {"max": 8},
  "trash": {"max": 3}
}

-- Example for Gold:
{
  "purity": {"min": 22, "exact": 22},
  "hallmark": {"required": ["BIS"]},
  "form": {"accepted": ["bars", "coins"]}
}

-- Example for Wheat:
{
  "protein": {"min": 11.5, "preferred": 12.5},
  "moisture": {"max": 13},
  "test_weight": {"min": 75}
}
```

#### **Budget & Pricing:**
```sql
max_budget_per_unit DECIMAL(15, 2) NOT NULL -- Maximum willing to pay
preferred_price_per_unit DECIMAL(15, 2) -- Target price
total_budget DECIMAL(18, 2) -- Overall budget limit
currency_code VARCHAR(3) DEFAULT 'INR'
```

#### **Payment & Delivery Preferences:**
```sql
preferred_payment_terms JSONB -- Array of acceptable payment term IDs
  -- ["cash-uuid", "15day-uuid", "30day-uuid"]
  
preferred_delivery_terms JSONB -- Array of acceptable delivery term IDs
  -- ["ex-gin-uuid", "delivered-uuid"]
  
delivery_locations JSONB -- Multiple acceptable delivery locations
  -- [
  --   {"location_id": "uuid-1", "latitude": 21.1, "longitude": 79.0, "max_distance_km": 50},
  --   {"location_id": "uuid-2", "latitude": 19.0, "longitude": 72.8, "max_distance_km": 100}
  -- ]
```

#### **Market Visibility & Privacy:**
```sql
market_visibility VARCHAR(20) NOT NULL DEFAULT 'PUBLIC'
  -- PUBLIC: All sellers can see
  -- PRIVATE: Only buyer's network
  -- RESTRICTED: Invited sellers only
  -- INTERNAL: Own organization only
  
invited_seller_ids JSONB -- For RESTRICTED visibility
  -- ["seller-uuid-1", "seller-uuid-2"]
```

#### **Requirement Lifecycle:**
```sql
status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
  -- DRAFT: Being created
  -- ACTIVE: Published and searchable
  -- PARTIALLY_FULFILLED: Some quantity purchased
  -- FULFILLED: All quantity purchased
  -- EXPIRED: Past validity date
  -- CANCELLED: Buyer cancelled
  
valid_from TIMESTAMP NOT NULL
valid_until TIMESTAMP NOT NULL
urgency_level VARCHAR(20) DEFAULT 'NORMAL'
  -- URGENT: Need immediately
  -- NORMAL: Standard procurement
  -- PLANNING: Future planning
```

#### **🚀 ENHANCEMENT #1: REQUIREMENT INTENT LAYER** (NEW)
```sql
intent_type VARCHAR(30) NOT NULL DEFAULT 'DIRECT_BUY'
  -- DIRECT_BUY: Immediate purchase intent
  -- NEGOTIATION: Want multiple offers, will negotiate
  -- AUCTION_REQUEST: Reverse auction (sellers bid down)
  -- PRICE_DISCOVERY_ONLY: Just exploring market prices
  
-- Why? Matching Engine understands buyer behavior & urgency!
-- DIRECT_BUY → Match with best availability immediately
-- NEGOTIATION → Match with multiple sellers, trigger negotiation engine
-- AUCTION_REQUEST → Trigger reverse auction module
-- PRICE_DISCOVERY_ONLY → Don't match, just provide price insights
```

#### **🚀 ENHANCEMENT #2: AI MARKET CONTEXT EMBEDDING** (NEW)
```sql
market_context_embedding VECTOR(1536) -- OpenAI ada-002 embeddings
  -- AI-powered semantic matching across:
  -- 1. Market sentiment (bullish/bearish)
  -- 2. Price trend alignment
  -- 3. Cross-commodity patterns
  -- 4. Seasonal behavior
  -- 5. Buyer historical preferences
  
-- Vector similarity search enables:
-- - Find requirements with similar market context
-- - Match based on market sentiment, not just quality/price
-- - Predict future requirement patterns
-- - Autonomous trade engine decision making
```

#### **🚀 ENHANCEMENT #3: DYNAMIC DELIVERY FLEXIBILITY WINDOW** (NEW)
```sql
delivery_window_start TIMESTAMP -- Earliest acceptable delivery
delivery_window_end TIMESTAMP -- Latest acceptable delivery
delivery_flexibility_hours INTEGER DEFAULT 168 -- Flexibility in hours (default 7 days)
  
-- Why? Matching engine scores delivery feasibility!
-- Seller can deliver on Dec 5, buyer needs Dec 1-10 → Score = 1.0
-- Seller can deliver on Dec 15, buyer needs Dec 1-10 → Score = 0.0
-- Enables logistics optimization
```

#### **🚀 ENHANCEMENT #4: MULTI-COMMODITY CONVERSION RULES** (NEW)
```sql
commodity_equivalents JSONB -- Intelligent substitution rules
  -- Example: Cotton buyer might accept Yarn
  -- {
  --   "acceptable_substitutes": [
  --     {"commodity_id": "uuid-of-yarn", "conversion_ratio": 0.85, "quality_mapping": {...}},
  --     {"commodity_id": "uuid-of-fabric", "conversion_ratio": 0.75, "quality_mapping": {...}}
  --   ]
  -- }
  
  -- Example: Paddy buyer might accept Rice
  -- {
  --   "acceptable_substitutes": [
  --     {"commodity_id": "uuid-of-rice", "conversion_ratio": 0.67, "quality_mapping": {...}}
  --   ]
  -- }
  
  -- Example: Soybean buyer might accept Soy Oil + DOC
  -- {
  --   "acceptable_substitutes": [
  --     {"commodity_id": "uuid-of-soy-oil", "conversion_ratio": 0.18, "quality_mapping": {...}},
  --     {"commodity_id": "uuid-of-doc", "conversion_ratio": 0.78, "quality_mapping": {...}}
  --   ]
  -- }
  
-- Enables intelligent cross-commodity matching!
```

#### **🚀 ENHANCEMENT #5: NEGOTIATION PREFERENCES BLOCK** (NEW)
```sql
negotiation_preferences JSONB
  -- {
  --   "allow_auto_negotiation": true,
  --   "max_rounds": 5,
  --   "price_tolerance_percent": 3.0,
  --   "quantity_tolerance_percent": 10.0,
  --   "auto_accept_if_score": 0.95,
  --   "escalate_to_human_if_score": 0.60
  -- }
  
-- Makes system self-negotiating!
-- AI negotiates on buyer's behalf within tolerance bounds
-- Escalates to human only when needed
```

#### **🚀 ENHANCEMENT #6: BUYER TRUST SCORE WEIGHTING** (NEW)
```sql
buyer_priority_score FLOAT DEFAULT 1.0
  -- 0.5: New/untrusted buyer (low priority)
  -- 1.0: Standard buyer (normal priority)
  -- 1.5: Repeat buyer (high priority)
  -- 2.0: Premium buyer (highest priority)
  
-- Used by Matching Engine to prioritize serious buyers
-- Prevents spam requirements
-- Rewards loyal buyers with faster matching
```

#### **Matching & Fulfillment Tracking:**
```sql
total_matched_quantity DECIMAL(15, 3) DEFAULT 0
total_purchased_quantity DECIMAL(15, 3) DEFAULT 0
total_spent DECIMAL(18, 2) DEFAULT 0
active_negotiation_count INTEGER DEFAULT 0
```

#### **AI-Powered Features:**
```sql
ai_suggested_max_price DECIMAL(15, 2) -- Fair market price suggestion
ai_confidence_score INTEGER -- Price confidence (0-100)
ai_score_vector JSONB -- ML embeddings for matching
  -- {
  --   "commodity_embedding": [0.12, 0.45, ...],
  --   "quality_flexibility": 75.5,
  --   "price_sensitivity": 60.2,
  --   "urgency_score": 85.0
  -- }
  
ai_price_alert_flag BOOLEAN DEFAULT FALSE -- Unrealistic budget
ai_alert_reason TEXT -- Why flagged
ai_recommended_sellers JSONB -- Pre-scored seller suggestions
```

#### **Metadata & Audit:**
```sql
notes TEXT -- Buyer's internal notes
attachments JSONB -- Specs, drawings, sample images
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
published_at TIMESTAMP -- When made ACTIVE
cancelled_at TIMESTAMP
cancelled_by_user_id UUID REFERENCES users(id)
cancellation_reason TEXT
```

---

### **INDEXES TO CREATE:**

#### **Core Indexes:**
```sql
CREATE INDEX ix_requirements_buyer_partner_id ON requirements(buyer_partner_id);
CREATE INDEX ix_requirements_commodity_id ON requirements(commodity_id);
CREATE INDEX ix_requirements_status ON requirements(status);
CREATE INDEX ix_requirements_market_visibility ON requirements(market_visibility);
CREATE INDEX ix_requirements_urgency_level ON requirements(urgency_level);
```

#### **Composite Indexes (Query Optimization):**
```sql
CREATE INDEX ix_requirements_commodity_status 
  ON requirements(commodity_id, status);
  
CREATE INDEX ix_requirements_commodity_visibility 
  ON requirements(commodity_id, market_visibility);
  
CREATE INDEX ix_requirements_status_urgency 
  ON requirements(status, urgency_level);
```

#### **JSONB GIN Indexes (Fast JSONB Queries):**
```sql
CREATE INDEX ix_requirements_quality_requirements_gin 
  ON requirements USING gin(quality_requirements);
  
CREATE INDEX ix_requirements_delivery_locations_gin 
  ON requirements USING gin(delivery_locations);
  
CREATE INDEX ix_requirements_ai_score_vector_gin 
  ON requirements USING gin(ai_score_vector);
```

#### **Partial Index (Active Requirements Only):**
```sql
CREATE INDEX ix_requirements_active 
  ON requirements(commodity_id, buyer_partner_id, urgency_level)
  WHERE status = 'ACTIVE' AND valid_until > NOW();
```

---

### **DATABASE TRIGGERS:**

#### **1. Auto-Update Fulfillment Status**
```sql
CREATE TRIGGER trigger_update_requirement_status
BEFORE INSERT OR UPDATE ON requirements
FOR EACH ROW EXECUTE FUNCTION update_requirement_status();
```

**Logic:**
- If `total_purchased_quantity` >= `min_quantity` → Status = `PARTIALLY_FULFILLED`
- If `total_purchased_quantity` >= `max_quantity` → Status = `FULFILLED`
- If `valid_until` < NOW() AND status = `ACTIVE` → Status = `EXPIRED`

#### **2. Auto-Update `updated_at` Timestamp**
```sql
CREATE TRIGGER trigger_requirements_updated_at
BEFORE UPDATE ON requirements
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

### **CONSTRAINTS:**

```sql
-- Quantity logic
CHECK (min_quantity > 0)
CHECK (max_quantity >= min_quantity)
CHECK (preferred_quantity IS NULL OR (preferred_quantity >= min_quantity AND preferred_quantity <= max_quantity))
CHECK (total_purchased_quantity <= max_quantity)

-- Pricing logic
CHECK (max_budget_per_unit > 0)
CHECK (preferred_price_per_unit IS NULL OR preferred_price_per_unit <= max_budget_per_unit)
CHECK (total_budget IS NULL OR total_budget >= (min_quantity * max_budget_per_unit))

-- Validity dates
CHECK (valid_from < valid_until)

-- Market visibility
CHECK (market_visibility IN ('PUBLIC', 'PRIVATE', 'RESTRICTED', 'INTERNAL'))

-- Status
CHECK (status IN ('DRAFT', 'ACTIVE', 'PARTIALLY_FULFILLED', 'FULFILLED', 'EXPIRED', 'CANCELLED'))

-- Urgency
CHECK (urgency_level IN ('URGENT', 'NORMAL', 'PLANNING'))
```

---

## 🚀 PHASE 2: MODELS & MICRO-EVENTS (Day 2)

### **Model: `Requirement`**

**Location:** `backend/modules/trade_desk/models/requirement.py`

**Inherits:** `EventMixin` (for event sourcing)

**Key Methods:**
```python
class Requirement(Base, EventMixin):
    # ... fields ...
    
    def can_update(self) -> bool:
        """Check if requirement can be updated"""
        return self.status in [RequirementStatus.DRAFT, RequirementStatus.ACTIVE]
    
    def can_cancel(self) -> bool:
        """Check if requirement can be cancelled"""
        return self.status not in [RequirementStatus.FULFILLED, RequirementStatus.CANCELLED]
    
    def update_fulfillment(
        self, 
        purchased_quantity: Decimal, 
        amount_spent: Decimal,
        user_id: UUID
    ) -> None:
        """Update when buyer purchases from an availability"""
        self.total_purchased_quantity += purchased_quantity
        self.total_spent += amount_spent
        
        # Emit micro-event for matching engine
        self.emit_fulfillment_updated(user_id, purchased_quantity, amount_spent)
    
    def mark_fulfilled(self, user_id: UUID) -> None:
        """Mark requirement as fully fulfilled"""
        self.status = RequirementStatus.FULFILLED
        self.emit_fulfilled(user_id)
    
    def cancel(self, user_id: UUID, reason: str) -> None:
        """Cancel requirement"""
        self.status = RequirementStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by_user_id = user_id
        self.cancellation_reason = reason
        self.emit_cancelled(user_id, reason)
```

---

### **Micro-Events (11 Events - ENHANCED):**

**Location:** `backend/modules/trade_desk/events/requirement_events.py`

1. **`requirement.created`**
   - When: Requirement created (any status)
   - Payload: Full requirement data
   - Consumers: Analytics, AI learning

2. **`requirement.published`**
   - When: Status changes to ACTIVE
   - Payload: requirement_id, commodity_id, quality_requirements, budget, **intent_type**
   - Consumers: Matching engine (start auto-matching with availabilities), **Intent-based routing**

3. **`requirement.updated`**
   - When: Any field updated
   - Payload: requirement_id, changed_fields
   - Consumers: Matching engine (re-match if quality/price changed)

4. **`requirement.budget_changed`**
   - When: max_budget_per_unit or total_budget updated
   - Payload: requirement_id, old_budget, new_budget
   - Consumers: Matching engine, seller notifications

5. **`requirement.quality_changed`**
   - When: quality_requirements updated
   - Payload: requirement_id, old_requirements, new_requirements
   - Consumers: Matching engine (re-score matches)

6. **`requirement.visibility_changed`**
   - When: market_visibility changed
   - Payload: requirement_id, old_visibility, new_visibility
   - Consumers: Search index, seller access control

7. **`requirement.fulfillment_updated`**
   - When: Buyer purchases from availability
   - Payload: requirement_id, purchased_quantity, remaining_quantity
   - Consumers: Matching engine (update urgency if partially fulfilled)

8. **`requirement.fulfilled`**
   - When: Status changes to FULFILLED
   - Payload: requirement_id, total_spent, total_quantity
   - Consumers: Analytics, AI learning, notifications

9. **`requirement.expired`**
   - When: valid_until passes and status still ACTIVE
   - Payload: requirement_id, unfulfilled_quantity
   - Consumers: Buyer notifications, analytics

10. **`requirement.cancelled`**
    - When: Buyer cancels requirement
    - Payload: requirement_id, cancellation_reason
    - Consumers: Matching engine (stop auto-matching), analytics

11. **🚀 `requirement.ai_adjusted`** **(NEW - ENHANCEMENT #7)**
    - When: AI modifies budget/quality/delivery window
    - Payload: requirement_id, adjustment_type, old_value, new_value, ai_confidence, ai_reasoning
    - Consumers: **Explainability dashboard**, audit trail, buyer notifications
    - **Why?** Transparency & trust in AI decisions!

---

## 🚀 PHASE 3: REPOSITORY LAYER (Day 3)

### **Repository: `RequirementRepository`**

**Location:** `backend/modules/trade_desk/repositories/requirement_repository.py`

**Key Methods:**

#### **1. Smart Search for Compatible Availabilities**
```python
async def search_compatible_availabilities(
    self,
    requirement_id: UUID,
    min_match_score: float = 0.6,
    limit: int = 20
) -> List[Tuple[Availability, float]]:
    """
    Find availabilities matching this requirement
    
    Returns: List of (availability, match_score) tuples sorted by score
    
    Matching Criteria:
    1. Commodity match (required)
    2. Quality parameters within tolerances (weighted)
    3. Price within budget (critical)
    4. Delivery location proximity (if specified)
    5. Quantity overlap (has enough or partial acceptable)
    6. Market visibility (buyer can see it)
    """
```

**Scoring Algorithm:**
```python
match_score = (
    commodity_match * 1.0 +        # Must match (0 or 1)
    quality_score * 0.35 +          # Quality fit (0-1)
    price_score * 0.25 +            # Price competitiveness (0-1)
    quantity_score * 0.15 +         # Quantity availability (0-1)
    proximity_score * 0.15 +        # Delivery proximity (0-1)
    urgency_bonus * 0.10            # Urgency premium (0-1)
)
```

#### **2. Buyer's Requirements**
```python
async def get_buyer_requirements(
    self,
    buyer_partner_id: UUID,
    status_filter: List[RequirementStatus] = None,
    commodity_id: UUID = None,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[Requirement], int]:
    """Get requirements for a specific buyer with filters"""
```

#### **3. Public/Searchable Requirements**
```python
async def search_requirements(
    self,
    commodity_id: UUID = None,
    min_quantity: Decimal = None,
    max_budget: Decimal = None,
    urgency_level: str = None,
    market_visibility: List[str] = None,
    seller_partner_id: UUID = None,  # Check if seller can see
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[Requirement], int]:
    """Search requirements (for sellers to find buyers)"""
```

#### **4. Update Fulfillment Tracking**
```python
async def update_fulfillment_from_trade(
    self,
    requirement_id: UUID,
    purchased_quantity: Decimal,
    amount_spent: Decimal,
    user_id: UUID
) -> Requirement:
    """Update requirement when trade is completed"""
```

#### **🚀 5. Search by Intent Type** **(NEW - ENHANCEMENT)**
```python
async def search_by_intent(
    self,
    intent_type: str,  # DIRECT_BUY, NEGOTIATION, AUCTION_REQUEST, PRICE_DISCOVERY_ONLY
    commodity_id: UUID = None,
    min_buyer_priority_score: float = 1.0,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[Requirement], int]:
    """
    Search requirements by intent type
    
    Use Cases:
    - Matching Engine: Route DIRECT_BUY to immediate matching
    - Negotiation Engine: Route NEGOTIATION to multi-round negotiation
    - Auction Module: Route AUCTION_REQUEST to reverse auction
    - Analytics: Route PRICE_DISCOVERY_ONLY to market insights
    
    Filters by buyer_priority_score to prioritize serious buyers
    """
```

#### **🚀 6. Search with Market Embedding** **(NEW - ENHANCEMENT)**
```python
async def search_with_market_embedding(
    self,
    embedding_vector: List[float],  # 1536-dim vector
    similarity_threshold: float = 0.85,
    commodity_id: UUID = None,
    limit: int = 20
) -> List[Tuple[Requirement, float]]:
    """
    Vector similarity search using market_context_embedding
    
    Enables:
    - Find requirements with similar market sentiment
    - Cross-commodity pattern matching
    - Predict future requirement trends
    - Autonomous trade engine decision making
    
    Uses: pgvector cosine similarity (<=>)
    Returns: List of (requirement, similarity_score) tuples
    """
```

---

## 🚀 PHASE 4: SERVICE LAYER (Day 4)

### **Service: `RequirementService`**

**Location:** `backend/modules/trade_desk/services/requirement_service.py`

**Key Features:**

#### **1. Create Requirement with AI Pipeline**
```python
async def create_requirement(
    self,
    buyer_partner_id: UUID,
    commodity_id: UUID,
    quality_requirements: dict,
    min_quantity: Decimal,
    max_quantity: Decimal,
    max_budget_per_unit: Decimal,
    user_id: UUID,
    **kwargs
) -> Requirement:
    """
    🚀 12-Step AI Pipeline (ENHANCED from 10):
    1. Validate buyer permissions
    2. Normalize quality requirements (AI)
    3. Suggest realistic budget (AI)
    4. Calculate AI score vector (embeddings)
    5. Detect unrealistic budget (AI)
    6. Generate requirement number (REQ-2025-000001)
    7. **🆕 Adjust market sentiment** (AI - ENHANCEMENT)
    8. **🆕 Calculate dynamic tolerance recommendations** (AI - ENHANCEMENT)
    9. Create requirement record
    10. Emit requirement.created event
    11. If status=ACTIVE, trigger auto-matching
    12. Return requirement with AI insights
    """
```

#### **2. Publish Requirement (DRAFT → ACTIVE)**
```python
async def publish_requirement(
    self,
    requirement_id: UUID,
    user_id: UUID
) -> Requirement:
    """
    Publish requirement to marketplace
    - Change status to ACTIVE
    - Emit requirement.published event
    - Trigger auto-matching with availabilities
    - Send notifications to relevant sellers
    """
```

#### **3. Auto-Match with Availabilities**
```python
async def find_compatible_availabilities(
    self,
    requirement_id: UUID,
    min_match_score: float = 0.6,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Find and score compatible availabilities
    
    Returns:
    [
        {
            "availability": Availability object,
            "match_score": 0.85,
            "match_details": {
                "quality_fit": 0.92,
                "price_competitiveness": 0.78,
                "quantity_match": 1.0,
                "proximity_km": 45,
                "delivery_feasibility": 0.95
            }
        }
    ]
    """
```

#### **4. Update Requirement**
```python
async def update_requirement(
    self,
    requirement_id: UUID,
    update_data: dict,
    user_id: UUID
) -> Requirement:
    """
    Smart update with change detection:
    - Detects quality_requirements changes → emit quality_changed
    - Detects budget changes → emit budget_changed
    - Detects visibility changes → emit visibility_changed
    - Re-triggers matching if quality/budget changed
    """
```

#### **5. AI Integration Hooks (TODO Placeholders)**
```python
async def _normalize_quality_requirements(
    self, 
    commodity_id: UUID, 
    quality_requirements: dict
) -> dict:
    """
    TODO: AI normalization
    - Standardize quality parameter names
    - Fill missing tolerances with commodity defaults
    - Validate parameter ranges against commodity specs
    """
    
async def _suggest_realistic_budget(
    self,
    commodity_id: UUID,
    quality_requirements: dict,
    quantity: Decimal,
    delivery_location: dict
) -> Tuple[Decimal, int]:
    """
    TODO: AI price suggestion
    - Analyze historical trades for similar quality
    - Factor in current market conditions
    - Consider delivery location premium
    Returns: (suggested_max_price, confidence_score)
    """
    
async def _detect_budget_anomaly(
    self,
    commodity_id: UUID,
    max_budget_per_unit: Decimal,
    quality_requirements: dict
) -> Tuple[bool, str]:
    """
    TODO: Detect unrealistic budgets
    - Too low: Won't find sellers
    - Too high: Overpaying risk
    Returns: (is_anomaly, reason)
    """
    
async def _calculate_requirement_score_vector(
    self,
    commodity_id: UUID,
    quality_requirements: dict,
    budget: Decimal,
    urgency: str
) -> dict:
    """
    TODO: Generate ML embeddings
    - Commodity type embedding
    - Quality flexibility score
    - Price sensitivity score
    - Urgency score
    - Used for smart matching
    """

async def _calculate_market_context_embedding(
    self,
    commodity_id: UUID,
    quality_requirements: dict,
    budget: Decimal,
    delivery_window: dict,
    urgency: str,
    intent_type: str
) -> List[float]:
    """
    🚀 TODO: Generate market context embedding (1536-dim vector)
    
    Inputs:
    - Current market sentiment (bullish/bearish)
    - Historical price trends
    - Seasonal patterns
    - Buyer's historical behavior
    - Quality requirements specificity
    - Budget vs market price delta
    - Urgency & intent signals
    
    Uses: OpenAI ada-002 or custom ML model
    Returns: 1536-dimensional embedding vector
    
    Enables:
    - Vector similarity search for matching
    - Cross-commodity pattern detection
    - Autonomous trade engine predictions
    """

async def _adjust_for_market_sentiment(
    self,
    commodity_id: UUID,
    max_budget_per_unit: Decimal,
    quality_requirements: dict,
    urgency: str
) -> Tuple[Decimal, dict, str]:
    """
    🚀 TODO: Market sentiment adjustment (ENHANCEMENT #7 - STEP 7)
    
    Analyzes:
    - Current commodity market trends (bull/bear)
    - Supply/demand imbalance
    - Recent price volatility
    - Seasonal factors
    
    Actions:
    - Suggests budget increase if market is bullish
    - Suggests budget decrease if market is bearish
    - Relaxes quality tolerances if supply is tight
    - Tightens quality tolerances if supply is abundant
    
    Returns: (adjusted_budget, adjusted_quality, reasoning)
    
    Emits: requirement.ai_adjusted event for transparency
    """

async def _calculate_dynamic_tolerance_recommendations(
    self,
    commodity_id: UUID,
    quality_requirements: dict,
    available_sellers_count: int,
    urgency: str
) -> dict:
    """
    🚀 TODO: Dynamic tolerance recommendations (ENHANCEMENT #7 - STEP 8)
    
    Logic:
    - If urgency=URGENT and sellers<5 → Suggest relaxing quality tolerances
    - If urgency=PLANNING and sellers>20 → Suggest tightening quality tolerances
    - Calculate optimal tolerance ranges for maximum matches
    
    Returns: 
    {
      "recommended_quality_tolerances": {...},
      "expected_match_increase": 15,  // % increase in matches
      "reasoning": "Relaxing micronaire from 4.0-4.3 to 3.8-4.5 will increase matches by 15%"
    }
    
    Emits: requirement.ai_adjusted event if tolerances modified
    """
```

---

## 🚀 PHASE 5: REST API + SCHEMAS (Day 5)

### **Routes: `RequirementRoutes`**

**Location:** `backend/modules/trade_desk/routes/requirement_routes.py`

**Router Prefix:** `/api/v1/requirements`

---

### **PUBLIC ENDPOINTS (Buyers):**

#### **1. POST /requirements**
```python
@router.post("/", response_model=RequirementResponse)
async def create_requirement(
    data: CreateRequirementRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create new requirement (buyer posts what they need)
    
    Auth: JWT required
    Permissions: requirement.create (buyers only)
    """
```

#### **2. GET /requirements/search**
```python
@router.get("/search", response_model=RequirementSearchResponse)
async def search_requirements(
    commodity_id: UUID = None,
    min_quantity: Decimal = None,
    max_budget: Decimal = None,
    urgency_level: str = None,
    market_visibility: List[str] = Query(default=["PUBLIC"]),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Search requirements (sellers find buyers)
    
    Auth: JWT required
    Filters: Respects market_visibility
    """
```

#### **3. GET /requirements/my**
```python
@router.get("/my", response_model=List[RequirementResponse])
async def get_my_requirements(
    status: List[RequirementStatus] = Query(default=None),
    commodity_id: UUID = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Get buyer's own requirements
    
    Auth: JWT required
    Returns: Only current user's partner requirements
    """
```

#### **4. GET /requirements/{id}**
```python
@router.get("/{id}", response_model=RequirementDetailResponse)
async def get_requirement(
    id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get requirement details
    
    Auth: JWT required
    Authorization: Buyer can see own, sellers can see if visible
    """
```

#### **5. PUT /requirements/{id}**
```python
@router.put("/{id}", response_model=RequirementResponse)
async def update_requirement(
    id: UUID,
    data: UpdateRequirementRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update requirement
    
    Auth: JWT required
    Authorization: Only requirement owner
    Constraints: Can only update if status = DRAFT or ACTIVE
    """
```

#### **6. POST /requirements/{id}/publish**
```python
@router.post("/{id}/publish", response_model=RequirementResponse)
async def publish_requirement(
    id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Publish requirement (DRAFT → ACTIVE)
    
    Auth: JWT required
    Authorization: Only requirement owner
    Triggers: Auto-matching with availabilities
    """
```

#### **7. POST /requirements/{id}/cancel**
```python
@router.post("/{id}/cancel", response_model=RequirementResponse)
async def cancel_requirement(
    id: UUID,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel requirement
    
    Auth: JWT required
    Authorization: Only requirement owner
    """
```

#### **8. GET /requirements/{id}/matches**
```python
@router.get("/{id}/matches", response_model=AvailabilityMatchResponse)
async def get_compatible_availabilities(
    id: UUID,
    min_match_score: float = 0.6,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """
    Get compatible availabilities for requirement
    
    Auth: JWT required
    Authorization: Only requirement owner
    Returns: Scored list of matching availabilities
    """
```

---

### **INTERNAL ENDPOINTS (System Use):**

#### **9. POST /requirements/{id}/update-fulfillment**
```python
@router.post("/{id}/update-fulfillment")
@require_permission("requirement.update_fulfillment")
async def update_fulfillment(
    id: UUID,
    purchased_quantity: Decimal,
    amount_spent: Decimal,
    current_user: User = Depends(get_current_user)
):
    """
    Update fulfillment when trade completed
    
    Auth: JWT required
    Permissions: requirement.update_fulfillment (internal)
    Called by: Trade Finalization Engine (Engine 5)
    """
```

#### **🚀 10. POST /requirements/{id}/ai-adjust** **(NEW - ENHANCEMENT)**
```python
@router.post("/{id}/ai-adjust", response_model=RequirementResponse)
async def ai_adjust_requirement(
    id: UUID,
    adjustment_params: AIAdjustmentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    AI adjusts requirement parameters for better matching
    
    Auth: JWT required
    Authorization: Only requirement owner
    
    AI Adjustments:
    - Market sentiment-based budget adjustment
    - Dynamic quality tolerance recommendations
    - Delivery window optimization
    - Commodity substitution suggestions
    
    Emits: requirement.ai_adjusted event for transparency
    
    Use Cases:
    - Buyer: "Not getting enough matches? Let AI adjust my requirement"
    - Autonomous Trade Engine: Auto-adjust requirements based on market conditions
    """
```

#### **🚀 11. GET /requirements/{id}/history** **(NEW - ENHANCEMENT)**
```python
@router.get("/{id}/history", response_model=RequirementHistoryResponse)
async def get_requirement_history(
    id: UUID,
    event_types: List[str] = Query(default=None),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Get full event history for requirement
    
    Auth: JWT required
    Authorization: Only requirement owner
    
    Returns:
    - All requirement.* events
    - AI adjustment history (requirement.ai_adjusted)
    - Matching attempts history
    - Fulfillment updates
    
    Use Cases:
    - Audit trail: "What changed and when?"
    - AI explainability: "Why did AI adjust my budget from 60K to 62K?"
    - Analytics: "Which adjustments led to successful matches?"
    """
```

---

### **Pydantic Schemas:**

**Location:** `backend/modules/trade_desk/schemas/requirement_schemas.py`

```python
class QualityRequirement(BaseModel):
    """Flexible quality requirement structure"""
    min: Optional[Decimal] = None
    max: Optional[Decimal] = None
    exact: Optional[Decimal] = None
    preferred: Optional[Decimal] = None
    accepted: Optional[List[str]] = None
    required: Optional[List[str]] = None

class DeliveryLocation(BaseModel):
    location_id: UUID
    latitude: Decimal
    longitude: Decimal
    max_distance_km: Optional[int] = 50

class CreateRequirementRequest(BaseModel):
    commodity_id: UUID
    variety_id: Optional[UUID] = None
    min_quantity: Decimal = Field(gt=0)
    max_quantity: Decimal = Field(gt=0)
    quantity_unit: str
    preferred_quantity: Optional[Decimal] = None
    quality_requirements: Dict[str, QualityRequirement]
    max_budget_per_unit: Decimal = Field(gt=0)
    preferred_price_per_unit: Optional[Decimal] = None
    total_budget: Optional[Decimal] = None
    preferred_payment_terms: Optional[List[UUID]] = None
    preferred_delivery_terms: Optional[List[UUID]] = None
    delivery_locations: Optional[List[DeliveryLocation]] = None
    market_visibility: MarketVisibility = MarketVisibility.PUBLIC
    invited_seller_ids: Optional[List[UUID]] = None
    valid_from: datetime
    valid_until: datetime
    urgency_level: UrgencyLevel = UrgencyLevel.NORMAL
    notes: Optional[str] = None
    attachments: Optional[List[dict]] = None
    
    @validator('max_quantity')
    def validate_max_quantity(cls, v, values):
        if 'min_quantity' in values and v < values['min_quantity']:
            raise ValueError('max_quantity must be >= min_quantity')
        return v

class RequirementResponse(BaseModel):
    id: UUID
    requirement_number: str
    buyer_partner_id: UUID
    commodity_id: UUID
    variety_id: Optional[UUID]
    status: RequirementStatus
    min_quantity: Decimal
    max_quantity: Decimal
    quantity_unit: str
    quality_requirements: dict
    max_budget_per_unit: Decimal
    market_visibility: MarketVisibility
    urgency_level: UrgencyLevel
    total_matched_quantity: Decimal
    total_purchased_quantity: Decimal
    ai_suggested_max_price: Optional[Decimal]
    ai_confidence_score: Optional[int]
    created_at: datetime
    valid_from: datetime
    valid_until: datetime
    
class RequirementDetailResponse(RequirementResponse):
    """Includes sensitive/full details"""
    preferred_price_per_unit: Optional[Decimal]
    total_budget: Optional[Decimal]
    preferred_payment_terms: Optional[list]
    preferred_delivery_terms: Optional[list]
    delivery_locations: Optional[list]
    invited_seller_ids: Optional[list]
    notes: Optional[str]
    attachments: Optional[list]
    ai_score_vector: Optional[dict]
    ai_price_alert_flag: bool
    ai_alert_reason: Optional[str]

class AvailabilityMatchResponse(BaseModel):
    requirement_id: UUID
    matches: List[dict]  # {availability, match_score, match_details}
    total_matches: int
    
class RequirementSearchResponse(BaseModel):
    requirements: List[RequirementResponse]
    total: int
    skip: int
    limit: int
```

---

## 🚀 PHASE 6: WEBSOCKET CHANNELS (Day 6)

**Reuse Existing Infrastructure:**
- `backend/core/events/event_bus.py` (already exists)
- WebSocket manager (already exists)

**New Channels:**

1. **`requirement.{requirement_id}.updates`**
   - Events: requirement.*, real-time updates

2. **`buyer.{buyer_partner_id}.requirements`**
   - Events: All requirement events for this buyer

3. **`commodity.{commodity_id}.requirements`**
   - Events: New requirements posted for this commodity (sellers subscribe)

4. **`requirement.{requirement_id}.matches`**
   - Events: New compatible availabilities found

5. **🚀 `requirement.intent_updates`** **(NEW - ENHANCEMENT)**
   - Events: Real-time intent-based requirement updates
   - Subscribers: Matching Engine, Negotiation Engine, Auction Module
   - Purpose: Route requirements based on intent_type
     - `DIRECT_BUY` → Immediate matching pipeline
     - `NEGOTIATION` → Multi-round negotiation queue
     - `AUCTION_REQUEST` → Reverse auction module
     - `PRICE_DISCOVERY_ONLY` → Market insights dashboard

---

## 🚀 PHASE 7: TESTING (Day 7)

### **Test Suite Structure:**

**Location:** `backend/tests/trade_desk/requirements/`

#### **1. `test_requirement_model.py`**
- Test quantity validations
- Test budget validations
- Test status transitions
- Test event emission
- Test fulfillment tracking

#### **2. `test_requirement_repository.py`**
- Test CRUD operations
- Test search_compatible_availabilities() matching algorithm
- Test quality tolerance matching
- Test price filtering
- Test geo-proximity scoring

#### **3. `test_requirement_service.py`**
- Test create_requirement() with AI pipeline
- Test publish_requirement()
- Test update_requirement() with change detection
- Test find_compatible_availabilities()
- Test update_fulfillment_from_trade()

#### **4. `test_requirement_api.py`**
- Test all **11 REST endpoints** (9 public + 2 new enhancements)
- Test JWT authentication
- Test RBAC permissions
- Test buyer/seller authorization
- Test market visibility filters
- Test AI adjustment endpoint (new)
- Test history endpoint (new)

#### **5. `test_requirement_matching.py`**
- Test matching score calculations
- Test quality tolerance logic
- Test price competitiveness scoring
- Test quantity overlap logic
- Test delivery proximity calculations

#### **6. `test_multi_commodity_requirements.py`**
- Cotton requirements
- Gold requirements
- Wheat requirements
- Custom commodity requirements

---

## 🎨 EXAMPLE DATA

### **Cotton Requirement (Buyer):**
```json
{
  "buyer_partner_id": "uuid-of-textile-mill",
  "commodity_id": "uuid-of-cotton",
  "variety_id": "uuid-of-dch32",
  "min_quantity": 200,
  "max_quantity": 500,
  "quantity_unit": "bales",
  "preferred_quantity": 300,
  "quality_requirements": {
    "staple_length": {
      "min": 28,
      "max": 30,
      "preferred": 29
    },
    "micronaire": {
      "min": 3.8,
      "max": 4.5,
      "preferred": 4.2
    },
    "moisture": {
      "max": 8
    },
    "trash": {
      "max": 3
    }
  },
  "max_budget_per_unit": 61000,
  "preferred_price_per_unit": 59500,
  "total_budget": 18000000,
  "preferred_payment_terms": ["cash-uuid", "15day-uuid"],
  "preferred_delivery_terms": ["delivered-uuid"],
  "delivery_locations": [
    {
      "location_id": "uuid-of-pune",
      "latitude": 18.5204,
      "longitude": 73.8567,
      "max_distance_km": 100
    }
  ],
  "market_visibility": "PUBLIC",
  "urgency_level": "URGENT",
  "valid_from": "2025-11-24T00:00:00Z",
  "valid_until": "2025-12-01T23:59:59Z"
}
```

### **Gold Requirement (Jewelry Manufacturer):**
```json
{
  "buyer_partner_id": "uuid-of-jewelry-manufacturer",
  "commodity_id": "uuid-of-gold",
  "min_quantity": 500,
  "max_quantity": 2000,
  "quantity_unit": "grams",
  "preferred_quantity": 1000,
  "quality_requirements": {
    "purity": {
      "exact": 22
    },
    "hallmark": {
      "required": ["BIS"]
    },
    "form": {
      "accepted": ["bars"]
    }
  },
  "max_budget_per_unit": 6600,
  "preferred_price_per_unit": 6400,
  "total_budget": 13000000,
  "preferred_payment_terms": ["cash-uuid"],
  "preferred_delivery_terms": ["delivered-uuid"],
  "delivery_locations": [
    {
      "location_id": "uuid-of-mumbai",
      "latitude": 19.0760,
      "longitude": 72.8777,
      "max_distance_km": 50
    }
  ],
  "market_visibility": "PUBLIC",
  "urgency_level": "NORMAL",
  "valid_from": "2025-11-24T00:00:00Z",
  "valid_until": "2025-11-30T23:59:59Z"
}
```

---

## 🔧 BUYER LOCATION VALIDATION RULES

**CRITICAL BUSINESS RULE:**

- **BUYER:** Can specify delivery to their OWN registered locations + branches
- **TRADER:** Can specify delivery to ANY location (flexibility)

**Implementation:**
- Enforced in `RequirementService.create_requirement()`
- Check: `partner.partner_type == 'TRADER' OR delivery_location_id IN partner.registered_locations`

---

## 📊 MATCHING ALGORITHM DETAILS

### **Quality Tolerance Matching:**

**Example: Cotton Staple Length**
```
Requirement: min=28, max=30, preferred=29
Availability: actual=29.5

Score = 1.0 - (|29.5 - 29| / tolerance_range)
      = 1.0 - (0.5 / 2)
      = 0.75
```

### **Price Competitiveness:**

```
Requirement: max_budget=61000, preferred=59500
Availability: price=60000

If price <= preferred: score = 1.0
If price > preferred && price <= max_budget:
  score = (max_budget - price) / (max_budget - preferred)
  score = (61000 - 60000) / (61000 - 59500)
  score = 1000 / 1500
  score = 0.67
If price > max_budget: score = 0.0
```

### **Quantity Match:**

```
Requirement: min=200, max=500
Availability: available=300

If available >= max: score = 1.0
If available >= min && available < max:
  score = available / max
  score = 300 / 500
  score = 0.6
If available < min: score = available / min (partial order)
```

### **Delivery Proximity:**

```
Requirement: delivery_location with max_distance=100km
Availability: delivery_location

distance = haversine(req_lat, req_lng, avail_lat, avail_lng)
distance = 45 km

If distance <= max_distance:
  score = 1.0 - (distance / max_distance)
  score = 1.0 - (45 / 100)
  score = 0.55
If distance > max_distance: score = 0.0
```

---

## ✅ IMPLEMENTATION CHECKLIST

### **Phase 1: Database (Day 1)**
- [ ] Create migration file
- [ ] Define `requirements` table with all fields
- [ ] Add quality_requirements JSONB
- [ ] Add delivery_locations JSONB
- [ ] Add ai_score_vector JSONB
- [ ] **🚀 Add intent_type field (ENHANCEMENT #1)**
- [ ] **🚀 Add market_context_embedding VECTOR(1536) (ENHANCEMENT #2)**
- [ ] **🚀 Add delivery_window_start, delivery_window_end, delivery_flexibility_hours (ENHANCEMENT #3)**
- [ ] **🚀 Add commodity_equivalents JSONB (ENHANCEMENT #4)**
- [ ] **🚀 Add negotiation_preferences JSONB (ENHANCEMENT #5)**
- [ ] **🚀 Add buyer_priority_score FLOAT (ENHANCEMENT #6)**
- [ ] Create core indexes
- [ ] Create JSONB GIN indexes
- [ ] Create composite indexes
- [ ] Create partial index for active requirements
- [ ] **🚀 Create vector index for market_context_embedding (pgvector)**
- [ ] Add auto-update trigger for fulfillment status
- [ ] Add validation constraints
- [ ] Add table/column comments
- [ ] Test upgrade/downgrade

### **Phase 2: Models & Events (Day 2)**
- [ ] Create `RequirementStatus` enum
- [ ] Create `UrgencyLevel` enum
- [ ] **🚀 Create `IntentType` enum (ENHANCEMENT #1)**
- [ ] Create `Requirement` model with EventMixin
- [ ] Add business logic methods
- [ ] Create `requirement_events.py` with 11 events (10 + 1 new)
- [ ] **🚀 Add requirement.ai_adjusted event (ENHANCEMENT #7)**
- [ ] Test event emission
- [ ] Test status transitions

### **Phase 3: Repository (Day 3)**
- [ ] Create `RequirementRepository`
- [ ] Implement `create()`
- [ ] Implement `get_by_id()`
- [ ] Implement `get_buyer_requirements()`
- [ ] Implement `search_requirements()`
- [ ] Implement `search_compatible_availabilities()` with scoring
- [ ] Implement `update_fulfillment_from_trade()`
- [ ] **🚀 Implement `search_by_intent()` (ENHANCEMENT)**
- [ ] **🚀 Implement `search_with_market_embedding()` with vector similarity (ENHANCEMENT)**
- [ ] Test all repository methods

### **Phase 4: Service (Day 4)**
- [ ] Create `RequirementService`
- [ ] Implement `create_requirement()` with **12-step AI pipeline** (enhanced from 10)
- [ ] Implement `publish_requirement()`
- [ ] Implement `update_requirement()` with change detection
- [ ] Implement `cancel_requirement()`
- [ ] Implement `find_compatible_availabilities()`
- [ ] Implement `update_fulfillment_from_trade()`
- [ ] Add AI integration hooks (TODO placeholders)
- [ ] **🚀 Add `_calculate_market_context_embedding()` hook (ENHANCEMENT)**
- [ ] **🚀 Add `_adjust_for_market_sentiment()` hook (ENHANCEMENT - Step 7)**
- [ ] **🚀 Add `_calculate_dynamic_tolerance_recommendations()` hook (ENHANCEMENT - Step 8)**
- [ ] Test all service methods

### **Phase 5: API + Schemas (Day 5)**
- [ ] Create Pydantic schemas
- [ ] Create `requirement_routes.py`
- [ ] Implement POST /requirements
- [ ] Implement GET /requirements/search
- [ ] Implement GET /requirements/my
- [ ] Implement GET /requirements/{id}
- [ ] Implement PUT /requirements/{id}
- [ ] Implement POST /requirements/{id}/publish
- [ ] Implement POST /requirements/{id}/cancel
- [ ] Implement GET /requirements/{id}/matches
- [ ] Implement POST /requirements/{id}/update-fulfillment (internal)
- [ ] **🚀 Implement POST /requirements/{id}/ai-adjust (NEW ENDPOINT)**
- [ ] **🚀 Implement GET /requirements/{id}/history (NEW ENDPOINT)**
- [ ] Add JWT authentication to all endpoints
- [ ] Add RBAC permissions
- [ ] Register routes in main router

### **Phase 6: WebSocket (Day 6)**
- [ ] Create requirement.* event channels
- [ ] Create buyer.* subscription channels
- [ ] Create commodity.* requirement channels
- [ ] Create requirement.matches channels
- [ ] **🚀 Create requirement.intent_updates channel (ENHANCEMENT)**
- [ ] Test real-time updates

### **Phase 7: Testing (Day 7)**
- [ ] Create test fixtures
- [ ] Write model tests
- [ ] Write repository tests
- [ ] Write service tests
- [ ] Write API integration tests
- [ ] Write matching algorithm tests
- [ ] Write multi-commodity tests
- [ ] Achieve 12/12 tests passing (100%)

### **Phase 8: Documentation & Merge**
- [ ] Create REQUIREMENT_ENGINE_COMPLETE.md
- [ ] Update API documentation
- [ ] Create usage examples
- [ ] Run full test suite
- [ ] Merge to main
- [ ] Tag release v1.1.0-requirement-engine

---

## 🚀 ESTIMATED TIMELINE

- **Day 1:** Database schema, migration, constraints ✅
- **Day 2:** Models, enums, events, EventMixin integration ✅
- **Day 3:** Repository layer, matching algorithm ✅
- **Day 4:** Service layer, AI pipeline, change detection ✅
- **Day 5:** REST API, schemas, JWT auth, RBAC ✅
- **Day 6:** WebSocket channels, real-time updates ✅
- **Day 7:** Comprehensive testing (100% coverage) ✅
- **Day 8:** Documentation, merge, release ✅

**Total:** 7-8 days for complete Engine 2

---

## 🎯 SUCCESS CRITERIA

1. ✅ All tests passing (12/12 or more)
2. ✅ Multi-commodity support validated (Cotton, Gold, Wheat)
3. ✅ JWT authentication on all endpoints
4. ✅ RBAC permissions enforced
5. ✅ Matching algorithm scoring validated
6. ✅ Quality tolerance logic tested
7. ✅ Price competitiveness logic tested
8. ✅ Delivery proximity calculations tested
9. ✅ Event sourcing working (10 events)
10. ✅ WebSocket real-time updates functional
11. ✅ AI hooks ready for ML integration
12. ✅ Documentation complete

---

## 🔗 INTEGRATION WITH ENGINE 1 (AVAILABILITY)

**Key Integration Points:**

1. **Matching Algorithm:**
   - Requirement service calls AvailabilityRepository to find matches
   - Scoring algorithm compares requirement criteria vs availability data

2. **Event Synchronization:**
   - When new availability posted → trigger re-matching for active requirements
   - When requirement budget increased → re-score existing availabilities

3. **Shared Services:**
   - Same commodity validation
   - Same location validation
   - Same market visibility logic

4. **WebSocket Coordination:**
   - Requirement and Availability updates flow to same channels
   - Matching engine subscribes to both event streams

---

## 🎨 KEY DESIGN DECISIONS

### **1. Why Min/Max Quantity Ranges?**
Buyers are flexible! They want 200-500 bales, not exactly 300. Sellers can fulfill partially.

### **2. Why Quality Tolerances (min/max/preferred)?**
Real-world procurement has acceptable ranges. Preferred=29mm, but 28-30mm is acceptable.

### **3. Why Multiple Delivery Locations?**
Large buyers have multiple facilities. Willing to accept delivery to any of them.

### **4. Why AI Budget Suggestion?**
First-time buyers don't know fair prices. AI guides them to realistic budgets.

### **5. Why Urgency Levels?**
Urgent requirements get priority in matching. Planning requirements can wait for better prices.

### **6. Why Market Visibility?**
Some requirements are strategic (don't want competitors to see). Others are public tenders.

---

## 📝 NEXT STEPS AFTER APPROVAL

1. ✅ Get approval on this implementation plan
2. ✅ Start Phase 1 (Database Schema)
3. ✅ Commit Phase 1 and get validation
4. ✅ Continue systematic 8-phase implementation
5. ✅ Test after each phase
6. ✅ Merge to main when 100% complete

---

**Status:** ⏳ Awaiting Approval to Begin Implementation

**Question for You:**
1. Approve this plan as-is? ✅ / ❌
2. Any modifications needed?
3. Any additional features for requirements?
4. Ready to start Phase 1 (Database)? ✅ / ❌

---

## 🎯 **WHAT MAKES THIS 2035-READY?**

### **Autonomous AI Capabilities:**
- Self-adjusting requirements based on market sentiment
- AI-powered quality tolerance optimization
- Autonomous negotiation within buyer preferences
- Predictive matching using vector embeddings

### **Real-Time Intent Matching:**
- Routes requirements based on buyer intent
- DIRECT_BUY → Immediate matching
- NEGOTIATION → Multi-round negotiation engine
- AUCTION_REQUEST → Reverse auction module
- PRICE_DISCOVERY_ONLY → Market insights only

### **Cross-Commodity Intelligence:**
- Intelligent substitutions (Cotton → Yarn, Paddy → Rice)
- Value chain integration
- Supply chain optimization
- Multi-commodity pattern detection

### **Explainable AI:**
- requirement.ai_adjusted events for transparency
- GET /requirements/{id}/history for audit trail
- AI reasoning exposed to buyers
- Trust through transparency

### **Scalability:**
- Works with ANY commodity (universal JSONB schema)
- Vector similarity search (millions of requirements)
- Buyer priority scoring (prevent spam)
- Market context embeddings (predictive analytics)

---

**Let's build the 2035 Requirement Engine NOW! 🚀**

