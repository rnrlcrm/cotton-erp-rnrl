# Commodity Master Module - Complete Documentation

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Business Logic Flow](#business-logic-flow)
5. [AI Features](#ai-features)
6. [API Endpoints](#api-endpoints)
7. [Event System](#event-system)
8. [Bulk Operations](#bulk-operations)
9. [Complete Workflows](#complete-workflows)

---

## 🎯 Overview

The Commodity Master module is a sophisticated system for managing commodities (cotton, textiles, agricultural products) with **AI-powered intelligence** and **self-learning capabilities**. It's designed for the cotton trading industry with support for quality parameters, trade terms, and commission structures.

### Key Features
- ✅ **Commodity Management** - Full CRUD with varieties and quality parameters
- ✅ **AI-Powered HSN Suggestions** - Intelligent tax code detection with learning
- ✅ **Self-Learning System** - SystemCommodityParameter learns from user behavior
- ✅ **Quality Parameters** - Configurable quality metrics per commodity
- ✅ **Trade Terms** - 6 types of trading terms (Trade, Bargain, Passing, etc.)
- ✅ **Commission Structures** - Percentage/Fixed/Tiered commission models
- ✅ **Event Sourcing** - Complete audit trail of all changes
- ✅ **Bulk Operations** - Excel import/export
- ✅ **Advanced Filtering** - Search with caching

### Module Structure (12 Files)
```
backend/modules/settings/commodities/
├── models.py                    # 11 data models
├── schemas.py                   # Pydantic validation schemas
├── services.py                  # Business logic (11 services)
├── repositories.py              # Data access layer (11 repositories)
├── router.py                    # REST API endpoints (50+ routes)
├── events.py                    # Event definitions (10 events)
├── ai_helpers.py                # AI enrichment logic
├── hsn_learning.py              # Self-learning HSN system
├── hsn_models.py                # HSN knowledge base model
├── bulk_operations.py           # Excel import/export
├── filters.py                   # Advanced search & caching
└── __init__.py                  # Module initialization
```

---

## 🏗️ Architecture

### Layered Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER (router.py)                    │
│  - 50+ REST endpoints                                            │
│  - Request validation (Pydantic schemas)                         │
│  - Response serialization                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC (services.py)                  │
│  - 11 service classes                                            │
│  - AI enrichment integration                                     │
│  - Event emission                                                │
│  - Transaction management                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  DATA ACCESS (repositories.py)                   │
│  - 11 repository classes                                         │
│  - SQLAlchemy queries                                            │
│  - CRUD operations                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL)                         │
│  - 11 tables with relationships                                  │
│  - Audit trails (EventMixin)                                     │
│  - Full referential integrity                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Cross-Cutting Concerns
```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  AI Helpers      │  │  Event System    │  │  Bulk Operations │
│  ─────────────   │  │  ──────────────  │  │  ──────────────  │
│  • HSN Learning  │  │  • EventEmitter  │  │  • Excel Import  │
│  • Category AI   │  │  • 10 Event      │  │  • Excel Export  │
│  • Parameter AI  │  │    Types         │  │  • Validation    │
│  • Validation    │  │  • Audit Trail   │  │  • Templates     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 📊 Data Models

### 1. Commodity (Core Entity)
**Purpose**: Main commodity definition (e.g., "Raw Cotton", "Cotton Yarn")

**Fields**:
- `id` - UUID primary key
- `name` - Commodity name (unique)
- `category` - Category (e.g., "Natural Fiber", "Synthetic")
- `hsn_code` - Tax classification code
- `gst_rate` - Tax rate percentage
- `description` - Detailed description
- `uom` - Unit of measurement (MT, Bales, etc.)
- `is_active` - Soft delete flag
- Audit: `created_at`, `updated_at`, `created_by`, `updated_by`

**Relationships**:
- `varieties` → One-to-Many → CommodityVariety
- `parameters` → One-to-Many → CommodityParameter
- `commissions` → One-to-Many → CommissionStructure

**Events**: EventMixin enabled (commodity.created, commodity.updated, commodity.deleted)

---

### 2. CommodityVariety
**Purpose**: Sub-types of commodities (e.g., "DCH-32", "Shankar-6" for cotton)

**Fields**:
- `id` - UUID
- `commodity_id` - Foreign key to Commodity
- `name` - Variety name
- `code` - Short code
- `description` - Details
- `is_standard` - Flag for standard varieties
- `is_active` - Status

**Unique Constraint**: `(commodity_id, name)` - No duplicate varieties per commodity

**Example**:
```
Commodity: "Raw Cotton"
  ├── Variety: "DCH-32" (code: DCH32)
  ├── Variety: "Shankar-6" (code: SHK6)
  └── Variety: "MCU-5" (code: MCU5)
```

---

### 3. CommodityParameter
**Purpose**: Quality metrics for each commodity (e.g., Staple Length, Micronaire)

**Fields**:
- `id` - UUID
- `commodity_id` - Foreign key
- `parameter_name` - Name (e.g., "Staple Length")
- `parameter_type` - NUMERIC, TEXT, or RANGE
- `unit` - Measurement unit (mm, %, g/tex)
- `min_value`, `max_value` - Range for NUMERIC/RANGE
- `default_value` - Default
- `is_mandatory` - Required field?
- `display_order` - UI ordering

**Parameter Types**:
1. **NUMERIC**: Single value (e.g., Micronaire: 4.2)
2. **TEXT**: Text value (e.g., Color Grade: "White")
3. **RANGE**: Min-Max range (e.g., Strength: 26-32 g/tex)

**Unique Constraint**: `(commodity_id, parameter_name)`

**Example**:
```
Commodity: "Raw Cotton"
  ├── Parameter: "Staple Length" (NUMERIC, unit: mm, mandatory)
  ├── Parameter: "Micronaire" (NUMERIC, unit: units, mandatory)
  ├── Parameter: "Strength" (NUMERIC, unit: g/tex)
  ├── Parameter: "Color Grade" (TEXT)
  └── Parameter: "Trash Content" (NUMERIC, unit: %)
```

---

### 4. SystemCommodityParameter (AI Learning)
**Purpose**: Template parameters that the system learns from user behavior

**Fields**:
- `id` - UUID
- `commodity_category` - Category (e.g., "Natural Fiber")
- `parameter_name` - Template name
- `parameter_type` - NUMERIC/TEXT/RANGE
- `unit` - Measurement unit
- `min_value`, `max_value` - Typical range
- `default_value` - Suggested default
- `is_mandatory` - Suggested mandatory flag
- `description` - Help text
- **`usage_count`** - How many times users added this parameter (AI ranking)
- **`source`** - Where it came from (AI_LEARNED, MANUAL, SEED)
- `is_verified` - Admin approved?

**AI Learning Cycle**:
1. User creates commodity parameter (e.g., "Staple Length" for cotton)
2. System checks if template exists for this category
3. If yes → Increment `usage_count` (popularity tracking)
4. If no → Create new template for future suggestions
5. Next time → Suggest parameters ordered by `usage_count DESC`

**Example**:
```sql
-- After 50 users add "Micronaire" to cotton commodities:
{
  "commodity_category": "Natural Fiber - Cotton",
  "parameter_name": "Micronaire",
  "usage_count": 50,  ← High popularity = suggested first
  "source": "AI_LEARNED"
}
```

---

### 5. TradeType
**Purpose**: Types of trades (e.g., "Spot", "Forward", "Basis")

**Fields**:
- `id`, `name`, `code`, `description`, `is_active`

**Example**: "Spot Trade", "Forward Contract", "Basis Trading"

---

### 6. BargainType
**Purpose**: Negotiation types (e.g., "Open", "Closed", "Auction")

**Fields**:
- `id`, `name`, `code`, `description`
- `requires_approval` - Flag for approval workflow
- `is_active`

---

### 7. PassingTerm
**Purpose**: Quality acceptance terms (e.g., "As Is", "FAQ", "SQ")

**Fields**:
- `id`, `name`, `code`, `description`
- `requires_quality_test` - Flag for QC requirement
- `is_active`

**Example**: "FAQ" (Fair Average Quality), "SQ" (Superior Quality)

---

### 8. WeightmentTerm
**Purpose**: Weight calculation methods

**Fields**:
- `id`, `name`, `code`, `description`
- `weight_deduction_percent` - Deduction for moisture/trash
- `is_active`

---

### 9. DeliveryTerm
**Purpose**: Delivery conditions (e.g., "FOB", "CIF", "Ex-Works")

**Fields**:
- `id`, `name`, `code`, `description`
- `includes_freight` - Freight included?
- `includes_insurance` - Insurance included?
- `is_active`

---

### 10. PaymentTerm
**Purpose**: Payment conditions (e.g., "Immediate", "30 Days", "Against Delivery")

**Fields**:
- `id`, `name`, `code`
- `days` - Payment period
- `payment_percentage` - Percentage to pay
- `description`, `is_active`

**Example**: "30 Days Net" (days=30, payment_percentage=100)

---

### 11. CommissionStructure
**Purpose**: Commission rates for commodities or trade types

**Fields**:
- `id`
- `commodity_id` - Optional (commission per commodity)
- `trade_type_id` - Optional (commission per trade type)
- `name` - Structure name
- `commission_type` - PERCENTAGE, FIXED, or TIERED
- `rate` - Rate value
- `min_amount`, `max_amount` - For TIERED
- `applies_to` - BUYER, SELLER, or BOTH
- `description`, `is_active`

**Commission Types**:
1. **PERCENTAGE**: 2% of transaction value
2. **FIXED**: ₹500 per transaction
3. **TIERED**: 1% up to ₹1L, 0.5% above

---

### 12. HSNKnowledgeBase (AI Learning)
**Purpose**: Self-learning HSN code database

**Fields**:
- `id` - UUID
- `commodity_name` - Search key
- `commodity_category` - Search key
- `hsn_code` - Tax code
- `hsn_description` - Description
- `gst_rate` - Tax rate
- **`source`** - API, MANUAL, AI_LEARNED, SEED
- **`confidence`** - 0.0 to 1.0 (AI confidence score)
- **`is_verified`** - User confirmed?
- **`usage_count`** - Popularity metric
- `created_at`, `updated_at`, `created_by`

**Unique Constraint**: `(commodity_name, hsn_code)`

**Learning Flow**:
1. User creates commodity "Raw Cotton" with HSN "5201"
2. System stores in knowledge base with `source=MANUAL`, `confidence=1.0`
3. Next user types "raw cotton" → Instant suggestion from knowledge base
4. Every use increments `usage_count` → More popular = higher ranking

---

## 🔄 Business Logic Flow

### Flow 1: Create Commodity with AI Enrichment

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLIENT REQUEST                                                │
│    POST /api/commodities                                         │
│    {                                                             │
│      "name": "Raw Cotton",                                       │
│      "category": "Natural Fiber",                                │
│      "description": "High quality kapas"                         │
│      // hsn_code and gst_rate MISSING                           │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ROUTER VALIDATION                                             │
│    - router.py: create_commodity()                               │
│    - Pydantic validates CommodityCreate schema                   │
│    - Injects dependencies:                                       │
│      • db: AsyncSession                                          │
│      • event_emitter: EventEmitter                               │
│      • ai_helper: CommodityAIHelper (with HSN learning)         │
│      • user_id: UUID                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. SERVICE LAYER - AI ENRICHMENT                                 │
│    - services.py: CommodityService.create_commodity()            │
│                                                                  │
│    Step 3a: Check if HSN/GST missing                            │
│    if not data.hsn_code or not data.gst_rate:                   │
│                                                                  │
│    Step 3b: AI Enrichment                                       │
│      enrichment = await ai_helper.enrich_commodity_data(        │
│        name="Raw Cotton",                                        │
│        category="Natural Fiber",                                 │
│        description="High quality kapas"                          │
│      )                                                           │
│      # Returns: {                                               │
│      #   "suggested_hsn_code": "5201",                          │
│      #   "suggested_gst_rate": 5.0,                             │
│      #   "confidence": 0.95                                     │
│      # }                                                        │
│                                                                  │
│    Step 3c: Apply AI suggestions                                │
│      data.hsn_code = "5201"                                     │
│      data.gst_rate = 5.0                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. AI HELPER - HSN LEARNING                                      │
│    - ai_helpers.py: CommodityAIHelper.enrich_commodity_data()    │
│    - hsn_learning.py: HSNLearningService.suggest_hsn()          │
│                                                                  │
│    Step 4a: Search knowledge base                               │
│      SELECT * FROM hsn_knowledge_base                            │
│      WHERE LOWER(commodity_name) = 'raw cotton'                  │
│      ORDER BY is_verified DESC, confidence DESC, usage_count DESC│
│      LIMIT 1;                                                    │
│                                                                  │
│    Step 4b: If found → Return cached result (FAST!)            │
│      {                                                           │
│        "hsn_code": "5201",                                      │
│        "gst_rate": 5.0,                                         │
│        "confidence": 1.0                                        │
│      }                                                           │
│      → Increment usage_count                                    │
│                                                                  │
│    Step 4c: If not found → Try HSN API (if configured)         │
│                                                                  │
│    Step 4d: If API unavailable → Use dummy data                │
│      DUMMY_HSN_DATA = {                                         │
│        "raw cotton": {"hsn": "5201", "gst": 5.0}               │
│      }                                                           │
│                                                                  │
│    Step 4e: If still not found → Category fallback             │
│      if "cotton" in category:                                    │
│        return {"hsn": "5201", "gst": 5.0, "confidence": 0.4}   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. REPOSITORY - DATABASE INSERT                                  │
│    - repositories.py: CommodityRepository.create()               │
│                                                                  │
│    commodity = Commodity(                                        │
│      id=uuid4(),                                                 │
│      name="Raw Cotton",                                          │
│      category="Natural Fiber",                                   │
│      hsn_code="5201",  ← AI suggested                           │
│      gst_rate=5.0,     ← AI suggested                           │
│      description="High quality kapas",                           │
│      created_by=user_id,                                         │
│      created_at=NOW()                                            │
│    )                                                             │
│    db.add(commodity)                                             │
│    await db.flush()  # Get ID                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. AI LEARNING - Save to Knowledge Base                          │
│    - services.py (continued)                                     │
│                                                                  │
│    if ai_helper.hsn_learning and data.hsn_code:                 │
│      await ai_helper.hsn_learning.confirm_hsn_mapping(          │
│        commodity_name="Raw Cotton",                              │
│        category="Natural Fiber",                                 │
│        hsn_code="5201",                                         │
│        gst_rate=5.0,                                            │
│        user_id=user_id                                           │
│      )                                                           │
│                                                                  │
│    → Saves to hsn_knowledge_base table:                         │
│      {                                                           │
│        "commodity_name": "Raw Cotton",                           │
│        "hsn_code": "5201",                                      │
│        "gst_rate": 5.0,                                         │
│        "source": "MANUAL",                                      │
│        "confidence": 1.0,                                       │
│        "is_verified": True,                                     │
│        "usage_count": 1                                         │
│      }                                                           │
│                                                                  │
│    → Next time "Raw Cotton" is created → INSTANT suggestion!    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. EVENT EMISSION                                                │
│    - services.py (continued)                                     │
│                                                                  │
│    await event_emitter.emit(                                     │
│      CommodityCreated(                                           │
│        aggregate_id=commodity.id,                                │
│        user_id=user_id,                                          │
│        data={                                                    │
│          "name": "Raw Cotton",                                   │
│          "category": "Natural Fiber",                            │
│          "hsn_code": "5201",                                    │
│          "gst_rate": "5.0"                                      │
│        }                                                         │
│      )                                                           │
│    )                                                             │
│                                                                  │
│    → Stores in events table:                                    │
│      {                                                           │
│        "event_type": "commodity.created",                        │
│        "aggregate_id": commodity.id,                             │
│        "aggregate_type": "commodity",                            │
│        "user_id": user_id,                                       │
│        "data": {...},                                            │
│        "occurred_at": NOW()                                      │
│      }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. RESPONSE                                                      │
│    - router.py (continued)                                       │
│                                                                  │
│    return CommodityResponse(                                     │
│      id=commodity.id,                                            │
│      name="Raw Cotton",                                          │
│      category="Natural Fiber",                                   │
│      hsn_code="5201",                                           │
│      gst_rate=5.0,                                              │
│      description="High quality kapas",                           │
│      uom=None,                                                   │
│      is_active=True,                                             │
│      created_at="2025-01-15T10:30:00Z",                         │
│      created_by=user_id,                                         │
│      updated_by=None,                                            │
│      updated_at=None                                             │
│    )                                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Key Takeaways**:
1. ✅ AI auto-fills missing HSN/GST data
2. ✅ System learns from user confirmations
3. ✅ Knowledge base grows over time
4. ✅ Future lookups are instant (no API calls)
5. ✅ Event sourcing creates audit trail

---

### Flow 2: Add Parameter with AI Learning

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLIENT REQUEST                                                │
│    POST /api/commodities/{commodity_id}/parameters               │
│    {                                                             │
│      "parameter_name": "Micronaire",                             │
│      "parameter_type": "NUMERIC",                                │
│      "unit": "units",                                            │
│      "min_value": 3.5,                                           │
│      "max_value": 4.9,                                           │
│      "is_mandatory": true                                        │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. SERVICE - Create Parameter                                    │
│    - services.py: CommodityParameterService.add_parameter()      │
│                                                                  │
│    Step 2a: Create parameter                                    │
│      parameter = await repository.create(                        │
│        commodity_id=commodity_id,                                │
│        parameter_name="Micronaire",                              │
│        parameter_type="NUMERIC",                                 │
│        unit="units",                                             │
│        min_value=3.5,                                            │
│        max_value=4.9,                                            │
│        is_mandatory=True                                         │
│      )                                                           │
│      → Inserted into commodity_parameters table                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. AI LEARNING - Learn Parameter Template                        │
│    - services.py: _learn_parameter_template()                    │
│                                                                  │
│    Step 3a: Get commodity to determine category                 │
│      commodity = await commodity_repo.get_by_id(commodity_id)    │
│      # commodity.category = "Natural Fiber - Cotton"            │
│                                                                  │
│    Step 3b: Check if template exists                            │
│      SELECT * FROM system_commodity_parameters                   │
│      WHERE commodity_category = 'Natural Fiber - Cotton'         │
│        AND parameter_name = 'Micronaire';                        │
│                                                                  │
│    Step 3c: If template exists → Increment usage count          │
│      UPDATE system_commodity_parameters                          │
│      SET usage_count = usage_count + 1,                         │
│          updated_at = NOW()                                      │
│      WHERE id = template_id;                                     │
│                                                                  │
│      → Result: usage_count goes from 25 → 26                    │
│      → Higher count = Higher ranking in future suggestions      │
│                                                                  │
│    Step 3d: If template doesn't exist → Create new template    │
│      INSERT INTO system_commodity_parameters (                   │
│        commodity_category='Natural Fiber - Cotton',              │
│        parameter_name='Micronaire',                              │
│        parameter_type='NUMERIC',                                 │
│        unit='units',                                             │
│        min_value=3.5,                                            │
│        max_value=4.9,                                            │
│        is_mandatory=True,                                        │
│        usage_count=1,  ← First time this parameter used         │
│        source='AI_LEARNED',                                     │
│        created_by=user_id                                        │
│      );                                                          │
│                                                                  │
│      → New parameter discovered!                                │
│      → Will be suggested to future users creating cotton        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. EVENT EMISSION                                                │
│    await event_emitter.emit(                                     │
│      CommodityParameterAdded(                                    │
│        aggregate_id=commodity_id,                                │
│        user_id=user_id,                                          │
│        data={                                                    │
│          "parameter_id": parameter.id,                           │
│          "name": "Micronaire",                                   │
│          "type": "NUMERIC"                                       │
│        }                                                         │
│      )                                                           │
│    )                                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Learning Example Over Time**:
```sql
-- Day 1: User 1 adds "Micronaire" to cotton
usage_count = 1

-- Day 5: User 2 adds "Micronaire" to another cotton commodity
usage_count = 2

-- Month 1: 50 users have added "Micronaire"
usage_count = 50

-- Month 6: 200 users have added "Micronaire"
usage_count = 200  ← Top suggestion!

-- When new user creates cotton commodity:
POST /api/commodities/{id}/ai/suggest-parameters
Response:
[
  {
    "name": "Micronaire",        ← Suggested first (usage_count=200)
    "type": "NUMERIC",
    "unit": "units",
    "mandatory": true
  },
  {
    "name": "Staple Length",      ← Second (usage_count=180)
    ...
  },
  {
    "name": "Strength",           ← Third (usage_count=150)
    ...
  }
]
```

---

## 🤖 AI Features

### 1. HSN Code Suggestion (Self-Learning)

**Purpose**: Automatically suggest HSN tax codes and GST rates

**Components**:
- `ai_helpers.py`: CommodityAIHelper
- `hsn_learning.py`: HSNLearningService
- `hsn_models.py`: HSNKnowledgeBase table

**Flow**:
```
User Input: "Raw Cotton"
    ↓
1. Search Knowledge Base (instant, no API)
   - Query: commodity_name = "raw cotton"
   - Order: is_verified DESC, confidence DESC, usage_count DESC
   - Found? → Return HSN "5201", GST 5%
    ↓
2. Query HSN API (if configured)
   - External API call
   - Store result in knowledge base
   - Return suggestion
    ↓
3. Use Dummy Data (development mode)
   - Hardcoded mappings for common commodities
   - Cotton → 5201, Polyester → 5503, etc.
    ↓
4. Category Fallback
   - "Natural Fiber" → 5201 (cotton default)
   - "Synthetic" → 5503 (polyester default)
    ↓
5. Generic Fallback
   - HSN "0000", GST 0%, confidence 0%
   - Manual verification required
```

**Learning Cycle**:
```
User confirms HSN code
    ↓
Save to hsn_knowledge_base (source=MANUAL, confidence=1.0, is_verified=True)
    ↓
Next user types same commodity name
    ↓
Instant suggestion from knowledge base (no API call)
    ↓
Every use increments usage_count
    ↓
Popular mappings ranked higher
```

**Confidence Levels**:
- `1.0` - User confirmed (MANUAL)
- `0.95` - API verified
- `0.85` - Exact match from knowledge base
- `0.75` - Partial match from knowledge base
- `0.60` - Category fallback
- `0.40` - Generic fallback

---

### 2. Category Detection

**Purpose**: Detect commodity category from name/description

**Method**: Pattern matching (can be replaced with ML model)

**Patterns**:
```python
CATEGORY_PATTERNS = {
    "Natural Fiber": ["cotton", "jute", "silk", "wool", "linen"],
    "Synthetic Fiber": ["polyester", "nylon", "acrylic", "spandex"],
    "Blended Fiber": ["poly cotton", "cotton blend", "mixed fiber"],
    "Waste": ["waste", "scrap", "residue"],
    "Yarn": ["yarn", "thread", "spun"],
    "Fabric": ["fabric", "cloth", "textile"],
    "Seed": ["seed", "ginned"],
}
```

**API Endpoint**:
```http
POST /api/commodities/ai/detect-category
{
  "name": "raw cotton lint",
  "description": "high quality kapas"
}

Response:
{
  "category": "Natural Fiber",
  "subcategory": "Cotton",
  "confidence": 0.85
}
```

---

### 3. Quality Parameter Suggestions

**Purpose**: Suggest quality parameters based on commodity category

**Two Modes**:

#### Mode 1: Database Templates (AI Learning Enabled)
```sql
-- Query system_commodity_parameters
SELECT * FROM system_commodity_parameters
WHERE commodity_category ILIKE '%Natural Fiber%'
ORDER BY usage_count DESC,        ← Most popular first
         is_mandatory DESC,        ← Mandatory parameters first
         parameter_name
LIMIT 20;
```

**Result**:
```json
[
  {
    "name": "Micronaire",
    "type": "NUMERIC",
    "unit": "units",
    "typical_range": "3.5-4.9",
    "mandatory": true,
    "description": "Fiber fineness and maturity"
  },
  {
    "name": "Staple Length",
    "type": "NUMERIC",
    "unit": "mm",
    "typical_range": "28-32",
    "mandatory": true,
    "description": "Fiber length in millimeters"
  }
]
```

#### Mode 2: Hardcoded Standards (Fallback)
```python
STANDARD_PARAMETERS = {
    "Natural Fiber - Cotton": [
        {
            "name": "Staple Length",
            "type": "NUMERIC",
            "unit": "mm",
            "typical_range": [28, 32],
            "mandatory": True
        },
        {
            "name": "Micronaire",
            "type": "NUMERIC",
            "unit": "units",
            "typical_range": [3.5, 4.9],
            "mandatory": True
        },
        ...
    ],
    "Yarn": [...],
    "Fabric": [...]
}
```

**API Endpoint**:
```http
POST /api/commodities/{id}/ai/suggest-parameters
{
  "category": "Natural Fiber - Cotton",
  "name": "Raw Cotton"
}

Response:
[
  {
    "name": "Staple Length",
    "type": "NUMERIC",
    "unit": "mm",
    "typical_range": [28, 32],
    "mandatory": true,
    "description": "Fiber length in millimeters"
  },
  ...
]
```

---

### 4. Data Validation (AI Anomaly Detection)

**Purpose**: Validate commodity data for anomalies

**Checks**:
1. **HSN vs Category Mismatch**
   - Cotton should be 52xx
   - Synthetic should be 55xx

2. **Invalid GST Rates**
   - Valid rates: 0, 5, 12, 18, 28
   - Warn if unusual rate

3. **Range Validation**
   - min_value < max_value
   - Logical ranges

**API**:
```python
warnings = await ai_helper.validate_commodity_data({
    "category": "Natural Fiber",
    "hsn_code": "5503"  # Wrong! Should be 52xx for natural fiber
})

# Returns:
{
  "hsn_code": [
    "HSN code 5503 seems unusual for cotton (expected 52xx)"
  ]
}
```

---

## 🔌 API Endpoints

### Commodity CRUD
```http
# Create commodity
POST /api/commodities
Request: CommodityCreate
Response: CommodityResponse (201)

# Get commodity
GET /api/commodities/{id}
Response: CommodityResponse (200)

# List commodities
GET /api/commodities?category=Natural+Fiber&is_active=true
Response: List[CommodityResponse] (200)

# Update commodity
PUT /api/commodities/{id}
Request: CommodityUpdate
Response: CommodityResponse (200)

# Delete commodity (soft delete)
DELETE /api/commodities/{id}
Response: 204 No Content
```

### AI Endpoints
```http
# Detect category
POST /api/commodities/ai/detect-category
Request: {"name": "raw cotton", "description": "..."}
Response: CategorySuggestion

# Suggest HSN code
POST /api/commodities/ai/suggest-hsn
Request: {"name": "raw cotton", "category": "Natural Fiber"}
Response: HSNSuggestion

# Suggest parameters
POST /api/commodities/{id}/ai/suggest-parameters
Request: {"category": "Natural Fiber", "name": "Raw Cotton"}
Response: List[ParameterSuggestion]
```

### Variety Management
```http
# Add variety
POST /api/commodities/{id}/varieties
Request: CommodityVarietyCreate
Response: CommodityVarietyResponse (201)

# List varieties
GET /api/commodities/{id}/varieties
Response: List[CommodityVarietyResponse]

# Update variety
PUT /api/commodities/varieties/{id}
Request: CommodityVarietyUpdate
Response: CommodityVarietyResponse
```

### Parameter Management
```http
# Add parameter
POST /api/commodities/{id}/parameters
Request: CommodityParameterCreate
Response: CommodityParameterResponse (201)

# List parameters
GET /api/commodities/{id}/parameters
Response: List[CommodityParameterResponse]

# Update parameter
PUT /api/commodities/parameters/{id}
Request: CommodityParameterUpdate
Response: CommodityParameterResponse
```

### System Parameters (Admin)
```http
# Create system parameter
POST /api/commodities/system-parameters
Request: SystemCommodityParameterCreate
Response: SystemCommodityParameterResponse (201)

# List system parameters
GET /api/commodities/system-parameters?category=Natural+Fiber
Response: List[SystemCommodityParameterResponse]

# Update system parameter
PUT /api/commodities/system-parameters/{id}
Request: SystemCommodityParameterUpdate
Response: SystemCommodityParameterResponse
```

### Trade Terms
```http
# Trade Types
POST /api/commodities/trade-types
GET /api/commodities/trade-types
PUT /api/commodities/trade-types/{id}

# Bargain Types
POST /api/commodities/bargain-types
GET /api/commodities/bargain-types
PUT /api/commodities/bargain-types/{id}

# Passing Terms
POST /api/commodities/passing-terms
GET /api/commodities/passing-terms
PUT /api/commodities/passing-terms/{id}

# Weightment Terms
POST /api/commodities/weightment-terms
GET /api/commodities/weightment-terms
PUT /api/commodities/weightment-terms/{id}

# Delivery Terms
POST /api/commodities/delivery-terms
GET /api/commodities/delivery-terms
PUT /api/commodities/delivery-terms/{id}

# Payment Terms
POST /api/commodities/payment-terms
GET /api/commodities/payment-terms
PUT /api/commodities/payment-terms/{id}
```

### Commission Management
```http
# Set commission
POST /api/commodities/{id}/commission
Request: CommissionStructureCreate
Response: CommissionStructureResponse (201)

# Get commission
GET /api/commodities/{id}/commission
Response: CommissionStructureResponse

# Update commission
PUT /api/commodities/commission/{id}
Request: CommissionStructureUpdate
Response: CommissionStructureResponse
```

### Bulk Operations
```http
# Bulk upload
POST /api/commodities/bulk/upload
Request: multipart/form-data (Excel file)
Response: BulkOperationResult

# Download template
GET /api/commodities/bulk/download?include_data=false
Response: Excel file

# Validate upload
POST /api/commodities/bulk/validate
Request: multipart/form-data (Excel file)
Response: ValidationResult
```

### Advanced Search
```http
GET /api/commodities/search/advanced
  ?query=cotton
  &category=Natural+Fiber
  &hsn_code=5201
  &min_gst_rate=0
  &max_gst_rate=10
  &is_active=true
  &skip=0
  &limit=100

Response: List[CommodityResponse]
```

**Total Endpoints**: 50+ REST API routes

---

## 📡 Event System

### Event Types (10 Events)

1. **commodity.created**
   - Emitted when: New commodity created
   - Data: `{name, category, hsn_code, gst_rate}`

2. **commodity.updated**
   - Emitted when: Commodity modified
   - Data: `{changes: {field: {old, new}}}`

3. **commodity.deleted**
   - Emitted when: Commodity soft-deleted
   - Data: `{name}`

4. **commodity.variety.added**
   - Emitted when: Variety added
   - Data: `{variety_id, name, code}`

5. **commodity.variety.updated**
   - Emitted when: Variety modified
   - Data: `{variety_id, variety_name}`

6. **commodity.parameter.added**
   - Emitted when: Parameter added
   - Data: `{parameter_id, name, type}`

7. **commodity.parameter.updated**
   - Emitted when: Parameter modified
   - Data: `{parameter_id, parameter_name}`

8. **commodity.commission.set**
   - Emitted when: Commission structure set/updated
   - Data: `{commission_id, name, rate}`

9. **trade_terms.created**
   - Emitted when: Trade term created
   - Data: `{term_type, name}`

10. **trade_terms.updated**
    - Emitted when: Trade term updated
    - Data: `{term_type, name}`

### Event Storage
All events stored in `events` table:
```sql
{
  "id": UUID,
  "event_type": "commodity.created",
  "aggregate_id": commodity_id,
  "aggregate_type": "commodity",
  "user_id": user_id,
  "data": {...},
  "occurred_at": TIMESTAMP,
  "metadata": {...}
}
```

**Use Cases**:
- Audit trail
- Event replay
- Analytics
- Integration with external systems
- CQRS pattern support

---

## 📦 Bulk Operations

### Excel Import Flow
```
1. User uploads Excel file (.xlsx or .csv)
    ↓
2. System validates file format
    ↓
3. Parse rows (skip header)
    ↓
4. For each row:
   - Validate data (Pydantic schema)
   - Create commodity
   - Store in database
   - Track success/failure
    ↓
5. Commit successful imports
    ↓
6. Return summary:
   {
     "success": 95,
     "failed": 5,
     "errors": [
       {"row": 12, "error": "Invalid HSN code"},
       ...
     ],
     "created_ids": [...]
   }
```

### Excel Template Format
```
| ID | Name       | Category       | HSN Code | GST Rate | Description | UOM   | Active |
|----|------------|----------------|----------|----------|-------------|-------|--------|
|    | Raw Cotton | Natural Fiber  | 5201     | 5.0      | ...         | MT    | Yes    |
|    | Cotton Yarn| Textile        | 5205     | 12.0     | ...         | Bales | Yes    |
```

**Features**:
- ✅ Validates before import
- ✅ Skip invalid rows (configurable)
- ✅ Bulk commit for performance
- ✅ Detailed error reporting
- ✅ Download template with examples
- ✅ Export existing data to Excel

### API
```http
# Upload file
POST /api/commodities/bulk/upload
Content-Type: multipart/form-data
file: commodities.xlsx

Response:
{
  "success": 100,
  "failed": 0,
  "errors": [],
  "created_ids": [...]
}

# Download template
GET /api/commodities/bulk/download?include_data=false

# Download with existing data
GET /api/commodities/bulk/download?include_data=true

# Validate before import
POST /api/commodities/bulk/validate
Content-Type: multipart/form-data
file: commodities.xlsx

Response:
{
  "valid": true,
  "warnings": [],
  "errors": []
}
```

---

## 🔄 Complete Workflows

### Workflow 1: Create Commodity with Full Setup

**Scenario**: User creates "Raw Cotton" commodity with varieties and parameters

```
STEP 1: Create Commodity
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities
{
  "name": "Raw Cotton",
  "category": "Natural Fiber",
  "description": "High quality kapas"
}

→ AI enriches with HSN "5201" and GST 5%
→ Event emitted: commodity.created
→ Response: commodity_id = "abc-123"


STEP 2: Add Varieties
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/abc-123/varieties
{
  "name": "DCH-32",
  "code": "DCH32",
  "is_standard": true
}
→ Event emitted: commodity.variety.added

POST /api/commodities/abc-123/varieties
{
  "name": "Shankar-6",
  "code": "SHK6",
  "is_standard": true
}
→ Event emitted: commodity.variety.added


STEP 3: Get AI Parameter Suggestions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/abc-123/ai/suggest-parameters
{
  "category": "Natural Fiber",
  "name": "Raw Cotton"
}

→ Response: [
    {
      "name": "Micronaire",
      "type": "NUMERIC",
      "unit": "units",
      "typical_range": [3.5, 4.9],
      "mandatory": true
    },
    {
      "name": "Staple Length",
      "type": "NUMERIC",
      "unit": "mm",
      "typical_range": [28, 32],
      "mandatory": true
    },
    ...
  ]


STEP 4: Add Parameters
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/abc-123/parameters
{
  "parameter_name": "Micronaire",
  "parameter_type": "NUMERIC",
  "unit": "units",
  "min_value": 3.5,
  "max_value": 4.9,
  "is_mandatory": true
}
→ Event emitted: commodity.parameter.added
→ AI learns: Creates/updates SystemCommodityParameter template

POST /api/commodities/abc-123/parameters
{
  "parameter_name": "Staple Length",
  "parameter_type": "NUMERIC",
  "unit": "mm",
  "min_value": 28,
  "max_value": 32,
  "is_mandatory": true
}
→ Event emitted: commodity.parameter.added
→ AI learns: Creates/updates SystemCommodityParameter template


STEP 5: Set Commission
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/abc-123/commission
{
  "name": "Cotton Trading Commission",
  "commission_type": "PERCENTAGE",
  "rate": 2.0,
  "applies_to": "BOTH"
}
→ Event emitted: commodity.commission.set


RESULT: Complete Commodity Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commodity: "Raw Cotton"
├── HSN: 5201 (AI suggested)
├── GST: 5% (AI suggested)
├── Varieties:
│   ├── DCH-32
│   └── Shankar-6
├── Parameters:
│   ├── Micronaire (3.5-4.9, mandatory)
│   └── Staple Length (28-32mm, mandatory)
└── Commission: 2% on both sides

Events Created: 6 events
AI Learning: 2 parameter templates created/updated
HSN Knowledge: 1 new mapping learned
```

---

### Workflow 2: Bulk Import with Excel

**Scenario**: Import 100 commodities from Excel file

```
STEP 1: Download Template
━━━━━━━━━━━━━━━━━━━━━━━━
GET /api/commodities/bulk/download?include_data=false

→ Receives commodities_template.xlsx with:
  - Headers
  - Example data
  - Instructions sheet


STEP 2: Fill Template
━━━━━━━━━━━━━━━━━━━━━━
User fills Excel:
| Name          | Category       | HSN Code | GST Rate | ...
|---------------|----------------|----------|----------|----
| Raw Cotton    | Natural Fiber  | 5201     | 5.0      | ...
| Cotton Yarn   | Textile        | 5205     | 12.0     | ...
| Cotton Fabric | Textile        | 5208     | 5.0      | ...
... (97 more rows)


STEP 3: Validate (Optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/bulk/validate
file: commodities.xlsx

→ Response:
{
  "valid": true,
  "warnings": [
    "Row 15: GST rate 7% is unusual"
  ],
  "errors": []
}


STEP 4: Upload
━━━━━━━━━━━━━━
POST /api/commodities/bulk/upload
file: commodities.xlsx

→ Processing:
  - Row 2: Create "Raw Cotton" ✓
  - Row 3: Create "Cotton Yarn" ✓
  - Row 4: Create "Cotton Fabric" ✓
  - Row 5: Error - Invalid HSN ✗
  - Row 6: Create "Polyester" ✓
  ...

→ Response:
{
  "success": 95,
  "failed": 5,
  "errors": [
    {"row": 5, "error": "Invalid HSN code format"},
    {"row": 12, "error": "Duplicate commodity name"},
    ...
  ],
  "created_ids": [...]
}


RESULT
━━━━━━
✅ 95 commodities created
❌ 5 failed (with detailed errors)
📊 Events: 95 commodity.created events
🤖 AI Learning: 95 new HSN mappings learned
```

---

### Workflow 3: AI-Powered Commodity Creation

**Scenario**: User creates commodity with minimal input, AI fills everything

```
STEP 1: Minimal Input
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities
{
  "name": "kapas",
  "description": "cotton from Gujarat"
}

→ AI Processing:
  1. Detect Category: "kapas" → "Natural Fiber"
  2. Suggest HSN: "kapas" → "5201"
  3. Suggest GST: "5201" → 5.0%
  4. Enrich data


STEP 2: AI Suggestions
━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/{id}/ai/suggest-parameters
{
  "category": "Natural Fiber",
  "name": "kapas"
}

→ Response: (Ordered by popularity - usage_count DESC)
[
  {
    "name": "Micronaire",
    "type": "NUMERIC",
    "unit": "units",
    "mandatory": true,
    "typical_range": [3.5, 4.9]
  },
  {
    "name": "Staple Length",
    "type": "NUMERIC",
    "unit": "mm",
    "mandatory": true,
    "typical_range": [28, 32]
  },
  ...
]


STEP 3: Auto-Add Parameters
━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /api/commodities/{id}/parameters (Batch)
[
  {"parameter_name": "Micronaire", ...},
  {"parameter_name": "Staple Length", ...},
  {"parameter_name": "Strength", ...}
]

→ Each parameter:
  - Created in commodity_parameters
  - AI learns: Updates system_commodity_parameters usage_count
  - Event emitted


RESULT
━━━━━━
Commodity Created:
  Name: "kapas"
  Category: "Natural Fiber" (AI detected)
  HSN: "5201" (AI suggested)
  GST: 5.0% (AI suggested)
  Parameters: 5 standard parameters (AI suggested)
  
AI Learning:
  ✅ HSN mapping learned
  ✅ 5 parameter templates updated
  ✅ Next "kapas" creation will be instant!
```

---

## 📈 Performance & Scalability

### Caching Strategy
```python
# In-memory cache with TTL (5 minutes)
commodity_cache = SimpleCache(ttl_seconds=300)

# Cache keys:
- "categories" → List of all categories
- "hsn_codes" → List of all HSN codes
- search hash → Search results
```

### Database Indexes
```sql
-- Commodities
CREATE INDEX idx_commodities_name ON commodities(name);
CREATE INDEX idx_commodities_category ON commodities(category);
CREATE INDEX idx_commodities_hsn_code ON commodities(hsn_code);

-- HSN Knowledge Base
CREATE INDEX idx_hsn_kb_commodity_name ON hsn_knowledge_base(commodity_name);
CREATE INDEX idx_hsn_kb_category ON hsn_knowledge_base(commodity_category);
CREATE INDEX idx_hsn_kb_hsn_code ON hsn_knowledge_base(hsn_code);

-- System Parameters
CREATE INDEX idx_sys_params_category ON system_commodity_parameters(commodity_category);
```

### Query Optimization
```python
# Use select with limit for large datasets
query = (
    select(Commodity)
    .where(conditions)
    .offset(skip)
    .limit(100)  # Pagination
    .order_by(Commodity.name)
)

# Eager loading for relationships
query = select(Commodity).options(
    selectinload(Commodity.varieties),
    selectinload(Commodity.parameters)
)
```

---

## 🔐 Security & Validation

### Input Validation (Pydantic)
```python
class CommodityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    ...
```

### Authorization (Future)
```python
# User permissions
def get_current_user_id() -> UUID:
    # TODO: Replace with actual auth
    # Check roles: ADMIN, MANAGER, USER
    # Validate tenant isolation
    pass
```

### Data Integrity
- Unique constraints on critical fields
- Foreign key constraints
- Cascade deletes configured
- Soft deletes for audit trail

---

## 📚 Summary

### What We Built
1. **11 Data Models** - Complete commodity management schema
2. **11 Repositories** - Clean data access layer
3. **11 Services** - Business logic with event sourcing
4. **50+ API Endpoints** - Complete REST API
5. **AI System** - Self-learning HSN and parameter suggestions
6. **Event System** - Full audit trail
7. **Bulk Operations** - Excel import/export
8. **Advanced Search** - Filtering with caching

### Key Innovations
✨ **Self-Learning AI**: SystemCommodityParameter learns from user behavior
✨ **HSN Knowledge Base**: Grows over time, reduces API dependencies
✨ **Event Sourcing**: Complete audit trail of all changes
✨ **Quality Parameters**: Flexible, configurable quality metrics
✨ **Bulk Operations**: Efficient mass data management

### Technology Stack
- **Framework**: FastAPI
- **ORM**: SQLAlchemy (async)
- **Database**: PostgreSQL
- **Validation**: Pydantic
- **Events**: Custom event sourcing
- **AI**: Pattern matching + learning (extensible to ML)
- **Excel**: openpyxl

### Next Steps
1. Add frontend UI
2. Integrate real HSN API
3. Add ML models for category detection
4. Implement user authentication
5. Add multi-tenant support
6. Create mobile app integration

---

## 📞 Contact & Support

For questions about this module, refer to:
- Architecture docs: `ARCHITECTURE_AUDIT_REPORT.md`
- Implementation status: `PROJECT_STATUS.md`
- Partner module example: `BUSINESS_PARTNER_TEST_SUMMARY.md`

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-15  
**Author**: GitHub Copilot  
**Status**: ✅ Complete
