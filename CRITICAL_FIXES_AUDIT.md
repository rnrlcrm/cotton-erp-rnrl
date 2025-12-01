# 🔥 CRITICAL FIXES - AVAILABILITY & REQUIREMENT ENGINES

**Branch:** `fix/availability-requirement-critical-fixes`  
**Date:** December 1, 2025  
**Status:** AUDIT COMPLETE → READY FOR IMPLEMENTATION

---

## 📋 ISSUES IDENTIFIED

### **ISSUE #1: Role-Based Auth Instead of Capability-Based** ❌

**Current State:**
- Using `get_seller_id_from_user()` and `get_buyer_id_from_user()` helper functions
- Hardcoded role extraction from user context
- No capability checks in routes

**Expected State:**
- Use `@RequireCapability` decorator for all endpoints
- Check capabilities like `AVAILABILITY_CREATE`, `REQUIREMENT_CREATE`
- Remove role-based helpers

**Files Affected:**
- `backend/modules/trade_desk/routes/availability_routes.py`
- `backend/modules/trade_desk/routes/requirement_routes.py`

**Fix:**
```python
# BEFORE (WRONG):
def get_seller_id_from_user(user) -> UUID:
    if user.user_type == "EXTERNAL" and user.business_partner_id:
        return user.business_partner_id
    ...

@router.post("")
async def create_availability(
    request: AvailabilityCreateRequest,
    current_user=Depends(get_current_user),
    ...
):
    seller_id = get_seller_id_from_user(current_user)  # ❌

# AFTER (CORRECT):
@router.post("")
@RequireCapability(Capabilities.AVAILABILITY_CREATE)
async def create_availability(
    request: AvailabilityCreateRequest,
    current_user=Depends(get_current_user),
    ...
):
    seller_id = current_user.business_partner_id  # ✅
```

---

### **ISSUE #2: No EOD Square-Off for Availabilities** ❌

**Current State:**
- Availabilities stay ACTIVE indefinitely until manually marked SOLD/CANCELLED
- No automatic EOD cleanup

**Expected State:**
- All ACTIVE/AVAILABLE positions must square off at EOD (End of Day)
- Timezone-aware EOD calculation (global system, multiple timezones)
- Seller can re-post next day if needed

**Solution:**
1. Add `eod_cutoff` timestamp to Availability model
2. Create cron job to expire availabilities at their timezone's EOD
3. Status transition: ACTIVE → EXPIRED (automatic)

**Implementation:**
```python
# In Availability model:
eod_cutoff = Column(
    TIMESTAMP(timezone=True),
    nullable=False,
    comment='End-of-day cutoff based on location timezone'
)

# Cron job (runs every hour):
async def expire_availabilities_eod():
    """
    Expire availabilities past their EOD cutoff.
    Timezone-aware: Uses location's timezone for EOD calculation.
    """
    now = datetime.now(timezone.utc)
    
    # Find expired availabilities
    expired = await db.execute(
        select(Availability)
        .where(
            Availability.status.in_(['ACTIVE', 'AVAILABLE']),
            Availability.eod_cutoff <= now
        )
    )
    
    for avail in expired.scalars():
        avail.status = AvailabilityStatus.EXPIRED
        # Emit event
        await emit_event('availability.expired', avail.id)
    
    await db.commit()
```

---

### **ISSUE #3: No EOD Square-Off for Requirements** ❌

**Current State:**
- Requirements stay ACTIVE until manually cancelled or fulfilled
- No automatic EOD cleanup

**Expected State:**
- Same as availabilities - must square off at EOD
- Buyer can re-post next day

**Solution:** Same as #2 but for Requirement model

---

### **ISSUE #4: Circular Trading Logic is Wrong** ❌

**Current State:**
```python
# In risk_engine.py:
func.date(Availability.created_at) == trade_date  # ❌ Blocks same-day
```

**CORRECT Business Logic:**
```
SCENARIO 1: Own Position Check
ALLOWED ✅:
- 9 AM: Manjeet BUYS from Party A (trade COMPLETED/SETTLED)
- 3 PM: Manjeet SELLS to Party B (different party, owns commodity now)

BLOCKED ❌:
- 9 AM: Manjeet creates BUY requirement (status=ACTIVE, not settled)
- 10 AM: Manjeet creates SELL availability (can't sell what he doesn't own yet)

SCENARIO 2: Same Counter-Party (WASH TRADING)
BLOCKED ❌:
- 9 AM: Manjeet BUYS from Harman (100 bales cotton)
- 10 AM: Manjeet SELLS to Harman (same 100 bales, same day, same commodity)
         ↑ This is CIRCULAR/WASH TRADING - BLOCKED!

KEY RULES:
1. Can't sell commodity you don't own yet (unsettled BUY)
2. Can't buy/sell SAME commodity with SAME party on SAME DAY (circular trading)
```

**Expected State:**
- Block UNSETTLED positions (can't sell what you don't own)
- Block same-day BUY from Party A → SELL to Party A (wash trading)
- Allow: BUY from Party A → SELL to Party B (legitimate trading)

**Fix:**
```python
# CORRECT LOGIC:
async def check_circular_trading(
    self,
    partner_id: UUID,
    commodity_id: UUID,
    transaction_type: str,  # "BUY" or "SELL"
    counter_party_id: Optional[UUID] = None  # 🔥 NEW: Who they're trading with
) -> Dict[str, Any]:
    """
    Prevent circular trading:
    1. Can't sell what you don't own (unsettled positions)
    2. Can't buy/sell same commodity with same party same day (wash trading)
    
    Rules:
    - SELL: Blocked if (a) OPEN BUY exists, OR (b) BUY from this counter-party today
    - BUY: Blocked if (a) OPEN SELL exists, OR (b) SELL to this counter-party today
    """
    today = datetime.now().date()
    
    if transaction_type == "SELL":
        # Check 1: Do they have UNSETTLED BUY?
        unsettled_buys = await self.db.execute(
            select(Requirement).where(
                and_(
                    Requirement.buyer_partner_id == partner_id,
                    Requirement.commodity_id == commodity_id,
                    Requirement.status.in_(['DRAFT', 'ACTIVE', 'PENDING_APPROVAL'])
                )
            )
        )
        
        if unsettled_buys.scalars().first():
            return {
                "blocked": True,
                "reason": "Cannot SELL: You have OPEN BUY position(s) for this commodity. Settle first.",
                "violation_type": "UNSETTLED_BUY_EXISTS"
            }
        
        # Check 2: Did they BUY from this counter-party TODAY?
        if counter_party_id:
            # Find completed trades today where they BOUGHT from counter_party
            todays_buys = await self.db.execute(
                select(Trade).where(
                    and_(
                        Trade.buyer_partner_id == partner_id,
                        Trade.seller_partner_id == counter_party_id,
                        Trade.commodity_id == commodity_id,
                        func.date(Trade.created_at) == today,
                        Trade.status.in_(['PENDING', 'CONFIRMED', 'IN_PROGRESS'])
                    )
                )
            )
            
            if todays_buys.scalars().first():
                return {
                    "blocked": True,
                    "reason": (
                        f"WASH TRADING BLOCKED: You bought this commodity from this party TODAY. "
                        f"Cannot sell back to same party on same day."
                    ),
                    "violation_type": "SAME_DAY_REVERSE_TRADE",
                    "recommendation": "Wait until tomorrow or sell to different party"
                }
    
    elif transaction_type == "BUY":
        # Check 1: Do they have UNSETTLED SELL?
        unsettled_sells = await self.db.execute(
            select(Availability).where(
                and_(
                    Availability.seller_partner_id == partner_id,
                    Availability.commodity_id == commodity_id,
                    Availability.status.in_(['DRAFT', 'ACTIVE', 'AVAILABLE', 'PARTIALLY_SOLD'])
                )
            )
        )
        
        if unsettled_sells.scalars().first():
            return {
                "blocked": True,
                "reason": "Cannot BUY: You have OPEN SELL position(s) for this commodity. Settle first.",
                "violation_type": "UNSETTLED_SELL_EXISTS"
            }
        
        # Check 2: Did they SELL to this counter-party TODAY?
        if counter_party_id:
            # Find completed trades today where they SOLD to counter_party
            todays_sells = await self.db.execute(
                select(Trade).where(
                    and_(
                        Trade.seller_partner_id == partner_id,
                        Trade.buyer_partner_id == counter_party_id,
                        Trade.commodity_id == commodity_id,
                        func.date(Trade.created_at) == today,
                        Trade.status.in_(['PENDING', 'CONFIRMED', 'IN_PROGRESS'])
                    )
                )
            )
            
            if todays_sells.scalars().first():
                return {
                    "blocked": True,
                    "reason": (
                        f"WASH TRADING BLOCKED: You sold this commodity to this party TODAY. "
                        f"Cannot buy back from same party on same day."
                    ),
                    "violation_type": "SAME_DAY_REVERSE_TRADE",
                    "recommendation": "Wait until tomorrow or buy from different party"
                }
    
    # No circular trading detected
    return {
        "blocked": False,
        "reason": "No circular trading detected"
    }

# USAGE in Availability/Requirement creation:
circular_check = await risk_engine.check_circular_trading(
    partner_id=seller_id,
    commodity_id=commodity_id,
    transaction_type="SELL",
    counter_party_id=buyer_id  # 🔥 Pass the counter-party for wash trading check
)
```

**Summary:**
- ✅ Blocks UNSETTLED positions (can't sell what you don't own)
- ✅ Blocks same-day reverse trades with SAME party (Manjeet ↔ Harman circular)
- ✅ Allows legitimate trading (Manjeet buys from Harman, sells to Different Party)

---

### **ISSUE #5: Payment Terms Not Mandatory in Requirement** ❌

**Current State:**
```python
# In RequirementCreateRequest:
preferred_payment_terms: Optional[List[UUID]] = None  # ❌ Optional
preferred_delivery_terms: Optional[List[UUID]] = None  # ❌ Optional
```

**Expected State:**
- Buyer MUST specify payment terms
- Buyer MUST specify delivery/passing/weighment terms

**Fix:**
```python
# AFTER:
class RequirementCreateRequest(BaseModel):
    # ... existing fields ...
    
    # 🔥 MANDATORY TERMS
    payment_terms: List[UUID] = Field(
        ...,  # Required
        min_items=1,
        description="MANDATORY: Acceptable payment term IDs (LC, TT, DA, etc.)"
    )
    
    delivery_terms: List[UUID] = Field(
        ...,  # Required
        min_items=1,
        description="MANDATORY: Delivery/passing/weighment term IDs"
    )
    
    weighment_terms: List[UUID] = Field(
        ...,  # Required
        min_items=1,
        description="MANDATORY: Weighment term IDs (seller's scale, buyer's scale, third-party)"
    )
```

---

### **ISSUE #6: Budget Naming - Should be "Target Price"** ❌

**Current State:**
```python
max_budget_per_unit: Decimal = Field(...)  # ❌ Confusing name
preferred_price_per_unit: Optional[Decimal] = None  # ❌ Optional
```

**Expected State:**
- Rename `preferred_price_per_unit` → `target_price_per_unit` (clearer)
- Make it MANDATORY
- Remove `max_budget_per_unit` (or make it optional ceiling)

**Fix:**
```python
# AFTER:
class RequirementCreateRequest(BaseModel):
    # ... existing fields ...
    
    # 🔥 PRICING (Revised)
    target_price_per_unit: Decimal = Field(
        ...,  # MANDATORY
        gt=0,
        description="MANDATORY: Target/desired price per unit (buyer's offer price)"
    )
    
    max_budget_per_unit: Optional[Decimal] = Field(
        None,  # Optional ceiling
        gt=0,
        description="OPTIONAL: Maximum price willing to pay (if different from target)"
    )
```

---

### **ISSUE #7: Price Optional in Requirement (After Match)** ❌

**Current State:**
- Buyer must specify price upfront when creating requirement

**Expected State:**
- Buyer can create requirement WITHOUT price
- After match, seller can offer price OR buyer can offer price
- Negotiation can start from either side

**Solution:**
```python
# Make pricing optional
class RequirementCreateRequest(BaseModel):
    # ... existing fields ...
    
    # 🔥 PRICING (OPTIONAL - for negotiation)
    target_price_per_unit: Optional[Decimal] = Field(
        None,
        gt=0,
        description="OPTIONAL: Target price. If NULL, buyer wants seller to quote."
    )
    
    max_budget_per_unit: Optional[Decimal] = Field(
        None,
        gt=0,
        description="OPTIONAL: Maximum ceiling price"
    )
    
    price_discovery_mode: bool = Field(
        default=False,
        description="If True, buyer wants sellers to quote prices (no buyer price upfront)"
    )
```

---

### **ISSUE #8: Timezone Handling for Global System** ❌

**Current State:**
- No timezone awareness
- EOD uses server time (India)

**Expected State:**
- Each location has timezone
- EOD calculated per location's timezone
- Mumbai seller → 11:59 PM IST
- New York seller → 11:59 PM EST
- London seller → 11:59 PM GMT

**Implementation:**
```python
# In settings_locations table:
ALTER TABLE settings_locations ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Kolkata';

# EOD calculation:
def calculate_eod_cutoff(location_timezone: str) -> datetime:
    """
    Calculate EOD cutoff for given timezone.
    Always midnight (00:00) of NEXT day in that timezone.
    """
    tz = pytz.timezone(location_timezone)
    now_in_tz = datetime.now(tz)
    
    # Next midnight in that timezone
    next_midnight = (now_in_tz + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    # Convert to UTC for storage
    return next_midnight.astimezone(pytz.UTC)
```

---

## ✅ IMPLEMENTATION PLAN

### **Phase 1: Database Changes** (30 mins)
1. Add `eod_cutoff` column to `availabilities` table
2. Add `eod_cutoff` column to `requirements` table
3. Add `timezone` column to `settings_locations` table
4. Add migration script

### **Phase 2: Model Updates** (30 mins)
1. Update `Availability` model with `eod_cutoff`
2. Update `Requirement` model with `eod_cutoff`
3. Add timezone handling in location model

### **Phase 3: Schema Changes** (45 mins)
1. Make `payment_terms`, `delivery_terms`, `weighment_terms` MANDATORY in `RequirementCreateRequest`
2. Rename `preferred_price_per_unit` → `target_price_per_unit`
3. Make pricing optional (support price discovery mode)

### **Phase 4: Service Layer Fixes** (1 hour)
1. Remove role-based helpers
2. Add capability checks
3. Update circular trading logic (check CURRENT open positions, not full day)
4. Add timezone-aware EOD calculation

### **Phase 5: Route Updates** (1 hour)
1. Add `@RequireCapability` decorators to all endpoints
2. Update availability routes
3. Update requirement routes

### **Phase 6: Cron Jobs** (45 mins)
1. Create `expire_availabilities_eod.py` job
2. Create `expire_requirements_eod.py` job
3. Schedule jobs (run every hour, check timezone-aware EOD)

### **Phase 7: Testing** (1 hour)
1. Test capability-based auth
2. Test EOD expiry (multiple timezones)
3. Test circular trading (intraday buy/sell allowed)
4. Test mandatory payment terms

---

### **ISSUE #9: Buyer Preference Saving (Payment/Delivery/Weighment Terms)** ❌

**Current State:**
- Buyer selects terms every time creating requirement
- No option to save preferences

**Expected State:**
- System asks: "Save these terms as default preferences?"
- Buyer can save commonly used terms
- Auto-populate on next requirement creation

**Implementation:**
```python
# New table: buyer_preferences
CREATE TABLE buyer_preferences (
    id UUID PRIMARY KEY,
    buyer_partner_id UUID REFERENCES business_partners(id),
    
    # Default terms
    default_payment_terms JSONB,  # Array of term UUIDs
    default_delivery_terms JSONB,  # Array of term UUIDs
    default_weighment_terms JSONB,  # Array of term UUIDs
    
    # Quick-use presets
    preset_name VARCHAR(100),  # "Standard Purchase", "Urgent Buy", etc.
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(buyer_partner_id, preset_name)
);

# In RequirementCreateRequest:
class RequirementCreateRequest(BaseModel):
    # ... existing fields ...
    
    save_as_preference: bool = Field(
        default=False,
        description="Save these terms as default preference"
    )
    
    preference_preset_name: Optional[str] = Field(
        None,
        description="Name for this preference preset (e.g., 'Standard Purchase')"
    )
    
    load_from_preference: bool = Field(
        default=False,
        description="Load terms from saved preferences"
    )

# Service logic:
async def create_requirement(self, ...):
    # Load preferences if requested
    if request.load_from_preference:
        prefs = await self.get_buyer_preferences(buyer_id)
        if prefs:
            request.payment_terms = prefs.default_payment_terms
            request.delivery_terms = prefs.default_delivery_terms
            request.weighment_terms = prefs.default_weighment_terms
    
    # ... create requirement ...
    
    # Save preferences if requested
    if request.save_as_preference:
        await self.save_buyer_preferences(
            buyer_id=buyer_id,
            payment_terms=request.payment_terms,
            delivery_terms=request.delivery_terms,
            weighment_terms=request.weighment_terms,
            preset_name=request.preference_preset_name
        )
```

---

### **ISSUE #10: Commodity Parameter Validation Missing** ❌

**Current State:**
- Availability & Requirement accept ANY quality parameters in JSONB
- No validation against Commodity Master's CommodityParameter table
- min_value/max_value defined but not enforced

**Expected State:**
- Validate quality_params against commodity's registered parameters
- Enforce min/max ranges from CommodityParameter table
- Reject invalid parameters

**Implementation:**
```python
# In AvailabilityService.create_availability():
async def _validate_quality_parameters(
    self,
    commodity_id: UUID,
    quality_params: dict
) -> None:
    """
    Validate quality parameters against commodity master.
    
    Rules:
    1. Check if parameter is registered in CommodityParameter
    2. Validate min/max ranges
    3. Check mandatory parameters are present
    """
    # Get commodity's registered parameters
    registered_params = await self.db.execute(
        select(CommodityParameter)
        .where(CommodityParameter.commodity_id == commodity_id)
    )
    params_list = registered_params.scalars().all()
    
    # Build validation map
    param_map = {p.parameter_name: p for p in params_list}
    
    # Check each provided parameter
    for param_name, param_value in quality_params.items():
        if param_name not in param_map:
            raise ValueError(
                f"Parameter '{param_name}' is not registered for this commodity. "
                f"Registered parameters: {list(param_map.keys())}"
            )
        
        registered = param_map[param_name]
        
        # Validate NUMERIC type with min/max
        if registered.parameter_type == "NUMERIC":
            value = Decimal(str(param_value))
            
            if registered.min_value and value < registered.min_value:
                raise ValueError(
                    f"{param_name}: {value} is below minimum {registered.min_value}"
                )
            
            if registered.max_value and value > registered.max_value:
                raise ValueError(
                    f"{param_name}: {value} exceeds maximum {registered.max_value}"
                )
        
        # Validate RANGE type
        if registered.parameter_type == "RANGE":
            if not isinstance(param_value, dict) or 'min' not in param_value or 'max' not in param_value:
                raise ValueError(
                    f"{param_name}: RANGE type requires {{min: X, max: Y}} format"
                )
    
    # Check mandatory parameters are present
    mandatory_params = [p.parameter_name for p in params_list if p.is_mandatory]
    missing = set(mandatory_params) - set(quality_params.keys())
    
    if missing:
        raise ValueError(
            f"Missing mandatory parameters: {list(missing)}"
        )
```

---

### **ISSUE #11: Unit Conversion Not Validated** ❌

**Current State:**
- Availability/Requirement accept any quantity_unit
- No validation against commodity's base_unit/trade_unit
- Conversion happens but not validated upfront

**Expected State:**
- Validate quantity_unit is compatible with commodity's base_unit
- Auto-convert using unit_converter.py
- Reject incompatible units (e.g., KG for METER-based commodity)

**Implementation:**
```python
# In AvailabilityService.create_availability():
async def _validate_and_convert_units(
    self,
    commodity_id: UUID,
    quantity: Decimal,
    quantity_unit: str
) -> dict:
    """
    Validate unit compatibility and convert to base unit.
    
    Returns:
        {
            "quantity": original quantity,
            "quantity_unit": original unit,
            "quantity_in_base_unit": converted quantity,
            "base_unit": commodity's base unit,
            "conversion_factor": factor used
        }
    """
    # Get commodity
    commodity_result = await self.db.execute(
        select(Commodity).where(Commodity.id == commodity_id)
    )
    commodity = commodity_result.scalar_one_or_none()
    
    if not commodity:
        raise ValueError(f"Commodity {commodity_id} not found")
    
    # Get unit info from catalog
    from backend.modules.settings.commodities.unit_converter import UnitConverter
    from backend.modules.settings.commodities.unit_catalog import get_unit_info
    
    unit_info = get_unit_info(quantity_unit)
    if not unit_info:
        raise ValueError(
            f"Unknown unit: {quantity_unit}. "
            f"Please use standard units like BALE, KG, MT, CANDY, QUINTAL"
        )
    
    # Validate unit is compatible with commodity's base_unit
    if unit_info["base_unit"] != commodity.base_unit:
        raise ValueError(
            f"Unit '{quantity_unit}' (base: {unit_info['base_unit']}) is incompatible "
            f"with commodity's base unit '{commodity.base_unit}'. "
            f"Please use units based on {commodity.base_unit}."
        )
    
    # Convert to base unit
    quantity_in_base = UnitConverter.convert_to_base(
        quantity=quantity,
        from_unit=quantity_unit,
        base_unit=commodity.base_unit
    )
    
    return {
        "quantity": quantity,
        "quantity_unit": quantity_unit,
        "quantity_in_base_unit": quantity_in_base,
        "base_unit": commodity.base_unit,
        "conversion_factor": unit_info["conversion_factor"]
    }

# Call in create_availability():
unit_validation = await self._validate_and_convert_units(
    commodity_id=commodity_id,
    quantity=total_quantity,
    quantity_unit=quantity_unit
)

# Store in availability
availability.quantity_in_base_unit = unit_validation["quantity_in_base_unit"]
```

---

### **ISSUE #12: Risk Engine Uses Role-Based, Not Capability-Based** ❌

**Current State:**
- Risk engine references `buyer_partner_id`, `seller_id`, `BUYER`, `SELLER` hardcoded
- No capability checks in risk_engine.py or risk_service.py

**Expected State:**
- Risk engine should use partner_id generically
- Capability-based access in risk routes (if any)
- Risk assessment based on partner capabilities, not roles

**Files to Update:**
- `backend/modules/risk/risk_engine.py` - Remove role-based terminology
- `backend/modules/risk/risk_service.py` - Use generic partner_id
- Risk routes (if exist) - Add `@RequireCapability` decorators

---

### **ISSUE #13: Risk Engine Must Run AFTER Creation, BEFORE Matching** ❌

**Current State:**
```python
# In requirement_service.py:
1. Create requirement in DB
2. Emit requirement.created event
3. Matching service triggered immediately → finds matches ❌ WRONG
4. Risk check happens somewhere (unclear when)
```

**CORRECT Sequential Flow:**
```python
1. Validate input data
2. Create requirement/availability in DB
3. 🔥 RUN RISK ENGINE (comprehensive check on saved entity)
4. If FAIL → Mark as BLOCKED/REJECTED
5. If PASS/WARN → THEN trigger matching
```

**Why This Matters:**
- Risk needs the entity ID to perform circular trading checks
- Risk needs DB access to query historical trades
- Matching should ONLY process risk-approved entities
- Current: Matching runs in parallel with risk (race condition)

**Expected State:**
```python
# In RequirementService.create_requirement():

# STEP 1: Validate input
validate_commodity_exists(commodity_id)
validate_payment_terms(payment_terms)

# STEP 2: Create requirement in DB
requirement = Requirement(...)
await self.db.add(requirement)
await self.db.commit()
await self.db.refresh(requirement)

# STEP 3: 🔥 RUN RISK ENGINE (synchronous, blocks until complete)
risk_result = await risk_engine.comprehensive_check(
    entity_type="requirement",
    entity_id=requirement.id,
    partner_id=buyer_id,
    estimated_value=estimated_value
)

# STEP 4: Update requirement with risk assessment
requirement.risk_precheck_status = risk_result["status"]
requirement.risk_precheck_score = risk_result["score"]
requirement.risk_flags = risk_result["flags"]

if risk_result["status"] == "FAIL":
    requirement.status = "BLOCKED"
    await self.db.commit()
    raise RiskCheckFailedError(f"Risk check failed: {risk_result['reason']}")

await self.db.commit()

# STEP 5: Emit requirement.created event (AFTER risk check)
await emit_event('requirement.created', requirement.id)

# STEP 6: Trigger matching (ONLY if risk passed)
# Matching service picks up requirement.created event
# OR call directly:
await matching_service.find_matches_for_requirement(requirement.id)
```

**Flow Diagram:**
```
User Request
   ↓
1. Validate inputs
   ↓
2. Create requirement in DB ✓
   ↓
3. 🔥 RISK ENGINE (synchronous)
   ├─ Circular trading check (needs entity ID)
   ├─ Wash trading check (needs DB queries)
   ├─ Credit limit check
   └─ Historical analysis
   ↓
   ├─ FAIL → Mark BLOCKED, Reject ❌
   └─ PASS/WARN → Continue ✓
   ↓
4. Emit requirement.created event
   ↓
5. 🎯 MATCHING SERVICE (ONLY for approved entities)
   ├─ Find availabilities
   ├─ Score matches
   └─ Create negotiations
```

**Benefits:**
- ✅ Risk has access to entity ID for circular trading checks
- ✅ Risk can query DB for historical trades (wash trading detection)
- ✅ Matching ONLY processes approved entities
- ✅ No race condition between risk and matching
- ✅ Clear sequential flow: Create → Risk → Match

**Key Design:**
- Risk runs **synchronously** after creation (blocks user response)
- Matching runs **after** risk approval (event-driven or direct call)
- All business logic in services, routes just call services

---

### **ISSUE #14: Missing Peer-to-Peer Performance Validation Before Matching** ❌

**Current State:**
- Risk Engine checks credit limits and party links
- NO validation of peer-to-peer historical performance
- Matching happens without checking if buyer/seller have good track record together
- No quality performance scoring between specific partners

**Expected State:**
Before matching buyer requirement with seller availability, system MUST check:

**1. Peer-to-Peer Outstanding Amount:**
```python
# Check if buyer has unpaid invoices with this specific seller
outstanding_amount = await get_outstanding_between_partners(
    buyer_id=buyer_partner_id,
    seller_id=seller_partner_id
)

if outstanding_amount > threshold:
    risk_score -= 30
    risk_factors.append(f"Buyer has ₹{outstanding_amount} outstanding with this seller")
```

**2. Buyer Payment Performance (with this specific seller):**
```python
# Not global payment score, but payment history with THIS seller
peer_payment_score = await calculate_peer_payment_performance(
    buyer_id=buyer_partner_id,
    seller_id=seller_partner_id
)
# Score based on:
# - Average days to payment (target: 0-30 days)
# - Late payment count
# - Disputed payment count
# - Full vs partial payment ratio

if peer_payment_score < 30:
    risk_score -= 40
    risk_factors.append(f"Very poor payment history with this seller: {peer_payment_score}/100")
    # BLOCK matching with THIS seller only
    blocked_sellers.append({
        "seller_id": seller_partner_id,
        "reason": f"Poor payment history ({peer_payment_score}/100)",
        "recommendation": "Improve payment performance before trading again"
    })
elif peer_payment_score < 50:
    risk_score -= 20
    risk_factors.append(f"Below average payment history with this seller: {peer_payment_score}/100")
    # WARN but allow matching
    warnings.append({
        "seller_id": seller_partner_id,
        "severity": "WARN",
        "message": f"Below average payment history with this seller ({peer_payment_score}/100)"
    })
```

**3. Seller Delivery Performance (with this specific buyer):**
```python
# How well has THIS seller delivered to THIS buyer in past
peer_delivery_score = await calculate_peer_delivery_performance(
    seller_id=seller_partner_id,
    buyer_id=buyer_partner_id
)
# Score based on:
# - On-time delivery rate
# - Quantity variance (delivered vs promised)
# - Delivery condition/damage rate
# - Delivery documentation completeness

if peer_delivery_score < 30:
    risk_score -= 40
    risk_factors.append(f"Very poor delivery history with this buyer: {peer_delivery_score}/100")
    # BLOCK matching with THIS buyer only
    blocked_buyers.append({
        "buyer_id": buyer_partner_id,
        "reason": f"Poor delivery history ({peer_delivery_score}/100)",
        "recommendation": "Improve delivery performance before trading again"
    })
elif peer_delivery_score < 50:
    risk_score -= 20
    risk_factors.append(f"Below average delivery history with this buyer: {peer_delivery_score}/100")
    # WARN but allow matching
    warnings.append({
        "buyer_id": buyer_partner_id,
        "severity": "WARN",
        "message": f"Below average delivery history with this buyer ({peer_delivery_score}/100)"
    })
```

**4. Quality Performance (between these two partners):**
```python
# Quality disputes/issues between THIS buyer-seller pair
peer_quality_score = await calculate_peer_quality_performance(
    buyer_id=buyer_partner_id,
    seller_id=seller_partner_id
)
# Score based on:
# - Quality dispute count
# - Quality variance (promised vs delivered parameters)
# - Quality claim amount/resolution
# - Return/rejection rate

if peer_quality_score < 30:
    risk_score -= 30
    risk_factors.append(f"Severe quality issues with this partner: {peer_quality_score}/100")
    # BLOCK matching with THIS partner only
    blocked_partners.append({
        "partner_id": counterparty_id,
        "reason": f"Severe quality issues ({peer_quality_score}/100)",
        "recommendation": "Resolve quality disputes before trading again"
    })
elif peer_quality_score < 50:
    risk_score -= 15
    risk_factors.append(f"Quality concerns with this partner: {peer_quality_score}/100")
    # WARN but allow matching
    warnings.append({
        "partner_id": counterparty_id,
        "severity": "WARN",
        "message": f"Quality concerns with this partner ({peer_quality_score}/100)"
    })
```

**5. Overall Peer-to-Peer Relationship Score:**
```python
peer_relationship_score = (
    peer_payment_score * 0.35 +      # 35% weight
    peer_delivery_score * 0.30 +     # 30% weight
    peer_quality_score * 0.25 +      # 25% weight
    peer_dispute_resolution * 0.10   # 10% weight
)

# GRANULAR BLOCKING: Block only THIS specific partner, not all matches
if peer_relationship_score < 30:
    return {
        "status": "BLOCKED_FOR_THIS_PARTNER",  # Not global FAIL
        "peer_score": peer_relationship_score,
        "blocked_partner_id": counterparty_id,
        "reason": "Very poor historical relationship with this specific partner",
        "recommendation": "Match with OTHER sellers/buyers, but NOT this one",
        "allow_other_matches": True  # ✅ Can match with different partners
    }
elif peer_relationship_score < 50:
    return {
        "status": "WARN",
        "peer_score": peer_relationship_score,
        "partner_id": counterparty_id,
        "reason": "Below average relationship with this partner",
        "recommendation": "Proceed with caution - require manual approval"
    }
```

**Why This Matters:**
- A buyer may have good GLOBAL payment score but poor history with THIS seller
- A seller may have good GLOBAL delivery score but failed THIS buyer before
- **GRANULAR BLOCKING:** Block matching with specific bad partner, allow others
- Prevents matching partners who have history of disputes
- Protects both parties from repeat bad experiences

**Matching Behavior:**
```python
# Example: Buyer has 30% payment score with Seller A, 85% with Seller B

# ❌ BLOCKED: Buyer requirement + Seller A availability (peer score < 30)
# ✅ ALLOWED: Buyer requirement + Seller B availability (good peer score)
# ✅ ALLOWED: Buyer requirement + Seller C availability (no history, global score used)

# Result: Buyer can still trade with OTHER sellers, just not Seller A
```

**Implementation Location:**
```python
# In MatchingService.find_matches():

# STEP 1: Find potential matches (commodity, quantity, price, quality)
potential_matches = await query_availabilities_for_requirement(requirement)

# STEP 2: Filter by peer-to-peer performance
for availability in potential_matches:
    # 🔥 Check peer relationship for each potential match
    peer_check = await risk_engine.assess_peer_relationship(
        buyer_partner_id=requirement.buyer_partner_id,
        seller_partner_id=availability.seller_partner_id,
        commodity_id=requirement.commodity_id
    )
    
    if peer_check["status"] == "BLOCKED_FOR_THIS_PARTNER":
        # Skip this specific seller, continue with other matches
        logger.info(f"Skipping match with seller {availability.seller_partner_id}: {peer_check['reason']}")
        continue  # ✅ Try next seller
    
    if peer_check["status"] == "WARN":
        # Flag for manual review but include in matches
        match.peer_relationship_warning = peer_check["reason"]
        match.requires_manual_approval = True
    
    # Add to final matches list
    filtered_matches.append(match)

return filtered_matches
```

**Database Tables Needed:**
- `trades` table (historical transactions between partners)
- `invoices` table (payment tracking)
- `deliveries` table (delivery performance)
- `quality_claims` table (quality disputes)

**Files to Update:**
- `backend/modules/risk/risk_engine.py` - Add `assess_peer_relationship()` method
- Risk check runs BEFORE matching triggers
- Matching service filters out FAIL peer relationships

---

## 📊 SUMMARY (FINAL UPDATE)

**Total Issues:** 14 critical  
**Estimated Fix Time:** 10-11 hours  
**Files to Modify:** 19 files  
**Database Changes:** 4 columns added + 1 new table + 1 migration  

**Priority:**
1. 🔴 HIGH: Capability-based auth (#1, #12)
2. 🔴 HIGH: Peer-to-peer validation BEFORE matching (#14 - NEW)
3. 🔴 HIGH: Risk sequential flow (#13 - critical architecture)
4. 🔴 HIGH: EOD square-off (#2, #3, #8 - timezone)
5. 🔴 HIGH: Parameter validation (#10)
6. 🔴 HIGH: Unit conversion validation (#11)
7. 🟡 MEDIUM: Circular/wash trading (#4)
8. 🟡 MEDIUM: Mandatory payment terms (#5)
9. 🟡 MEDIUM: Buyer preferences (#9)
10. 🟢 LOW: Naming/UX (#6, #7)

---

## ✅ FINAL IMPLEMENTATION CHECKLIST (UPDATED)

### Phase 1: Database (1 hour)
- [ ] Add `eod_cutoff` to `availabilities` table
- [ ] Add `eod_cutoff` to `requirements` table
- [ ] Add `timezone` to `settings_locations` table
- [ ] Create `buyer_preferences` table
- [ ] Create migration script

### Phase 2: Models (1 hour)
- [ ] Update `Availability` model
- [ ] Update `Requirement` model
- [ ] Create `BuyerPreference` model
- [ ] Add timezone handling

### Phase 3: Risk Engine Refactor (3 hours) 🆕
- [ ] **Remove role-based terminology:**
  - [ ] Replace `buyer_data`/`seller_data` with generic `partner_a_data`/`partner_b_data`
  - [ ] Replace `seller_id` with `partner_id` in methods
  - [ ] Update method signatures to be role-agnostic
- [ ] **Fix circular trading logic (CRITICAL):**
  - [ ] Change from `func.date(created_at) == trade_date` to settlement-based
  - [ ] Check for UNSETTLED positions (status != COMPLETED/SETTLED)
  - [ ] Block if trying to sell commodity that hasn't been settled yet
- [ ] **Add wash trading prevention:**
  - [ ] Check for same-party reverse trades on same day
  - [ ] Block: Buy from Partner A at 9am → Sell to Partner A at 10am (same day)
  - [ ] Query both requirements and availabilities tables
- [ ] **Add peer-to-peer relationship validation (NEW - CRITICAL):**
  - [ ] Create `assess_peer_relationship()` method
  - [ ] Check outstanding amount between buyer-seller pair
  - [ ] Calculate peer payment performance (buyer's history with THIS seller)
  - [ ] Calculate peer delivery performance (seller's history with THIS buyer)
  - [ ] Calculate peer quality performance (quality disputes between pair)
  - [ ] Return composite peer relationship score (0-100)
  - [ ] FAIL if peer score < 50
- [ ] **Create unified comprehensive_check() method:**
  ```python
  async def comprehensive_check(
      entity_type: str,  # "requirement" or "availability"
      entity_id: UUID,
      partner_id: UUID,
      estimated_value: Decimal,
      counterparty_id: UUID = None  # For peer-to-peer check
  ) -> Dict[str, Any]:
      # Runs ALL checks:
      # 1. Credit limit
      # 2. Circular trading (settlement-based)
      # 3. Wash trading (same-party same-day)
      # 4. Party links
      # 5. Peer-to-peer relationship (if counterparty_id provided)
      # Returns comprehensive risk result
  ```
- [ ] Add RiskCheckFailedError exception
- [ ] Update all method signatures to accept partner_id (not buyer/seller)

### Phase 4: Service Layer Updates (2.5 hours)
- [ ] **RequirementService.create_requirement():**
  - [ ] Create requirement in DB first
  - [ ] Call risk_engine.comprehensive_check(requirement.id) SYNCHRONOUSLY
  - [ ] Update requirement with risk results
  - [ ] If FAIL, mark as BLOCKED and raise exception
  - [ ] If PASS/WARN, emit requirement.created event
  - [ ] Then trigger matching (direct call or event)
- [ ] **AvailabilityService.create_availability():**
  - [ ] Create availability in DB first
  - [ ] Call risk_engine.comprehensive_check(availability.id) SYNCHRONOUSLY
  - [ ] Update availability with risk results
  - [ ] If FAIL, mark as BLOCKED and raise exception
  - [ ] If PASS/WARN, emit availability.created event
  - [ ] Then trigger matching
- [ ] Add commodity parameter validation (in services)
- [ ] Add unit conversion validation (in services)
- [ ] Add buyer preference service methods
- [ ] Update timezone-aware EOD calculation

### Phase 5: Schemas (1 hour)
- [ ] Make payment/delivery/weighment terms MANDATORY
- [ ] Add buyer preference fields
- [ ] Rename pricing fields
- [ ] Add validation schemas

### Phase 6: Routes (1 hour)
- [ ] Add `@RequireCapability` to all endpoints
- [ ] **Remove ALL business logic from routes:**
  - [ ] Routes should ONLY: validate request schema, call service method, return response
  - [ ] No risk checks in routes
  - [ ] No validation logic in routes
  - [ ] No database queries in routes
- [ ] Update availability routes (clean architecture)
- [ ] Update requirement routes (clean architecture)
- [ ] Add buyer preference endpoints

### Phase 7: Cron Jobs (30 mins)
- [ ] Create EOD expiry job for availabilities
- [ ] Create EOD expiry job for requirements
- [ ] Schedule jobs

### Phase 8: Testing (1.5 hours)
- [ ] Test capability-based auth
- [ ] Test sequential flow: Create → Risk → Match
- [ ] Test risk FAIL blocks matching
- [ ] **Test peer-to-peer validation:**
  - [ ] Test outstanding amount blocking
  - [ ] Test poor payment history with specific seller blocks match
  - [ ] Test poor delivery history with specific buyer blocks match
  - [ ] Test quality dispute history affects matching
- [ ] Test parameter validation
- [ ] Test unit conversion validation
- [ ] Test buyer preferences
- [ ] Test EOD expiry
- [ ] Test circular + wash trading detection

---

## 📊 IMPLEMENTATION STATUS (Updated: Dec 1, 2025)

### ✅ COMPLETED

#### 1. Routes Cleanup & Capability-Based Auth
- ✅ **availability_routes.py**: 11 endpoints updated
  - Removed `get_seller_id_from_user()` and `get_buyer_id_from_user()` helpers
  - Added `@RequireCapability` decorators (TRADE_SELL, TRADE_BUY, etc.)
  - Fixed redis_client dependency injection
  - Deprecated POST /availabilities/search (HTTP 410 GONE)
- ✅ **requirement_routes.py**: 10 endpoints updated
  - Same cleanup as availability routes
  - Deprecated POST /requirements/search (HTTP 410 GONE)
  - Deprecated POST /requirements/search/by-intent (HTTP 410 GONE)
- ✅ Documentation: ROUTES_CLEANUP_COMPLETE.md created

#### 2. Instant Automatic Matching Implementation
- ✅ **Architectural Change**: Moved from marketplace listing to instant matching
  - **Old**: Users search/browse → Manual selection → Negotiation
  - **New**: Post requirement/availability → System instantly finds matches → Notifications sent
- ✅ **availability_service.py**: Added instant matching trigger (Step 13)
  - Calls `MatchingService.on_availability_created()` with HIGH priority
  - Synchronous matching after risk check passes
  - Event-driven fallback if instant matching fails
- ✅ **requirement_service.py**: Added instant matching trigger (Step 14)
  - Calls `MatchingService.on_requirement_created()` with HIGH priority
  - Instant automatic intent routing (DIRECT_BUY → Matching, NEGOTIATION → Queue, etc.)
- ✅ **Deprecated Endpoints**: 3 marketplace search endpoints return HTTP 410 GONE
  - POST /availabilities/search
  - POST /requirements/search
  - POST /requirements/search/by-intent
- ✅ Documentation: INSTANT_MATCHING_ARCHITECTURE.md created (comprehensive)

#### 3. Database Schema Updates
- ✅ **Migration Created**: 2025_12_01_add_eod_timezone_buyer_prefs.py
  - Added `eod_cutoff` (TIMESTAMP WITH TIME ZONE) to availabilities table
  - Added `eod_cutoff` (TIMESTAMP WITH TIME ZONE) to requirements table
  - Added `timezone` (VARCHAR 50) to settings_locations table
  - Created `buyer_preferences` table with JSONB columns (payment_terms, delivery_terms, weighment_terms)
- ✅ **Migration Applied**: `alembic upgrade head` executed successfully
  - Current version: 2025_12_01_eod_tz (head)
- ✅ **Merge Migration**: Created 5ac2637fb0dd_merge_migration_heads.py to resolve duplicate heads

### ⏳ NEXT PRIORITIES

#### Priority 1: Test Instant Matching Flow (IMMEDIATE)
Execute test cases from INSTANT_MATCHING_TEST_PLAN.md:
1. TC1: Buyer creates requirement → Instant match with availability
2. TC2: Seller creates availability → Instant match with requirement
3. TC3: Deprecated endpoints return HTTP 410 GONE
4. TC6: Multiple matches found and ranked by score
5. TC10: Performance test (verify < 1 second response time)

**Success Criteria:**
- ✅ Matches created instantly (< 1 second)
- ✅ WebSocket notifications sent to both parties
- ✅ Match scores calculated correctly (> 0.6 threshold)
- ✅ Deprecated endpoints return proper error messages

#### Priority 2: EOD Cron Jobs (HIGH)
Implement timezone-aware expiry management:
1. Create `backend/modules/trade_desk/cron/eod_expiry.py`
2. Expire availabilities past their eod_cutoff
3. Expire requirements past their eod_cutoff
4. Use location timezone for accurate calculations
5. Schedule cron jobs (every hour)

#### Priority 3: Validation Services (MEDIUM)
- ❌ Implement `_validate_quality_params()` in AvailabilityService
- ❌ Implement unit conversion validation
- ❌ Check CommodityParameter min/max values
- ❌ Add buyer preference service methods

#### Priority 4: Peer-to-Peer Validation (HIGH - BLOCKED)
**BLOCKER**: Requires trades/invoices/deliveries table schema
- Outstanding amount blocking
- Payment history validation with specific sellers
- Delivery history validation with specific buyers
- Quality dispute history affects matching

---

## 🚀 KEY ARCHITECTURAL CHANGE: INSTANT MATCHING

### Before (Marketplace Pattern)
```
Buyer → Search Availabilities → Browse Listings → Select Match → Start Negotiation
Seller → Post Availability → Wait for Buyers to Find It → Receive Offers
```

### After (Instant Automatic Matching)
```
Buyer → Post Requirement → INSTANT MATCH (AI-powered) → Notifications Sent → Direct P2P
Seller → Post Availability → INSTANT MATCH (AI-powered) → Notifications Sent → Direct P2P
```

**Benefits:**
- ✅ Real-time matching (< 1 second)
- ✅ No manual searching needed
- ✅ AI-optimized matches (scoring + risk)
- ✅ Direct peer-to-peer communication
- ✅ No stale inventory
- ✅ Better user experience

---

**🎯 IMPLEMENTATION IN PROGRESS**

See INSTANT_MATCHING_ARCHITECTURE.md for complete details.
See INSTANT_MATCHING_TEST_PLAN.md for testing strategy.
See ROUTES_CLEANUP_COMPLETE.md for routes changes.
```
