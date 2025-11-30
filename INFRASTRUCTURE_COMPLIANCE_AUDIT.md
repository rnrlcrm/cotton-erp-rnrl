# INFRASTRUCTURE COMPLIANCE AUDIT - COMPLETE SYSTEM REVIEW

**Date**: 2025-11-30  
**Auditor**: Architecture Team  
**Scope**: ALL modules must comply with 15-year infrastructure standards

---

## 🎯 AUDIT CRITERIA

Every module MUST have:

1. ✅ **Idempotency** - All POST/PUT/PATCH endpoints
2. ✅ **Service Layer** - NO direct DB queries in routers
3. ✅ **Circuit Breaker** - External API calls
4. ✅ **Authentication** - JWT validation
5. ✅ **Capability Auth** - Beyond role checks
6. ✅ **Outbox Pattern** - Event publishing
7. ✅ **Error Handling** - Standard exceptions

---

## 📋 MODULE AUDIT RESULTS

### 1. AUTH MODULE (`backend/modules/auth/router.py`)

**Endpoints**: 6 (1 POST, 2 GET, 3 DELETE)

| Criteria | Status | Notes |
|----------|--------|-------|
| Idempotency | ❌ MISSING | `/refresh` POST has NO idempotency header |
| Service Layer | ⚠️ PARTIAL | Uses SessionService BUT router has business logic |
| Circuit Breaker | ✅ N/A | No external APIs |
| Authentication | ✅ PASS | Uses `get_current_user` |
| Capability Auth | ❌ MISSING | No capability checks beyond auth |
| Outbox Pattern | ❌ MISSING | No event publishing |
| Error Handling | ✅ PASS | Standard HTTPException |

**REQUIRED FIXES**:
```python
# 1. Add idempotency to /refresh
@router.post("/refresh")
async def refresh_token(
    body: RefreshTokenRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),  # ADD THIS
    ...
)

# 2. Move business logic to service
# Current: Router has session lookup logic
# Fix: Move to SessionService.logout_current_session()
```

---

### 2. PARTNERS MODULE (`backend/modules/partners/router.py`)

**Status**: CHECKING...

---

### 3. COMMODITIES MODULE (`backend/modules/settings/commodities/router.py`)

**Status**: CHECKING...

---

### 4. LOCATIONS MODULE (`backend/modules/settings/locations/router.py`)

**Status**: CHECKING...

---

### 5. ORGANIZATION MODULE (`backend/modules/settings/organization/router.py`)

**Status**: CHECKING...

---

### 6. AVAILABILITY MODULE (`backend/modules/trade_desk/routes/availability_routes.py`)

**Status**: ✅ COMPLIANT (recently fixed)

| Criteria | Status | Notes |
|----------|--------|-------|
| Idempotency | ✅ PASS | `create_availability` has idempotency header + docs |
| Service Layer | ✅ PASS | Uses AvailabilityService |
| Circuit Breaker | ✅ N/A | No external APIs |
| Authentication | ✅ PASS | Uses `get_current_user` |
| Capability Auth | ❌ MISSING | No capability framework |
| Outbox Pattern | ❌ MISSING | Events published directly |
| Error Handling | ✅ PASS | Standard HTTPException |

---

### 7. REQUIREMENT MODULE (`backend/modules/trade_desk/routes/requirement_routes.py`)

**Status**: ✅ COMPLIANT (recently fixed)

| Criteria | Status | Notes |
|----------|--------|-------|
| Idempotency | ✅ PASS | `create_requirement` has idempotency header + docs |
| Service Layer | ✅ PASS | Uses RequirementService |
| Circuit Breaker | ✅ N/A | No external APIs |
| Authentication | ✅ PASS | Uses `get_current_user` |
| Capability Auth | ❌ MISSING | No capability framework |
| Outbox Pattern | ❌ MISSING | Events published directly |
| Error Handling | ✅ PASS | Standard HTTPException |

---

### 8. MATCHING MODULE (`backend/modules/trade_desk/routes/matching_router.py`)

**Status**: CHECKING...

---

## 🔴 CRITICAL GAPS (SYSTEM-WIDE)

### 1. Outbox Pattern NOT Implemented

**Problem**: Events published directly to Pub/Sub WITHOUT transactional safety.

**Risk**: Lost events if DB commits but Pub/Sub publish fails.

**Required Implementation**:
```sql
-- Create outbox table
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_version INT NOT NULL DEFAULT 1,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_outbox_unpublished (published, created_at) WHERE NOT published
);
```

```python
# Event publishing flow
async def publish_event(event: BaseEvent, db: AsyncSession):
    # 1. Write to outbox (SAME transaction as business logic)
    outbox_record = EventOutbox(
        event_type=event.event_type,
        aggregate_id=event.aggregate_id,
        payload=event.dict()
    )
    db.add(outbox_record)
    await db.commit()  # ✅ Transactional safety
    
    # 2. Background worker publishes from outbox
    # (separate process, polls every 1 second)
```

---

### 2. Capability-Based Authorization NOT Implemented

**Problem**: Only role-based checks (INTERNAL, EXTERNAL, SUPER_ADMIN).

**Risk**: Cannot enforce fine-grained permissions (e.g., "can approve trades > ₹1Cr").

**Required Implementation**:
```python
# Capability framework
class Capability(str, Enum):
    # Availability capabilities
    CAN_POST_AVAILABILITY = "availability:post"
    CAN_EDIT_OWN_AVAILABILITY = "availability:edit:own"
    CAN_EDIT_ANY_AVAILABILITY = "availability:edit:any"
    CAN_APPROVE_AVAILABILITY = "availability:approve"
    
    # Requirement capabilities  
    CAN_POST_REQUIREMENT = "requirement:post"
    CAN_APPROVE_REQUIREMENT = "requirement:approve"
    
    # Trade capabilities
    CAN_INITIATE_TRADE = "trade:initiate"
    CAN_APPROVE_TRADE = "trade:approve"
    CAN_APPROVE_TRADE_ABOVE_1CR = "trade:approve:high_value"
    CAN_SETTLE_TRADE = "trade:settle"
    
    # Partner capabilities
    CAN_ONBOARD_PARTNER = "partner:onboard"
    CAN_APPROVE_PARTNER = "partner:approve"
    CAN_VERIFY_KYC = "partner:kyc:verify"

# Capability checks in services
class AvailabilityService:
    async def create_availability(self, request, user_id):
        # Check capability
        if not await self.has_capability(user_id, Capability.CAN_POST_AVAILABILITY):
            raise HTTPException(403, "Missing capability: availability:post")
        
        # Business logic...
```

---

### 3. Pub/Sub DLQ NOT Configured

**Problem**: Failed event deliveries have no retry or dead-letter handling.

**Required Implementation**:
```python
# GCP Pub/Sub configuration
from google.cloud import pubsub_v1

# Create DLQ topic
dlq_topic = publisher.create_topic(
    request={"name": "projects/cotton-erp/topics/events-dlq"}
)

# Create subscription with retry policy
subscriber.create_subscription(
    request={
        "name": "projects/cotton-erp/subscriptions/events-sub",
        "topic": "projects/cotton-erp/topics/events",
        "dead_letter_policy": {
            "dead_letter_topic": "projects/cotton-erp/topics/events-dlq",
            "max_delivery_attempts": 5
        },
        "retry_policy": {
            "minimum_backoff": {"seconds": 10},
            "maximum_backoff": {"seconds": 600}
        }
    }
)

# Monitor DLQ
async def monitor_dlq():
    # Alert if DLQ has > 100 messages
    dlq_count = await get_dlq_message_count()
    if dlq_count > 100:
        send_alert("DLQ threshold exceeded", dlq_count)
```

---

## 📝 DETAILED MODULE AUDITS

(In progress - checking each module systematically...)

---

## ✅ ACTION ITEMS (PRIORITY ORDER)

### P0 - CRITICAL (Must fix before production)
1. [ ] Implement outbox pattern (ALL modules)
2. [ ] Configure Pub/Sub DLQ + retry policies
3. [ ] Add capability-based authorization framework

### P1 - HIGH (Fix within 1 week)
4. [ ] Add idempotency to auth/refresh endpoint
5. [ ] Audit partners module
6. [ ] Audit commodities module
7. [ ] Audit locations module
8. [ ] Audit organization module
9. [ ] Audit matching module

### P2 - MEDIUM (Fix within 2 weeks)
10. [ ] Move router business logic to services
11. [ ] Add circuit breakers to any remaining external APIs
12. [ ] Create capability migration guide

---

**AUDIT IN PROGRESS...**
