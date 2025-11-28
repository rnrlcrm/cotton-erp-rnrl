# CDPS End-to-End Business Partner Module Flow

**Complete Flow Documentation for Production Deployment**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Business Partner Types & Classification](#business-partner-types--classification)
3. [Complete Onboarding Flow](#complete-onboarding-flow)
4. [Capability Detection Rules](#capability-detection-rules)
5. [Trade Desk Integration Flow](#trade-desk-integration-flow)
6. [Insider Trading Prevention Flow](#insider-trading-prevention-flow)
7. [Database Schema & Constraints](#database-schema--constraints)
8. [API Endpoints Flow](#api-endpoints-flow)
9. [Validation Rules Summary](#validation-rules-summary)
10. [Production Deployment Checklist](#production-deployment-checklist)

---

## 1. System Overview

### What CDPS Does
**Capability-Driven Partner System (CDPS)** automatically detects trading capabilities based on verified documents and enforces compliance rules at multiple layers.

### Key Components
```
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS PARTNER MODULE                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📝 Onboarding → 🔍 Document Verification → ✅ Capability    │
│     Detection → 🛡️ Compliance Validation → 📊 Trade Desk    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Architecture Layers
1. **Database Layer**: Enforces data integrity (UNIQUE constraints, JSONB indexes)
2. **Service Layer**: Auto-detects capabilities from verified documents
3. **Validator Layer**: Prevents insider trading and enforces trade rules
4. **API Layer**: Integrates with Trade Desk for availability/requirement posting

---

## 2. Business Partner Types & Classification

### 2.1 Entity Classes (entity_class field)

| Entity Class | Description | Can Trade? | Documents Required |
|--------------|-------------|------------|-------------------|
| `business_entity` | Indian/Foreign trading companies | ✅ Yes | GST/PAN/IEC/Foreign Tax |
| `service_provider` | Brokers, transporters, controllers | ❌ No | No GST Declaration |

### 2.2 Business Entity Types (Enum)

```python
class BusinessEntityType(str, Enum):
    # Indian Entities
    PROPRIETARY_FIRM = "proprietary_firm"           # Individual ownership
    PARTNERSHIP_FIRM = "partnership_firm"           # Partnership
    LIMITED_LIABILITY_PARTNERSHIP = "llp"           # LLP
    PRIVATE_LIMITED_COMPANY = "private_limited"     # Pvt Ltd
    PUBLIC_LIMITED_COMPANY = "public_limited"       # Ltd
    
    # Foreign Entities
    FOREIGN_ENTITY = "foreign_entity"               # Any foreign company
    
    # Special Cases
    HINDU_UNDIVIDED_FAMILY = "huf"                  # HUF
    COOPERATIVE_SOCIETY = "cooperative_society"      # Co-op
    TRUST = "trust"                                  # Trust
    GOVERNMENT_ENTITY = "government_entity"          # Govt dept
```

### 2.3 Service Provider Types

```python
class ServiceProviderType(str, Enum):
    BROKER = "broker"
    SUB_BROKER = "sub_broker"
    TRANSPORTER = "transporter"
    CONTROLLER = "controller"
    FINANCER = "financer"
    SHIPPING_AGENT = "shipping_agent"
```

---

## 3. Complete Onboarding Flow

### 3.1 Onboarding Application Submission

```
USER SUBMITS APPLICATION
         ↓
┌─────────────────────────────────────────────────────┐
│ POST /api/v1/partners/onboarding                    │
├─────────────────────────────────────────────────────┤
│ Required Fields:                                     │
│  - legal_name: "ABC Cotton Mills"                  │
│  - country: "India"                                 │
│  - entity_class: "business_entity"                 │
│  - business_entity_type: "private_limited"         │
│  - primary_contact_name/email/phone                │
│  - primary_address/city/state/postal_code/country │
│  - bank details (account_name, bank_name, etc.)   │
└─────────────────────────────────────────────────────┘
         ↓
    STATUS: "pending"
    capabilities: {}  (empty - no docs verified yet)
```

### 3.2 Document Upload & Verification

```
ADMIN UPLOADS DOCUMENTS
         ↓
┌─────────────────────────────────────────────────────┐
│ POST /api/v1/partners/{partner_id}/documents        │
├─────────────────────────────────────────────────────┤
│ Document Types:                                      │
│  - GST_CERTIFICATE: GST registration                │
│  - PAN_CARD: PAN card                               │
│  - IEC_CERTIFICATE: Import/Export license          │
│  - FOREIGN_TAX_ID: Foreign tax registration        │
│  - NO_GST_DECLARATION: For service providers       │
└─────────────────────────────────────────────────────┘
         ↓
    DOCUMENTS STORED
    document_verified: false (waiting for admin verification)
```

### 3.3 Admin Verification Trigger

```
ADMIN VERIFIES DOCUMENTS
         ↓
┌─────────────────────────────────────────────────────┐
│ PUT /api/v1/partners/{partner_id}/documents/{doc_id}│
├─────────────────────────────────────────────────────┤
│ Action: Set document_verified = true                │
└─────────────────────────────────────────────────────┘
         ↓
    🔄 AUTOMATIC CAPABILITY DETECTION TRIGGERED
```

### 3.4 Automatic Capability Detection

**This is the CORE of CDPS - Happens automatically when documents are verified**

```python
# backend/modules/partners/cdps/capability_detection.py
# CapabilityDetectionService.detect_capabilities()

STEP 1: Fetch all VERIFIED documents for partner
    ↓
STEP 2: Apply Detection Rules (see Section 4)
    ↓
STEP 3: Update partner.capabilities JSONB field
    ↓
STEP 4: Log detected_at timestamp
```

### 3.5 Partner Approval

```
ADMIN APPROVES PARTNER
         ↓
┌─────────────────────────────────────────────────────┐
│ PUT /api/v1/partners/{partner_id}/approve           │
├─────────────────────────────────────────────────────┤
│ Actions:                                             │
│  - status: "pending" → "active"                     │
│  - approved_at: CURRENT_TIMESTAMP                   │
│  - approved_by: admin_user_id                       │
└─────────────────────────────────────────────────────┘
         ↓
    PARTNER CAN NOW TRADE (if capabilities allow)
```

---

## 4. Capability Detection Rules

### 🔍 Rule A: Indian Domestic Capabilities

**Trigger:** Partner has VERIFIED GST + PAN documents

```python
Documents Required:
  - GST_CERTIFICATE (verified=true)
  - PAN_CARD (verified=true)

Capabilities Granted:
{
    "domestic_sell_india": True,
    "domestic_buy_india": True,
    "domestic_sell_home_country": False,
    "domestic_buy_home_country": False,
    "import_allowed": False,
    "export_allowed": False,
    "auto_detected": True,
    "detected_from_documents": ["GST", "PAN"],
    "detected_at": "2025-11-28T10:30:00Z"
}
```

**Real Example:**
```
Partner: ABC Cotton Mills (Mumbai)
Country: India
Documents: GST (27AAAAA1234A1Z5) ✅, PAN (AAAAA1234A) ✅
Result: ✅ Can buy and sell cotton in India
```

---

### 🔍 Rule B: Import/Export Capabilities

**Trigger:** Partner has VERIFIED GST + PAN + IEC documents

```python
Documents Required:
  - GST_CERTIFICATE (verified=true)
  - PAN_CARD (verified=true)
  - IEC_CERTIFICATE (verified=true)

Capabilities Granted:
{
    "domestic_sell_india": True,
    "domestic_buy_india": True,
    "domestic_sell_home_country": False,
    "domestic_buy_home_country": False,
    "import_allowed": True,      # ← NEW
    "export_allowed": True,       # ← NEW
    "auto_detected": True,
    "detected_from_documents": ["GST", "PAN", "IEC"],
    "detected_at": "2025-11-28T10:30:00Z"
}
```

**Real Example:**
```
Partner: Global Cotton Traders (Delhi)
Country: India
Documents: GST ✅, PAN ✅, IEC ✅
Result: ✅ Can buy/sell in India + import/export internationally
```

---

### 🔍 Rule C: Foreign Entity Home Country Capabilities

**⚠️ CRITICAL RULE: Foreign entities can ONLY trade in their home country, NOT in India**

**Trigger:** Partner has country != "India" AND has VERIFIED foreign tax documents

```python
Documents Required:
  - FOREIGN_TAX_ID (verified=true)

Capabilities Granted:
{
    "domestic_sell_india": False,           # ← ALWAYS False!
    "domestic_buy_india": False,            # ← ALWAYS False!
    "domestic_sell_home_country": True,     # ← Home country only
    "domestic_buy_home_country": True,      # ← Home country only
    "import_allowed": True,
    "export_allowed": True,
    "auto_detected": True,
    "detected_from_documents": ["FOREIGN_TAX_ID"],
    "detected_at": "2025-11-28T10:30:00Z"
}
```

**Real Example:**
```
Partner: USA Cotton Corporation
Country: USA (not India)
Documents: Foreign Tax ID ✅
Result: 
  ✅ Can buy/sell in USA (home country)
  ✅ Can import/export internationally
  ❌ CANNOT buy/sell in India domestic market
```

**Why This Rule Exists:**
- Foreign entities are registered abroad, not in India
- They don't have Indian GST/PAN
- They can only trade domestically in their own country
- For India trade, they must use import/export (international trade)

---

### 🔍 Rule D: No Capabilities (No Documents)

**Trigger:** No verified documents

```python
Documents: None verified

Capabilities:
{
    "domestic_sell_india": False,
    "domestic_buy_india": False,
    "domestic_sell_home_country": False,
    "domestic_buy_home_country": False,
    "import_allowed": False,
    "export_allowed": False,
    "auto_detected": True,
    "detected_from_documents": [],
    "detected_at": "2025-11-28T10:30:00Z"
}
```

---

### 🔍 Rule E: Service Provider (Cannot Trade)

**Trigger:** entity_class = "service_provider"

```python
Entity Class: service_provider
Service Type: broker / transporter / etc.

Capabilities:
{
    "domestic_sell_india": False,
    "domestic_buy_india": False,
    "domestic_sell_home_country": False,
    "domestic_buy_home_country": False,
    "import_allowed": False,
    "export_allowed": False,
    "auto_detected": True,
    "detected_from_documents": [],
    "detected_at": "2025-11-28T10:30:00Z"
}
```

**Real Example:**
```
Partner: Cotton Broker Services
Entity Class: service_provider
Service Type: broker
Result: ❌ Cannot post availability or requirements (brokers don't trade)
```

---

## 5. Trade Desk Integration Flow

### 5.1 Posting Availability (Seller Listing)

```
SELLER POSTS COTTON AVAILABILITY
         ↓
┌─────────────────────────────────────────────────────┐
│ POST /api/v1/trade-desk/availability                │
├─────────────────────────────────────────────────────┤
│ Payload:                                             │
│  - seller_id: UUID                                  │
│  - commodity: "cotton"                              │
│  - delivery_location: "Mumbai, India"               │
│  - quantity: 100 bales                              │
└─────────────────────────────────────────────────────┘
         ↓
    🛡️ VALIDATION LAYER 1: TradeCapabilityValidator
         ↓
┌─────────────────────────────────────────────────────┐
│ Check seller.capabilities                            │
├─────────────────────────────────────────────────────┤
│ IF delivery_location is in India:                   │
│   → Seller MUST have domestic_sell_india = True     │
│                                                      │
│ IF delivery_location is in seller's home country:   │
│   → Seller MUST have domestic_sell_home_country=True│
│                                                      │
│ IF seller is service_provider:                      │
│   → REJECT (service providers cannot trade)         │
└─────────────────────────────────────────────────────┘
         ↓
    ✅ VALIDATION PASSED
         ↓
    AVAILABILITY POSTED TO TRADE DESK
```

**Example Scenarios:**

| Seller | Country | Delivery Location | domestic_sell_india | Result |
|--------|---------|-------------------|-------------------|---------|
| ABC Mills | India | Mumbai, India | ✅ True | ✅ ALLOWED |
| USA Corp | USA | New York, USA | ❌ False | ✅ ALLOWED (home country) |
| USA Corp | USA | Mumbai, India | ❌ False | ❌ REJECTED |
| Cotton Broker | India | Mumbai, India | ❌ False (service provider) | ❌ REJECTED |

---

### 5.2 Posting Requirement (Buyer Listing)

```
BUYER POSTS COTTON REQUIREMENT
         ↓
┌─────────────────────────────────────────────────────┐
│ POST /api/v1/trade-desk/requirements                │
├─────────────────────────────────────────────────────┤
│ Payload:                                             │
│  - buyer_id: UUID                                   │
│  - commodity: "cotton"                              │
│  - delivery_location: "Delhi, India"                │
│  - quantity: 50 bales                               │
└─────────────────────────────────────────────────────┘
         ↓
    🛡️ VALIDATION LAYER 1: TradeCapabilityValidator
         ↓
┌─────────────────────────────────────────────────────┐
│ Check buyer.capabilities                             │
├─────────────────────────────────────────────────────┤
│ IF delivery_location is in India:                   │
│   → Buyer MUST have domestic_buy_india = True       │
│                                                      │
│ IF delivery_location is in buyer's home country:    │
│   → Buyer MUST have domestic_buy_home_country = True│
│                                                      │
│ IF buyer is service_provider:                       │
│   → REJECT (service providers cannot trade)         │
└─────────────────────────────────────────────────────┘
         ↓
    ✅ VALIDATION PASSED
         ↓
    REQUIREMENT POSTED TO TRADE DESK
```

---

### 5.3 Matching Availability with Requirement

```
SYSTEM MATCHES AVAILABILITY WITH REQUIREMENT
         ↓
┌─────────────────────────────────────────────────────┐
│ MatchValidator.validate_potential_match()           │
├─────────────────────────────────────────────────────┤
│ Validations:                                         │
│  1. Buyer has buy capability for delivery location  │
│  2. Seller has sell capability for delivery location│
│  3. NOT insider trading (see Section 6)             │
└─────────────────────────────────────────────────────┘
         ↓
    ✅ ALL VALIDATIONS PASSED
         ↓
    MATCH CREATED & NOTIFIED TO BOTH PARTIES
```

---

## 6. Insider Trading Prevention Flow

### 6.1 Insider Trading Rules (ALL Must Be False to Allow Trade)

```python
# backend/modules/partners/validators/insider_trading.py
# InsiderTradingValidator.validate_trade_parties()

🚫 BLOCKING RULE 1: Same Entity
   buyer_id == seller_id
   → REJECT: "Cannot trade with yourself"

🚫 BLOCKING RULE 2: Master-Branch Relationship
   buyer.master_entity_id == seller.id OR
   seller.master_entity_id == buyer.id
   → REJECT: "Master entity cannot trade with its branch"

🚫 BLOCKING RULE 3: Sibling Branches
   buyer.master_entity_id == seller.master_entity_id (both not null)
   → REJECT: "Branch offices of same company cannot trade"

🚫 BLOCKING RULE 4: Corporate Group
   buyer.corporate_group_id == seller.corporate_group_id (both not null)
   → REJECT: "Entities in same corporate group cannot trade"

🚫 BLOCKING RULE 5: Same GST Number
   buyer.tax_id_number == seller.tax_id_number (both not null)
   → REJECT: "Same GST number detected - same entity"
```

### 6.2 Entity Relationship Tracking

**Master-Branch Relationship:**
```
ABC Corporation (Master)
  ├── ABC Mumbai Branch (master_entity_id → ABC Corp)
  ├── ABC Delhi Branch (master_entity_id → ABC Corp)
  └── ABC Pune Branch (master_entity_id → ABC Corp)

❌ ABC Corp cannot trade with ABC Mumbai
❌ ABC Mumbai cannot trade with ABC Delhi (siblings)
✅ ABC Corp CAN trade with XYZ Corp (unrelated)
```

**Corporate Group:**
```
Group ID: 12345-ABCD-GROUP
  ├── ABC Cotton Mills (corporate_group_id: 12345)
  ├── ABC Textiles Ltd (corporate_group_id: 12345)
  └── ABC Spinning Co (corporate_group_id: 12345)

❌ ABC Cotton Mills cannot trade with ABC Textiles
❌ ABC Textiles cannot trade with ABC Spinning
✅ ABC Cotton Mills CAN trade with XYZ Corp (different group)
```

---

## 7. Database Schema & Constraints

### 7.1 Core Fields

```sql
-- business_partners table

-- PRIMARY KEY
id UUID PRIMARY KEY DEFAULT uuid_generate_v4()

-- CLASSIFICATION
entity_class VARCHAR(20) NOT NULL  -- 'business_entity' or 'service_provider'
business_entity_type VARCHAR(50)   -- Enum: 'proprietary_firm', 'foreign_entity', etc.
service_provider_type VARCHAR(50)  -- Enum: 'broker', 'transporter', etc.

-- IDENTITY (NO UNIQUE CONSTRAINT - allows duplicates)
legal_name VARCHAR(500) NOT NULL   -- ✅ "ABC Corporation" can exist multiple times
country VARCHAR(100) NOT NULL

-- TAX REGISTRATION (UNIQUE CONSTRAINT)
tax_id_number VARCHAR(50) UNIQUE   -- ✅ GST must be unique
pan_number VARCHAR(10)             -- ✅ NO unique constraint (branches share PAN)

-- CDPS CORE FIELD
capabilities JSONB DEFAULT '{}'::json
```

### 7.2 JSONB Capabilities Structure

```json
{
  "domestic_sell_india": true,
  "domestic_buy_india": true,
  "domestic_sell_home_country": false,
  "domestic_buy_home_country": false,
  "import_allowed": false,
  "export_allowed": false,
  "auto_detected": true,
  "detected_from_documents": ["GST", "PAN"],
  "detected_at": "2025-11-28T10:30:00Z",
  "manual_override": false,
  "override_reason": null
}
```

### 7.3 Insider Trading Fields

```sql
-- Entity Hierarchy
master_entity_id UUID REFERENCES business_partners(id)
is_master_entity BOOLEAN DEFAULT FALSE
corporate_group_id UUID
entity_hierarchy JSONB  -- Full ownership tree
```

### 7.4 Database Indexes (Performance)

```sql
-- JSONB Indexes for fast capability queries
CREATE INDEX idx_capabilities_domestic_sell_india 
  ON business_partners((capabilities->>'domestic_sell_india'));

CREATE INDEX idx_capabilities_domestic_buy_india 
  ON business_partners((capabilities->>'domestic_buy_india'));

CREATE INDEX idx_capabilities_domestic_sell_home 
  ON business_partners((capabilities->>'domestic_sell_home_country'));

CREATE INDEX idx_capabilities_domestic_buy_home 
  ON business_partners((capabilities->>'domestic_buy_home_country'));

CREATE INDEX idx_capabilities_import 
  ON business_partners((capabilities->>'import_allowed'));

CREATE INDEX idx_capabilities_export 
  ON business_partners((capabilities->>'export_allowed'));

CREATE INDEX idx_capabilities_auto_detected 
  ON business_partners((capabilities->>'auto_detected'));

-- Relationship Indexes
CREATE INDEX idx_master_entity ON business_partners(master_entity_id);
CREATE INDEX idx_corporate_group ON business_partners(corporate_group_id);
CREATE INDEX idx_country ON business_partners(country);
CREATE INDEX idx_entity_class ON business_partners(entity_class);
```

---

## 8. API Endpoints Flow

### 8.1 Onboarding Flow

```
1. POST /api/v1/partners/onboarding
   → Create pending partner application
   
2. POST /api/v1/partners/{id}/documents
   → Upload GST/PAN/IEC documents
   
3. PUT /api/v1/partners/{id}/documents/{doc_id}
   → Admin verifies document
   → 🔄 AUTOMATIC capability detection triggered
   
4. GET /api/v1/partners/{id}/capabilities
   → Check detected capabilities
   
5. PUT /api/v1/partners/{id}/approve
   → Admin approves partner
   → Status: pending → active
```

### 8.2 Trade Desk Flow

```
1. POST /api/v1/trade-desk/availability
   → Validate seller.capabilities
   → Check delivery_location vs domestic_sell_*
   → Post to trade desk
   
2. POST /api/v1/trade-desk/requirements
   → Validate buyer.capabilities
   → Check delivery_location vs domestic_buy_*
   → Post to trade desk
   
3. GET /api/v1/trade-desk/matches
   → System finds matching availability/requirement
   → Validate both parties' capabilities
   → Validate insider trading rules
   → Create match if all pass
```

---

## 9. Validation Rules Summary

### ✅ Partner Can Trade IF:

**For Selling in India:**
```
✓ entity_class = "business_entity"
✓ capabilities.domestic_sell_india = true
✓ status = "active"
✓ NOT insider trading with buyer
```

**For Buying in India:**
```
✓ entity_class = "business_entity"
✓ capabilities.domestic_buy_india = true
✓ status = "active"
✓ NOT insider trading with seller
```

**For Selling in Home Country (Foreign):**
```
✓ entity_class = "business_entity"
✓ country != "India"
✓ capabilities.domestic_sell_home_country = true
✓ status = "active"
✓ NOT insider trading with buyer
```

**For Buying in Home Country (Foreign):**
```
✓ entity_class = "business_entity"
✓ country != "India"
✓ capabilities.domestic_buy_home_country = true
✓ status = "active"
✓ NOT insider trading with seller
```

### ❌ Partner CANNOT Trade IF:

```
✗ entity_class = "service_provider" (brokers, transporters)
✗ capabilities for the action are false
✗ status != "active"
✗ Insider trading detected (same entity, master-branch, corporate group, same GST)
✗ Foreign entity trying to trade domestically in India
```

---

## 10. Production Deployment Checklist

### 10.1 Pre-Deployment

- [x] ✅ All models updated (entity_class, capabilities, insider trading fields)
- [x] ✅ Migration created with 8-step data conversion
- [x] ✅ CapabilityDetectionService implemented (5 rules)
- [x] ✅ InsiderTradingValidator implemented (5 blocking rules)
- [x] ✅ TradeCapabilityValidator integrated into Trade Desk
- [x] ✅ JSONB indexes created (7 capability indexes)
- [x] ✅ All 23 tests passing (capability detection, insider trading, trade desk)
- [x] ✅ Unique constraints verified (GST unique, legal_name allows duplicates)

### 10.2 Deployment Steps

```bash
# 1. Backup database
pg_dump production_db > backup_before_cdps.sql

# 2. Run migration
alembic upgrade head

# 3. Verify migration
SELECT COUNT(*) FROM business_partners WHERE capabilities IS NOT NULL;

# 4. Test capability detection
# Upload test document → Verify capabilities auto-populated

# 5. Test trade desk integration
# Post availability → Verify validation works
# Post requirement → Verify validation works

# 6. Monitor logs
tail -f /var/log/cotton-erp/capability_detection.log
tail -f /var/log/cotton-erp/insider_trading.log
```

### 10.3 Post-Deployment Verification

```sql
-- Check all partners have capabilities field
SELECT COUNT(*) FROM business_partners WHERE capabilities IS NULL;
-- Should be 0

-- Check capability distribution
SELECT 
  (capabilities->>'domestic_sell_india')::boolean as can_sell_india,
  COUNT(*) as count
FROM business_partners
GROUP BY can_sell_india;

-- Check foreign entities correctly configured
SELECT legal_name, country, capabilities
FROM business_partners
WHERE country != 'India'
  AND (capabilities->>'domestic_sell_india')::boolean = true;
-- Should be 0 rows (foreign cannot sell in India)

-- Check service providers
SELECT legal_name, service_provider_type, capabilities
FROM business_partners
WHERE entity_class = 'service_provider'
  AND (
    (capabilities->>'domestic_sell_india')::boolean = true OR
    (capabilities->>'domestic_buy_india')::boolean = true
  );
-- Should be 0 rows (service providers cannot trade)
```

### 10.4 Rollback Plan

```bash
# If issues detected:
alembic downgrade -1

# Restore from backup if needed:
psql production_db < backup_before_cdps.sql
```

---

## 11. Key Business Rules (Quick Reference)

### 🔐 Golden Rules

1. **Document-Driven**: Capabilities are ONLY granted based on verified documents
2. **Auto-Detection**: System automatically detects capabilities (no manual entry)
3. **Foreign Entity Rule**: Foreign entities can NEVER trade domestically in India
4. **Service Provider Rule**: Service providers (brokers, etc.) can NEVER trade
5. **Insider Trading**: Same entity, branches, corporate group members CANNOT trade with each other
6. **Unique Constraints**: 
   - ✅ GST (tax_id_number) must be unique
   - ✅ Company name (legal_name) can be duplicate
   - ✅ PAN can be duplicate (branches share)

---

## 12. Common Scenarios

### Scenario 1: Indian Cotton Mill Onboarding
```
1. Submit application → status: pending
2. Upload GST + PAN → documents stored
3. Admin verifies docs → capabilities auto-detected
4. capabilities.domestic_sell_india = true ✅
5. capabilities.domestic_buy_india = true ✅
6. Admin approves → status: active
7. Can now post availability and requirements in India ✅
```

### Scenario 2: Foreign Entity Onboarding
```
1. Submit application (Country: USA) → status: pending
2. Upload Foreign Tax ID → documents stored
3. Admin verifies docs → capabilities auto-detected
4. capabilities.domestic_sell_india = false ❌
5. capabilities.domestic_buy_india = false ❌
6. capabilities.domestic_sell_home_country = true ✅ (USA)
7. Admin approves → status: active
8. Can post availability in USA ✅
9. CANNOT post availability in India ❌
```

### Scenario 3: Branch Office Setup
```
1. Master: ABC Corporation (Mumbai)
2. Branch: ABC Corporation (Akola)
   - legal_name: "ABC Corporation" (same as master) ✅
   - tax_id_number: "27AKOLA..." (different GST) ✅
   - pan_number: "ABCCO1234A" (same PAN) ✅
   - master_entity_id: <master's UUID>
3. System detects relationship
4. ABC Mumbai tries to trade with ABC Akola → ❌ REJECTED (insider trading)
```

### Scenario 4: Broker Registration
```
1. Submit application with entity_class: "service_provider"
2. Upload No GST Declaration
3. capabilities.domestic_sell_india = false ❌
4. capabilities.domestic_buy_india = false ❌
5. Status: active
6. Tries to post availability → ❌ REJECTED (service providers cannot trade)
7. Can only provide brokerage services (not trading)
```

---

## 📊 System Metrics

**Performance Targets:**
- Capability detection: < 500ms per partner
- Insider trading validation: < 100ms per check
- Trade desk validation: < 200ms per posting
- JSONB query performance: < 50ms (indexed)

**Success Metrics:**
- 100% capability detection accuracy
- 0% false positives in insider trading detection
- 0% false negatives in trade capability validation
- 99.9% uptime for capability detection service

---

## 🎯 Production Ready Confirmation

✅ **All Components Implemented**
✅ **All Tests Passing (23/23)**
✅ **Database Schema Verified**
✅ **API Integration Complete**
✅ **Validation Rules Enforced**
✅ **Documentation Complete**

**Status: READY FOR PRODUCTION DEPLOYMENT** 🚀

---

**Last Updated:** November 28, 2025  
**Version:** 1.0.0  
**Branch:** feature/cdps-capability-system
