# Infrastructure Compliance Audit - All Modules

**Date**: 2025-11-30  
**Status**: IN PROGRESS  
**Target**: 100% compliance across ALL modules

---

## Compliance Requirements

Every module MUST have:

1. ✅ **Idempotency** - All POST/PUT endpoints with `Idempotency-Key` header
2. ✅ **Service Layer** - NO direct DB queries in routers  
3. ✅ **Circuit Breaker** - All external API calls wrapped
4. ✅ **Outbox Pattern** - All events go through outbox table
5. ✅ **Capability Auth** - Permission checks beyond roles
6. ✅ **PII Sanitization** - Auto-enabled in logs
7. ✅ **Event Versioning** - All events versioned
8. ✅ **Error Handling** - Standard HTTP exceptions

---

## Module Audit Status

### ✅ Infrastructure Layer (DONE)
- [x] Idempotency middleware created
- [x] Circuit breaker patterns created
- [x] PII filter created
- [x] Event versioning created
- [x] AI orchestrator created
- [x] GCP observability created
- [x] Tests passing (10/11)

### 🔴 Auth Module (`backend/api/v1/routers/auth.py`)
- [ ] **Idempotency**: Missing on `/refresh`, `/reset-password`, `/verify-email`
- [x] **Service Layer**: SessionService exists ✅
- [ ] **Outbox**: No outbox for auth events
- [ ] **Capability Auth**: Role-based only (no capabilities)
- [ ] **Events**: `user.logged_in`, `user.logged_out`, `password.reset` not versioned

**Action Required**: Add idempotency + outbox pattern

---

### 🔴 Partners Module (`backend/modules/partners/router.py`)
- [ ] **Idempotency**: 11 POST endpoints WITHOUT Idempotency-Key:
  - `/onboarding/start`
  - `/onboarding/{id}/documents`
  - `/onboarding/{id}/submit`
  - `/{id}/approve`
  - `/{id}/reject`
  - `/{id}/amendments`
  - `/{id}/employees`
  - `/{id}/kyc/renew`
  - `/{id}/locations`
  - `/{id}/vehicles`
  - `/{id}/bank-accounts`

- [x] **Service Layer**: PartnerService, PartnerAnalyticsService ✅
- [x] **Circuit Breaker**: GST API has @api_circuit_breaker ✅
- [ ] **Outbox**: Direct event emission (no outbox)
- [ ] **Capability Auth**: No capability checks (role-based only)
- [ ] **Events**: 15+ events not in outbox pattern

**Action Required**: Add idempotency to ALL POST endpoints + outbox pattern

---

### 🔴 Commodities Module (`backend/modules/settings/commodities/router.py`)
- [ ] **Idempotency**: 28 POST/PUT endpoints WITHOUT Idempotency-Key:
  - `/commodities` (POST)
  - `/commodities/{id}` (PUT)
  - `/varieties` (POST/PUT)
  - `/grades` (POST/PUT)
  - `/quality-parameters` (POST/PUT)
  - `/trade-types` (POST/PUT)
  - `/pricing-units` (POST/PUT)
  - ... and 19 more

- [x] **Service Layer**: CommodityService exists ✅
- [ ] **Outbox**: Direct event emission
- [ ] **Capability Auth**: No capability checks
- [ ] **Events**: Not versioned

**Action Required**: Add idempotency to ALL 28 endpoints + outbox pattern

---

### 🔴 Locations Module (`backend/modules/settings/locations/router.py`)
- [ ] **Idempotency**: 8 POST/PUT endpoints missing Idempotency-Key
- [x] **Service Layer**: LocationService exists ✅
- [ ] **Outbox**: Direct event emission
- [ ] **Capability Auth**: No capability checks

**Action Required**: Add idempotency + outbox pattern

---

### 🔴 Organization Module (`backend/modules/organization/router.py`)
- [ ] **Idempotency**: Missing on org creation/update
- [ ] **Service Layer**: Mixed (some queries in router)
- [ ] **Outbox**: No event outbox
- [ ] **Capability Auth**: No capability checks

**Action Required**: Full refactor needed

---

### 🟡 Availability Module (`backend/modules/trade_desk/routes/availability_routes.py`)
- [x] **Idempotency**: create_availability has Idempotency-Key ✅
- [ ] **Idempotency**: Missing on 12 other POST/PUT endpoints:
  - `/reserve`
  - `/release`
  - `/mark-sold`
  - `/{id}/approve`
  - `/{id}/reject`
  - ... and 7 more

- [x] **Service Layer**: AvailabilityService ✅
- [ ] **Outbox**: Direct event emission
- [ ] **Capability Auth**: No capability checks

**Action Required**: Add idempotency to remaining 12 endpoints + outbox pattern

---

### 🟡 Requirement Module (`backend/modules/trade_desk/routes/requirement_routes.py`)
- [x] **Idempotency**: create_requirement has Idempotency-Key ✅
- [ ] **Idempotency**: Missing on 10 other POST/PUT endpoints:
  - `/{id}/ai-adjust`
  - `/{id}/cancel`
  - `/{id}/fulfill`
  - ... and 7 more

- [x] **Service Layer**: RequirementService ✅
- [ ] **Outbox**: Direct event emission
- [ ] **Capability Auth**: No capability checks

**Action Required**: Add idempotency to remaining 10 endpoints + outbox pattern

---

### 🔴 Matching Module (`backend/modules/trade_desk/routes/matching_router.py`)
- [ ] **Idempotency**: All POST endpoints missing Idempotency-Key
- [x] **Service Layer**: MatchingEngineService ✅
- [x] **Circuit Breaker**: RiskEngine has circuit breaker ✅
- [ ] **Outbox**: Direct event emission
- [ ] **Capability Auth**: No capability checks

**Action Required**: Add idempotency + outbox pattern

---

## Missing Infrastructure Components

### 1. Outbox Pattern (CRITICAL)
**Status**: NOT IMPLEMENTED  
**Impact**: Event delivery not guaranteed, no transaction safety

**Required**:
```sql
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_version INT NOT NULL,
    payload JSONB NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    processing_attempts INT DEFAULT 0,
    last_error TEXT,
    status VARCHAR(20) DEFAULT 'pending' -- pending, processing, published, failed
);

CREATE INDEX idx_outbox_status ON event_outbox(status, created_at);
CREATE INDEX idx_outbox_aggregate ON event_outbox(aggregate_type, aggregate_id);
```

**Worker Required**:
- Polls outbox every 100ms
- Publishes to GCP Pub/Sub
- Marks as published
- Retries on failure

---

### 2. GCP Pub/Sub DLQ (CRITICAL)
**Status**: NOT CONFIGURED  
**Impact**: Failed events lost, no retry mechanism

**Required**:
```bash
# Create DLQ topic
gcloud pubsub topics create cotton-erp-events-dlq

# Create DLQ subscription
gcloud pubsub subscriptions create cotton-erp-events-dlq-sub \
  --topic cotton-erp-events-dlq \
  --ack-deadline=600

# Update main subscription with DLQ
gcloud pubsub subscriptions update cotton-erp-events-sub \
  --dead-letter-topic=cotton-erp-events-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d
```

---

### 3. Capability-Based Authorization (HIGH PRIORITY)
**Status**: NOT IMPLEMENTED  
**Impact**: Only role-based auth, not fine-grained enough

**Required**:
```python
# Capability definitions
CAPABILITIES = {
    # Availability capabilities
    "availability.create": ["SELLER", "TRADER"],
    "availability.approve": ["INTERNAL_MANAGER", "INTERNAL_DIRECTOR"],
    "availability.view_all": ["INTERNAL"],
    
    # Requirement capabilities  
    "requirement.create": ["BUYER", "TRADER"],
    "requirement.approve": ["INTERNAL_MANAGER", "INTERNAL_DIRECTOR"],
    
    # Trade capabilities
    "trade.approve": ["INTERNAL_MANAGER"],
    "trade.settle": ["INTERNAL_FINANCE"],
    "trade.cancel": ["INTERNAL_DIRECTOR"],
    
    # Partner capabilities
    "partner.approve": ["INTERNAL_MANAGER", "INTERNAL_DIRECTOR"],
    "partner.reject": ["INTERNAL_MANAGER", "INTERNAL_DIRECTOR"],
    "partner.suspend": ["INTERNAL_DIRECTOR"],
}

# Usage
@require_capability("availability.approve")
async def approve_availability(...):
    ...
```

---

## Implementation Plan

### Phase 1: Outbox Pattern (3 days)
**Priority**: CRITICAL  
**Owner**: TBD

1. Create outbox table migration
2. Implement OutboxRepository
3. Implement OutboxWorker (background task)
4. Update EventEmitter to use outbox
5. Configure GCP Pub/Sub DLQ
6. Add monitoring/alerts

**Files to create**:
- `backend/core/outbox/models.py`
- `backend/core/outbox/repository.py`
- `backend/core/outbox/worker.py`
- `backend/core/events/emitter.py` (UPDATE)
- `alembic/versions/XXX_create_outbox_table.py`

---

### Phase 2: Capability Authorization (2 days)
**Priority**: HIGH  
**Owner**: TBD

1. Define capability matrix
2. Implement CapabilityChecker
3. Add `@require_capability` decorator
4. Update all routers to use capability checks
5. Add tests

**Files to create**:
- `backend/core/auth/capabilities.py`
- `backend/core/auth/decorators.py`
- `backend/tests/unit/test_capabilities.py`

---

### Phase 3: Idempotency Rollout (5 days)
**Priority**: HIGH  
**Owner**: TBD

**Add Idempotency-Key to 80+ endpoints**:
- Day 1: Auth (3) + Partners (11) = 14 endpoints
- Day 2: Commodities (28) = 28 endpoints
- Day 3: Locations (8) + Organization (6) = 14 endpoints
- Day 4: Availability (12) + Requirement (10) = 22 endpoints
- Day 5: Matching (6) + Testing = 6 endpoints

**Total**: 84 endpoints

---

### Phase 4: Testing & Validation (2 days)
**Priority**: CRITICAL  
**Owner**: TBD

1. E2E tests for outbox pattern
2. E2E tests for capability auth
3. Load tests for idempotency
4. GCP Pub/Sub DLQ tests
5. Rollback plan

---

## Timeline

**Total Duration**: 12 days  
**Start Date**: 2025-12-01  
**Target Completion**: 2025-12-12

| Phase | Duration | Dependencies | Status |
|-------|----------|-------------|--------|
| Outbox Pattern | 3 days | None | NOT STARTED |
| Capability Auth | 2 days | None | NOT STARTED |
| Idempotency Rollout | 5 days | Outbox complete | NOT STARTED |
| Testing & Validation | 2 days | All above | NOT STARTED |

---

## Success Criteria

- [ ] 100% of POST/PUT endpoints have Idempotency-Key
- [ ] 100% of events go through outbox table
- [ ] GCP Pub/Sub DLQ configured and monitored
- [ ] All critical operations have capability checks
- [ ] All tests passing (unit + E2E)
- [ ] Zero event loss in production
- [ ] Monitoring/alerts configured

---

## Blockers

1. **Outbox Pattern** - Requires DB migration (risk: data loss)
2. **Capability Auth** - Requires capability matrix definition (who decides?)
3. **Idempotency** - 84 endpoints (time-consuming, error-prone)
4. **GCP Pub/Sub** - Requires GCP project setup (credentials?)

---

**Status**: READY TO START  
**Next Action**: Get approval + assign owners + start Phase 1 (Outbox Pattern)
