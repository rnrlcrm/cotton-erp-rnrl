# TRADE DESK INTERNATIONAL SUPPORT - GAP ANALYSIS

**Date:** December 3, 2025  
**Branch:** feat/international-trade-desk-review  
**Status:** 🔴 CRITICAL GAPS FOUND

---

## EXECUTIVE SUMMARY

**PROBLEM:** Commodity Master has full international support (25 fields), but Trade Desk (Availability, Requirement, Matching Engine) is **INDIA-ONLY** design.

### Key Findings:

| Module | International Support | Status |
|--------|----------------------|--------|
| **Commodity Master** | ✅ Full (25 international fields) | COMPLETE |
| **Risk Engine** | ✅ International compliance checks | COMPLETE |
| **Availability Model** | ❌ No international fields | **MISSING** |
| **Requirement Model** | ⚠️ Partial (`currency_code` only) | **INCOMPLETE** |
| **Matching Engine** | ❌ India-only logic | **MISSING** |

---

## 1. COMMODITY MASTER (Reference - Already Complete)

### International Fields Available:
```sql
-- Currency & Pricing (3 fields)
default_currency              VARCHAR(3)      -- USD, EUR, GBP
supported_currencies          TEXT[]          -- Multi-currency support
international_pricing_unit    VARCHAR(50)     -- CENTS_PER_POUND, USD_PER_KG

-- Tax & Compliance (2 fields)
hs_code_6digit               VARCHAR(6)      -- Global HS code
country_tax_codes            JSON            -- {"IND": {"hsn"}, "USA": {"hts"}}

-- Quality Standards (3 fields)
quality_standards            JSON            -- ["USDA", "BCI", "ISO_9001"]
international_grades         JSON            -- {"USDA": [...], "Liverpool": [...]}
certification_required       JSON            -- {"organic": false, "bci": true}

-- Geography (3 fields)
major_producing_countries    JSON            -- ["India", "USA", "China"]
major_consuming_countries    JSON            -- ["China", "Bangladesh"]
trading_hubs                 JSON            -- ["Mumbai", "New York"]

-- Import/Export (4 fields)
export_regulations           JSON            -- {"license_required": true}
import_regulations           JSON            -- {"license_required": false}
phytosanitary_required       BOOLEAN         -- Plant health certificate
fumigation_required          BOOLEAN         -- Fumigation requirement

-- Trading Infrastructure (3 fields)
traded_on_exchanges          JSON            -- ["MCX", "ICE_Futures"]
contract_specifications      JSON            -- Exchange contract details
price_volatility             VARCHAR(20)     -- HIGH/MEDIUM/LOW

-- Seasonal (3 fields)
seasonal_commodity           BOOLEAN
harvest_season               JSON            -- {"India": ["Oct"], "USA": ["Aug"]}
shelf_life_days             INTEGER

-- Storage (1 field)
storage_conditions          JSON             -- Temperature, humidity

-- Contract Terms (3 fields)
standard_lot_size           JSON             -- Domestic vs international
min_order_quantity          JSON
delivery_tolerance_pct      NUMERIC(5,2)
weight_tolerance_pct        NUMERIC(5,2)
```

**TOTAL:** 25 international fields ✅

---

## 2. AVAILABILITY MODEL - GAPS IDENTIFIED

### Current State (India-Only):
```python
class Availability(Base):
    # Location (India-only concept)
    location_id = Column(UUID)  # settings_locations (India cities)
    delivery_terms = Column(String(50))  # "Ex-gin", "Delivered"
    delivery_address = Column(Text)
    delivery_latitude = Column(Numeric)
    delivery_longitude = Column(Numeric)
    delivery_region = Column(String(50))  # India regions
    
    # Pricing (Single currency assumed)
    price_type = Column(String(20))
    base_price = Column(Numeric(15, 2))  # ← No currency specified!
    price_unit = Column(String(20))
    
    # Quantity
    total_quantity = Column(Numeric)
    quantity_unit = Column(String(20))
```

### ❌ MISSING INTERNATIONAL FIELDS:

#### Critical Missing Fields:
1. **origin_country** - Where is the commodity located? (India? USA? China?)
2. **destination_country** - Where can it be shipped? (Domestic? International?)
3. **currency_code** - Price in which currency? (USD, INR, EUR?)
4. **incoterm** - International shipping term (FOB, CIF, CFR, EXW)
5. **port_of_loading** - For international shipments
6. **port_of_discharge** - For international delivery
7. **is_cross_border** - Boolean flag (domestic vs international)
8. **customs_clearance_included** - Who handles customs?
9. **export_license_available** - Does seller have export license?
10. **phytosanitary_certificate_available** - For agricultural exports

#### Impact:
- **CANNOT** differentiate domestic vs international listings
- **CANNOT** filter by origin/destination country
- **CANNOT** apply international compliance rules during matching
- **CANNOT** calculate accurate pricing (currency unknown)
- **CANNOT** determine shipping terms
- **BUYERS from USA/China cannot find Indian cotton exports**

---

## 3. REQUIREMENT MODEL - GAPS IDENTIFIED

### Current State (Partial Support):
```python
class Requirement(Base):
    # Location (India-only)
    preferred_location_ids = Column(ARRAY(UUID))  # India cities only
    delivery_location_id = Column(UUID)  # India location
    delivery_address = Column(Text)
    delivery_latitude = Column(Numeric)
    delivery_longitude = Column(Numeric)
    delivery_state = Column(String(50))  # Indian state
    delivery_city = Column(String(100))  # Indian city
    
    # Pricing
    max_budget_per_unit = Column(Numeric)
    currency_code = Column(String(3), default='INR')  # ✅ HAS THIS!
    
    # Delivery
    delivery_requirements = Column(JSONB)  # Undefined structure
```

### ❌ MISSING INTERNATIONAL FIELDS:

#### Critical Missing Fields:
1. **buyer_country** - Where is buyer located? (Critical for compliance!)
2. **origin_countries_accepted** - Will accept from India? USA? China?
3. **destination_port** - If importing, which port?
4. **preferred_incoterm** - FOB, CIF, CFR, EXW?
5. **max_delivery_distance_km** - Cross-border = unlimited
6. **customs_clearance_handled_by** - BUYER or SELLER
7. **import_license_available** - Does buyer have import license?
8. **preferred_quality_standard** - USDA? BCI? CCI?
9. **phytosanitary_acceptance** - Will accept certificate?
10. **is_cross_border_accepted** - Accept international sellers?

#### Impact:
- **CANNOT** match international sellers with buyers
- **CANNOT** validate buyer country for sanctions check
- **CANNOT** apply import license validation
- **CANNOT** determine if buyer accepts cross-border trade
- **USA buyer cannot specify they want Indian cotton**

---

## 4. MATCHING ENGINE - GAPS IDENTIFIED

### Current Logic (India-Only):
```python
class MatchingEngine:
    async def find_matches(self, requirement: Requirement):
        # STEP 1: LOCATION FILTER (India cities only!)
        location_filter = select(Availability).where(
            Availability.location_id.in_(requirement.preferred_location_ids)
        )
        
        # STEP 2: Score based on:
        # - Distance (lat/long in India)
        # - Delivery region (Indian states)
        # - Price match
        # - Quality match
        
        # ❌ NO INTERNATIONAL LOGIC!
```

### ❌ MISSING INTERNATIONAL MATCHING LOGIC:

#### Required Features:
1. **Cross-Border Detection**
   ```python
   is_international = (
       availability.origin_country != requirement.buyer_country
   )
   ```

2. **Country Filtering**
   ```python
   # Buyer in USA wants cotton from India
   if "India" in requirement.origin_countries_accepted:
       # Include Indian availabilities
   ```

3. **Sanctions Check Integration**
   ```python
   # BEFORE matching, check:
   sanctions_result = await risk_engine.check_sanctions_compliance(
       buyer_country=requirement.buyer_country,
       seller_country=availability.origin_country,
       commodity_id=commodity_id
   )
   if sanctions_result["blocked"]:
       continue  # Skip this match
   ```

4. **Incoterm Matching**
   ```python
   # Buyer wants FOB, Seller offers CIF
   if requirement.preferred_incoterm == availability.incoterm:
       score += 10  # Bonus points
   ```

5. **Currency Conversion**
   ```python
   # Seller: $100 USD/KG
   # Buyer budget: ₹9000 INR/KG
   # Convert to common currency for comparison
   seller_price_inr = convert_currency(
       availability.base_price,
       availability.currency_code,
       requirement.currency_code
   )
   ```

6. **Port Proximity Scoring**
   ```python
   # Instead of city distance, use port-to-port routes
   if is_international:
       distance = calculate_port_distance(
           origin_port=availability.port_of_loading,
           destination_port=requirement.destination_port
       )
   ```

7. **Compliance Pre-Check**
   ```python
   # Check export/import licenses BEFORE showing match
   license_check = await risk_engine.check_export_import_license(
       commodity_id=commodity_id,
       seller_partner_id=availability.seller_partner_id,
       buyer_partner_id=requirement.buyer_partner_id,
       buyer_country=requirement.buyer_country,
       seller_country=availability.origin_country
   )
   if license_check["blocked"]:
       match_result.risk_status = "BLOCKED"
   ```

#### Impact:
- **CANNOT** match USA buyers with Indian sellers
- **CANNOT** apply international compliance during matching
- **CANNOT** compare prices across currencies
- **CANNOT** score based on incoterms
- **CANNOT** calculate international shipping distances
- **Entire international trade flow BROKEN**

---

## 5. REAL-WORLD SCENARIO - CURRENT FAILURE

### Scenario: USA Textile Company wants Indian Cotton

**Setup:**
```python
# Commodity (already in system)
commodity = Commodity(
    name="Cotton - Shankar-6",
    default_currency="USD",
    origin_country="India",
    export_regulations={"license_required": True},
    phytosanitary_required=True
)

# Seller (Indian cotton exporter)
seller = BusinessPartner(
    legal_name="ABC Cotton Exports",
    primary_country="India",
    has_export_license=True
)

# Buyer (USA textile mill)
buyer = BusinessPartner(
    legal_name="XYZ Textiles Inc",
    primary_country="USA",
    needs_import=True
)
```

### Step 1: Seller Posts Availability
```python
# ❌ CURRENT (FAILS):
availability = Availability(
    commodity_id=commodity_id,
    location_id=mumbai_location_id,  # ← India city
    base_price=100.00,  # ← No currency! Assumes INR?
    delivery_terms="Ex-gin"  # ← India domestic term
)

# ✅ NEEDED:
availability = Availability(
    commodity_id=commodity_id,
    origin_country="India",  # ← Missing field!
    destination_countries=["USA", "EU", "China"],  # ← Missing!
    currency_code="USD",  # ← Missing!
    base_price=100.00,
    incoterm="FOB",  # ← Missing field!
    port_of_loading="Mumbai Port",  # ← Missing!
    export_license_available=True,  # ← Missing!
    is_cross_border=True  # ← Missing!
)
```

### Step 2: Buyer Creates Requirement
```python
# ❌ CURRENT (FAILS):
requirement = Requirement(
    commodity_id=commodity_id,
    preferred_location_ids=[mumbai_id, delhi_id],  # ← Only India cities!
    currency_code="USD",  # ← Has this ✅
    max_budget_per_unit=110.00,
    delivery_location_id=new_york_location_id  # ← DOESN'T EXIST!
)

# ✅ NEEDED:
requirement = Requirement(
    commodity_id=commodity_id,
    buyer_country="USA",  # ← Missing field!
    origin_countries_accepted=["India", "USA"],  # ← Missing!
    currency_code="USD",
    max_budget_per_unit=110.00,
    destination_port="New York Port",  # ← Missing!
    preferred_incoterm="FOB",  # ← Missing!
    is_cross_border_accepted=True,  # ← Missing!
    import_license_available=False  # ← Missing (cotton doesn't need it)
)
```

### Step 3: Matching Engine Runs
```python
# ❌ CURRENT (FAILS):
matches = await matching_engine.find_matches(requirement)

# LOCATION FILTER:
# preferred_location_ids = [mumbai_id, delhi_id]
# availability.location_id = mumbai_id
# ✅ PASSES location filter

# BUT THEN:
# - No country validation
# - No sanctions check
# - No export license check
# - No incoterm matching
# - No currency conversion
# - Price comparison fails (USD vs INR?)

# RESULT: Match appears but WILL FAIL at trade execution!

# ✅ NEEDED:
matches = await matching_engine.find_matches(requirement)

# INTERNATIONAL FILTER:
# 1. Check origin country
if availability.origin_country not in requirement.origin_countries_accepted:
    continue  # SKIP

# 2. Run sanctions check
sanctions = await risk_engine.check_sanctions_compliance(
    buyer_country="USA",
    seller_country="India",
    commodity_id=commodity_id
)
if sanctions["blocked"]:
    match.risk_status = "BLOCKED"
    continue

# 3. Check export license
license_check = await risk_engine.check_export_import_license(...)
if license_check["blocked"]:
    match.risk_status = "BLOCKED"
    continue

# 4. Convert currency for price comparison
seller_price_usd = 100.00  # Already USD
buyer_budget_usd = 110.00
if seller_price_usd <= buyer_budget_usd:
    score += 30  # Price match

# 5. Incoterm matching
if requirement.preferred_incoterm == availability.incoterm:
    score += 10

# RESULT: Valid international match with compliance checks!
```

---

## 6. RECOMMENDED FIXES

### Phase 1: Database Schema Changes (CRITICAL)

#### A. Availability Table - Add International Fields
```sql
ALTER TABLE availabilities ADD COLUMN origin_country VARCHAR(100);
ALTER TABLE availabilities ADD COLUMN destination_countries TEXT[];
ALTER TABLE availabilities ADD COLUMN currency_code VARCHAR(3) DEFAULT 'INR';
ALTER TABLE availabilities ADD COLUMN incoterm VARCHAR(10);  -- FOB, CIF, CFR, EXW
ALTER TABLE availabilities ADD COLUMN port_of_loading VARCHAR(200);
ALTER TABLE availabilities ADD COLUMN port_of_discharge VARCHAR(200);
ALTER TABLE availabilities ADD COLUMN is_cross_border BOOLEAN DEFAULT FALSE;
ALTER TABLE availabilities ADD COLUMN customs_clearance_included BOOLEAN;
ALTER TABLE availabilities ADD COLUMN export_license_available BOOLEAN;
ALTER TABLE availabilities ADD COLUMN phytosanitary_cert_available BOOLEAN;

CREATE INDEX idx_availabilities_origin_country ON availabilities(origin_country);
CREATE INDEX idx_availabilities_currency ON availabilities(currency_code);
CREATE INDEX idx_availabilities_is_cross_border ON availabilities(is_cross_border);
```

#### B. Requirements Table - Add International Fields
```sql
ALTER TABLE requirements ADD COLUMN buyer_country VARCHAR(100);
ALTER TABLE requirements ADD COLUMN origin_countries_accepted TEXT[];
ALTER TABLE requirements ADD COLUMN destination_port VARCHAR(200);
ALTER TABLE requirements ADD COLUMN preferred_incoterm VARCHAR(10);
ALTER TABLE requirements ADD COLUMN customs_clearance_handled_by VARCHAR(20);  -- BUYER, SELLER
ALTER TABLE requirements ADD COLUMN import_license_available BOOLEAN;
ALTER TABLE requirements ADD COLUMN preferred_quality_standard VARCHAR(50);  -- USDA, BCI, CCI
ALTER TABLE requirements ADD COLUMN phytosanitary_acceptance BOOLEAN DEFAULT TRUE;
ALTER TABLE requirements ADD COLUMN is_cross_border_accepted BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_requirements_buyer_country ON requirements(buyer_country);
CREATE INDEX idx_requirements_is_cross_border ON requirements(is_cross_border_accepted);
```

### Phase 2: Model Updates

#### A. Availability Model
```python
class Availability(Base):
    # ... existing fields ...
    
    # International Fields
    origin_country = Column(String(100), nullable=True, index=True)
    destination_countries = Column(ARRAY(String), nullable=True)
    currency_code = Column(String(3), nullable=False, server_default='INR')
    incoterm = Column(String(10), nullable=True)  # FOB, CIF, CFR, EXW
    port_of_loading = Column(String(200), nullable=True)
    port_of_discharge = Column(String(200), nullable=True)
    is_cross_border = Column(Boolean, default=False, nullable=False, index=True)
    customs_clearance_included = Column(Boolean, nullable=True)
    export_license_available = Column(Boolean, nullable=True)
    phytosanitary_cert_available = Column(Boolean, nullable=True)
```

#### B. Requirement Model
```python
class Requirement(Base):
    # ... existing fields ...
    
    # International Fields
    buyer_country = Column(String(100), nullable=True, index=True)
    origin_countries_accepted = Column(ARRAY(String), nullable=True)
    destination_port = Column(String(200), nullable=True)
    preferred_incoterm = Column(String(10), nullable=True)
    customs_clearance_handled_by = Column(String(20), nullable=True)
    import_license_available = Column(Boolean, nullable=True)
    preferred_quality_standard = Column(String(50), nullable=True)
    phytosanitary_acceptance = Column(Boolean, default=True)
    is_cross_border_accepted = Column(Boolean, default=False, index=True)
```

### Phase 3: Matching Engine Enhancements

```python
class MatchingEngine:
    async def find_matches(self, requirement: Requirement):
        # STEP 1: Determine trade type
        is_cross_border = (
            requirement.is_cross_border_accepted and
            requirement.buyer_country is not None
        )
        
        # STEP 2: Build query with international filters
        query = select(Availability).where(
            Availability.commodity_id == requirement.commodity_id,
            Availability.status == "ACTIVE"
        )
        
        if is_cross_border:
            # International matching
            if requirement.origin_countries_accepted:
                query = query.where(
                    Availability.origin_country.in_(
                        requirement.origin_countries_accepted
                    )
                )
            
            # Filter by destination countries
            if requirement.buyer_country:
                query = query.where(
                    or_(
                        Availability.destination_countries.contains([requirement.buyer_country]),
                        Availability.destination_countries.is_(None)  # Worldwide
                    )
                )
            
            # Must be cross-border enabled
            query = query.where(Availability.is_cross_border == True)
        else:
            # Domestic matching (existing logic)
            query = query.where(
                Availability.location_id.in_(requirement.preferred_location_ids)
            )
        
        availabilities = await self.db.execute(query)
        
        # STEP 3: Score each match
        matches = []
        for avail in availabilities:
            # Run compliance checks FIRST
            if is_cross_border:
                compliance = await self._check_international_compliance(
                    requirement=requirement,
                    availability=avail
                )
                if compliance["blocked"]:
                    continue  # Skip blocked matches
            
            # Calculate match score
            score = await self._calculate_match_score(
                requirement=requirement,
                availability=avail,
                is_cross_border=is_cross_border
            )
            
            matches.append(MatchResult(
                requirement_id=requirement.id,
                availability_id=avail.id,
                score=score,
                risk_status=compliance.get("risk_status", "PASS")
            ))
        
        return matches
    
    async def _check_international_compliance(self, requirement, availability):
        """Run all international compliance checks"""
        
        # 1. Sanctions check
        sanctions = await self.risk_engine.check_sanctions_compliance(
            buyer_country=requirement.buyer_country,
            seller_country=availability.origin_country,
            commodity_id=requirement.commodity_id
        )
        if sanctions["blocked"]:
            return {"blocked": True, "reason": sanctions["reason"]}
        
        # 2. Export/import license
        license_check = await self.risk_engine.check_export_import_license(
            commodity_id=requirement.commodity_id,
            seller_partner_id=availability.seller_partner_id,
            buyer_partner_id=requirement.buyer_partner_id,
            buyer_country=requirement.buyer_country,
            seller_country=availability.origin_country,
            transaction_value=self._estimate_trade_value(requirement, availability)
        )
        if license_check["blocked"]:
            return {"blocked": True, "reason": license_check["reason"]}
        
        # 3. Currency support
        commodity = await self._get_commodity(requirement.commodity_id)
        if requirement.currency_code not in commodity.supported_currencies:
            return {
                "blocked": True,
                "reason": f"Currency {requirement.currency_code} not supported"
            }
        
        return {"blocked": False, "risk_status": "PASS"}
    
    async def _calculate_match_score(self, requirement, availability, is_cross_border):
        """Calculate match score with international factors"""
        score = 0.0
        
        if is_cross_border:
            # International scoring factors
            
            # 1. Price match (convert currency)
            buyer_price_converted = await self._convert_currency(
                amount=requirement.max_budget_per_unit,
                from_currency=requirement.currency_code,
                to_currency=availability.currency_code
            )
            if availability.base_price <= buyer_price_converted:
                score += 30
            
            # 2. Incoterm match
            if requirement.preferred_incoterm == availability.incoterm:
                score += 10
            
            # 3. Quality standard match
            if requirement.preferred_quality_standard:
                commodity = await self._get_commodity(requirement.commodity_id)
                if requirement.preferred_quality_standard in commodity.quality_standards:
                    score += 10
            
            # 4. Port proximity (if applicable)
            if requirement.destination_port and availability.port_of_discharge:
                # Calculate shipping route efficiency
                port_score = self._calculate_port_proximity(
                    requirement.destination_port,
                    availability.port_of_discharge
                )
                score += port_score * 15  # Max 15 points
            
            # 5. Compliance readiness
            if availability.export_license_available:
                score += 5
            if availability.phytosanitary_cert_available:
                score += 5
            
        else:
            # Domestic scoring (existing logic)
            # ... existing distance-based scoring ...
            pass
        
        return min(100.0, score)
```

---

## 7. MIGRATION PLAN

### Step 1: Database Migration
1. Create migration file: `20251203_add_international_trade_desk_fields.py`
2. Add columns to `availabilities` table (10 fields)
3. Add columns to `requirements` table (9 fields)
4. Create indexes for performance
5. Run migration on dev/staging/prod

### Step 2: Model Updates
1. Update `Availability` model with international fields
2. Update `Requirement` model with international fields
3. Update Pydantic schemas for API
4. Add validation logic

### Step 3: Matching Engine Enhancement
1. Add international matching logic
2. Integrate compliance checks from RiskEngine
3. Add currency conversion support
4. Add port-based distance calculation
5. Update scoring algorithm

### Step 4: Service Layer Updates
1. Update `AvailabilityService` to handle international fields
2. Update `RequirementService` to handle international fields
3. Update `MatchingService` to use enhanced engine

### Step 5: API Updates
1. Update POST `/availabilities` endpoint
2. Update POST `/requirements` endpoint
3. Update GET `/matches` endpoint
4. Add international filters to search

### Step 6: Frontend Updates
1. Add country selectors to forms
2. Add incoterm dropdowns
3. Add port selection fields
4. Add currency selector
5. Show international matches separately

---

## 8. TESTING REQUIREMENTS

### Test Scenarios:
1. **Domestic Trade (India-India)** - Should work as before
2. **International Export (India→USA)** - New functionality
3. **International Import (USA→India)** - New functionality
4. **Blocked Trade (India→Iran)** - Sanctions compliance
5. **Multi-Currency Matching** - USD seller, INR buyer
6. **Incoterm Matching** - FOB vs CIF preferences
7. **License Validation** - Export license required
8. **Port-Based Matching** - Mumbai→New York route

---

## 9. PRIORITY & TIMELINE

### CRITICAL (Week 1):
- [ ] Database migration for international fields
- [ ] Model updates (Availability, Requirement)
- [ ] Basic international matching logic

### HIGH (Week 2):
- [ ] Compliance integration (sanctions, licenses)
- [ ] Currency conversion in matching
- [ ] Incoterm support

### MEDIUM (Week 3):
- [ ] Port-based distance calculation
- [ ] Quality standard matching
- [ ] Enhanced scoring algorithm

### LOW (Week 4):
- [ ] Frontend internationalization
- [ ] Multi-currency display
- [ ] Port selection UI

---

## 10. CONCLUSION

**VERDICT:** Trade Desk is **NOT READY** for international trade despite having:
- ✅ International Commodity Master
- ✅ International Risk Engine with compliance checks
- ✅ Multi-currency support in backend

**ROOT CAUSE:** Availability/Requirement models and Matching Engine designed for **India-only** domestic trade.

**IMPACT:** Cannot support cross-border transactions without major schema and logic changes.

**RECOMMENDATION:** Implement Phase 1-3 (database + models + matching) **immediately** to unlock international trading capabilities that other modules already support.

---

**Generated:** December 3, 2025  
**Author:** GitHub Copilot  
**Review Status:** Pending stakeholder approval
