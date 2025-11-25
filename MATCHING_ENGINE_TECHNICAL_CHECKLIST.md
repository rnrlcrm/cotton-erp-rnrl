# MATCHING ENGINE - TECHNICAL CHECKLIST & CODE VALIDATION

**Purpose:** Complete validation of all existing modules before implementing Matching Engine  
**Date:** November 25, 2025  
**Status:** 🔍 PRE-IMPLEMENTATION AUDIT

---

## 📋 TABLE SCHEMA VALIDATION

### ✅ Required Tables (Must Exist)

| Table Name | Status | Fields to Validate | Purpose |
|------------|--------|-------------------|---------|
| `requirements` | 🟡 CHECK | buyer_partner_id, commodity_id, quality_requirements, min_quantity, max_quantity, max_budget_per_unit, status | Buyer requirements |
| `availabilities` | 🟡 CHECK | seller_id, commodity_id, quality_params, total_quantity, available_quantity, base_price, status | Seller inventory |
| `business_partners` | 🟡 CHECK | id, partner_type, pan_number, tax_id_number, primary_contact_phone | Partner master |
| `commodities` | 🟡 CHECK | id, name, category, uom | Commodity master |
| `settings_locations` | 🟡 CHECK | id, name, latitude, longitude, region | Location master |

### 🔍 Field-Level Validation

#### Requirements Table
```sql
-- Check if these fields exist and have correct types
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'requirements'
AND column_name IN (
    'buyer_partner_id',
    'commodity_id',
    'variety_id',
    'min_quantity',
    'max_quantity',
    'preferred_quantity',
    'quality_requirements',
    'max_budget_per_unit',
    'preferred_price_per_unit',
    'status',
    'created_at'
);
```

**Expected:**
- `buyer_partner_id` → UUID NOT NULL
- `commodity_id` → UUID NOT NULL
- `quality_requirements` → JSONB NOT NULL
- `min_quantity` → NUMERIC(15,3) NOT NULL
- `max_quantity` → NUMERIC(15,3) NOT NULL
- `max_budget_per_unit` → NUMERIC(18,2)
- `status` → VARCHAR (DRAFT/ACTIVE/...)

#### Availabilities Table
```sql
-- Check if these fields exist and have correct types
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'availabilities'
AND column_name IN (
    'seller_id',
    'commodity_id',
    'variety_id',
    'total_quantity',
    'available_quantity',
    'quality_params',
    'base_price',
    'status',
    'created_at'
);
```

**Expected:**
- `seller_id` → UUID NOT NULL
- `commodity_id` → UUID NOT NULL
- `quality_params` → JSONB
- `total_quantity` → NUMERIC(15,3) NOT NULL
- `available_quantity` → NUMERIC(15,3) NOT NULL
- `base_price` → NUMERIC(15,2)
- `status` → VARCHAR (DRAFT/AVAILABLE/...)

---

## 🔗 RELATIONSHIP VALIDATION

### Foreign Key Constraints

```sql
-- Check all foreign keys exist
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('requirements', 'availabilities');
```

**Expected Relationships:**

Requirements:
- `buyer_partner_id` → `business_partners(id)`
- `commodity_id` → `commodities(id)`
- `variety_id` → `commodity_varieties(id)` (nullable)
- `created_by_user_id` → `users(id)`

Availabilities:
- `seller_id` → `business_partners(id)`
- `commodity_id` → `commodities(id)`
- `variety_id` → `commodity_varieties(id)` (nullable)
- `location_id` → `settings_locations(id)`

---

## 📦 MODEL VALIDATION

### Requirements Model (`backend/modules/trade_desk/models/requirement.py`)

**Check these properties exist:**
- [ ] `buyer_partner_id` property
- [ ] `commodity_id` property
- [ ] `quality_requirements` property (JSONB)
- [ ] `min_quantity` property
- [ ] `max_quantity` property
- [ ] `preferred_quantity` property
- [ ] `max_budget_per_unit` property
- [ ] `preferred_price_per_unit` property
- [ ] `status` property
- [ ] `calculate_estimated_trade_value()` method
- [ ] Relationships: `buyer`, `commodity`, `variety`

**Check these methods exist:**
```python
# Expected methods for matching
def calculate_estimated_trade_value(self) -> Decimal:
    """Calculate estimated value for risk assessment"""
    
def is_compatible_with(self, availability: Availability) -> bool:
    """Quick compatibility check"""
    
def get_quality_tolerance(self) -> Dict[str, float]:
    """Get tolerance ranges for quality matching"""
```

### Availabilities Model (`backend/modules/trade_desk/models/availability.py`)

**Check these properties exist:**
- [ ] `seller_id` property
- [ ] `commodity_id` property
- [ ] `quality_params` property (JSONB)
- [ ] `total_quantity` property
- [ ] `available_quantity` property
- [ ] `base_price` property
- [ ] `status` property
- [ ] `calculate_estimated_trade_value()` method
- [ ] Relationships: `seller`, `commodity`, `variety`, `location`

**Check these methods exist:**
```python
# Expected methods for matching
def calculate_estimated_trade_value(self) -> Decimal:
    """Calculate estimated value for risk assessment"""
    
def is_compatible_with(self, requirement: Requirement) -> bool:
    """Quick compatibility check"""
    
def has_sufficient_quantity(self, required_quantity: Decimal) -> bool:
    """Check if enough quantity available"""
```

---

## 🔌 REPOSITORY VALIDATION

### RequirementRepository (`backend/modules/trade_desk/repositories/requirement_repository.py`)

**Check these methods exist:**
- [ ] `create(requirement_data: Dict) -> Requirement`
- [ ] `get_by_id(id: UUID) -> Requirement`
- [ ] `get_active_requirements() -> List[Requirement]`
- [ ] `get_by_commodity(commodity_id: UUID) -> List[Requirement]`
- [ ] `update(id: UUID, data: Dict) -> Requirement`

**Methods needed for Matching (may not exist yet):**
```python
# These will be added during matching engine implementation
async def search_compatible_availabilities(
    self,
    requirement_id: UUID,
    filters: Optional[Dict] = None
) -> List[Availability]:
    """Search for compatible availabilities"""
    
async def get_active_by_commodity(
    self,
    commodity_id: UUID
) -> List[Requirement]:
    """Get all active requirements for a commodity"""
```

### AvailabilityRepository (`backend/modules/trade_desk/repositories/availability_repository.py`)

**Check these methods exist:**
- [ ] `create(availability_data: Dict) -> Availability`
- [ ] `get_by_id(id: UUID) -> Availability`
- [ ] `get_active_availabilities() -> List[Availability]`
- [ ] `get_by_commodity(commodity_id: UUID) -> List[Availability]`
- [ ] `smart_search()` - AI-powered search method
- [ ] `update(id: UUID, data: Dict) -> Availability`

**Methods needed for Matching (may not exist yet):**
```python
# These will be added during matching engine implementation
async def search_compatible_requirements(
    self,
    availability_id: UUID,
    filters: Optional[Dict] = None
) -> List[Requirement]:
    """Search for compatible requirements"""
    
async def get_active_by_commodity(
    self,
    commodity_id: UUID
) -> List[Availability]:
    """Get all active availabilities for a commodity"""
```

---

## ⚙️ SERVICE VALIDATION

### RequirementService (`backend/modules/trade_desk/services/requirement_service.py`)

**Check these methods exist:**
- [ ] `create(requirement_data: Dict, user: User) -> Requirement`
- [ ] `get_by_id(id: UUID) -> Requirement`
- [ ] `update(id: UUID, data: Dict, user: User) -> Requirement`
- [ ] `publish(id: UUID, user: User) -> Requirement` (change status to ACTIVE)
- [ ] `cancel(id: UUID, user: User) -> Requirement`

**Integration point for Matching:**
```python
# Add this to create() method after requirement is saved
async def create(self, requirement_data: Dict, user: User) -> Requirement:
    # ... existing creation logic ...
    
    # NEW: Auto-match after creation
    if requirement.status == RequirementStatus.ACTIVE:
        from backend.modules.trade_desk.services.matching_service import MatchingService
        matching_service = MatchingService(self.db, ...)
        await matching_service.auto_match_on_new_post(
            entity_type="requirement",
            entity_id=requirement.id
        )
    
    return requirement
```

### AvailabilityService (`backend/modules/trade_desk/services/availability_service.py`)

**Check these methods exist:**
- [ ] `create(availability_data: Dict, user: User) -> Availability`
- [ ] `get_by_id(id: UUID) -> Availability`
- [ ] `update(id: UUID, data: Dict, user: User) -> Availability`
- [ ] `publish(id: UUID, user: User) -> Availability` (change status to AVAILABLE)
- [ ] `cancel(id: UUID, user: User) -> Availability`

**Integration point for Matching:**
```python
# Add this to create() method after availability is saved
async def create(self, availability_data: Dict, user: User) -> Availability:
    # ... existing creation logic ...
    
    # NEW: Auto-match after creation
    if availability.status == AvailabilityStatus.AVAILABLE:
        from backend.modules.trade_desk.services.matching_service import MatchingService
        matching_service = MatchingService(self.db, ...)
        await matching_service.auto_match_on_new_post(
            entity_type="availability",
            entity_id=availability.id
        )
    
    return availability
```

---

## 🛡️ RISK ENGINE VALIDATION

### RiskEngine (`backend/modules/risk/risk_engine.py`)

**Check these methods exist and are working:**

- [x] `check_party_links(buyer_partner_id: UUID, seller_partner_id: UUID)` ✅
  - Returns: `{"linked": bool, "severity": "BLOCK/WARN/PASS", "violations": []}`
  - Checks: PAN, Tax ID, mobile, email

- [x] `check_circular_trading(partner_id: UUID, commodity_id: UUID, transaction_type: str, trade_date: date)` ✅
  - Returns: `{"blocked": bool, "reason": str, "violation_type": str}`
  - Prevents: Same-day buy/sell reversals

- [x] `validate_partner_role(partner_id: UUID, transaction_type: str)` ✅
  - Returns: `{"allowed": bool, "reason": str, "partner_type": str}`
  - Validates: BUYER can only buy, SELLER only sell, TRADER both

- [x] `assess_trade_risk(requirement, availability, trade_quantity, trade_price, buyer_data, seller_data, user_id)` ✅
  - Returns: Complete risk assessment with PASS/WARN/FAIL status
  - Includes: All above checks + credit limits + internal trade blocking

**Integration Validation:**
```python
# Test that Risk Engine is accessible from matching context
from backend.modules.risk.risk_engine import RiskEngine

async def test_risk_integration():
    risk_engine = RiskEngine(db_session)
    
    # Test party links
    result = await risk_engine.check_party_links(
        buyer_partner_id=buyer_id,
        seller_partner_id=seller_id
    )
    assert "severity" in result
    
    # Test circular trading
    result = await risk_engine.check_circular_trading(
        partner_id=trader_id,
        commodity_id=commodity_id,
        transaction_type="BUY",
        trade_date=datetime.now().date()
    )
    assert "blocked" in result
    
    # Test role validation
    result = await risk_engine.validate_partner_role(
        partner_id=buyer_id,
        transaction_type="BUY"
    )
    assert "allowed" in result
```

---

## 🌐 API ROUTE VALIDATION

### Existing Routes to Integrate With

**Requirements Router** (`backend/modules/trade_desk/routes/requirement_router.py`)

Check these endpoints exist:
- [ ] `POST /api/v1/trade-desk/requirements` - Create requirement
- [ ] `GET /api/v1/trade-desk/requirements/{id}` - Get requirement
- [ ] `PUT /api/v1/trade-desk/requirements/{id}` - Update requirement
- [ ] `GET /api/v1/trade-desk/requirements` - List requirements

**Will add:**
- `POST /api/v1/trade-desk/requirements/{id}/find-matches` - Find compatible availabilities

**Availabilities Router** (`backend/modules/trade_desk/routes/availability_router.py`)

Check these endpoints exist:
- [ ] `POST /api/v1/trade-desk/availabilities` - Create availability
- [ ] `GET /api/v1/trade-desk/availabilities/{id}` - Get availability
- [ ] `PUT /api/v1/trade-desk/availabilities/{id}` - Update availability
- [ ] `GET /api/v1/trade-desk/availabilities` - List availabilities

**Will add:**
- `POST /api/v1/trade-desk/availabilities/{id}/find-matches` - Find compatible requirements

---

## 📊 DATA VALIDATION

### Sample Data Requirements

For testing matching engine, we need:

**1. Sample Commodities**
```sql
-- Check if cotton commodity exists
SELECT id, name, category, uom FROM commodities WHERE category = 'Cotton';

-- Check if gold commodity exists  
SELECT id, name, category, uom FROM commodities WHERE category = 'Gold';
```

**2. Sample Business Partners**
```sql
-- Check if we have buyers
SELECT id, name, partner_type FROM business_partners WHERE partner_type = 'BUYER';

-- Check if we have sellers
SELECT id, name, partner_type FROM business_partners WHERE partner_type = 'SELLER';

-- Check if we have traders
SELECT id, name, partner_type FROM business_partners WHERE partner_type = 'TRADER';
```

**3. Sample Locations**
```sql
-- Check if we have locations with coordinates
SELECT id, name, latitude, longitude, region 
FROM settings_locations 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
```

**4. Sample Requirements**
```sql
-- Check if we have active requirements
SELECT id, commodity_id, status, quality_requirements, min_quantity, max_budget_per_unit
FROM requirements
WHERE status = 'ACTIVE'
LIMIT 5;
```

**5. Sample Availabilities**
```sql
-- Check if we have active availabilities
SELECT id, commodity_id, status, quality_params, available_quantity, base_price
FROM availabilities
WHERE status IN ('AVAILABLE', 'PARTIALLY_SOLD')
LIMIT 5;
```

---

## 🔧 UTILITY FUNCTIONS VALIDATION

### Geographic Distance Calculation

**Check if Haversine formula exists:**

```python
# Expected in: backend/core/utils/geo.py or similar

from math import radians, cos, sin, asin, sqrt

def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate distance between two points on Earth using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Earth radius in km
    r = 6371
    
    return c * r
```

**If doesn't exist:** Will create during implementation

---

## 📝 ENUM VALIDATION

### Check Enums Exist

**File:** `backend/modules/trade_desk/enums.py`

```python
# Check these enums exist:

class RequirementStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class AvailabilityStatus(str, Enum):
    DRAFT = "DRAFT"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    PARTIALLY_SOLD = "PARTIALLY_SOLD"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class MarketVisibility(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    RESTRICTED = "RESTRICTED"
    INTERNAL = "INTERNAL"
```

---

## 🧪 PRE-IMPLEMENTATION TESTS

### Test 1: Can we query requirements and availabilities together?

```python
async def test_basic_join():
    """Test if we can join requirements with availabilities"""
    from sqlalchemy import select
    from backend.modules.trade_desk.models import Requirement, Availability
    
    query = select(Requirement, Availability).where(
        Requirement.commodity_id == Availability.commodity_id,
        Requirement.status == "ACTIVE",
        Availability.status == "AVAILABLE"
    )
    
    result = await db.execute(query)
    pairs = result.all()
    
    assert len(pairs) >= 0  # Should not error
```

### Test 2: Can we access quality parameters?

```python
async def test_quality_params_access():
    """Test if quality parameters are properly stored as JSONB"""
    requirement = await requirement_repo.get_by_id(sample_req_id)
    
    assert isinstance(requirement.quality_requirements, dict)
    assert "staple_length" in requirement.quality_requirements  # or appropriate param
    
    availability = await availability_repo.get_by_id(sample_avail_id)
    
    assert isinstance(availability.quality_params, dict)
    assert "staple_length" in availability.quality_params
```

### Test 3: Can we call Risk Engine?

```python
async def test_risk_engine_callable():
    """Test if Risk Engine is accessible"""
    from backend.modules.risk.risk_engine import RiskEngine
    
    risk_engine = RiskEngine(db)
    
    # Test party links
    result = await risk_engine.check_party_links(
        buyer_partner_id=sample_buyer_id,
        seller_partner_id=sample_seller_id
    )
    
    assert "severity" in result
    assert result["severity"] in ["PASS", "WARN", "BLOCK"]
```

---

## ✅ PRE-IMPLEMENTATION CHECKLIST

**Before starting Matching Engine implementation, verify:**

### Database Level
- [ ] `requirements` table exists with all required fields
- [ ] `availabilities` table exists with all required fields
- [ ] All foreign key relationships working
- [ ] JSONB fields properly indexed
- [ ] Sample data exists for testing

### Model Level
- [ ] Requirement model loads successfully
- [ ] Availability model loads successfully
- [ ] All relationships working (buyer, seller, commodity, location)
- [ ] JSONB fields accessible as dicts

### Repository Level
- [ ] RequirementRepository basic CRUD working
- [ ] AvailabilityRepository basic CRUD working
- [ ] Can query by commodity_id
- [ ] Can query by status

### Service Level
- [ ] RequirementService can create requirements
- [ ] AvailabilityService can create availabilities
- [ ] Status transitions working (DRAFT → ACTIVE)

### Risk Engine Level
- [ ] Risk Engine accessible from trade_desk module
- [ ] `check_party_links()` working
- [ ] `check_circular_trading()` working
- [ ] `validate_partner_role()` working
- [ ] `assess_trade_risk()` working

### API Level
- [ ] Requirement endpoints accessible
- [ ] Availability endpoints accessible
- [ ] Authentication working
- [ ] RBAC permissions working

### Data Level
- [ ] Sample commodities exist
- [ ] Sample business partners exist (buyers, sellers)
- [ ] Sample locations exist with coordinates
- [ ] Sample requirements exist (at least 5)
- [ ] Sample availabilities exist (at least 5)

---

## 🚨 BLOCKERS TO RESOLVE

**If any of these are missing, they must be resolved BEFORE starting Matching Engine:**

### Critical Blockers (Must Fix)
- [ ] No requirements or availabilities in database → Need seed data
- [ ] Quality parameters not properly stored as JSONB → Migration needed
- [ ] Risk Engine not accessible → Import path issue
- [ ] Foreign key constraints broken → Database integrity issue

### Important (Should Fix)
- [ ] Geographic distance utility missing → Will create during implementation
- [ ] No locations with coordinates → Need to add lat/lng to seed data
- [ ] Status enums not matching database values → Need alignment

### Nice to Have (Can Work Around)
- [ ] Limited test data → Can generate during testing
- [ ] Performance issues → Can optimize later
- [ ] Missing documentation → Will add during implementation

---

## 📞 VALIDATION COMMANDS

### Run Full Validation

```bash
# Check database schema
cd /workspaces/cotton-erp-rnrl
psql $DATABASE_URL -c "\d requirements"
psql $DATABASE_URL -c "\d availabilities"

# Check Python imports
python -c "from backend.modules.trade_desk.models import Requirement, Availability; print('✓ Models OK')"
python -c "from backend.modules.risk.risk_engine import RiskEngine; print('✓ Risk Engine OK')"

# Run existing tests
pytest backend/tests/trade_desk/ -v
pytest backend/tests/risk/ -v

# Check sample data
psql $DATABASE_URL -c "SELECT COUNT(*) FROM requirements WHERE status = 'ACTIVE';"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM availabilities WHERE status = 'AVAILABLE';"
```

---

**END OF TECHNICAL CHECKLIST**

*This document should be reviewed and all items checked before starting Matching Engine implementation.*
