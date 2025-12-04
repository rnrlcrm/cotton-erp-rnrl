# TRADE ENGINE - FINAL PLAN (With Validation)

## 🎯 FINAL UNDERSTANDING

**Trade Engine validates that negotiation terms are complete and valid BEFORE creating contract.**

---

## 📊 COMPLETE FLOW

### STEP 1: User Clicks "Create Contract"

```
User: Ramesh (Buyer)
Action: Click "Create Trade" button from completed negotiation
Negotiation ID: NEG-2025-00123
Status: COMPLETED
```

### STEP 2: Trade Engine Validates Terms & Conditions

```python
# VALIDATION CHECKS (Not AI - just business rules!)

class TradeValidationService:
    """Validate negotiation has all required terms"""
    
    def validate_negotiation_for_trade(self, negotiation_id):
        """
        Check if negotiation is READY to become a contract
        
        This is NOT AI validation (Risk Engine did that)
        This is COMPLETENESS validation (are all terms filled?)
        """
        
        negotiation = get_negotiation(negotiation_id)
        errors = []
        
        # ✅ CHECK 1: Negotiation Status
        if negotiation.status != "COMPLETED":
            errors.append("Negotiation not completed yet")
        
        # ✅ CHECK 2: Price Terms
        if not negotiation.final_price or negotiation.final_price <= 0:
            errors.append("Final price not set")
        
        if not negotiation.price_per_unit:
            errors.append("Price per unit missing")
        
        # ✅ CHECK 3: Quantity Terms
        if not negotiation.final_quantity or negotiation.final_quantity <= 0:
            errors.append("Final quantity not set")
        
        if not negotiation.unit_of_measure:
            errors.append("Unit of measure missing")
        
        # ✅ CHECK 4: Delivery Terms (MUST BE COMPLETE!)
        if not negotiation.delivery_location:
            errors.append("Delivery location not specified")
        
        if not negotiation.delivery_date:
            errors.append("Delivery date not set")
        
        if not negotiation.delivery_terms:
            errors.append("Delivery terms missing (FOB/CIF/etc)")
        
        # ✅ CHECK 5: Payment Terms (MUST BE COMPLETE!)
        if not negotiation.payment_terms:
            errors.append("Payment terms not specified")
        
        if not negotiation.advance_percentage:
            errors.append("Advance percentage not set")
        
        if not negotiation.payment_due_days:
            errors.append("Payment due days not set")
        
        # ✅ CHECK 6: Quality Specifications (MUST BE COMPLETE!)
        if not negotiation.quality_parameters:
            errors.append("Quality specifications missing")
        else:
            # Check individual quality params
            quality = negotiation.quality_parameters  # JSON field
            
            if not quality.get("moisture_max"):
                errors.append("Maximum moisture % not specified")
            
            if not quality.get("trash_max"):
                errors.append("Maximum trash % not specified")
            
            if not quality.get("staple_length_min"):
                errors.append("Minimum staple length not specified")
            
            if not quality.get("micronaire_range"):
                errors.append("Micronaire range not specified")
        
        # ✅ CHECK 7: Commodity Details
        if not negotiation.commodity_id:
            errors.append("Commodity not specified")
        
        if not negotiation.commodity_variety:
            errors.append("Commodity variety not specified")
        
        # ✅ CHECK 8: Parties Information
        if not negotiation.buyer_id or not negotiation.seller_id:
            errors.append("Buyer or seller information missing")
        
        # ✅ CHECK 9: Insurance & Risk Terms (if applicable)
        if negotiation.requires_insurance and not negotiation.insurance_terms:
            errors.append("Insurance terms required but not specified")
        
        # ✅ CHECK 10: Inspection Terms
        if not negotiation.inspection_terms:
            errors.append("Inspection terms not specified")
        
        if not negotiation.inspection_location:
            errors.append("Inspection location not set")
        
        # ✅ CHECK 11: Dispute Resolution
        if not negotiation.dispute_resolution_method:
            errors.append("Dispute resolution method not specified")
        
        if not negotiation.arbitration_location:
            errors.append("Arbitration location not set")
        
        # ✅ CHECK 12: Force Majeure Terms
        if not negotiation.force_majeure_terms:
            errors.append("Force majeure clause missing")
        
        # ✅ CHECK 13: Penalties & Liquidated Damages
        if not negotiation.penalty_terms:
            errors.append("Penalty terms for delays not specified")
        
        if not negotiation.quality_rejection_terms:
            errors.append("Quality rejection terms missing")
        
        # RESULT
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "message": "Negotiation terms incomplete - cannot create contract"
            }
        
        return {
            "valid": True,
            "message": "All terms validated - ready for contract creation"
        }
```

---

## 🔍 DETAILED VALIDATION CHECKS

### Category 1: PRICE & QUANTITY TERMS

```json
{
  "final_price_per_unit": 7150.00,          // ✅ Required
  "total_quantity": 50,                      // ✅ Required
  "unit_of_measure": "QUINTAL",             // ✅ Required
  "total_amount": 357500.00,                // ✅ Auto-calculated
  "currency": "INR",                        // ✅ Required
  "price_validity_days": 7                  // ✅ Required
}
```

**Validation**:
- Price must be > 0
- Quantity must be > 0
- Unit of measure must be standard (QUINTAL/TON/KG)
- Total amount must match price × quantity

---

### Category 2: DELIVERY TERMS (Critical!)

```json
{
  "delivery_location": {
    "address": "Textile Mill, Ahmedabad",
    "city": "Ahmedabad",
    "state": "Gujarat",
    "pincode": "380001"
  },
  "delivery_date": "2025-12-15",            // ✅ Required
  "delivery_window_days": 2,                // ✅ Flexibility
  "delivery_terms": "FOB",                  // ✅ FOB/CIF/EXW/etc
  "transportation_mode": "TRUCK",           // ✅ Required
  "freight_charges_borne_by": "SELLER"      // ✅ Required
}
```

**Validation**:
- Delivery location must be complete (city, state, pincode)
- Delivery date must be future date
- Delivery terms must be standard (FOB/CIF/EXW/DDP)
- Transportation mode specified
- Freight responsibility clear

---

### Category 3: PAYMENT TERMS (Critical!)

```json
{
  "payment_method": "BANK_TRANSFER",        // ✅ Required
  "advance_percentage": 30,                 // ✅ Required (0-100)
  "advance_due_days": 2,                    // ✅ Within X days of signing
  "balance_payment_trigger": "ON_DELIVERY", // ✅ Required
  "balance_due_days": 7,                    // ✅ After delivery
  "late_payment_penalty": 2.0,              // ✅ % per month
  "payment_guarantee": "BANK_GUARANTEE"     // ✅ Optional but recommended
}
```

**Validation**:
- Payment method must be valid (BANK_TRANSFER/LC/CASH)
- Advance % between 0-100
- Payment triggers defined (ON_SIGNING/ON_DELIVERY/ON_QUALITY_CHECK)
- Late payment penalty specified
- Bank details verified

---

### Category 4: QUALITY SPECIFICATIONS (Critical!)

```json
{
  "commodity_variety": "SHANKAR-6",
  "quality_parameters": {
    "moisture_max": 8.0,                    // ✅ Max % allowed
    "trash_max": 2.5,                       // ✅ Max % allowed
    "staple_length_min": 28.0,              // ✅ Min mm
    "staple_length_max": 30.0,              // ✅ Max mm
    "micronaire_min": 3.8,                  // ✅ Min value
    "micronaire_max": 4.2,                  // ✅ Max value
    "strength_min": 28.0,                   // ✅ g/tex
    "color_grade": "WHITE"                  // ✅ Required
  },
  "testing_method": "ASTM_D1448",           // ✅ Standard
  "sample_size": "500g",                    // ✅ For testing
  "tolerance_allowed": 2                    // ✅ % deviation allowed
}
```

**Validation**:
- All quality parameters defined
- Values within industry standards
- Testing method specified
- Sample size for inspection defined
- Tolerance limits clear

---

### Category 5: INSPECTION TERMS

```json
{
  "inspection_required": true,
  "inspection_agency": "THIRD_PARTY",       // SELLER/BUYER/THIRD_PARTY
  "inspection_location": "DESTINATION",     // SOURCE/DESTINATION/TRANSIT
  "inspection_timeline": "WITHIN_24_HOURS", // After delivery
  "inspection_cost_borne_by": "BUYER",
  "quality_rejection_terms": {
    "rejection_allowed_if": "BELOW_SPECS",
    "notification_period_hours": 48,
    "replacement_timeline_days": 7,
    "refund_if_no_replacement": true
  }
}
```

**Validation**:
- Inspection agency identified
- Location specified
- Timeline defined
- Rejection terms clear
- Cost responsibility assigned

---

### Category 6: LEGAL & DISPUTE TERMS

```json
{
  "governing_law": "INDIAN_CONTRACT_ACT_1872",
  "jurisdiction": "AHMEDABAD",
  "dispute_resolution_method": "ARBITRATION",
  "arbitration_location": "Ahmedabad, Gujarat",
  "arbitration_rules": "INDIAN_ARBITRATION_ACT",
  "language": "ENGLISH",
  "force_majeure_terms": {
    "events_covered": [
      "NATURAL_DISASTER",
      "WAR",
      "GOVERNMENT_ACTION",
      "PANDEMIC"
    ],
    "notice_period_days": 7,
    "liability_waiver": true
  }
}
```

**Validation**:
- Governing law specified
- Jurisdiction clear
- Dispute resolution method defined
- Force majeure events listed
- Notice periods specified

---

### Category 7: PENALTY & DAMAGE TERMS

```json
{
  "late_delivery_penalty": {
    "penalty_per_day": 0.5,                 // % of total amount
    "max_penalty_percentage": 10,           // Cap at 10%
    "grace_period_days": 2
  },
  "quality_rejection_penalty": {
    "replacement_cost": "SELLER_BEARS",
    "transportation_cost": "SELLER_BEARS",
    "storage_cost_per_day": 500             // INR
  },
  "cancellation_terms": {
    "buyer_cancellation_penalty": 5,        // % of total amount
    "seller_cancellation_penalty": 10,      // % of total amount
    "notice_period_days": 3
  }
}
```

**Validation**:
- Penalty rates defined
- Maximum caps specified
- Grace periods clear
- Cancellation terms fair

---

## ✅ VALIDATION RESULT EXAMPLES

### Example 1: COMPLETE Negotiation ✅

```json
{
  "negotiation_id": "NEG-2025-00123",
  "status": "COMPLETED",
  
  "validation_result": {
    "valid": true,
    "completeness_score": 100,
    "missing_terms": [],
    "message": "✅ All terms complete - Ready for contract creation"
  },
  
  "validated_terms": {
    "price_quantity": "✅ Complete",
    "delivery": "✅ Complete",
    "payment": "✅ Complete",
    "quality": "✅ Complete",
    "inspection": "✅ Complete",
    "legal": "✅ Complete",
    "penalties": "✅ Complete"
  }
}

Action: CREATE TRADE → SUCCESS
```

### Example 2: INCOMPLETE Negotiation ❌

```json
{
  "negotiation_id": "NEG-2025-00124",
  "status": "COMPLETED",
  
  "validation_result": {
    "valid": false,
    "completeness_score": 65,
    "missing_terms": [
      "Quality specifications incomplete",
      "Inspection location not specified",
      "Penalty terms missing",
      "Force majeure clause not defined"
    ],
    "message": "❌ Cannot create contract - terms incomplete"
  },
  
  "validated_terms": {
    "price_quantity": "✅ Complete",
    "delivery": "✅ Complete",
    "payment": "✅ Complete",
    "quality": "❌ Incomplete - moisture & trash limits missing",
    "inspection": "❌ Incomplete - location not set",
    "legal": "✅ Complete",
    "penalties": "❌ Missing - no penalty terms defined"
  }
}

Action: BLOCK TRADE CREATION
User Message: "Please complete missing terms before creating contract"
```

---

## 🔄 CORRECTED TRADE ENGINE FLOW

### STEP 1: User Initiates Trade Creation

```
User Action: Click "Create Trade" from negotiation page
Request: POST /api/trades/create
Body: { "negotiation_id": "NEG-2025-00123" }
```

### STEP 2: Validation Layer (NEW!)

```python
# Validate terms & conditions
validation = TradeValidationService.validate_negotiation(negotiation_id)

if not validation["valid"]:
    # REJECT - Terms incomplete
    return {
        "success": false,
        "error": "TERMS_INCOMPLETE",
        "missing_terms": validation["errors"],
        "action_required": "Complete all terms in negotiation"
    }

# ✅ PASSED - Proceed to create trade
```

### STEP 3: Create Trade Record

```python
trade = Trade(
    trade_number=generate_number(),
    negotiation_id=negotiation_id,
    
    # Copy ALL validated terms
    buyer_id=negotiation.buyer_id,
    seller_id=negotiation.seller_id,
    commodity_id=negotiation.commodity_id,
    
    # Price terms (frozen)
    price_per_unit=negotiation.final_price,
    quantity=negotiation.final_quantity,
    total_amount=negotiation.total_amount,
    
    # Delivery terms (frozen)
    delivery_location=negotiation.delivery_location,
    delivery_date=negotiation.delivery_date,
    delivery_terms=negotiation.delivery_terms,
    
    # Payment terms (frozen)
    payment_terms=negotiation.payment_terms,
    advance_percentage=negotiation.advance_percentage,
    
    # Quality specs (frozen)
    quality_parameters=negotiation.quality_parameters,
    
    # Legal terms (frozen)
    dispute_resolution=negotiation.dispute_resolution_method,
    force_majeure_terms=negotiation.force_majeure_terms,
    
    # Penalty terms (frozen)
    penalty_terms=negotiation.penalty_terms,
    
    # Immutability
    contract_hash=calculate_hash(all_terms),
    terms_locked_at=datetime.utcnow(),
    
    # Status
    status="DRAFT",
    created_at=datetime.utcnow()
)
```

### STEP 4: Generate Contract PDF

```python
# Create professional contract document
contract_pdf = ContractPDFService.generate(
    trade=trade,
    template="cotton_trade_contract_v1.html",
    include_sections=[
        "parties_details",
        "commodity_specs",
        "price_quantity",
        "delivery_terms",
        "payment_terms",
        "quality_specifications",
        "inspection_procedure",
        "penalties_damages",
        "force_majeure",
        "dispute_resolution",
        "signatures"
    ]
)

# Upload to S3
pdf_url = upload_to_s3(contract_pdf)
trade.contract_pdf_url = pdf_url
```

### STEP 5: Notify Parties

```python
# Email both parties
send_email(
    to=[buyer_email, seller_email],
    subject=f"Contract Ready for Signature - {trade.trade_number}",
    body="Your trade contract is ready. Please review and sign.",
    attachments=[contract_pdf]
)

# SMS notification
send_sms(
    to=[buyer_phone, seller_phone],
    message=f"Contract {trade.trade_number} ready for signature. Check email."
)

# Update status
trade.status = "PENDING_SIGNATURE"
```

---

## 📋 FINAL DATABASE SCHEMA

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_number VARCHAR(50) UNIQUE NOT NULL,
    negotiation_id UUID NOT NULL REFERENCES negotiations(id),
    
    -- Parties
    buyer_id UUID NOT NULL REFERENCES business_partners(id),
    seller_id UUID NOT NULL REFERENCES business_partners(id),
    
    -- Commodity
    commodity_id UUID NOT NULL REFERENCES commodities(id),
    commodity_variety VARCHAR(100),
    
    -- Price & Quantity (FROZEN)
    price_per_unit DECIMAL(15,2) NOT NULL,
    quantity DECIMAL(15,3) NOT NULL,
    unit_of_measure VARCHAR(20) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    
    -- Delivery Terms (FROZEN)
    delivery_location JSONB NOT NULL,
    delivery_date DATE NOT NULL,
    delivery_window_days INTEGER,
    delivery_terms VARCHAR(50) NOT NULL,  -- FOB/CIF/EXW
    transportation_mode VARCHAR(50),
    freight_charges_borne_by VARCHAR(20),
    
    -- Payment Terms (FROZEN)
    payment_method VARCHAR(50) NOT NULL,
    payment_terms TEXT NOT NULL,
    advance_percentage DECIMAL(5,2) NOT NULL,
    advance_due_days INTEGER,
    balance_payment_trigger VARCHAR(50),
    balance_due_days INTEGER,
    late_payment_penalty DECIMAL(5,2),
    
    -- Quality Specifications (FROZEN)
    quality_parameters JSONB NOT NULL,
    testing_method VARCHAR(100),
    tolerance_allowed DECIMAL(5,2),
    
    -- Inspection Terms (FROZEN)
    inspection_terms JSONB NOT NULL,
    inspection_location VARCHAR(100),
    quality_rejection_terms JSONB,
    
    -- Legal Terms (FROZEN)
    governing_law VARCHAR(200),
    jurisdiction VARCHAR(100),
    dispute_resolution_method VARCHAR(50),
    arbitration_location VARCHAR(200),
    force_majeure_terms JSONB,
    
    -- Penalty Terms (FROZEN)
    penalty_terms JSONB NOT NULL,
    late_delivery_penalty JSONB,
    cancellation_terms JSONB,
    
    -- Immutability
    contract_hash VARCHAR(64) NOT NULL,
    terms_locked_at TIMESTAMP NOT NULL,
    contract_pdf_url TEXT,
    
    -- Status
    status VARCHAR(50) NOT NULL,  -- DRAFT/PENDING_SIGNATURE/ACTIVE/COMPLETED/CANCELLED
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signed_at TIMESTAMP,
    activated_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT valid_status CHECK (status IN (
        'DRAFT', 'PENDING_SIGNATURE', 'ACTIVE', 
        'IN_TRANSIT', 'DELIVERED', 'QUALITY_CHECK',
        'COMPLETED', 'CANCELLED', 'DISPUTED'
    ))
);

-- Signatures table
CREATE TABLE trade_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id),
    user_id UUID NOT NULL REFERENCES users(id),
    signature_type VARCHAR(20) NOT NULL,  -- BUYER/SELLER
    signature_data TEXT NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(trade_id, signature_type)
);

-- Milestones for other modules
CREATE TABLE trade_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id),
    milestone_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- PENDING/COMPLETED/FAILED
    completed_by UUID REFERENCES users(id),
    completed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events for audit trail
CREATE TABLE trade_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    created_by UUID REFERENCES users(id),
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_trades_negotiation ON trades(negotiation_id);
CREATE INDEX idx_trades_buyer ON trades(buyer_id);
CREATE INDEX idx_trades_seller ON trades(seller_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trade_events_trade ON trade_events(trade_id);
CREATE INDEX idx_trade_milestones_trade ON trade_milestones(trade_id);
```

---

## 📁 FINAL FILE STRUCTURE

```
backend/modules/trade_desk/
├── models/
│   ├── trade.py                      # Trade model (400 lines)
│   ├── trade_signature.py            # Signature model (100 lines)
│   ├── trade_milestone.py            # Milestone model (100 lines)
│   └── trade_event.py                # Event model (100 lines)
│
├── services/
│   ├── trade_validation_service.py   # ✅ NEW! Validate terms (300 lines)
│   ├── trade_service.py              # Create/manage trades (500 lines)
│   ├── contract_pdf_service.py       # Generate PDF (400 lines)
│   └── trade_notification_service.py # Email/SMS (200 lines)
│
├── schemas/
│   └── trade_schemas.py              # Request/response (300 lines)
│
└── routes/
    └── trade_routes.py               # API endpoints (300 lines)

backend/db/migrations/versions/
└── xxx_add_trades_tables.py          # Migration (250 lines)

Total: ~2,950 lines
Time: 4-5 hours
```

---

## 🔌 API ENDPOINTS

```python
# 1. Validate negotiation for trade
GET /api/trades/validate/{negotiation_id}
Response: {
    "valid": true/false,
    "missing_terms": [],
    "completeness_score": 100
}

# 2. Create trade from negotiation
POST /api/trades/create
Body: { "negotiation_id": "..." }
Response: { "trade_id": "...", "status": "DRAFT" }

# 3. Get trade details
GET /api/trades/{trade_id}
Response: { full trade object with all terms }

# 4. Download contract PDF
GET /api/trades/{trade_id}/contract.pdf

# 5. Sign trade
POST /api/trades/{trade_id}/sign
Body: { "signature": "..." }
Response: { "signed": true, "status": "ACTIVE" }

# 6. List user's trades
GET /api/trades/my-trades?status=ACTIVE

# 7. Update trade status
PUT /api/trades/{trade_id}/status
Body: { "status": "COMPLETED" }

# 8. Record milestone
POST /api/trades/{trade_id}/milestones
Body: { "type": "ADVANCE_PAID", "amount": 107250 }

# 9. Get trade events (audit log)
GET /api/trades/{trade_id}/events

# 10. Admin - List all trades
GET /api/admin/trades?status=ACTIVE&date_from=2025-12-01
```

---

## ✅ FINAL SUMMARY

### What Trade Engine Does:

1. **✅ Validates Terms & Conditions**
   - All 13 categories checked
   - Ensures negotiation is COMPLETE
   - Blocks incomplete contracts

2. **✅ Creates Legal Contract**
   - Freezes all negotiated terms
   - Generates immutable hash
   - Creates professional PDF

3. **✅ Manages Signatures**
   - Digital signature collection
   - Both parties must sign
   - Contract becomes binding

4. **✅ Tracks Lifecycle**
   - Status progression
   - Milestone tracking
   - Complete audit trail

5. **✅ Provides Integration Hooks**
   - `trade_id` for all modules
   - Milestone events
   - Status updates

### What Trade Engine Does NOT Do:

❌ AI fraud detection (Risk Engine)
❌ Price validation (Risk Engine)
❌ Admin approval (User only)
❌ Quality inspection (Quality Module)
❌ Logistics tracking (Logistics Module)
❌ Payment processing (Payment Module)

---

## 🚀 READY TO START?

**Implementation Plan**:
- **Phase 5A**: Core trade engine (2,950 lines, 4-5 hours)
- **Files**: 10 files (models, services, schemas, routes, migration)
- **Database**: 4 tables
- **API**: 10 endpoints

**SHALL I START PHASE 5A NOW?** 🎯
