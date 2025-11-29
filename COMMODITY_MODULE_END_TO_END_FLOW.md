# Commodity Master Module - Complete End-to-End Flow Documentation

## Table of Contents
1. [Module Overview](#module-overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Core Components](#core-components)
5. [End-to-End Business Flows](#end-to-end-business-flows)
6. [AI/ML Features](#aiml-features)
7. [Event System](#event-system)
8. [API Endpoints](#api-endpoints)
9. [Testing Strategy](#testing-strategy)
10. [Suggestions & Improvements](#suggestions--improvements)

---

## Module Overview

The **Commodity Master Module** is the foundation for all trading operations in the Cotton ERP system. It manages:

- **Commodities**: Core trading items (Cotton, Wheat, Pulses, etc.)
- **Varieties**: Sub-types of commodities (DCH-32, Shankar-6 for Cotton)
- **Quality Parameters**: Specifications like Staple Length, Micronaire, Moisture
- **Trading Terms**: Trade types, bargain types, passing/weightment/delivery/payment terms
- **Commission Structures**: Buyer/seller commission configurations
- **AI-powered HSN/GST lookup**: Self-learning system for tax codes

### Key Design Principles
1. **Event Sourcing**: All state changes emit events for audit trails
2. **AI Integration**: Intelligent suggestions for HSN codes and quality parameters
3. **Self-Learning**: System learns from user confirmations to improve suggestions
4. **Clean Architecture**: Layered structure (Models → Repositories → Services → Router)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (router.py)                    │
│   REST Endpoints: POST, GET, PUT, DELETE /api/v1/commodities    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer (services.py)                │
│   Business Logic + Event Emission + AI Integration              │
│   • CommodityService            • TradeTypeService              │
│   • CommodityVarietyService     • BargainTypeService            │
│   • CommodityParameterService   • PassingTermService            │
│   • CommissionStructureService  • WeightmentTermService         │
│   • SystemCommodityParameterSvc • DeliveryTermService           │
│                                 • PaymentTermService            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  Repository Layer       │     │  AI Helper Layer                │
│  (repositories.py)      │     │  (ai_helpers.py, hsn_learning)  │
│  Data Access Patterns   │     │  • HSN Code Suggestion          │
│  • CRUD Operations      │     │  • Category Detection           │
│  • Query Builders       │     │  • Quality Parameter Suggestion │
│  • Filtering            │     │  • Self-Learning System         │
└─────────────────────────┘     └─────────────────────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Model Layer (models.py)                   │
│   SQLAlchemy Models: Commodity, CommodityVariety, etc.          │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                        │
│   11 Tables + HSN Knowledge Base                                │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure
```
backend/modules/settings/commodities/
├── __init__.py           # Module exports
├── models.py             # 11 SQLAlchemy models
├── schemas.py            # Pydantic validation schemas (~470 LOC)
├── repositories.py       # Data access layer (11 repositories)
├── services.py           # Business logic (~818 LOC)
├── router.py             # FastAPI endpoints (~824 LOC)
├── events.py             # 10 event definitions
├── ai_helpers.py         # AI intelligence (~407 LOC)
├── hsn_learning.py       # Self-learning HSN system (~357 LOC)
├── hsn_models.py         # HSN Knowledge Base model
├── filters.py            # Advanced search & caching
└── bulk_operations.py    # Excel import/export
```

---

## Database Schema

### Core Tables (11 Total)

#### 1. `commodities` - Core Entity
```sql
id                UUID PRIMARY KEY
name              VARCHAR(200) NOT NULL      -- "Raw Cotton"
category          VARCHAR(100) NOT NULL      -- "Natural Fiber"
hsn_code          VARCHAR(20)                -- "5201"
gst_rate          DECIMAL(5,2)               -- 5.00
description       TEXT
uom               VARCHAR(50)                -- "Bales", "MT", "Quintals"
is_active         BOOLEAN DEFAULT TRUE
created_by        UUID
updated_by        UUID
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

#### 2. `commodity_varieties` - Sub-types
```sql
id                UUID PRIMARY KEY
commodity_id      UUID NOT NULL FK → commodities
name              VARCHAR(200) NOT NULL      -- "DCH-32", "Shankar-6"
code              VARCHAR(50)                -- "DCH32"
description       TEXT
is_standard       BOOLEAN DEFAULT FALSE
is_active         BOOLEAN DEFAULT TRUE
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

#### 3. `commodity_parameters` - Quality Specifications
```sql
id                UUID PRIMARY KEY
commodity_id      UUID NOT NULL FK → commodities
parameter_name    VARCHAR(100) NOT NULL      -- "Staple Length"
parameter_type    VARCHAR(50) NOT NULL       -- "NUMERIC", "TEXT", "RANGE"
unit              VARCHAR(50)                -- "mm", "g/tex", "%"
min_value         DECIMAL(10,2)              -- 28.0
max_value         DECIMAL(10,2)              -- 32.0
default_value     VARCHAR(100)
is_mandatory      BOOLEAN DEFAULT FALSE
display_order     INTEGER
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

#### 4. `system_commodity_parameters` - AI Learning Templates
```sql
id                  UUID PRIMARY KEY
commodity_category  VARCHAR(100) NOT NULL    -- "Cotton"
parameter_name      VARCHAR(100) NOT NULL    -- "Staple Length"
parameter_type      VARCHAR(50) NOT NULL
unit                VARCHAR(50)
min_value           DECIMAL(10,2)
max_value           DECIMAL(10,2)
default_value       VARCHAR(100)
is_mandatory        BOOLEAN DEFAULT FALSE
description         TEXT
usage_count         INTEGER DEFAULT 0        -- AI learning: popularity
source              VARCHAR(100)             -- "SEED", "AI_LEARNED"
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
created_by          UUID
-- UNIQUE(commodity_category, parameter_name)
```

#### 5. `trade_types`
```sql
id                UUID PRIMARY KEY
name              VARCHAR(100) NOT NULL UNIQUE  -- "Purchase", "Sale"
code              VARCHAR(20) UNIQUE            -- "PUR", "SAL"
description       TEXT
is_active         BOOLEAN DEFAULT TRUE
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

#### 6. `bargain_types`
```sql
id                  UUID PRIMARY KEY
name                VARCHAR(100) NOT NULL UNIQUE  -- "Open", "Closed"
code                VARCHAR(20) UNIQUE            -- "OPEN", "CLOSED"
description         TEXT
requires_approval   BOOLEAN DEFAULT FALSE
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### 7. `passing_terms`
```sql
id                    UUID PRIMARY KEY
name                  VARCHAR(100) NOT NULL UNIQUE  -- "As Per Sample"
code                  VARCHAR(20) UNIQUE            -- "APS"
description           TEXT
requires_quality_test BOOLEAN DEFAULT FALSE
is_active             BOOLEAN DEFAULT TRUE
created_at            TIMESTAMPTZ
updated_at            TIMESTAMPTZ
```

#### 8. `weightment_terms`
```sql
id                        UUID PRIMARY KEY
name                      VARCHAR(100) NOT NULL UNIQUE  -- "Seller Weighment"
code                      VARCHAR(20) UNIQUE            -- "SEL_WT"
description               TEXT
weight_deduction_percent  DECIMAL(5,2)                  -- 2.0
is_active                 BOOLEAN DEFAULT TRUE
created_at                TIMESTAMPTZ
updated_at                TIMESTAMPTZ
```

#### 9. `delivery_terms`
```sql
id                  UUID PRIMARY KEY
name                VARCHAR(100) NOT NULL UNIQUE  -- "FOB", "CIF"
code                VARCHAR(20) UNIQUE
description         TEXT
includes_freight    BOOLEAN DEFAULT FALSE
includes_insurance  BOOLEAN DEFAULT FALSE
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### 10. `payment_terms`
```sql
id                  UUID PRIMARY KEY
name                VARCHAR(100) NOT NULL UNIQUE  -- "30 Days Credit"
code                VARCHAR(20) UNIQUE            -- "30D"
days                INTEGER                       -- 30
payment_percentage  DECIMAL(5,2)                  -- % advance
description         TEXT
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### 11. `commission_structures`
```sql
id                UUID PRIMARY KEY
commodity_id      UUID FK → commodities (nullable)
trade_type_id     UUID FK → trade_types (nullable)
name              VARCHAR(100) NOT NULL      -- "Standard Commission"
commission_type   VARCHAR(50) NOT NULL       -- "PERCENTAGE", "FIXED", "TIERED"
rate              DECIMAL(5,2)               -- 2.5
min_amount        DECIMAL(15,2)
max_amount        DECIMAL(15,2)
applies_to        VARCHAR(50)                -- "BUYER", "SELLER", "BOTH"
description       TEXT
is_active         BOOLEAN DEFAULT TRUE
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ
```

#### 12. `hsn_knowledge_base` - AI Learning Storage
```sql
id                  UUID PRIMARY KEY
commodity_name      VARCHAR(200) NOT NULL INDEX
commodity_category  VARCHAR(100) INDEX
hsn_code            VARCHAR(20) NOT NULL INDEX
hsn_description     TEXT
gst_rate            DECIMAL(5,2) NOT NULL
source              VARCHAR(50) NOT NULL      -- "API", "MANUAL", "AI_LEARNED"
confidence          DECIMAL(3,2) DEFAULT 1.0  -- 0.0 to 1.0
is_verified         BOOLEAN DEFAULT FALSE
usage_count         INTEGER DEFAULT 0
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
created_by          UUID
-- UNIQUE(commodity_name, hsn_code)
```

---

## Core Components

### 1. Models (models.py)

All models use:
- **UUID primary keys** for distributed systems
- **Soft deletes** via `is_active` flag
- **Audit fields** (`created_at`, `updated_at`, `created_by`, `updated_by`)
- **SQLAlchemy relationships** with cascade deletes

```python
class Commodity(Base, EventMixin):
    """Core commodity entity"""
    __tablename__ = "commodities"
    
    # Relationships
    varieties = relationship("CommodityVariety", back_populates="commodity", cascade="all, delete-orphan")
    parameters = relationship("CommodityParameter", back_populates="commodity", cascade="all, delete-orphan")
    commissions = relationship("CommissionStructure", back_populates="commodity")
```

### 2. Schemas (schemas.py)

Pydantic schemas for validation:
- **Base schemas**: Common fields
- **Create schemas**: Required fields for creation
- **Update schemas**: All optional for partial updates
- **Response schemas**: `model_config = {"from_attributes": True}`

```python
class CommodityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    # ...

class CommodityCreate(CommodityBase):
    pass

class CommodityUpdate(BaseModel):
    # All fields optional
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    # ...

class CommodityResponse(CommodityBase):
    id: UUID
    created_by: Optional[UUID]
    # ...
    model_config = {"from_attributes": True}
```

### 3. Repositories (repositories.py)

Data access patterns for each model:
- `create(**kwargs)` → Creates entity
- `get_by_id(id)` → Returns Optional[Entity]
- `list_all(filters)` → Returns List[Entity]
- `update(id, **kwargs)` → Returns Optional[Entity]
- `delete(id)` → Soft delete, returns bool

```python
class CommodityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> Commodity:
        commodity = Commodity(**kwargs)
        self.db.add(commodity)
        await self.db.flush()
        return commodity
    
    async def get_by_id(self, commodity_id: UUID) -> Optional[Commodity]:
        result = await self.db.execute(
            select(Commodity).where(Commodity.id == commodity_id)
        )
        return result.scalar_one_or_none()
```

### 4. Services (services.py)

Business logic with event emission:

```python
class CommodityService:
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        ai_helper: CommodityAIHelper,
        current_user_id: UUID
    ):
        self.repository = CommodityRepository(session)
        self.event_emitter = event_emitter
        self.ai_helper = ai_helper
        self.current_user_id = current_user_id
    
    async def create_commodity(self, data: CommodityCreate) -> Commodity:
        # 1. AI Enrichment
        if not data.hsn_code or not data.gst_rate:
            enrichment = await self.ai_helper.enrich_commodity_data(...)
        
        # 2. Create in database
        commodity = await self.repository.create(**data.model_dump())
        
        # 3. AI Learning
        if self.ai_helper.hsn_learning and data.hsn_code:
            await self.ai_helper.hsn_learning.confirm_hsn_mapping(...)
        
        # 4. Emit Event
        await self.event_emitter.emit(CommodityCreated(...))
        
        return commodity
```

---

## End-to-End Business Flows

### Flow 1: Create New Commodity (with AI)

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   User/Admin     │───►│   REST API       │───►│   Service Layer  │
│   Frontend       │    │   /commodities   │    │   CommodityService│
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────┐
                        │                                │                        │
                        ▼                                ▼                        ▼
               ┌──────────────────┐           ┌──────────────────┐    ┌──────────────────┐
               │   AI Helper      │           │   Repository     │    │   Event Emitter  │
               │   - Detect HSN   │           │   - Create       │    │   - Emit Event   │
               │   - Suggest GST  │           │   - Flush        │    │   - Audit Trail  │
               └──────────────────┘           └──────────────────┘    └──────────────────┘
                        │                                │                        │
                        ▼                                │                        │
               ┌──────────────────┐                     │                        │
               │   HSN Learning   │◄────────────────────┘                        │
               │   - Save mapping │                                              │
               └──────────────────┘                                              │
                                                                                 ▼
                                                                      ┌──────────────────┐
                                                                      │   Event Store    │
                                                                      │   domain_events  │
                                                                      └──────────────────┘
```

**Step-by-step:**

1. **User Input**: Admin enters commodity name "Raw Cotton", category "Natural Fiber"
2. **API Receives**: POST `/api/v1/commodities` with payload
3. **AI Enrichment**: If HSN/GST not provided:
   - System queries HSN Knowledge Base
   - Falls back to dummy data/API
   - Suggests HSN "5201", GST 5%
4. **Database Create**: Repository creates record
5. **AI Learning**: If HSN confirmed, saves to knowledge base for future
6. **Event Emission**: `CommodityCreated` event stored for audit

```python
# API Call Example
POST /api/v1/commodities
{
    "name": "Raw Cotton",
    "category": "Natural Fiber",
    "description": "High quality cotton fiber",
    "uom": "Bales"
    // hsn_code and gst_rate will be AI-suggested
}

# Response with AI enrichment
{
    "id": "uuid",
    "name": "Raw Cotton",
    "category": "Natural Fiber",
    "hsn_code": "5201",           // AI suggested
    "gst_rate": "5.00",           // AI suggested
    "description": "High quality cotton fiber",
    "uom": "Bales",
    "is_active": true,
    "created_at": "2025-11-29T07:00:00Z"
}
```

### Flow 2: Add Quality Parameters (with Learning)

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   User adds      │───►│   POST /params   │───►│   ParameterService│
│   "Staple Length"│    │                  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │   Create in DB   │
                                               │   commodity_     │
                                               │   parameters     │
                                               └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │   AI Learning    │
                                               │   _learn_param   │
                                               │   _template()    │
                                               └──────────────────┘
                                                         │
                          ┌──────────────────────────────┴─────────────────────────┐
                          │                                                        │
                          ▼                                                        ▼
                 ┌──────────────────┐                                   ┌──────────────────┐
                 │  Template Exists?│                                   │  Create New      │
                 │  → Increment     │                                   │  Template        │
                 │  usage_count     │                                   │  (AI_LEARNED)    │
                 └──────────────────┘                                   └──────────────────┘
```

**Learning Logic:**

```python
async def _learn_parameter_template(self, parameter: CommodityParameter):
    """
    When user adds a custom parameter:
    1. Get commodity's category
    2. Check if template exists for this category+parameter
    3. If exists: increment usage_count (popularity)
    4. If not: create new template for future suggestions
    """
    commodity = await self.commodity_repository.get_by_id(parameter.commodity_id)
    
    # Check existing template
    existing_template = await session.execute(
        select(SystemCommodityParameter).where(
            category == commodity.category,
            parameter_name == parameter.parameter_name
        )
    )
    
    if existing_template:
        existing_template.usage_count += 1  # Track popularity
    else:
        # New parameter discovered - save for future suggestions
        new_template = SystemCommodityParameter(
            commodity_category=commodity.category,
            parameter_name=parameter.parameter_name,
            source="AI_LEARNED",
            usage_count=1
        )
```

### Flow 3: HSN Code Suggestion (Self-Learning)

```
┌──────────────────┐
│   User enters    │
│   "Kapas"        │
└──────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    HSN Learning Service                      │
│                                                              │
│   ┌──────────────┐   No    ┌──────────────┐   No    ┌─────┐ │
│   │ 1. Knowledge │────────►│ 2. HSN API   │────────►│3.Dum│ │
│   │    Base      │         │ (if enabled) │         │my DB│ │
│   └──────────────┘         └──────────────┘         └─────┘ │
│          │                        │                    │    │
│          │ Found                  │ Found              │    │
│          ▼                        ▼                    ▼    │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              Return HSN Suggestion                    │  │
│   │              - hsn_code: "5201"                       │  │
│   │              - gst_rate: 5.0                          │  │
│   │              - confidence: 0.85                       │  │
│   └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
         │
         │ On user confirmation
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Save to Knowledge Base                    │
│   - commodity_name: "Kapas"                                  │
│   - hsn_code: "5201"                                         │
│   - source: "MANUAL" (user confirmed)                        │
│   - is_verified: true                                        │
│   - confidence: 1.0                                          │
└──────────────────────────────────────────────────────────────┘
```

### Flow 4: Bulk Import from Excel

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Upload Excel   │───►│   POST /bulk/    │───►│   BulkOperation  │
│   .xlsx file     │    │   upload         │    │   Service        │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │   Parse Excel    │
                                               │   using openpyxl │
                                               └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │   For each row:  │
                                               │   - Validate     │
                                               │   - Create       │
                                               │   - Track errors │
                                               └──────────────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │   Return Result  │
                                               │   - success: 95  │
                                               │   - failed: 5    │
                                               │   - errors: [...]│
                                               └──────────────────┘
```

---

## AI/ML Features

### 1. Category Detection

```python
async def detect_commodity_category(name: str, description: str) -> CategorySuggestion:
    """
    Pattern matching to identify category.
    
    Input: "DCH-32 Cotton Bales"
    Output: {
        "category": "Natural Fiber",
        "confidence": 0.85,
        "subcategory": "Cotton"
    }
    """
    CATEGORY_PATTERNS = {
        "Natural Fiber": ["cotton", "jute", "silk", "wool"],
        "Synthetic Fiber": ["polyester", "nylon", "acrylic"],
        "Yarn": ["yarn", "thread", "spun"],
        "Fabric": ["fabric", "cloth", "textile"],
    }
```

### 2. HSN Code Suggestion (Self-Learning)

```python
# Knowledge Base Priority Order:
1. hsn_knowledge_base (learned from users) - Highest confidence
2. External HSN API (if configured)
3. DUMMY_HSN_DATA (hardcoded fallback)
4. Category-based generic fallback

# Dummy Data Examples:
"kapas": {"hsn": "5201", "desc": "Cotton, not carded", "gst": 5.0}
"chana": {"hsn": "0713", "desc": "Dried leguminous vegetables", "gst": 5.0}
"wheat": {"hsn": "1001", "desc": "Wheat and meslin", "gst": 5.0}
```

### 3. Quality Parameter Suggestion

```python
async def suggest_quality_parameters(commodity_id, category, name):
    """
    Suggests parameters based on:
    1. Database templates (ordered by usage_count DESC)
    2. Hardcoded standards (fallback)
    """
    
    # Database query with AI ranking:
    stmt = select(SystemCommodityParameter).where(
        category.ilike(f"%{category}%")
    ).order_by(
        usage_count.desc(),      # Most popular first
        is_mandatory.desc(),     # Then mandatory
        parameter_name
    ).limit(20)
    
    # Hardcoded Cotton parameters (fallback):
    STANDARD_PARAMETERS["Natural Fiber - Cotton"] = [
        {"name": "Staple Length", "type": "NUMERIC", "unit": "mm", "mandatory": True},
        {"name": "Micronaire", "type": "NUMERIC", "unit": "units", "mandatory": True},
        {"name": "Strength", "type": "NUMERIC", "unit": "g/tex", "mandatory": True},
        {"name": "Color Grade", "type": "TEXT", "mandatory": False},
        {"name": "Trash Content", "type": "NUMERIC", "unit": "%", "mandatory": False},
    ]
```

### 4. Data Validation (AI-Powered)

```python
async def validate_commodity_data(data: Dict) -> Dict[str, List[str]]:
    """
    Validates for anomalies:
    - HSN vs Category mismatch (Cotton should be 52xx)
    - Invalid GST rates (must be 0, 5, 12, 18, or 28%)
    - Parameter range errors (min >= max)
    """
    warnings = {}
    
    # HSN validation
    if "cotton" in category and not hsn.startswith("52"):
        warnings["hsn_code"].append("HSN unusual for cotton")
    
    # GST validation
    if gst_rate not in [0, 5, 12, 18, 28]:
        warnings["gst_rate"].append("GST rate unusual")
```

---

## Event System

### Event Types (10 Events)

| Event | Trigger | Data |
|-------|---------|------|
| `commodity.created` | New commodity | name, category, hsn_code |
| `commodity.updated` | Commodity modified | changes dict |
| `commodity.deleted` | Soft delete | name |
| `commodity.variety.added` | New variety | variety_id, name, code |
| `commodity.variety.updated` | Variety changed | variety_id, name |
| `commodity.parameter.added` | New parameter | parameter_id, name, type |
| `commodity.parameter.updated` | Parameter changed | parameter_id, name |
| `commodity.commission.set` | Commission configured | commission_id, name, rate |
| `trade_terms.created` | New term | term_type, name |
| `trade_terms.updated` | Term modified | term_type, name |

### Event Structure

```python
class CommodityCreated(BaseEvent):
    def __init__(self, aggregate_id, user_id, data, metadata=None):
        super().__init__(
            event_type="commodity.created",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )
```

### Event Emission Pattern

```python
# In service methods:
await self.event_emitter.emit(
    CommodityCreated(
        aggregate_id=commodity.id,
        user_id=self.current_user_id,
        data={
            "name": commodity.name,
            "category": commodity.category,
            "hsn_code": commodity.hsn_code,
            "ai_assisted": True
        }
    )
)
```

---

## API Endpoints

### Commodity Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/` | Create commodity |
| GET | `/api/v1/commodities/` | List with filters |
| GET | `/api/v1/commodities/{id}` | Get by ID |
| PUT | `/api/v1/commodities/{id}` | Update |
| DELETE | `/api/v1/commodities/{id}` | Soft delete |

### Variety Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/{id}/varieties` | Add variety |
| GET | `/api/v1/commodities/{id}/varieties` | List varieties |
| PUT | `/api/v1/commodities/varieties/{id}` | Update variety |

### Parameter Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/{id}/parameters` | Add parameter |
| GET | `/api/v1/commodities/{id}/parameters` | List parameters |
| PUT | `/api/v1/commodities/parameters/{id}` | Update parameter |

### AI Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/ai/detect-category` | AI category detection |
| POST | `/api/v1/commodities/ai/suggest-hsn` | AI HSN suggestion |
| POST | `/api/v1/commodities/{id}/ai/suggest-parameters` | AI parameter suggestions |

### Trading Terms Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/trade-types` | Create trade type |
| POST | `/api/v1/commodities/bargain-types` | Create bargain type |
| POST | `/api/v1/commodities/passing-terms` | Create passing term |
| POST | `/api/v1/commodities/weightment-terms` | Create weightment term |
| POST | `/api/v1/commodities/delivery-terms` | Create delivery term |
| POST | `/api/v1/commodities/payment-terms` | Create payment term |

### Bulk Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/bulk/upload` | Import from Excel |
| GET | `/api/v1/commodities/bulk/download` | Export/template |
| POST | `/api/v1/commodities/bulk/validate` | Validate file |

### Commission Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/commodities/{id}/commission` | Set commission |
| GET | `/api/v1/commodities/{id}/commission` | Get commission |
| PUT | `/api/v1/commodities/commission/{id}` | Update commission |

---

## Testing Strategy

### Unit Tests (test_ai_commodity_learning.py)
- HSN suggestion from dummy data
- Fallback behavior without database
- Backwards compatibility tests

### Integration Tests (test_commodity_module_integration.py)
- Full CRUD operations
- Cascade delete verification
- Event emission verification
- Multi-entity relationships

### Test Categories

```python
class TestCommodityCRUD:
    test_create_commodity()
    test_create_commodity_duplicate_name()
    test_get_commodity()
    test_get_commodity_not_found()
    test_list_commodities()
    test_update_commodity()
    test_delete_commodity()

class TestCommodityVariety:
    test_add_variety_to_commodity()
    test_list_varieties_for_commodity()
    test_update_variety()

class TestCommodityParameter:
    test_add_quality_parameter()
    test_list_parameters_for_commodity()
    test_update_parameter()

class TestTradeType:
    test_create_trade_type()
    test_list_trade_types()

class TestCommissionStructure:
    test_set_commission_for_commodity()
    test_list_commissions()
```

---

## Suggestions & Improvements

### 1. **Add Async Keyword to Router Endpoints** ⚠️
**Issue**: Router functions are missing `async` keyword.
```python
# Current (problematic):
@router.post("/")
def create_commodity(data: CommodityCreate, ...):
    commodity = service.create_commodity(data)  # Missing await!

# Should be:
@router.post("/")
async def create_commodity(data: CommodityCreate, ...):
    commodity = await service.create_commodity(data)
```

### 2. **Add Database Transactions** ⚠️
**Issue**: Services use `flush()` but don't manage commits properly.
```python
# Suggestion: Add transaction management
async with session.begin():
    commodity = await self.repository.create(**data.model_dump())
    await self.event_emitter.emit(CommodityCreated(...))
    # Auto-commit on success, rollback on error
```

### 3. **Implement External HSN API Integration** 📋
```python
# hsn_learning.py has placeholder:
async def _query_hsn_api(self, commodity_name, category):
    """TODO: Implement actual API integration"""
    # Options:
    # - GST.gov.in API (official)
    # - Masters India API (commercial)
    # - ClearTax API (commercial)
    return None
```

### 4. **Add Pagination to List Endpoints** 📋
```python
# Current:
async def list_all(self, skip=0, limit=100) -> List[Commodity]

# Suggestion: Return total count for pagination
async def list_all(self, skip=0, limit=100) -> Tuple[List[Commodity], int]:
    return commodities, total_count
```

### 5. **Add Full-Text Search** 📋
```python
# Current CommodityFilter uses ILIKE which is slow
# Suggestion: Add PostgreSQL full-text search
from sqlalchemy import func
query = query.where(
    func.to_tsvector('english', Commodity.name).match(search_text)
)
```

### 6. **Add Rate Limiting** 🔒
```python
# AI endpoints could be rate-limited:
from fastapi import BackgroundTasks
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/ai/suggest-hsn")
@limiter.limit("10/minute")
async def suggest_hsn(...):
```

### 7. **Add Caching Layer** ⚡
```python
# filters.py has SimpleCache but not integrated
# Suggestion: Redis caching for frequently accessed data

import redis.asyncio as redis

async def get_commodity_cached(id: UUID):
    cached = await redis.get(f"commodity:{id}")
    if cached:
        return CommodityResponse.parse_raw(cached)
    
    commodity = await repository.get_by_id(id)
    await redis.setex(f"commodity:{id}", 300, commodity.json())
    return commodity
```

### 8. **Add Export/Import for All Terms** 📋
Current bulk operations only support commodities. Extend to:
- Trade types
- Payment terms
- All other terms

### 9. **Add Webhook Notifications** 📋
```python
# On commodity changes, notify external systems
async def notify_webhooks(event: BaseEvent):
    webhooks = await get_registered_webhooks("commodity.*")
    for webhook in webhooks:
        await http_client.post(webhook.url, json=event.data)
```

### 10. **Add Parameter Templates UI** 📋
Allow admins to manage `system_commodity_parameters` directly:
- View all templates
- Edit ranges
- Add new templates
- View usage statistics

---

## Security Considerations

1. **Authentication**: Currently uses mock user ID. Integrate with auth module.
2. **Authorization**: Add role-based access (Admin, Viewer, Editor)
3. **Input Validation**: Pydantic handles basic validation. Add business rules.
4. **SQL Injection**: Using SQLAlchemy ORM - safe by default.
5. **Rate Limiting**: Add for AI endpoints to prevent abuse.

---

## Performance Considerations

1. **Database Indexing**: Already indexed on `name`, `category`, `hsn_code`
2. **Lazy Loading**: Relationships use lazy loading by default
3. **Pagination**: Implemented but not returning total count
4. **Caching**: Simple in-memory cache exists, consider Redis
5. **Async Operations**: All operations are async-ready

---

## Conclusion

The Commodity Master Module is a well-structured, feature-rich module with:
- ✅ Clean layered architecture
- ✅ Event sourcing for audit trails
- ✅ Self-learning AI for HSN codes
- ✅ Comprehensive test coverage
- ✅ Bulk import/export capabilities

Main areas for improvement:
- ⚠️ Fix async/await in router
- ⚠️ Add proper transaction management
- 📋 Integrate external HSN API
- 📋 Add Redis caching
- 📋 Implement full-text search
