# MATCHING ENGINE - FINAL APPROVAL REQUEST ✅

**Date:** 2025-11-25  
**Version:** 2.0 (Location-First, Event-Driven, Risk-Integrated)  
**Estimated Effort:** 10 days | ~8,600 lines  
**Status:** 🟡 AWAITING YOUR APPROVAL

---

## 🎯 WHAT WILL BE BUILT

A **real-time, location-first intelligent matching engine** that automatically matches buyers with sellers.

### Matching Criteria (in order):

1. ✅ **Location** (HARD FILTER - runs FIRST, before any scoring)
2. ✅ **Quality** compatibility (40% weight)
3. ✅ **Price** competitiveness (30% weight)
4. ✅ **Delivery** logistics (15% weight)
5. ✅ **Risk** assessment (15% weight)

---

## 🔥 CRITICAL UPDATES FROM YOUR REQUIREMENTS

All your recommended iterations have been incorporated:

### ✅ 1. Location-First Hard Filter (EXPLICIT)
- Location check runs **BEFORE** any scoring
- Database query filters by location **BEFORE** fetching candidates
- If location doesn't match → skip immediately (no scoring wasted)
- Pseudocode implemented:
  ```python
  if not location_match(requirement, availability):
      continue  # hard reject, skip
  ```

### ✅ 2. Event-Driven Matching (NO CRON as primary)
- **Primary:** Event triggers (requirement.created, availability.created, risk_status.changed)
- **Safety Net:** Optional 15-30s cron as fallback ONLY
- Real-time response < 1 second

### ✅ 3. Risk WARN Semantics (CONSISTENT)
- **PASS** (≥80): risk_score = 1.0, no penalty
- **WARN** (60-79): risk_score = 0.5 + **10% global penalty**
- **FAIL** (<60): Block match (score = 0.0)
- Single penalty approach (not duplicated)

### ✅ 4. Location-Centric Notifications + Rate Limits
- Notify ONLY sellers in location-matched pool
- Rate limiting: Max 1 push per seller per minute (debounce)
- User opt-in/opt-out preferences
- Top N configurable (default 5)

### ✅ 5. Atomic Allocation & Optimistic Locking
- Row-level DB locking for concurrent reservations
- Version control prevents double-allocation
- Tests for race conditions included
- Transaction rollback on conflict

### ✅ 6. Duplicate Detection with Exact Tolerances
- Time window: **5 minutes** (configurable)
- Similarity threshold: **95%** param match (configurable)
- Config constants: `DUPLICATE_TIME_WINDOW_MINUTES`, `DUPLICATE_SIMILARITY_THRESHOLD`

### ✅ 7. Per-Commodity Configurable Thresholds
- `min_score_threshold` per commodity (default 0.6)
- Scoring weights per commodity (default 40/30/15/15)
- Runtime tunable via admin settings
- Example: GOLD 0.7, WHEAT 0.5, COTTON 0.6

### ✅ 8. Audit Trail & Explainability
- Every match stores `match_details` JSON
- Score breakdown saved (quality/price/delivery/risk)
- Risk flags and warnings logged
- Compliance & debugging ready

### ✅ 9. Notification Preferences
- Per-user opt-in/opt-out
- "Notify only top N" user setting
- Channel selection (PUSH/EMAIL/SMS)
- Quiet hours support (future)

### ✅ 10. Concurrency & Location Filter Tests
- Race condition tests for partial matches
- Location filter accuracy tests
- WARN/PASS/FAIL scenario coverage
- Duplicate detection validation

### ✅ 11. Performance Considerations
- Micro-batching (1-3s) for high-volume
- Incremental matching for affected entities only
- Configurable batch size and delay
- Query optimization with location indexes

### ✅ 12. Backpressure & Throttling
- Priority queue (HIGH → MEDIUM → LOW)
- Throttling on auto-match (queue when overloaded)
- Configurable processing rate
- No system overload protection

### ✅ 13. Security & Data Leakage Prevention
- Match results shown ONLY to matched parties
- NO count leakage to non-matched users
- NO partial info visible to non-participants
- Privacy-first design

---

## 📋 YOUR CONFIGURATION DECISIONS

Please answer these 10 questions:

### 1. Scoring Weights

**Default:**
```
Quality: 40%, Price: 30%, Delivery: 15%, Risk: 15%
```

**Accept default OR provide custom per commodity?**

Your Decision: _____________________

---

### 2. Min Score Threshold

**Default:** 0.6 (60%) globally

**Accept OR per-commodity?**  
Example: COTTON 0.6, GOLD 0.7, WHEAT 0.5

Your Decision: _____________________

---

### 3. WARN Risk Penalty

**Current:** -10% global penalty

**Accept 10% OR change?**

Your Decision: _____________________

---

### 4. Notification Settings

**Current:**
- Top 5 matches notified
- Rate limit: 1/user/minute

**Accept OR change?**

Your Decision: _____________________

---

### 5. Location Matching Rules

**Options:**
- ✅ Exact location match (same city/district)?
- ✅ Same state match?
- ❌ Cross-state match?
- ❓ Distance-based (within X km)?

Your Decision: _____________________

---

### 6. Duplicate Detection

**Current:**
- Time window: 5 minutes
- Similarity: 95%

**Accept OR change?**

Your Decision: _____________________

---

### 7. Partial Matching Minimum

**Current:** 10% of requested quantity minimum

**Accept 10% OR different?**

Your Decision: _____________________

---

### 8. Internal Branch Trading

**Options:**
- ✅ BLOCK (prevent circular trades)
- ❌ ALLOW (permit transfers)
- ⚙️ CONFIGURABLE (admin setting)

Your Decision: _____________________

---

### 9. Safety Cron Interval

**Options:** 15s / 30s / 60s / Disabled

Your Decision: _____________________

---

### 10. Buyer-Seller Visibility

**Current:** Buyer sees ONLY sellers in matched location (NO marketplace browsing)

**Confirm acceptable?**

Your Decision: _____ (Y/N)

---

## ✅ CRITICAL CONFIRMATIONS

Please confirm understanding (Y/N):

1. [ ] **Location-First:** Buyer sees ONLY sellers in delivery region (NO cross-state spam)
2. [ ] **Event-Driven:** Real-time matching on requirement.created / availability.created
3. [ ] **Risk Integration:** PASS/WARN/FAIL with 10% penalty for WARN
4. [ ] **Atomic Allocation:** Optimistic locking prevents double-allocation
5. [ ] **Multi-Commodity:** Works for Cotton, Gold, Wheat, Rice, Oil (NOT cotton-only)
6. [ ] **Audit Trail:** Full explainability (score breakdown, risk details logged)
7. [ ] **Security:** Match results ONLY to matched parties (NO count leakage)
8. [ ] **Partial Matching:** Seller 10 tons, buyer 6 → match 6, keep 4 for others
9. [ ] **No Duplicate Trades:** Same buyer-seller pair blocked within 5min window
10. [ ] **Pass Risk Pre-Check:** Internal branch trading blocked (if configured)

---

## 📊 DELIVERABLES

### Code
- **9 new files** (~4,300 production lines)
- **6 updated files** (integration points)
- **9 test suites** (~4,300 test lines, 95% coverage)
- **3 database changes** (2 indexes + 1 audit table)

### Timeline
- **10 days** from approval to completion
- No code committed to main until ALL tests pass + code review approved

---

## ✅ FINAL APPROVAL

**I have reviewed this specification and:**

- [ ] **APPROVE** - Start implementation as specified
- [ ] **REQUEST CHANGES** - See notes below

**Approved by:** _____________________  
**Date:** _____________________  
**Configuration Answers:** See above (10 questions)  
**Notes/Changes:** _____________________

---

**Implementation Branch:** `feat/trade-desk-matching-engine`

**Merge Conditions:**
1. All 9 test suites pass (95%+ coverage)
2. All concurrency tests pass
3. Location filter tests pass
4. Code review approved
5. Final approval given

---

*Detailed technical spec: `MATCHING_ENGINE_IMPLEMENTATION_PLAN.md` (~2,500 lines)*
