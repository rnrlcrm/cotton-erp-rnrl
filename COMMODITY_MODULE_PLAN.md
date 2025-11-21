# Commodity Master Module - Implementation Plan

## Overview

Build the **Commodity Master Module** as the foundation for all trading operations. This module will manage commodities, their varieties, quality parameters, and trading terms with full event sourcing and AI intelligence.

## Database Schema (11 Tables)

### 1. `commodities` (Core Entity)
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(200) NOT NULL
category                    VARCHAR(100) NOT NULL  -- Natural Fiber, Synthetic, Blended
hsn_code                    VARCHAR(20)
gst_rate                    DECIMAL(5,2)
description                 TEXT
uom                         VARCHAR(50)  -- Unit: MT, Quintals, Bales
is_active                   BOOLEAN DEFAULT TRUE
created_by                  UUID
updated_by                  UUID
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 2. `commodity_varieties`
```sql
id                          UUID PRIMARY KEY
commodity_id                UUID NOT NULL FOREIGN KEY
name                        VARCHAR(200) NOT NULL  -- DCH-32, Shankar-6
code                        VARCHAR(50)
description                 TEXT
is_standard                 BOOLEAN DEFAULT FALSE
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 3. `commodity_parameters`
```sql
id                          UUID PRIMARY KEY
commodity_id                UUID NOT NULL FOREIGN KEY
parameter_name              VARCHAR(100) NOT NULL  -- Staple Length, Micronaire
parameter_type              VARCHAR(50)  -- NUMERIC, TEXT, RANGE
unit                        VARCHAR(50)  -- mm, g/tex, %
min_value                   DECIMAL(10,2)
max_value                   DECIMAL(10,2)
default_value               VARCHAR(100)
is_mandatory                BOOLEAN DEFAULT FALSE
display_order               INTEGER
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 4. `system_commodity_parameters` (AI-Suggested Defaults)
```sql
id                          UUID PRIMARY KEY
commodity_category          VARCHAR(100)  -- For AI suggestions
parameter_name              VARCHAR(100)
parameter_type              VARCHAR(50)
unit                        VARCHAR(50)
typical_range_min           DECIMAL(10,2)
typical_range_max           DECIMAL(10,2)
description                 TEXT
source                      VARCHAR(100)  -- Industry Standard, CCI, Custom
created_at                  TIMESTAMPTZ
```

### 5. `trade_types`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- Purchase, Sale, Transfer
code                        VARCHAR(20) UNIQUE
description                 TEXT
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 6. `bargain_types`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- Open, Closed, Firm Offer
code                        VARCHAR(20) UNIQUE
description                 TEXT
requires_approval           BOOLEAN DEFAULT FALSE
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 7. `passing_terms`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- As Per Sample, As Per Standard
code                        VARCHAR(20) UNIQUE
description                 TEXT
requires_quality_test       BOOLEAN DEFAULT FALSE
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 8. `weightment_terms`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- Ex-Gin, Delivered, Ex-Warehouse
code                        VARCHAR(20) UNIQUE
description                 TEXT
weight_deduction_percent    DECIMAL(5,2)  -- Tare, moisture deduction
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 9. `delivery_terms`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- FOB, CIF, Ex-Works
code                        VARCHAR(20) UNIQUE
description                 TEXT
includes_freight            BOOLEAN DEFAULT FALSE
includes_insurance          BOOLEAN DEFAULT FALSE
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 10. `payment_terms`
```sql
id                          UUID PRIMARY KEY
name                        VARCHAR(100) NOT NULL  -- Advance, Against Delivery, Credit
code                        VARCHAR(20) UNIQUE
days                        INTEGER  -- Credit period
payment_percentage          DECIMAL(5,2)  -- % upfront
description                 TEXT
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

### 11. `commission_structures`
```sql
id                          UUID PRIMARY KEY
commodity_id                UUID FOREIGN KEY (nullable)  -- Can be generic
trade_type_id               UUID FOREIGN KEY (nullable)
name                        VARCHAR(100) NOT NULL
commission_type             VARCHAR(50)  -- PERCENTAGE, FIXED, TIERED
rate                        DECIMAL(5,2)  -- % or fixed amount
min_amount                  DECIMAL(15,2)
max_amount                  DECIMAL(15,2)
applies_to                  VARCHAR(50)  -- BUYER, SELLER, BOTH
description                 TEXT
is_active                   BOOLEAN DEFAULT TRUE
created_at                  TIMESTAMPTZ
updated_at                  TIMESTAMPTZ
```

## Event Types (10 Events)

1. `commodity.created` - New commodity added
2. `commodity.updated` - Commodity details changed
3. `commodity.deleted` - Commodity soft-deleted
4. `commodity.variety.added` - New variety added
5. `commodity.variety.updated` - Variety changed
6. `commodity.parameter.added` - Quality parameter added
7. `commodity.parameter.updated` - Parameter changed
8. `commodity.commission.set` - Commission structure set
9. `trade_terms.created` - Trade/bargain/payment term added
10. `trade_terms.updated` - Terms modified

## API Endpoints (REST)

### Commodities
- `POST   /api/v1/commodities` - Create commodity
- `GET    /api/v1/commodities` - List with filters
- `GET    /api/v1/commodities/{id}` - Get details
- `PATCH  /api/v1/commodities/{id}` - Update
- `DELETE /api/v1/commodities/{id}` - Soft delete

### Varieties
- `POST   /api/v1/commodities/{id}/varieties` - Add variety
- `GET    /api/v1/commodities/{id}/varieties` - List varieties
- `PATCH  /api/v1/varieties/{id}` - Update variety
- `DELETE /api/v1/varieties/{id}` - Delete variety

### Parameters
- `POST   /api/v1/commodities/{id}/parameters` - Add parameter
- `GET    /api/v1/commodities/{id}/parameters` - List parameters
- `PATCH  /api/v1/parameters/{id}` - Update parameter
- `DELETE /api/v1/parameters/{id}` - Delete parameter

### Trade Terms (Similar CRUD for each)
- Trade Types: `/api/v1/trade-terms/types`
- Bargain Types: `/api/v1/trade-terms/bargains`
- Passing Terms: `/api/v1/trade-terms/passing`
- Weightment Terms: `/api/v1/trade-terms/weightment`
- Delivery Terms: `/api/v1/trade-terms/delivery`
- Payment Terms: `/api/v1/trade-terms/payment`

### Commissions
- `POST   /api/v1/commissions` - Set commission
- `GET    /api/v1/commissions` - List commissions
- `PATCH  /api/v1/commissions/{id}` - Update
- `DELETE /api/v1/commissions/{id}` - Delete

### AI Endpoints
- `POST   /api/v1/commodities/ai/suggest-category` - AI category detection
- `POST   /api/v1/commodities/ai/suggest-hsn` - HSN code suggestion
- `POST   /api/v1/commodities/ai/suggest-parameters` - Quality parameters suggestion
- `GET    /api/v1/commodities/ai/system-parameters` - Get standard parameters

## AI Features (Medium Complexity)

### 1. Category Detection (`ai_helpers.py`)
```python
async def detect_commodity_category(name: str, description: str) -> dict:
    """
    Use AI to detect commodity category from name/description.
    
    Input: "Raw Cotton" or "Cotton Lint"
    Output: {
        "category": "Natural Fiber",
        "confidence": 0.95,
        "subcategory": "Cotton"
    }
    """
```

### 2. HSN Code Lookup
```python
async def suggest_hsn_code(name: str, category: str) -> dict:
    """
    Suggest HSN/GST code based on commodity.
    
    Input: name="Raw Cotton", category="Natural Fiber"
    Output: {
        "hsn_code": "5201",
        "description": "Cotton, not carded or combed",
        "gst_rate": 5.0
    }
    """
```

### 3. Quality Parameter Suggestion
```python
async def suggest_quality_parameters(commodity_id: UUID, category: str) -> list:
    """
    AI suggests standard quality parameters.
    
    Input: category="Natural Fiber - Cotton"
    Output: [
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
            "typical_range": [3.5, 4.9]
        }
    ]
    """
```

### 4. Data Validation
```python
async def validate_commodity_data(data: dict) -> dict:
    """
    AI-powered validation for anomalies.
    
    - Unusual HSN for category
    - GST rate mismatch
    - Parameter ranges outside norms
    """
```

## File Structure

```
backend/modules/commodities/
├── __init__.py
├── models.py                 # 11 SQLAlchemy models
├── schemas.py                # Pydantic validation schemas
├── repositories.py           # Data access layer (11 repos)
├── services.py               # Business logic + events
├── router.py                 # FastAPI endpoints
├── events.py                 # 10 event definitions
└── ai_helpers.py             # AI integration (~200 LOC)
```

## Implementation Steps

### Phase 1: Core Models (Day 1)
1. ✅ Create feature branch `feat/commodity-master`
2. ✅ Create `models.py` with 11 SQLAlchemy models
3. ✅ Create `schemas.py` with Pydantic schemas (Create/Update/Response)
4. ✅ Create migration for 11 tables
5. ✅ Test models and schemas

### Phase 2: Events & Repositories (Day 1-2)
6. ✅ Create `events.py` with 10 event types
7. ✅ Create `repositories.py` with CRUD for all 11 models
8. ✅ Create `services.py` with EventEmitter integration
9. ✅ Test event emission

### Phase 3: API & AI (Day 2-3)
10. ✅ Create `router.py` with all REST endpoints
11. ✅ Create `ai_helpers.py` with 4 AI functions
12. ✅ Integrate AI suggestions into API
13. ✅ Test all endpoints

### Phase 4: Testing & Documentation (Day 3)
14. ✅ Write tests for critical paths
15. ✅ Test event audit trail
16. ✅ Update API documentation
17. ✅ Merge to main

## Code Quality Standards

- ✅ All methods async (AsyncSession)
- ✅ Event emission on all state changes
- ✅ Proper error handling (NotFoundException, ValidationException)
- ✅ Type hints everywhere
- ✅ Docstrings for all public methods
- ✅ Input validation with Pydantic
- ✅ Transaction management (commit/rollback)

## Example: Commodity Service Pattern

```python
class CommodityService:
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
        self.repo = CommodityRepository(db)
        self.events = EventEmitter(db)
        self.ai = AIHelper()
    
    async def create_commodity(self, data: CommodityCreate) -> CommodityResponse:
        # AI: Suggest category if not provided
        if not data.category:
            suggestion = await self.ai.detect_commodity_category(
                data.name, data.description
            )
            data.category = suggestion["category"]
        
        # AI: Suggest HSN code
        if not data.hsn_code:
            hsn = await self.ai.suggest_hsn_code(data.name, data.category)
            data.hsn_code = hsn["hsn_code"]
            data.gst_rate = hsn["gst_rate"]
        
        # Create commodity
        commodity = await self.repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
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
        
        # Commit
        await self.db.commit()
        return CommodityResponse.model_validate(commodity)
```

## Success Criteria

✅ All 11 tables created with proper relationships
✅ Complete CRUD operations for all entities
✅ Event sourcing working (10 event types)
✅ AI helpers functional (4 AI features)
✅ REST API complete (35+ endpoints)
✅ Audit trail captures all changes
✅ Input validation working
✅ Error handling robust
✅ Documentation complete
✅ Tests passing

## Estimated Effort

- **Models + Migration**: 2-3 hours
- **Events + Repositories**: 3-4 hours
- **Services + Business Logic**: 4-5 hours
- **API Endpoints**: 3-4 hours
- **AI Integration**: 2-3 hours
- **Testing + Documentation**: 2-3 hours

**Total**: 16-22 hours (~2-3 days)

## Dependencies

✅ Event system (already built)
✅ PostgreSQL database (running)
✅ Organization module pattern (reference)
✅ AsyncIO support (ready)

## Ready to Build?

Once approved, I'll:
1. Create feature branch
2. Build all 11 models
3. Create migration
4. Implement events
5. Build repositories & services
6. Create REST API
7. Add AI helpers
8. Test everything
9. Merge to main

**Approve to proceed? 🚀**
