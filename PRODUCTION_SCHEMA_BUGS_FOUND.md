# PRODUCTION SCHEMA BUGS - CRITICAL FIXES REQUIRED

**Branch:** `fix/production-schema-bugs`  
**Date:** 2025-11-25  
**Severity:** 🔴 CRITICAL - Will cause production failures

---

## 🐛 BUGS FOUND

### 1. BusinessPartner Model - Incorrect `organization_id`

**File:** `/backend/modules/partners/models.py`

**Bug:**
```python
organization_id = Column(
    UUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
    comment="Organization this partner belongs to (for data isolation)"
)
```

**Why Wrong:**
- Business Partners are **EXTERNAL** entities (buyers, sellers, brokers, transporters)
- They do NOT belong to internal organization structure
- Organization is for internal company use ONLY (commission billing, branches, employees)
- Multi-tenant isolation does NOT apply to external partners

**Fix:** ✅ REMOVED `organization_id` from BusinessPartner

---

### 2. PartnerLocation Model - Incorrect `organization_id`

**File:** `/backend/modules/partners/models.py`

**Bug:**
```python
organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
```

**Why Wrong:**
- Partner locations (branches/warehouses) belong to PARTNER, not internal organization
- Same reason as BusinessPartner

**Fix:** ✅ REMOVED `organization_id` from PartnerLocation

---

### 3. PartnerEmployee - May Need Review

**File:** `/backend/modules/partners/models.py`  
**Line:** 377

**Current:**
```python
organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
```

**Question:** Does this track which internal user created the partner employee? If yes, keep. If not, remove.

**Status:** ⏳ PENDING REVIEW

---

### 4. PartnerDocument - May Need Review

**File:** `/backend/modules/partners/models.py`  
**Line:** 410

**Status:** ⏳ PENDING REVIEW (same question)

---

### 5. PartnerVehicle - May Need Review

**File:** `/backend/modules/partners/models.py`  
**Line:** 454

**Status:** ⏳ PENDING REVIEW (same question)

---

### 6. PartnerOnboardingApplication - Likely OK

**File:** `/backend/modules/partners/models.py`  
**Line:** 492

**Reason:** Tracks which internal user/organization processed the onboarding  
**Status:** ✅ KEEP (valid use case)

---

### 7. PartnerAmendment - May Need Review

**File:** `/backend/modules/partners/models.py`  
**Line:** 573

**Status:** ⏳ PENDING REVIEW

---

### 8. PartnerKYCRenewal - May Need Review

**File:** `/backend/modules/partners/models.py`  
**Line:** 610

**Status:** ⏳ PENDING REVIEW

---

## 🔴 CRITICAL: Requirement/Availability FK Bug

### 9. Requirement.buyer_branch_id - Wrong FK Reference

**File:** `/backend/modules/trade_desk/models/requirement.py`  
**Line:** 252

**Bug:**
```python
buyer_branch_id = Column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("branches.id", ondelete="SET NULL"),  # ❌ WRONG TABLE
    nullable=True,
    index=True,
    comment='Buyer branch ID for internal trade blocking logic'
)
```

**Why Wrong:**
- Table `branches` does NOT exist
- Should reference `partner_locations.id` (buyer's branch/location)
- This is for tracking which buyer location/branch is making the purchase

**Fix Required:**
```python
buyer_branch_id = Column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("partner_locations.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment='Buyer branch/location ID for internal trade blocking logic'
)
```

**Status:** ⏳ PENDING FIX

---

### 10. Availability.seller_branch_id - Wrong FK Reference

**File:** `/backend/modules/trade_desk/models/availability.py`  
**Line:** 142

**Bug:**
```python
seller_branch_id = Column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("branches.id", ondelete="SET NULL"),  # ❌ WRONG TABLE
    nullable=True,
    index=True
)
```

**Why Wrong:**
- Same as #9
- Should reference `partner_locations.id`

**Fix Required:**
```python
seller_branch_id = Column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("partner_locations.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment='Seller branch/location ID for internal trade blocking logic'
)
```

**Status:** ⏳ PENDING FIX

---

## 📋 FIX CHECKLIST

- [x] Remove `organization_id` from BusinessPartner
- [x] Remove `organization_id` from PartnerLocation
- [ ] Review & fix PartnerEmployee.organization_id
- [ ] Review & fix PartnerDocument.organization_id
- [ ] Review & fix PartnerVehicle.organization_id
- [ ] Review & fix PartnerAmendment.organization_id
- [ ] Review & fix PartnerKYCRenewal.organization_id
- [ ] Fix Requirement.buyer_branch_id FK → `partner_locations.id`
- [ ] Fix Availability.seller_branch_id FK → `partner_locations.id`
- [ ] Create database migration
- [ ] Test all partner module endpoints
- [ ] Test trade desk module with fixed FKs
- [ ] Update seed data in tests
- [ ] Run full integration test suite

---

## 🚨 IMPACT ANALYSIS

### Immediate Issues:
1. **Cannot create BusinessPartner** - requires non-existent organization_id
2. **Cannot test Requirement/Availability** - FK to non-existent `branches` table fails
3. **Matching engine tests blocked** - depends on above fixes

### Production Risk:
- **HIGH** - These bugs prevent core functionality from working
- Must fix before any production deployment
- Requires database migration for existing data

---

## 📝 NEXT STEPS

1. ✅ Create `fix/production-schema-bugs` branch
2. ✅ Fix BusinessPartner + PartnerLocation (done)
3. ⏳ Fix Requirement/Availability FK references
4. ⏳ Review remaining organization_id fields
5. ⏳ Create Alembic migration
6. ⏳ Test partner module endpoints
7. ⏳ Test trade desk module
8. ⏳ Merge fixes to main
9. ⏳ Return to matching engine implementation

---

**Estimated Time:** 2-3 hours for complete fix + testing
