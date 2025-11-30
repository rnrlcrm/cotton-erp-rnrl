# Infrastructure Compliance Implementation Plan

## ✅ COMPLETED PHASES

### Phase 1: Outbox Pattern Foundation ✅
- Created `event_outbox` table
- Implemented `OutboxRepository` for transactional event storage
- Implemented `OutboxWorker` for async Pub/Sub publishing
- Updated `EventEmitter` to write to outbox (transactional safety)
- Migration: `001_outbox`

### Phase 2: Pub/Sub DLQ Configuration ✅  
- Created `setup_pubsub_dlq.py` configuration script
- Main topic: `cotton-erp-events`
- DLQ topic: `cotton-erp-events-dlq`
- Subscription with 5-retry exponential backoff policy
- DLQ subscription for ops team monitoring

### Phase 3: Capability Authorization Framework ✅
- Defined 60+ capabilities across all modules
- Created capability models: `Capability`, `UserCapability`, `RoleCapability`
- Implemented `CapabilityService` for authorization checks
- Created `@RequireCapability` decorator for route protection
- Migrations: `002_capabilities`, `003_seed_capabilities`

### Phase 4: Auth Module Full Compliance ✅
- `/auth/refresh` - Added idempotency_key header
- `/auth/sessions/{id}` - Added idempotency + AUTH_MANAGE_SESSIONS capability
- `/auth/sessions/all` - Added idempotency + AUTH_MANAGE_SESSIONS capability  
- `/auth/logout` - Added idempotency header
- **Compliance: 4/4 endpoints (100%)**

---

## 🚧 REMAINING WORK

### Phase 5: Partners Module (11 endpoints)
**File:** `backend/modules/partners/router.py`

| Endpoint | Method | Idempotency | Capability Required | Priority |
|----------|--------|-------------|---------------------|----------|
| `/onboarding/start` | POST | ❌ | PARTNER_CREATE | HIGH |
| `/onboarding/{app_id}/documents` | POST | ❌ | PARTNER_CREATE | HIGH |
| `/onboarding/{app_id}/submit` | POST | ❌ | PARTNER_CREATE | HIGH |
| `/partners/{partner_id}/approve` | POST | ❌ | PARTNER_APPROVE | CRITICAL |
| `/partners/{partner_id}/reject` | POST | ❌ | PARTNER_APPROVE | CRITICAL |
| `/partners/{partner_id}/amendments` | POST | ❌ | PARTNER_UPDATE | MEDIUM |
| `/partners/{partner_id}/employees` | POST | ❌ | PARTNER_CREATE | MEDIUM |
| `/partners/{partner_id}/kyc/renew` | POST | ❌ | PARTNER_UPDATE | HIGH |
| `/partners/{partner_id}/locations` | POST | ❌ | PARTNER_UPDATE | MEDIUM |
| `/partners/{partner_id}/vehicles` | POST | ❌ | PARTNER_UPDATE | MEDIUM |
| `/partners/{partner_id}/bank-accounts` | POST | ❌ | PARTNER_MANAGE_BANK_ACCOUNTS | HIGH |

**Changes Required:**
1. Add `from fastapi import Header` import
2. Add `from backend.core.auth.capabilities import Capabilities, RequireCapability` import
3. Add `idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")` parameter to each POST endpoint
4. Add `_check: None = Depends(RequireCapability(Capabilities.PARTNER_XXX))` to each endpoint
5. Pass `idempotency_key` to service layer methods
6. Update service layer to handle idempotency and emit events through outbox

### Phase 6: Commodities Module (28 endpoints)
**File:** `backend/modules/settings/commodities/router.py`

**Endpoints to Update:**
- All POST/PUT operations for commodity CRUD
- Specification management endpoints
- HSN code management endpoints
- Price update endpoints (CRITICAL - financial data)

**Required Capabilities:**
- `COMMODITY_CREATE`
- `COMMODITY_UPDATE`
- `COMMODITY_UPDATE_PRICE`
- `COMMODITY_MANAGE_SPECIFICATIONS`
- `COMMODITY_MANAGE_HSN`

### Phase 7: Locations Module (8 endpoints)
**File:** `backend/modules/settings/locations/router.py`

**Changes Required:**
- Add idempotency to all POST/PUT operations
- Add capability checks using `LOCATION_CREATE`, `LOCATION_UPDATE`, `LOCATION_DELETE`
- Update service layer for event emission through outbox

### Phase 8: Organization Module (6 endpoints)
**File:** `backend/modules/settings/organization/router.py`

**Changes Required:**
- Add idempotency to organization CRUD operations
- Add capability checks: `ORG_CREATE`, `ORG_UPDATE`, `ORG_MANAGE_USERS`, `ORG_MANAGE_ROLES`
- Update service layer for event emission through outbox

### Phase 9: Availability Module (12 remaining endpoints)
**File:** `backend/modules/trade_desk/routes/availability_routes.py`

**Status:** 1/13 endpoints compliant (`create_availability` has idempotency)

**Remaining Endpoints:**
- `/reserve` - AVAILABILITY_RESERVE
- `/release` - AVAILABILITY_RELEASE
- `/mark-sold` - AVAILABILITY_MARK_SOLD
- `/approve` - AVAILABILITY_APPROVE
- `/reject` - AVAILABILITY_REJECT
- `/cancel` - AVAILABILITY_CANCEL
- And 6 more...

### Phase 10: Requirement Module (10 remaining endpoints)
**File:** `backend/modules/trade_desk/routes/requirement_routes.py`

**Status:** 1/11 endpoints compliant (`create_requirement` has idempotency)

**Remaining Endpoints:**
- `/ai-adjust` - REQUIREMENT_AI_ADJUST
- `/cancel` - REQUIREMENT_CANCEL
- `/fulfill` - REQUIREMENT_FULFILL
- `/approve` - REQUIREMENT_APPROVE
- `/reject` - REQUIREMENT_REJECT
- And 5 more...

### Phase 11: Matching Module (6 endpoints)
**File:** `backend/modules/trade_desk/matching/router.py` (if exists)

**Changes Required:**
- Add capability checks: `MATCHING_EXECUTE`, `MATCHING_APPROVE_MATCH`, `MATCHING_REJECT_MATCH`
- Add idempotency to all match execution endpoints
- Update service layer for event emission through outbox

---

## 📋 IMPLEMENTATION CHECKLIST

### For EACH Endpoint:
- [ ] Add `idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")` parameter
- [ ] Add `_check: None = Depends(RequireCapability(Capabilities.XXX))` dependency
- [ ] Update docstring to document idempotency and capability requirements
- [ ] Pass `idempotency_key` to service method
- [ ] Update service method to check idempotency before processing
- [ ] Ensure service emits events through `EventEmitter` (uses outbox)
- [ ] Add integration test covering idempotency behavior
- [ ] Add integration test covering capability authorization

### Service Layer Updates (CRITICAL):
- [ ] All service methods must accept `idempotency_key: Optional[str]` parameter
- [ ] Implement idempotency check using Redis/DB before processing
- [ ] Emit events using `EventEmitter` (automatically uses outbox)
- [ ] Return cached result if idempotency key matches previous request

### Testing Requirements:
- [ ] Test idempotency: Same key = same result, no duplicate DB writes
- [ ] Test capability auth: Missing capability = 403 Forbidden
- [ ] Test outbox pattern: Events written to `event_outbox` table
- [ ] Test DLQ: Failed Pub/Sub publish retries 5 times, then DLQ

---

## 🎯 CURRENT STATUS

**Infrastructure Foundation:** ✅ 100% Complete
- Outbox Pattern: ✅ Implemented
- Pub/Sub DLQ: ✅ Configured
- Capabilities: ✅ 60+ defined
- Auth Module: ✅ 100% compliant (4/4)

**Module Compliance:**
- Auth: ✅ 4/4 (100%)
- Partners: ❌ 0/11 (0%)
- Commodities: ❌ 0/28 (0%)
- Locations: ❌ 0/8 (0%)
- Organization: ❌ 0/6 (0%)
- Availability: ⚠️ 1/13 (7.7%)
- Requirement: ⚠️ 1/11 (9.1%)
- Matching: ❌ 0/6 (0%)

**Overall Endpoint Compliance:** 6/87 (6.9%)

---

## ⚡ NEXT IMMEDIATE STEPS

1. **Phase 5: Partners Module (11 endpoints)** - Start here
2. **Phase 6: Commodities Module (28 endpoints)** - Largest module
3. **Phase 9-10: Complete Availability + Requirement** - Already partially done
4. **Phase 7-8: Locations + Organization** - Smaller modules
5. **Phase 11: Matching Module** - Final module

**Estimated Remaining Time:** 
- Partners: 3 hours
- Commodities: 5 hours
- Availability/Requirement: 2 hours (already started)
- Locations/Organization: 2 hours
- Matching: 1 hour
- Testing: 3 hours
- **Total: ~16 hours of focused work**

---

## 🔧 AUTOMATION OPPORTUNITIES

To speed up compliance implementation, consider:

1. **Code Generator Script:** Generate idempotency + capability boilerplate
2. **Bulk Find/Replace:** Use regex to add common patterns
3. **Service Layer Template:** Standardize idempotency checking logic
4. **Test Template:** Auto-generate compliance tests for each endpoint

**Recommendation:** Implement Partners module manually as template, then use automation for remaining modules.
