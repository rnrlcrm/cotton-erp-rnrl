# Instant Matching Test Plan

## Overview

This document outlines the testing plan for verifying the Instant Automatic Matching architecture works end-to-end.

---

## Test Environment Setup

### Prerequisites
- ✅ Database migrations applied (eod_cutoff, timezone, buyer_preferences)
- ✅ Services updated with instant matching triggers
- ✅ Deprecated search endpoints returning HTTP 410 GONE
- ✅ PostgreSQL and Redis containers running

### Test Data Requirements
1. **Test Commodity**: Cotton (commodity_id)
2. **Test Seller**: Business partner with TRADE_SELL capability
3. **Test Buyer**: Business partner with TRADE_BUY capability
4. **Test Location**: Valid location with timezone set
5. **Test Quality Params**: Compatible quality parameters

---

## Test Cases

### TC1: Buyer Creates Requirement → Instant Matching with Availability

**Objective:** Verify that when a buyer creates a requirement, the system instantly finds matching availabilities.

**Pre-conditions:**
1. Seller has created an ACTIVE availability:
   - commodity_id: Cotton
   - quantity: 500 bales
   - quality_params: {staple_length: 30mm, micronaire: 4.5, strength: 30}
   - price_per_unit: 48,000 INR
   - delivery_start_date: 2025-01-15
   - status: ACTIVE

**Test Steps:**
1. Buyer sends POST /requirements:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "quantity": 400,
     "unit": "BALES",
     "quality_requirements": {
       "staple_length": {"min": 28, "max": 32},
       "micronaire": {"min": 4.0, "max": 5.0},
       "strength": {"min": 28, "max": 35}
     },
     "max_price_per_unit": 50000,
     "delivery_date": "2025-01-20",
     "intent_type": "DIRECT_BUY",
     "urgency_level": "HIGH",
     "market_visibility": "PUBLIC"
   }
   ```

2. Measure API response time

**Expected Results:**
1. ✅ Requirement created successfully
2. ✅ API response time < 1000ms
3. ✅ Response includes instant matches or notification sent via WebSocket
4. ✅ Match score >= 0.6 (should be high due to compatible quality/price)
5. ✅ Match record created in database:
   - requirement_id: matches created requirement
   - availability_id: matches pre-existing availability
   - match_score: > 0.6
   - status: PENDING
6. ✅ WebSocket notification sent to buyer: "Match found!"
7. ✅ WebSocket notification sent to seller: "Your availability matched!"
8. ✅ Event emitted: `match.created`

**Verification Queries:**
```sql
-- Check match was created
SELECT id, requirement_id, availability_id, match_score, status, created_at
FROM matches
WHERE requirement_id = '{{requirement_id}}'
ORDER BY created_at DESC
LIMIT 1;

-- Check WebSocket notifications sent
SELECT id, user_id, type, message, created_at
FROM notifications
WHERE type = 'MATCH_FOUND'
AND user_id IN ('{{buyer_user_id}}', '{{seller_user_id}}')
ORDER BY created_at DESC;
```

---

### TC2: Seller Creates Availability → Instant Matching with Requirement

**Objective:** Verify that when a seller creates an availability, the system instantly finds matching requirements.

**Pre-conditions:**
1. Buyer has created an ACTIVE requirement:
   - commodity_id: Cotton
   - quantity: 600 bales
   - quality_requirements: {staple_length: 28-32mm, micronaire: 4.0-5.0}
   - max_price_per_unit: 52,000 INR
   - delivery_date: 2025-01-25
   - status: ACTIVE

**Test Steps:**
1. Seller sends POST /availabilities:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "quantity": 500,
     "unit": "BALES",
     "quality_params": {
       "staple_length": 30,
       "micronaire": 4.5,
       "strength": 30,
       "grade": "A"
     },
     "price_per_unit": 50000,
     "delivery_start_date": "2025-01-20",
     "delivery_end_date": "2025-01-30",
     "intent_type": "SPOT",
     "market_visibility": "PUBLIC"
   }
   ```

2. Measure API response time

**Expected Results:**
1. ✅ Availability created successfully
2. ✅ API response time < 1000ms
3. ✅ Instant match found with pre-existing requirement
4. ✅ Match score >= 0.6
5. ✅ Match record created in database
6. ✅ WebSocket notifications sent to both parties
7. ✅ Event emitted: `match.created`

**Verification:**
```sql
SELECT id, requirement_id, availability_id, match_score, status
FROM matches
WHERE availability_id = '{{availability_id}}'
ORDER BY created_at DESC
LIMIT 1;
```

---

### TC3: Deprecated Search Endpoint Returns 410 GONE

**Objective:** Verify that deprecated marketplace search endpoints return proper error messages.

**Test Steps:**
1. Send POST /availabilities/search:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "min_quantity": 100,
     "max_quantity": 1000
   }
   ```

2. Send POST /requirements/search:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "min_quantity": 100
   }
   ```

3. Send POST /requirements/search/by-intent:
   ```json
   {
     "intent_type": "DIRECT_BUY",
     "commodity_id": "{{cotton_commodity_id}}"
   }
   ```

**Expected Results:**
1. ✅ All endpoints return HTTP 410 GONE
2. ✅ Response body contains:
   - `error: "ENDPOINT_DEPRECATED"`
   - `message`: Explanation of instant matching
   - `recommendation`: Suggests correct endpoint
   - `reason`: Why marketplace pattern was deprecated
3. ✅ Endpoints marked as `deprecated=True` in OpenAPI docs

**Example Response:**
```json
{
  "detail": {
    "error": "ENDPOINT_DEPRECATED",
    "message": "Marketplace-style search is deprecated. Use INSTANT AUTOMATIC MATCHING instead.",
    "recommendation": "Post a requirement (POST /requirements) and receive instant matches via notifications.",
    "reason": "System moved from marketplace listing to real-time peer-to-peer matching for better efficiency and accuracy."
  }
}
```

---

### TC4: No Match Found (Below Threshold)

**Objective:** Verify system behavior when no compatible matches exist or scores are below threshold.

**Pre-conditions:**
1. Seller has availability with very specific quality params that won't match buyer requirements

**Test Steps:**
1. Buyer creates requirement with incompatible quality requirements:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "quantity": 1000,
     "quality_requirements": {
       "staple_length": {"min": 35, "max": 40},  // Very different from seller's 30mm
       "micronaire": {"min": 5.5, "max": 6.0}    // Very different from seller's 4.5
     },
     "max_price_per_unit": 45000,  // Below seller's asking price
     "delivery_date": "2025-01-05",  // Much sooner than seller can deliver
     "intent_type": "DIRECT_BUY"
   }
   ```

**Expected Results:**
1. ✅ Requirement created successfully
2. ✅ No matches created (score < 0.6 threshold)
3. ✅ No WebSocket notifications sent (no matches)
4. ✅ Event still emitted: `requirement.created` (for future matching)
5. ✅ API response indicates no instant matches found
6. ✅ System logs indicate "No compatible matches found"

**Verification:**
```sql
-- Should return 0 rows
SELECT COUNT(*)
FROM matches
WHERE requirement_id = '{{requirement_id}}';
```

---

### TC5: Risk Validation Fails

**Objective:** Verify that matches are not created when risk validation fails.

**Pre-conditions:**
1. Buyer has low credit score or outstanding disputes
2. Seller has compliance issues

**Test Steps:**
1. Create requirement/availability combination that would normally match well
2. Ensure one party has risk issues (mock or set in test data)

**Expected Results:**
1. ✅ Requirement/availability created successfully
2. ✅ Match scoring shows high compatibility (> 0.6)
3. ✅ Risk validation FAILS
4. ✅ No match record created
5. ✅ System logs: "Match failed risk validation"
6. ✅ Event emitted for manual review or alert to risk team

**Verification:**
```sql
-- Check risk validation logs
SELECT id, entity_type, entity_id, risk_level, validation_result, created_at
FROM risk_validations
WHERE entity_id IN ('{{requirement_id}}', '{{availability_id}}')
ORDER BY created_at DESC;
```

---

### TC6: Multiple Matches Found

**Objective:** Verify system behavior when multiple compatible matches exist.

**Pre-conditions:**
1. Seller 1 has availability: 500 bales @ 48,000 INR
2. Seller 2 has availability: 600 bales @ 49,000 INR
3. Seller 3 has availability: 400 bales @ 47,500 INR

**Test Steps:**
1. Buyer creates requirement:
   ```json
   {
     "commodity_id": "{{cotton_commodity_id}}",
     "quantity": 500,
     "quality_requirements": {...},  // Compatible with all 3
     "max_price_per_unit": 50000,
     "intent_type": "DIRECT_BUY"
   }
   ```

**Expected Results:**
1. ✅ Requirement created successfully
2. ✅ 3 match records created (one for each availability)
3. ✅ Matches ranked by score:
   - Seller 3: Highest score (best price, good quantity)
   - Seller 1: Medium score
   - Seller 2: Lower score (higher price)
4. ✅ All 3 sellers receive WebSocket notifications
5. ✅ Buyer receives notification: "3 matches found!"
6. ✅ Buyer can view all 3 matches sorted by score

**Verification:**
```sql
SELECT m.id, m.match_score, a.seller_id, a.price_per_unit, a.quantity
FROM matches m
JOIN availabilities a ON m.availability_id = a.id
WHERE m.requirement_id = '{{requirement_id}}'
ORDER BY m.match_score DESC;
```

---

### TC7: Intent-Based Automatic Routing

**Objective:** Verify that requirements/availabilities are automatically routed to correct engines based on intent.

**Test Steps:**
1. Create requirement with `intent_type: "DIRECT_BUY"` → Should route to Matching Engine
2. Create requirement with `intent_type: "NEGOTIATION"` → Should route to Negotiation Queue
3. Create requirement with `intent_type: "AUCTION_REQUEST"` → Should route to Reverse Auction
4. Create requirement with `intent_type: "PRICE_DISCOVERY_ONLY"` → Should route to Market Insights

**Expected Results:**
1. ✅ Each requirement created successfully
2. ✅ Routing record created with correct engine assignment:
   - DIRECT_BUY → `routing_engine: "MATCHING"`
   - NEGOTIATION → `routing_engine: "NEGOTIATION"`
   - AUCTION_REQUEST → `routing_engine: "REVERSE_AUCTION"`
   - PRICE_DISCOVERY_ONLY → `routing_engine: "MARKET_INSIGHTS"`
3. ✅ Instant matching only triggered for DIRECT_BUY intent
4. ✅ Other intents queued to respective engines

**Verification:**
```sql
SELECT r.id, r.intent_type, ir.routing_engine, ir.routing_status, ir.created_at
FROM requirements r
JOIN intent_routings ir ON r.id = ir.requirement_id
WHERE r.intent_type IN ('DIRECT_BUY', 'NEGOTIATION', 'AUCTION_REQUEST', 'PRICE_DISCOVERY_ONLY')
ORDER BY r.created_at DESC;
```

---

### TC8: Fallback to Event-Driven Matching

**Objective:** Verify that if instant synchronous matching fails, event-driven fallback works.

**Test Steps:**
1. Mock MatchingService to throw exception during instant matching
2. Create requirement
3. Verify event-driven fallback triggers

**Expected Results:**
1. ✅ Requirement created successfully (creation doesn't fail)
2. ✅ Instant matching throws exception (mocked)
3. ✅ Error logged: "Instant matching failed, fallback to event-driven"
4. ✅ Event emitted: `requirement.created`
5. ✅ Event subscriber (MatchingService) picks up event
6. ✅ Matching completed asynchronously (within 5-10 seconds)
7. ✅ Match notifications sent via WebSocket (delayed but delivered)

**Verification:**
```python
# In test code
mock_matching_service.on_requirement_created.side_effect = Exception("Timeout")

requirement = await create_requirement(...)

# Requirement still created
assert requirement.id is not None

# Event emitted
assert mock_event_bus.emit.called_with('requirement.created', ...)

# Wait for async matching
await asyncio.sleep(2)

# Match created by event-driven fallback
matches = await get_matches(requirement.id)
assert len(matches) > 0
```

---

### TC9: EOD Cutoff Handling

**Objective:** Verify that eod_cutoff field works correctly for expiry management.

**Pre-conditions:**
1. Location has timezone: "Asia/Kolkata"
2. Current time is before EOD cutoff

**Test Steps:**
1. Create availability with eod_cutoff: "18:00:00+05:30" (6 PM IST)
2. Verify availability is ACTIVE
3. Mock time to be after 18:00:00 IST
4. Run EOD cron job (when implemented)

**Expected Results:**
1. ✅ Availability created with eod_cutoff stored correctly
2. ✅ Availability remains ACTIVE before cutoff time
3. ✅ After EOD cutoff, cron job expires availability:
   - Status changed to EXPIRED
   - expired_at timestamp set
   - Match notifications sent if any pending matches
4. ✅ Expired availabilities excluded from matching

**Verification:**
```sql
-- Check eod_cutoff stored correctly
SELECT id, eod_cutoff, status, expired_at
FROM availabilities
WHERE id = '{{availability_id}}';

-- After cron job runs
SELECT id, status, expired_at
FROM availabilities
WHERE eod_cutoff < CURRENT_TIME
AND status = 'EXPIRED';
```

---

### TC10: Performance Test - Matching Latency

**Objective:** Verify instant matching meets performance SLA (< 1 second).

**Test Steps:**
1. Create 100 ACTIVE availabilities with varying quality params
2. Measure time to create requirement and receive matches
3. Repeat 10 times and calculate average

**Expected Results:**
1. ✅ Average API response time < 1000ms (p50)
2. ✅ p95 response time < 1500ms
3. ✅ p99 response time < 2000ms
4. ✅ All requests return within 3 seconds (max timeout)
5. ✅ Match scores calculated correctly (no degradation with 100 candidates)

**Performance Metrics:**
```python
import time
import statistics

response_times = []
for i in range(10):
    start = time.time()
    requirement = await create_requirement(...)
    end = time.time()
    response_times.append((end - start) * 1000)  # Convert to ms

print(f"Average: {statistics.mean(response_times):.2f}ms")
print(f"p50: {statistics.median(response_times):.2f}ms")
print(f"p95: {sorted(response_times)[int(len(response_times) * 0.95)]:.2f}ms")
print(f"Max: {max(response_times):.2f}ms")
```

---

## Integration Test Suite

### Test Execution Order
1. TC3 - Deprecated endpoints (no dependencies)
2. TC1 - Buyer creates requirement → instant match
3. TC2 - Seller creates availability → instant match
4. TC4 - No match found (threshold)
5. TC5 - Risk validation fails
6. TC6 - Multiple matches
7. TC7 - Intent routing
8. TC8 - Event-driven fallback
9. TC9 - EOD cutoff handling
10. TC10 - Performance test

### Test Data Cleanup
```sql
-- After each test, clean up
DELETE FROM matches WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM requirements WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM availabilities WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM notifications WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM risk_validations WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM intent_routings WHERE created_at > NOW() - INTERVAL '1 hour';
```

---

## Manual Testing Checklist

### API Testing (Postman/cURL)
- [ ] POST /requirements - Create requirement, verify instant matches
- [ ] POST /availabilities - Create availability, verify instant matches
- [ ] POST /availabilities/search - Verify HTTP 410 GONE
- [ ] POST /requirements/search - Verify HTTP 410 GONE
- [ ] POST /requirements/search/by-intent - Verify HTTP 410 GONE
- [ ] GET /requirements/buyer/my-requirements - Verify shows match status
- [ ] GET /availabilities/seller/my-availabilities - Verify shows match status

### WebSocket Testing
- [ ] Connect to /ws/matches/{user_id}
- [ ] Create requirement as buyer
- [ ] Verify "Match found!" notification received in real-time
- [ ] Create availability as seller
- [ ] Verify "Your availability matched!" notification received

### Database Verification
- [ ] Check `availabilities` table has `eod_cutoff` column
- [ ] Check `requirements` table has `eod_cutoff` column
- [ ] Check `settings_locations` table has `timezone` column
- [ ] Check `buyer_preferences` table exists with JSONB columns
- [ ] Check migration version: `alembic current` shows 2025_12_01_eod_tz

### Error Handling
- [ ] Create requirement without business_partner_id → 403 Forbidden
- [ ] Create availability without required capability → 403 Forbidden
- [ ] Invalid commodity_id → 404 Not Found
- [ ] Quality params validation fails → 400 Bad Request
- [ ] Risk check fails → Match not created, logged appropriately

---

## Acceptance Criteria

### ✅ Definition of Done
1. All 10 test cases pass
2. API response times meet SLA (< 1 second for instant matching)
3. Deprecated endpoints return HTTP 410 GONE with helpful messages
4. Database migrations applied and verified
5. WebSocket notifications working for real-time match delivery
6. No errors in application logs during normal operation
7. Documentation updated (INSTANT_MATCHING_ARCHITECTURE.md)
8. Code coverage > 80% for new instant matching logic

### 🚀 Success Metrics
- Match creation latency: < 500ms (p50), < 1000ms (p95)
- Match accuracy: > 90% of matches have score > 0.7
- User satisfaction: No manual searching needed
- System reliability: 99.9% uptime for matching service
- Event-driven fallback: 100% of failed instant matches recovered within 10s

---

## Next Steps After Testing

1. **Frontend Updates:**
   - Remove search forms and buttons
   - Add "Post Requirement"/"Post Availability" CTAs
   - Implement WebSocket listeners for match notifications
   - Update UI messaging to explain instant matching

2. **EOD Cron Jobs:**
   - Create cron job to expire availabilities at eod_cutoff
   - Create cron job to expire requirements at eod_cutoff
   - Use location.timezone for accurate time calculations

3. **Monitoring & Alerts:**
   - Prometheus metrics for matching latency
   - Alert if p95 latency > 1 second
   - Dashboard for match success rate, avg scores
   - Logging for failed matches, risk validations

4. **Documentation:**
   - Update API docs (OpenAPI/Swagger)
   - User guide: "How Instant Matching Works"
   - Developer guide: "Matching Algorithm Deep Dive"
   - Troubleshooting guide

5. **Performance Optimization:**
   - Review database indexes
   - Optimize matching queries
   - Implement Redis caching for commodity/quality metadata
   - Consider batch match creation for multiple candidates
