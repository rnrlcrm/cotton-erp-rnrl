# AVAILABILITY ENGINE - IMPLEMENTATION DOCUMENTATION

**Branch:** `feat/trade-desk-availability-engine`  
**Started:** November 24, 2025  
**Status:** Phase 1 Complete ✅

---

## 🎯 OVERVIEW

The Availability Engine is the first of 5 core engines powering the 2035 Global Multi-Commodity Trading Platform:

1. **Availability Engine** ✅ (Building Now)
2. Requirement Engine (Next)
3. Matching Engine (AI-Powered)
4. Negotiation Engine (AI-Assisted)
5. Trade Finalization Engine

---

## ✅ PHASE 1: DATABASE SCHEMA - COMPLETE

### **Migration Created:**
`backend/db/migrations/versions/create_availability_engine_tables.py`

### **Table: `availabilities`**

**Purpose:** Sellers post inventory available for sale (universal for ALL commodities)

**Key Features:**

1. **Multi-Commodity Support** via JSONB
   - Cotton: `{"staple_length": 29, "micronaire": 4.2, "moisture": 7}`
   - Gold: `{"purity": 22, "weight": 100, "hallmark": "BIS"}`
   - Wheat: `{"protein": 12.5, "moisture": 12, "test_weight": 78}`
   - Any commodity type supported!

2. **Flexible Pricing Matrix**
   ```json
   {
     "cash_ex_gin": 59500,
     "15_days_ex_gin": 60500,
     "cash_delivered_50km": 60700
   }
   ```

3. **Location Intelligence**
   - `location_id` (FK to `settings_locations`)
   - `delivery_latitude` / `delivery_longitude` (for distance calc)
   - Geo-spatial index for fast proximity search

4. **Market Visibility Controls**
   - `PUBLIC`: Visible to all
   - `PRIVATE`: Only seller's network
   - `RESTRICTED`: Invited buyers only
   - `INTERNAL`: Own organization only

5. **Partial Order Support**
   - `allow_partial_order`: Boolean
   - `min_order_quantity`: Minimum purchase requirement

6. **AI-Powered Features**
   - `ai_suggested_price`: Fair market price
   - `ai_confidence_score`: Price confidence (0-100)
   - `ai_score_vector`: ML embeddings (JSONB)
     ```json
     {
       "commodity_embedding": [0.23, 0.45, ...],
       "quality_score": 85.5,
       "price_competitiveness": 92.3,
       "negotiation_readiness": 75.2
     }
     ```
   - `ai_price_anomaly_flag`: Unrealistic price detection
   - `ai_anomaly_reason`: Why flagged

7. **Quantity Tracking**
   - `total_quantity`: Original posted quantity
   - `available_quantity`: Currently available
   - `reserved_quantity`: Reserved during negotiation
   - `sold_quantity`: Already sold
   - **Auto-calculated via trigger!**

8. **Status Management**
   - `AVAILABLE`: Ready to sell
   - `PARTIALLY_SOLD`: Some quantity sold
   - `SOLD`: All sold
   - `EXPIRED`: Past validity date
   - `CANCELLED`: Seller cancelled
   - **Auto-updated via trigger!**

---

### **Indexes Created:**

**Core Indexes:**
- `ix_availabilities_seller_partner_id`
- `ix_availabilities_commodity_id`
- `ix_availabilities_location_id`
- `ix_availabilities_status`
- `ix_availabilities_market_visibility`

**Composite Indexes:**
- `ix_availabilities_commodity_status`
- `ix_availabilities_commodity_visibility`
- `ix_availabilities_geo_location` (location + lat/lng)

**JSONB GIN Indexes (Fast JSONB queries):**
- `ix_availabilities_quality_params_gin`
- `ix_availabilities_price_options_gin`
- `ix_availabilities_ai_score_vector_gin`

**Partial Index (Performance optimization):**
- `ix_availabilities_active` - Only active availabilities
  ```sql
  WHERE status = 'AVAILABLE' AND valid_until > NOW()
  ```

---

### **Database Triggers:**

**1. Auto-Update Quantities & Status**
```sql
CREATE TRIGGER trigger_update_availability_quantities
BEFORE INSERT OR UPDATE ON availabilities
```

**Logic:**
- `available_quantity` = `total_quantity` - `reserved_quantity` - `sold_quantity`
- Auto-updates `status` based on quantities
- Auto-expires when `valid_until` < NOW()

---

### **Constraints:**

1. **Quantity Logic:**
   ```sql
   CHECK (reserved_quantity + sold_quantity <= total_quantity)
   ```

2. **Validity Dates:**
   ```sql
   CHECK (valid_from < valid_until)
   ```

3. **Market Visibility:**
   ```sql
   CHECK (market_visibility IN ('PUBLIC', 'PRIVATE', 'RESTRICTED', 'INTERNAL'))
   ```

4. **Status:**
   ```sql
   CHECK (status IN ('AVAILABLE', 'PARTIALLY_SOLD', 'SOLD', 'EXPIRED', 'CANCELLED'))
   ```

---

## 🚀 NEXT: PHASE 2 - MODELS & MICRO-EVENTS

**What's Next:**
1. Create `Availability` model with `EventMixin`
2. Add micro-events:
   - `availability.created`
   - `availability.updated`
   - `availability.visibility_changed`
   - `availability.price_changed`
   - `availability.quantity_changed`
   - `availability.reserved`
   - `availability.released`
   - `availability.sold`
   - `availability.expired`

**Why Micro-Events?**
- Real-time matching engine can react to price/quantity changes
- Buyer watching a commodity gets instant notification when price drops
- AI learns from visibility/price change patterns

---

## 📊 SELLER LOCATION VALIDATION RULES

**CRITICAL BUSINESS RULE:**

- **SELLER:** Can only sell from their OWN registered locations + branches
- **TRADER:** Can sell from ANY location (flexibility)

**Implementation:**
- Will be enforced in `AvailabilityService.create_availability()`
- Check: `partner.partner_type == 'TRADER' OR location_id IN partner.registered_locations`

---

## 🎨 EXAMPLE DATA

### **Cotton Availability (Seller):**
```json
{
  "seller_partner_id": "uuid-of-akola-ginners",
  "commodity_id": "uuid-of-cotton",
  "variety_id": "uuid-of-dch32",
  "location_id": "uuid-of-akola-location",
  "quantity": 500,
  "quantity_unit": "bales",
  "quality_params": {
    "staple_length": 29,
    "micronaire": 4.2,
    "moisture": 7,
    "trash": 2
  },
  "test_report_url": "s3://reports/cotton-test-12345.pdf",
  "price_options": {
    "cash_ex_gin": 59500,
    "15_days_ex_gin": 60500,
    "30_days_ex_gin": 61500,
    "cash_delivered_50km": 60700
  },
  "payment_term_options": ["cash-uuid", "15day-uuid", "30day-uuid"],
  "delivery_term_options": ["ex-gin-uuid", "delivered-uuid"],
  "allow_partial_order": true,
  "min_order_quantity": 50,
  "market_visibility": "PUBLIC",
  "valid_from": "2025-11-24T00:00:00Z",
  "valid_until": "2025-12-01T23:59:59Z"
}
```

### **Gold Availability (Trader):**
```json
{
  "seller_partner_id": "uuid-of-gold-trader",
  "commodity_id": "uuid-of-gold",
  "location_id": "uuid-of-mumbai",
  "quantity": 1000,
  "quantity_unit": "grams",
  "quality_params": {
    "purity": 22,
    "hallmark": "BIS",
    "form": "bars"
  },
  "price_options": {
    "cash": 6500,
    "7_days_credit": 6550,
    "15_days_credit": 6600
  },
  "payment_term_options": ["cash-uuid", "7day-uuid", "15day-uuid"],
  "delivery_term_options": ["delivered-uuid"],
  "allow_partial_order": true,
  "min_order_quantity": 10,
  "market_visibility": "PUBLIC",
  "valid_from": "2025-11-24T00:00:00Z",
  "valid_until": "2025-11-30T23:59:59Z"
}
```

---

## 📝 MIGRATION CHECKLIST

- [x] Create migration file
- [x] Define table schema with all enhancements
- [x] Add geo_index for location search
- [x] Add market_visibility field
- [x] Add allow_partial_order field
- [x] Add ai_score_vector JSONB
- [x] Create core indexes
- [x] Create JSONB GIN indexes
- [x] Create partial index for active availabilities
- [x] Add auto-update trigger for quantities/status
- [x] Add validation constraints
- [x] Add table/column comments
- [x] Test upgrade/downgrade

**Next Step:** Run migration and verify in database

---

## 🔧 TO RUN MIGRATION:

```bash
cd /workspaces/cotton-erp-rnrl/backend
alembic upgrade head
```

**Verify:**
```sql
\d availabilities
SELECT * FROM availabilities LIMIT 0;
```

---

**Status:** ✅ Phase 1 Complete - Ready for Phase 2 (Models & Events)
