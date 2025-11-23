# Technical Specification - Architecture Enhancements
## Multi-Commodity Trading Platform - Revolutionary Features

**Document Version:** 1.0  
**Date:** November 23, 2025  
**Status:** Approved for Implementation  
**Timeline:** 6-8 weeks

---

## Executive Summary

Transform the existing multi-commodity ERP into a revolutionary platform with:
1. **Real-Time Market Intelligence** - Live pricing from global exchanges
2. **AI-Powered Quality Grading** - Computer vision for instant commodity grading
3. **Smart Settlement Engine** - 60-second auto-reconciliation
4. **Cross-Commodity Analytics** - Portfolio optimization and hedging strategies
5. **Cryptographic Provenance** - Blockchain-less supply chain tracking

**Business Model:** Intermediary earning commission on trades between buyers and sellers with flexible payment terms (Credit, Cash, Advance).

---

## 1. Current Architecture Assessment

### ✅ What's Already Good

```
✅ Multi-commodity support (Commodity master with categories)
✅ Flexible quality parameters (CommodityParameter model)
✅ Payment terms (Advance, Credit, Cash - days & percentage)
✅ Commission structures (PERCENTAGE, FIXED, TIERED)
✅ Trading terms (Passing, Weightment, Delivery)
✅ Modular architecture (18 modules)
✅ Event-driven design
✅ RBAC & data isolation
```

### ⚠️ What Needs Enhancement

```
❌ No real-time market data integration
❌ No AI grading capabilities
❌ Manual settlement/reconciliation
❌ No cross-commodity analytics
❌ No provenance tracking
❌ No arbitrage detection
❌ Limited price prediction
```

---

## 2. Database Schema Enhancements

### 2.1 Add Market Intelligence Fields to Commodity Table

```sql
-- Migration: Add real-time market integration fields

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS 
    global_benchmark VARCHAR(100);  -- ICE_COTTON_NO2, COMEX_GOLD, CBOT_WHEAT

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    current_market_price NUMERIC(15, 2);

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    price_currency VARCHAR(3) DEFAULT 'USD';

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    last_price_update TIMESTAMP;

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    price_change_24h NUMERIC(5, 2);  -- Percentage

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    ai_price_prediction_1h NUMERIC(15, 2);

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    ai_price_prediction_24h NUMERIC(15, 2);

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    prediction_confidence NUMERIC(3, 2);  -- 0.00 to 1.00

ALTER TABLE commodities ADD COLUMN IF NOT EXISTS
    volume_24h NUMERIC(15, 2);

-- Index for fast market queries
CREATE INDEX idx_commodities_benchmark ON commodities(global_benchmark);
CREATE INDEX idx_commodities_category_active ON commodities(category, is_active);
```

### 2.2 Create Market Price History Table

```sql
-- Track historical prices for AI training

CREATE TABLE commodity_price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commodity_id UUID NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    
    -- Price data
    price NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    exchange VARCHAR(100),  -- ICE, COMEX, MCX, CBOT
    
    -- Volume & market depth
    volume NUMERIC(15, 2),
    bid_price NUMERIC(15, 2),
    ask_price NUMERIC(15, 2),
    
    -- Metadata
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source VARCHAR(50),  -- API, MANUAL, SCRAPER
    
    CONSTRAINT unique_commodity_timestamp UNIQUE(commodity_id, recorded_at, exchange)
);

CREATE INDEX idx_price_history_commodity_time 
    ON commodity_price_history(commodity_id, recorded_at DESC);
    
CREATE INDEX idx_price_history_exchange 
    ON commodity_price_history(exchange, recorded_at DESC);
```

### 2.3 Create Arbitrage Opportunities Table

```sql
-- Store detected arbitrage opportunities

CREATE TABLE arbitrage_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commodity_id UUID NOT NULL REFERENCES commodities(id),
    
    -- Opportunity details
    buy_exchange VARCHAR(100) NOT NULL,
    buy_price NUMERIC(15, 2) NOT NULL,
    sell_exchange VARCHAR(100) NOT NULL,
    sell_price NUMERIC(15, 2) NOT NULL,
    
    -- Profit calculation
    profit_percentage NUMERIC(5, 2) NOT NULL,
    estimated_profit_amount NUMERIC(15, 2),
    
    -- Risk & execution
    risk_score NUMERIC(3, 2),  -- 0.00 to 1.00
    execution_window_seconds INTEGER,  -- How long opportunity lasts
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'DETECTED',  -- DETECTED, NOTIFIED, EXECUTED, EXPIRED
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    executed_at TIMESTAMP,
    
    -- User action
    notified_users UUID[],
    executed_by UUID REFERENCES users(id)
);

CREATE INDEX idx_arbitrage_commodity_status 
    ON arbitrage_opportunities(commodity_id, status, detected_at DESC);
```

### 2.4 Create AI Quality Grading Table

```sql
-- Store AI grading results

CREATE TABLE ai_quality_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commodity_id UUID NOT NULL REFERENCES commodities(id),
    
    -- Grading input
    image_url TEXT,
    image_hash VARCHAR(64),  -- SHA-256 for deduplication
    lab_report_data JSONB,
    
    -- AI results
    grade VARCHAR(10),  -- A, B, C or numerical
    confidence_score NUMERIC(3, 2) NOT NULL,  -- 0.00 to 1.00
    detected_parameters JSONB,  -- JSON with all quality params
    
    -- Quality details (example for cotton)
    -- Will be flexible JSONB to support all commodities
    quality_data JSONB,
    /*
    Example for Cotton:
    {
        "fiber_length": 28.5,
        "micronaire": 4.2,
        "staple": "34mm",
        "trash_content": 2.1,
        "color_grade": "White",
        "strength": "30 g/tex"
    }
    
    Example for Wheat:
    {
        "protein_content": 12.5,
        "moisture": 13.0,
        "test_weight": 60,
        "foreign_matter": 1.5,
        "shriveled_kernels": 3.2
    }
    */
    
    -- Market estimate
    estimated_market_price NUMERIC(15, 2),
    price_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Audit
    graded_by UUID REFERENCES users(id),
    grading_model_version VARCHAR(50),
    graded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Verification
    verified_by_human BOOLEAN DEFAULT FALSE,
    human_grade VARCHAR(10),
    grade_difference NUMERIC(5, 2)  -- Difference between AI and human
);

CREATE INDEX idx_ai_grades_commodity ON ai_quality_grades(commodity_id, graded_at DESC);
CREATE INDEX idx_ai_grades_confidence ON ai_quality_grades(confidence_score);
CREATE INDEX idx_ai_grades_image_hash ON ai_quality_grades(image_hash);
```

### 2.5 Create Settlement/Reconciliation Tables

```sql
-- Auto-settlement tracking

CREATE TABLE settlement_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Trade reference
    contract_id UUID,  -- Will link to contracts module
    invoice_id UUID,
    delivery_note_id UUID,
    
    -- Parties (Buyer-Seller, no intermediary in payment)
    buyer_id UUID NOT NULL REFERENCES business_partners(id),
    seller_id UUID NOT NULL REFERENCES business_partners(id),
    intermediary_id UUID REFERENCES business_partners(id),  -- Your organization
    
    -- Amounts
    contract_amount NUMERIC(15, 2),
    invoice_amount NUMERIC(15, 2),
    delivered_amount NUMERIC(15, 2),
    final_settlement_amount NUMERIC(15, 2) NOT NULL,
    
    -- Adjustments
    quality_adjustment NUMERIC(15, 2) DEFAULT 0,
    quantity_adjustment NUMERIC(15, 2) DEFAULT 0,
    freight_adjustment NUMERIC(15, 2) DEFAULT 0,
    other_adjustments NUMERIC(15, 2) DEFAULT 0,
    
    -- Commission (your earning)
    commission_amount NUMERIC(15, 2) NOT NULL,
    commission_type VARCHAR(50),  -- PERCENTAGE, FIXED
    commission_rate NUMERIC(5, 2),
    
    -- Payment terms
    payment_term_id UUID REFERENCES payment_terms(id),
    payment_due_date DATE,
    payment_type VARCHAR(50),  -- CASH, CREDIT, ADVANCE
    
    -- Settlement status
    status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, AUTO_MATCHED, MANUAL_REVIEW, SETTLED, DISPUTED
    confidence_score NUMERIC(3, 2),  -- AI matching confidence
    
    -- AI reconciliation
    auto_matched BOOLEAN DEFAULT FALSE,
    matched_at TIMESTAMP,
    matched_by_ai_version VARCHAR(50),
    discrepancies JSONB,  -- JSON array of found issues
    
    -- Human intervention
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    settlement_notes TEXT,
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX idx_settlement_buyer ON settlement_records(buyer_id, status);
CREATE INDEX idx_settlement_seller ON settlement_records(seller_id, status);
CREATE INDEX idx_settlement_status ON settlement_records(status, created_at DESC);
CREATE INDEX idx_settlement_auto_matched ON settlement_records(auto_matched, confidence_score);
```

### 2.6 Create Provenance Tracking Table

```sql
-- Cryptographic provenance without blockchain

CREATE TABLE commodity_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Batch identification
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    commodity_id UUID NOT NULL REFERENCES commodities(id),
    quantity NUMERIC(15, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    
    -- Origin
    origin_type VARCHAR(50),  -- FARM, WAREHOUSE, IMPORT
    origin_id UUID,
    origin_gps_lat NUMERIC(10, 8),
    origin_gps_long NUMERIC(11, 8),
    origin_country VARCHAR(2),
    
    -- Provenance chain (cryptographically signed events)
    chain_events JSONB NOT NULL,
    /*
    [
        {
            "event": "HARVEST",
            "timestamp": "2025-11-23T10:00:00Z",
            "location": {"lat": 21.1458, "long": 79.0882},
            "actor_id": "uuid-farmer",
            "signature": "sha256-hash",
            "data": {"quantity": 1000, "unit": "KG"}
        },
        {
            "event": "QUALITY_TEST",
            "timestamp": "2025-11-23T14:00:00Z",
            "lab_id": "uuid-lab",
            "signature": "sha256-hash",
            "data": {"grade": "A", "report_id": "uuid"}
        }
    ]
    */
    
    -- Current status
    current_location_type VARCHAR(50),  -- FARM, WAREHOUSE, IN_TRANSIT, DELIVERED
    current_location_id UUID,
    current_owner_id UUID REFERENCES business_partners(id),
    
    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verification_method VARCHAR(50),  -- CRYPTOGRAPHIC, MANUAL, AUDIT
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX idx_provenance_batch ON commodity_provenance(batch_id);
CREATE INDEX idx_provenance_commodity ON commodity_provenance(commodity_id);
CREATE INDEX idx_provenance_owner ON commodity_provenance(current_owner_id);
```

---

## 3. Backend Module Enhancements

### 3.1 Create Market Intelligence Module

**Location:** `backend/modules/market_intelligence/`

```
backend/modules/market_intelligence/
├── __init__.py
├── models.py              # Price history, arbitrage models
├── schemas.py             # API request/response schemas
├── services.py            # Business logic
├── repositories.py        # Data access
├── router.py              # API endpoints
├── integrations/
│   ├── __init__.py
│   ├── ice_exchange.py    # ICE (Cotton, Sugar, Coffee)
│   ├── comex.py           # COMEX (Gold, Silver, Copper)
│   ├── cbot.py            # CBOT (Grains)
│   ├── mcx.py             # MCX India
│   └── nymex.py           # NYMEX (Oil, Gas)
└── ai/
    ├── __init__.py
    ├── price_predictor.py # Time series forecasting
    └── arbitrage_detector.py
```

**Key Services:**

```python
# backend/modules/market_intelligence/services.py

class MarketIntelligenceService:
    """Core market intelligence service"""
    
    async def fetch_live_prices(
        self, 
        commodity_ids: List[UUID]
    ) -> Dict[UUID, LivePrice]:
        """
        Fetch real-time prices from all relevant exchanges
        Updates commodity.current_market_price
        """
        pass
    
    async def predict_price_movement(
        self,
        commodity_id: UUID,
        horizon: str  # '1h', '24h', '7d'
    ) -> PricePrediction:
        """
        AI-powered price prediction using:
        - Historical data
        - Market sentiment
        - Geopolitical events
        - Weather patterns (for agri commodities)
        """
        pass
    
    async def detect_arbitrage_opportunities(
        self,
        min_profit_percentage: float = 2.0
    ) -> List[ArbitrageOpportunity]:
        """
        Scan all commodities across all exchanges
        Find profitable arbitrage opportunities
        """
        pass
    
    async def get_cross_commodity_correlation(
        self,
        commodity_id_1: UUID,
        commodity_id_2: UUID,
        period_days: int = 30
    ) -> float:
        """
        Calculate correlation between two commodities
        Used for hedging recommendations
        """
        pass
```

### 3.2 Create AI Quality Grading Module

**Location:** `backend/modules/ai_quality/`

```
backend/modules/ai_quality/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── repositories.py
├── router.py
├── ai_models/
│   ├── __init__.py
│   ├── cotton_grader.py       # Cotton-specific model
│   ├── wheat_grader.py        # Wheat-specific model
│   ├── gold_grader.py         # Metal purity detection
│   ├── universal_grader.py    # Multi-commodity base model
│   └── model_registry.py      # Load appropriate model
└── vision/
    ├── __init__.py
    ├── image_preprocessor.py
    ├── feature_extractor.py
    └── quality_detector.py
```

**Key Services:**

```python
# backend/modules/ai_quality/services.py

class AIQualityGradingService:
    """AI-powered quality grading"""
    
    async def grade_from_image(
        self,
        commodity_id: UUID,
        image: UploadFile,
        user_id: UUID
    ) -> AIQualityGrade:
        """
        Upload image → AI analysis → Quality grade
        
        Returns:
        - Grade (A, B, C)
        - Confidence score
        - Detected parameters
        - Estimated market price
        """
        pass
    
    async def grade_from_lab_report(
        self,
        commodity_id: UUID,
        lab_data: Dict,
        user_id: UUID
    ) -> AIQualityGrade:
        """
        Process lab report data → Quality grade
        Handles PDF extraction, OCR, and data parsing
        """
        pass
    
    async def compare_ai_vs_human(
        self,
        grading_id: UUID
    ) -> GradeComparison:
        """
        Compare AI grade with human inspector grade
        Track accuracy for model improvement
        """
        pass
    
    async def estimate_market_price(
        self,
        commodity_id: UUID,
        quality_parameters: Dict
    ) -> Decimal:
        """
        Estimate market price based on quality
        Uses current market data + quality adjustments
        """
        pass
```

### 3.3 Create Smart Settlement Module

**Location:** `backend/modules/smart_settlement/`

```
backend/modules/smart_settlement/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── repositories.py
├── router.py
├── matching/
│   ├── __init__.py
│   ├── fuzzy_matcher.py       # Fuzzy entity matching
│   ├── quantity_reconciler.py # Unit conversion & matching
│   └── price_calculator.py    # Adjustments & deductions
└── payment/
    ├── __init__.py
    ├── payment_calculator.py  # Calculate final amount
    ├── term_handler.py        # Handle Credit/Cash/Advance
    └── commission_calculator.py  # Calculate your commission
```

**Key Services:**

```python
# backend/modules/smart_settlement/services.py

class SmartSettlementService:
    """Automated settlement and reconciliation"""
    
    async def auto_reconcile(
        self,
        contract_id: UUID,
        invoice_id: UUID,
        delivery_note_id: UUID
    ) -> SettlementResult:
        """
        Auto-match contract → invoice → delivery note
        
        Steps:
        1. Fuzzy match buyer/seller names
        2. Reconcile quantities (handle unit conversions)
        3. Calculate quality adjustments
        4. Apply payment terms
        5. Calculate commission
        6. Auto-approve if confidence > 95%
        
        Returns settlement record with status
        """
        pass
    
    async def calculate_settlement_amount(
        self,
        contract_amount: Decimal,
        quality_actual: Dict,
        quality_contracted: Dict,
        quantity_delivered: Decimal,
        payment_term: PaymentTerm
    ) -> SettlementCalculation:
        """
        Calculate final settlement amount with all adjustments
        
        Buyer pays Seller directly
        You earn commission from both/either party
        """
        pass
    
    async def calculate_commission(
        self,
        settlement_amount: Decimal,
        commission_structure_id: UUID,
        party_type: str  # BUYER or SELLER
    ) -> Decimal:
        """
        Calculate intermediary commission
        Supports PERCENTAGE, FIXED, TIERED structures
        """
        pass
    
    async def trigger_payment(
        self,
        settlement_id: UUID,
        payment_term: PaymentTerm
    ) -> PaymentInitiation:
        """
        Initiate payment based on terms:
        - CASH: Immediate payment
        - ADVANCE: Already paid
        - CREDIT: Schedule payment on due date
        
        Payment flows: Buyer → Seller (not through intermediary)
        """
        pass
```

### 3.4 Create Provenance Tracking Module

**Location:** `backend/modules/provenance/`

```
backend/modules/provenance/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── repositories.py
├── router.py
├── crypto/
│   ├── __init__.py
│   ├── signer.py              # Cryptographic signatures
│   ├── verifier.py            # Signature verification
│   └── hash_generator.py
└── events/
    ├── __init__.py
    ├── harvest_event.py
    ├── quality_test_event.py
    ├── transport_event.py
    └── delivery_event.py
```

**Key Services:**

```python
# backend/modules/provenance/services.py

class ProvenanceService:
    """Blockchain-less provenance tracking"""
    
    async def create_batch(
        self,
        commodity_id: UUID,
        origin_data: OriginData,
        quantity: Decimal
    ) -> CommodityProvenance:
        """
        Create new commodity batch with provenance tracking
        Generates unique batch_id
        Creates first event (HARVEST/PRODUCTION/IMPORT)
        """
        pass
    
    async def add_event(
        self,
        batch_id: str,
        event_type: str,  # QUALITY_TEST, TRANSPORT, WAREHOUSE, DELIVERY
        event_data: Dict,
        actor_id: UUID
    ) -> ProvenanceEvent:
        """
        Add cryptographically signed event to chain
        
        Each event includes:
        - Timestamp
        - Actor (who did it)
        - Location (GPS if applicable)
        - Data (specific to event type)
        - Signature (SHA-256 hash)
        
        No blockchain fees, instant verification
        """
        pass
    
    async def verify_chain(
        self,
        batch_id: str
    ) -> VerificationResult:
        """
        Verify entire provenance chain
        Check all cryptographic signatures
        Returns TRUE if chain is intact
        """
        pass
    
    async def get_full_history(
        self,
        batch_id: str
    ) -> List[ProvenanceEvent]:
        """
        Get complete journey:
        Farm → Quality Test → Warehouse → Transport → Delivery
        
        Provides transparency to buyers
        """
        pass
```

---

## 4. API Endpoints Design

### 4.1 Market Intelligence APIs

```python
# GET /api/v1/market/live-prices?commodity_ids=uuid1,uuid2
# Response: Real-time prices for requested commodities

# GET /api/v1/market/predictions/{commodity_id}?horizon=24h
# Response: AI price prediction

# GET /api/v1/market/arbitrage-opportunities?min_profit=2.0
# Response: List of profitable arbitrage opportunities

# GET /api/v1/market/correlations?commodity1=uuid1&commodity2=uuid2
# Response: Correlation coefficient for hedging
```

### 4.2 AI Quality Grading APIs

```python
# POST /api/v1/ai-quality/grade-from-image
# Body: multipart/form-data (image file + commodity_id)
# Response: AIQualityGrade with confidence score

# POST /api/v1/ai-quality/grade-from-lab
# Body: JSON with lab report data
# Response: AIQualityGrade

# GET /api/v1/ai-quality/estimate-price
# Query: commodity_id, quality parameters
# Response: Estimated market price
```

### 4.3 Smart Settlement APIs

```python
# POST /api/v1/settlement/auto-reconcile
# Body: contract_id, invoice_id, delivery_note_id
# Response: SettlementRecord (with status: AUTO_MATCHED or NEEDS_REVIEW)

# GET /api/v1/settlement/calculate
# Query: contract details, delivery details
# Response: Settlement calculation breakdown

# POST /api/v1/settlement/approve/{settlement_id}
# Response: Payment initiated

# GET /api/v1/settlement/pending-reviews
# Response: List of settlements needing human review
```

### 4.4 Provenance APIs

```python
# POST /api/v1/provenance/create-batch
# Body: commodity_id, origin_data, quantity
# Response: CommodityProvenance with batch_id

# POST /api/v1/provenance/add-event
# Body: batch_id, event_type, event_data
# Response: ProvenanceEvent with signature

# GET /api/v1/provenance/verify/{batch_id}
# Response: Verification result (true/false)

# GET /api/v1/provenance/history/{batch_id}
# Response: Complete provenance chain
```

---

## 5. Integration Requirements

### 5.1 Exchange API Integrations

| Exchange | Commodities | API Type | Auth Method |
|----------|-------------|----------|-------------|
| ICE (Intercontinental Exchange) | Cotton, Sugar, Coffee | REST + WebSocket | API Key |
| COMEX (CME Group) | Gold, Silver, Copper | REST + FIX | OAuth 2.0 |
| CBOT (Chicago Board of Trade) | Wheat, Corn, Soy | REST + FIX | API Key |
| MCX (India) | Metals, Energy, Agri | REST | API Key |
| NYMEX (CME Group) | Oil, Natural Gas | REST + FIX | OAuth 2.0 |

**Implementation Priority:**
1. MCX (for Indian market)
2. ICE (for cotton)
3. COMEX (for metals)
4. CBOT (for grains)
5. NYMEX (for energy)

### 5.2 AI/ML Model Requirements

| Model | Purpose | Framework | Deployment |
|-------|---------|-----------|------------|
| Price Predictor | Time series forecasting | Prophet / LSTM | FastAPI endpoint |
| Quality Grader (Cotton) | Image → Quality grade | PyTorch / YOLO | FastAPI endpoint |
| Quality Grader (Grains) | Image → Quality grade | TensorFlow | FastAPI endpoint |
| OCR Engine | Lab report extraction | Tesseract / EasyOCR | FastAPI endpoint |
| Fuzzy Matcher | Entity matching | Sentence-BERT | In-process |

---

## 6. Implementation Phases

### Phase 1: Market Intelligence (Week 1-2)

**Tasks:**
1. Create database schema (price_history, arbitrage_opportunities)
2. Add market fields to commodities table
3. Build MarketIntelligenceService
4. Integrate MCX API (Indian market first)
5. Build price prediction model (basic ARIMA)
6. Create arbitrage detection algorithm
7. Build API endpoints
8. Create admin dashboard for monitoring

**Deliverables:**
- ✅ Real-time price updates every 5 minutes
- ✅ Price predictions (1h, 24h, 7d)
- ✅ Arbitrage alerts
- ✅ 3 exchange integrations (MCX, ICE, COMEX)

### Phase 2: AI Quality Grading (Week 3-4)

**Tasks:**
1. Create ai_quality_grades table
2. Build AIQualityGradingService
3. Train cotton grading model (transfer learning from ImageNet)
4. Train wheat grading model
5. Build image upload API
6. Create mobile camera integration
7. Build confidence scoring
8. Create human verification workflow

**Deliverables:**
- ✅ AI grading for 2 commodities (Cotton, Wheat)
- ✅ 90%+ accuracy compared to human graders
- ✅ 5-second grading time
- ✅ Mobile app integration

### Phase 3: Smart Settlement (Week 5-6)

**Tasks:**
1. Create settlement_records table
2. Build fuzzy matching engine
3. Build quantity reconciliation
4. Build price adjustment calculator
5. Build commission calculator
6. Integrate with payment terms
7. Create approval workflow
8. Build settlement dashboard

**Deliverables:**
- ✅ 95% auto-match rate for clean data
- ✅ 60-second settlement for auto-matched
- ✅ Commission calculation automation
- ✅ Payment term handling (Cash, Credit, Advance)

### Phase 4: Provenance Tracking (Week 7-8)

**Tasks:**
1. Create commodity_provenance table
2. Build cryptographic signing service
3. Build event chain management
4. Create verification service
5. Build QR code generation
6. Create public verification page
7. Mobile scanning integration

**Deliverables:**
- ✅ Complete supply chain tracking
- ✅ Instant verification (<1 second)
- ✅ QR code for batch tracking
- ✅ Public verification portal

---

## 7. Performance Requirements

### 7.1 Response Times

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Live price fetch | 500ms | 2 seconds |
| AI quality grading | 5 seconds | 10 seconds |
| Auto-reconciliation | 30 seconds | 60 seconds |
| Provenance verification | 500ms | 1 second |
| Arbitrage detection | 10 seconds | 30 seconds |

### 7.2 Accuracy Requirements

| Feature | Target Accuracy | Min Acceptable |
|---------|-----------------|----------------|
| AI quality grading | 95% | 90% |
| Auto-settlement matching | 98% | 95% |
| Price prediction (24h) | 80% | 70% |
| Fuzzy entity matching | 99% | 97% |

### 7.3 Scalability

- Support 100+ commodities
- Handle 10,000 price updates/minute
- Process 1,000 quality gradings/day
- Auto-reconcile 500 settlements/day
- Track 100,000+ provenance batches

---

## 8. Technology Stack Additions

### 8.1 New Dependencies

```toml
# Add to pyproject.toml

[tool.poetry.dependencies]
# Market data
websockets = "^12.0"          # Real-time price streaming
ccxt = "^4.1"                 # Cryptocurrency exchange library (has commodity APIs too)
pandas-ta = "^0.3"            # Technical analysis

# AI/ML
torch = "^2.1"                # Deep learning
torchvision = "^0.16"         # Computer vision
transformers = "^4.35"        # Pre-trained models
prophet = "^1.1"              # Time series forecasting
sentence-transformers = "^2.2" # Fuzzy matching

# Image processing
pillow = "^10.1"              # Image manipulation
opencv-python = "^4.8"        # Computer vision
pytesseract = "^0.3"          # OCR

# Cryptography
pycryptodome = "^3.19"        # Enhanced crypto functions
hashlib                        # Built-in, for signatures

# Data science
numpy = "^1.24"
scipy = "^1.11"
scikit-learn = "^1.3"
```

### 8.2 Infrastructure Additions

```yaml
# docker-compose additions

services:
  # Time series database for price history
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: market_data
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${TIMESCALE_PASSWORD}
    volumes:
      - timescale_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
  
  # AI model serving
  ai_service:
    build: ./backend/ai_models
    environment:
      MODEL_PATH: /models
    volumes:
      - ./ai_models:/models
    ports:
      - "8001:8000"
  
  # Redis for caching market data
  redis_cache:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - redis_cache_data:/data

volumes:
  timescale_data:
  redis_cache_data:
```

---

## 9. Security Considerations

### 9.1 API Keys Management

- Store exchange API keys in environment variables
- Rotate keys monthly
- Use separate keys for dev/staging/prod
- Implement rate limiting per key

### 9.2 Data Integrity

- Cryptographic signatures on all provenance events
- Audit trail for all settlement modifications
- Version control for AI model predictions
- Immutable price history records

### 9.3 Access Control

- RBAC for market data access
- Separate permissions for AI grading approval
- Settlement approval limits by role
- API rate limiting per user

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# test_market_intelligence.py
- test_fetch_live_prices()
- test_predict_price_movement()
- test_detect_arbitrage()

# test_ai_quality.py
- test_grade_from_image()
- test_estimate_market_price()
- test_compare_ai_vs_human()

# test_smart_settlement.py
- test_auto_reconcile()
- test_calculate_commission()
- test_fuzzy_matching()

# test_provenance.py
- test_create_batch()
- test_add_event()
- test_verify_chain()
```

### 10.2 Integration Tests

- End-to-end settlement flow
- Live API connectivity (sandbox)
- AI model inference pipeline
- Provenance chain verification

### 10.3 Performance Tests

- Load test: 10,000 price updates/minute
- Stress test: 1,000 concurrent AI gradings
- Latency test: Settlement under 60 seconds

---

## 11. Monitoring & Observability

### 11.1 Metrics to Track

```python
# Market Intelligence
- price_update_latency
- arbitrage_opportunities_detected
- prediction_accuracy_score

# AI Quality
- grading_requests_per_day
- average_confidence_score
- ai_vs_human_agreement_rate

# Smart Settlement
- auto_match_success_rate
- average_settlement_time
- manual_review_percentage

# Provenance
- batches_created_per_day
- verification_requests
- chain_integrity_failures
```

### 11.2 Alerts

- Exchange API downtime
- AI model accuracy drops below 90%
- Settlement auto-match rate drops below 95%
- Provenance signature verification failures

---

## 12. Documentation Requirements

### 12.1 Technical Documentation

- Architecture diagrams (Mermaid/Draw.io)
- API documentation (OpenAPI/Swagger)
- Database schema diagrams
- AI model documentation

### 12.2 User Documentation

- Market intelligence dashboard guide
- AI quality grading user manual
- Settlement reconciliation workflow
- Provenance tracking guide

---

## 13. Success Metrics

### 13.1 Business Metrics

- 80% reduction in settlement time (5 days → 60 seconds)
- 50% reduction in grading costs (AI vs human)
- 30% increase in arbitrage profit capture
- 100% provenance tracking coverage

### 13.2 Technical Metrics

- 99.9% API uptime
- <2 second average API response time
- 95%+ AI grading accuracy
- 98%+ auto-settlement match rate

---

## 14. Risk Mitigation

### 14.1 Identified Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Exchange API changes | HIGH | Version locking, fallback APIs |
| AI model drift | MEDIUM | Continuous retraining, human verification |
| Price data delays | HIGH | Multiple data sources, caching |
| Settlement errors | CRITICAL | Human review workflow, rollback capability |

### 14.2 Rollback Plan

- Feature flags for each new module
- Database migration rollback scripts
- AI model versioning
- Gradual rollout (10% → 50% → 100%)

---

## 15. Next Steps

### Immediate Actions (This Week)

1. ✅ Review and approve this spec
2. ✅ Set up TimescaleDB for price history
3. ✅ Create database migrations for new tables
4. ✅ Research and select exchange APIs
5. ✅ Set up AI model development environment

### Week 1-2 (Market Intelligence)

1. Implement market intelligence module
2. Integrate first exchange API (MCX)
3. Build price prediction model
4. Create arbitrage detection

### Week 3-4 (AI Quality)

1. Implement AI quality grading module
2. Train cotton grading model
3. Build mobile camera integration
4. Create verification workflow

### Week 5-6 (Smart Settlement)

1. Implement smart settlement module
2. Build fuzzy matching engine
3. Create commission calculator
4. Build approval workflow

### Week 7-8 (Provenance)

1. Implement provenance module
2. Build cryptographic services
3. Create QR code system
4. Build public verification portal

---

## Appendix A: Sample Data Structures

### A.1 Live Price Response

```json
{
  "commodity_id": "uuid",
  "commodity_name": "Cotton",
  "benchmark": "ICE_COTTON_NO2",
  "current_price": 85.50,
  "currency": "USD",
  "unit": "per pound",
  "change_24h": 2.3,
  "volume_24h": 15000000,
  "bid": 85.45,
  "ask": 85.55,
  "predictions": {
    "1h": {
      "price": 85.75,
      "confidence": 0.87,
      "trend": "UP"
    },
    "24h": {
      "price": 86.20,
      "confidence": 0.72,
      "trend": "UP"
    }
  },
  "last_updated": "2025-11-23T10:30:00Z"
}
```

### A.2 AI Quality Grade Response

```json
{
  "grade_id": "uuid",
  "commodity_id": "uuid",
  "commodity_name": "Cotton",
  "grade": "A",
  "confidence_score": 0.94,
  "quality_parameters": {
    "fiber_length": 28.5,
    "micronaire": 4.2,
    "staple": "34mm",
    "trash_content": 2.1,
    "color_grade": "White",
    "strength": "30 g/tex"
  },
  "estimated_market_price": 87.20,
  "price_currency": "USD",
  "grading_model_version": "cotton-v2.1",
  "graded_at": "2025-11-23T10:35:00Z"
}
```

### A.3 Settlement Record Response

```json
{
  "settlement_id": "uuid",
  "status": "AUTO_MATCHED",
  "confidence_score": 0.97,
  "buyer": {
    "id": "uuid",
    "name": "ABC Textiles"
  },
  "seller": {
    "id": "uuid",
    "name": "XYZ Cotton Farmers"
  },
  "intermediary": {
    "id": "uuid",
    "name": "Your Organization"
  },
  "amounts": {
    "contract_amount": 1000000.00,
    "invoice_amount": 1000000.00,
    "delivered_amount": 995000.00,
    "quality_adjustment": -5000.00,
    "final_settlement_amount": 995000.00
  },
  "commission": {
    "amount": 9950.00,
    "type": "PERCENTAGE",
    "rate": 1.0,
    "applies_to": "BUYER"
  },
  "payment": {
    "term": "CREDIT_30_DAYS",
    "due_date": "2025-12-23",
    "type": "CREDIT"
  },
  "matched_at": "2025-11-23T10:40:00Z"
}
```

---

**End of Technical Specification**

---

## Approval Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Tech Lead | | | |
| CTO | | | |

---

**Document Control:**
- Version: 1.0
- Last Updated: November 23, 2025
- Next Review: December 7, 2025
