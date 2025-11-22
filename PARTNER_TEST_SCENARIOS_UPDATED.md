# Business Partner Module - UPDATED Test Scenarios (For Review)

**Date:** November 22, 2025  
**Status:** 🔍 PENDING APPROVAL - DO NOT DEPLOY  
**Changes:** M-Parivahan API Integration + No-PAN Declaration for Commission Agents

---

## KEY UPDATES FOR REVIEW

### 1. ✅ Lorry Owner - M-Parivahan API Integration
- Vehicle RC verification via M-Parivahan API
- Auto-fetch vehicle details (owner, maker, model, capacity, fitness, insurance expiry)
- Real-time verification during onboarding
- Fallback to manual upload if API unavailable

### 2. ✅ Commission Agent - No-PAN Declaration Option
- Can proceed WITHOUT PAN card
- Must upload "No-PAN Declaration" document
- Declaration reason required
- Only GST (if applicable) + Cancelled Cheque + Declaration

---

## UPDATED TEST SCENARIOS

## 6. Transporter - Lorry Owner (WITH M-PARIVAHAN API)

### Test ID: TRANS_LORRY_001

### Business Context
- Owns 10 trucks
- Transports cotton Gujarat to Maharashtra
- Vehicle verification via M-Parivahan API

### Required Documents (Lorry Owner)
1. ✅ **GST Certificate** (if applicable)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **Vehicle RC** (verified via M-Parivahan API)
5. ✅ **Vehicle Insurance** (verified via M-Parivahan API)
6. ✅ **Fitness Certificate** (verified via M-Parivahan API)
7. ✅ **Permits** (All India Permit - manual upload)

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "transporter",
  "country": "India",
  "legal_name": "Gujarat Roadways Pvt Ltd",
  "gstin": "24AAACC9999F1Z9",
  "pan_number": "AAACC9999F",
  "bank_account_name": "Gujarat Roadways Pvt Ltd",
  "bank_name": "ICICI Bank",
  "bank_account_number": "001234567890",
  "bank_routing_code": "ICIC0000123",
  "primary_address": "Transport Nagar, Kalol",
  "primary_city": "Kalol",
  "primary_state": "Gujarat",
  "primary_postal_code": "382721",
  "primary_country": "India",
  "primary_contact_name": "Vijay Sharma",
  "primary_contact_email": "vijay@gujaratroadways.com",
  "primary_contact_phone": "+919898989898",
  "service_details": {
    "transporter_type": "lorry_owner",
    "operates_from_city": "Kalol",
    "operates_from_state": "Gujarat",
    "commodities_transported": ["cotton", "cotton_bales"],
    "routes": ["Gujarat-Maharashtra", "Gujarat-MP"],
    "fleet_size": 10,
    "vehicle_types": ["20-ton truck", "24-ton truck"]
  }
}
```

**Expected Result:**
- ✅ `transporter_type`: `lorry_owner` recorded
- ✅ System prompts for vehicle addition
- ✅ Vehicle verification flow enabled

#### Step 2: Upload Base Documents
- GST Certificate
- PAN Card
- Cancelled Cheque

**Expected Result:**
- ✅ Base documents verified
- ✅ Status: `pending_vehicles`
- ✅ UI shows "Add Vehicles" section

#### Step 3: Add Vehicle #1 with M-Parivahan Verification
```json
POST /api/v1/partners/{partner_id}/vehicles/verify
{
  "vehicle_number": "GJ01AB1234",
  "chassis_number": "MAT123456789012345"
}
```

**Expected Backend Flow:**
1. System calls M-Parivahan API (vahan.parivahan.gov.in)
2. API Request:
```json
{
  "regn_no": "GJ01AB1234",
  "chassis_no": "MAT123456789012345"
}
```

3. API Response (Success):
```json
{
  "status": "success",
  "data": {
    "registration_number": "GJ01AB1234",
    "owner_name": "GUJARAT ROADWAYS PVT LTD",
    "chassis_number": "MAT123456789012345",
    "maker_model": "TATA LPT 2518",
    "vehicle_class": "GOODS CARRIER",
    "fuel_type": "DIESEL",
    "color": "YELLOW",
    "seating_capacity": "3",
    "unladen_weight": "7000",
    "gross_vehicle_weight": "25000",
    "registration_date": "2022-03-15",
    "fitness_valid_upto": "2026-03-14",
    "insurance_valid_upto": "2025-12-31",
    "insurance_company": "National Insurance Company",
    "insurance_policy_number": "NIC/2024/12345",
    "permit_type": "All India",
    "permit_valid_upto": "2026-03-14",
    "rto_code": "GJ01",
    "rto_name": "Ahmedabad RTO"
  }
}
```

**Expected Frontend Result:**
- ✅ Vehicle details auto-populated
- ✅ Owner name validated against company name
- ✅ Fitness expiry displayed: March 14, 2026
- ✅ Insurance expiry displayed: December 31, 2025
- ✅ Permit type confirmed: All India
- ✅ Vehicle status: `verified_via_parivahan`
- ✅ Green checkmark: "✓ Verified via M-Parivahan"

#### Step 3a: M-Parivahan API Failure Scenario
```json
{
  "status": "error",
  "message": "Vehicle not found in registry"
}
```

**Expected Fallback:**
- ⚠️ Warning: "Could not verify via M-Parivahan. Please upload documents manually."
- ✅ System switches to manual upload mode
- ✅ User uploads RC PDF, Insurance PDF, Fitness PDF
- ✅ OCR extracts details from uploaded documents
- ✅ Status: `manual_verification_pending`

#### Step 4: Repeat for All 10 Vehicles
- Add 9 more vehicles using M-Parivahan verification
- Each vehicle verified in real-time
- System tracks:
  - Fitness expiry dates
  - Insurance expiry dates
  - Permit validity

**Expected Result:**
- ✅ All 10 vehicles registered
- ✅ 10/10 verified via M-Parivahan (or manual if API fails)
- ✅ Automated expiry tracking enabled
- ✅ Dashboard shows: "2 vehicles fitness expiring in 90 days"

#### Step 5: Upload Permit Documents
```bash
POST /api/v1/partners/{partner_id}/documents
- Upload All India Permit PDF (common for all vehicles)
```

**Expected Result:**
- ✅ Permit document attached to partner
- ✅ Available for all vehicles

#### Step 6: Submit for Approval

**Expected Result:**
- ✅ Risk score: ~30 (Low - all vehicles verified via govt API)
- ✅ Approval route: **Manager**
- ✅ Email to manager with vehicle verification summary

#### Step 7: Manager Reviews
**Manager sees:**
- ✅ 10 vehicles verified via M-Parivahan
- ✅ All fitness certificates valid for 1+ year
- ✅ All insurance policies active
- ✅ All India permits valid
- ✅ Vehicle ownership confirmed

**Manager Decision:**
```json
POST /api/v1/partners/{partner_id}/approve
{
  "decision": "approve",
  "notes": "All vehicles verified via M-Parivahan API. Strong fleet."
}
```

**Expected Result:**
- ✅ Status: `approved`
- ✅ Partner code: `BP-IND-TRANS-0001`
- ✅ KYC expiry: November 22, 2026

### Verification Checklist
- [ ] M-Parivahan API integration working
- [ ] Vehicle number validation successful
- [ ] Owner name matches company name
- [ ] Maker/model auto-populated
- [ ] Fitness expiry tracked automatically
- [ ] Insurance expiry tracked automatically
- [ ] Permit validity tracked
- [ ] Fallback to manual upload works
- [ ] All 10 vehicles verified
- [ ] Risk score reduced due to govt verification
- [ ] Manager can see M-Parivahan verification status
- [ ] Expiry alerts scheduled for vehicles

### M-Parivahan API Technical Details

**API Endpoint:** `https://vahan.parivahan.gov.in/nrservices/v1/rc-details`

**Request:**
```http
POST /nrservices/v1/rc-details
Content-Type: application/json
Authorization: Bearer {API_TOKEN}

{
  "regn_no": "GJ01AB1234",
  "chassis_no": "MAT123456789012345"
}
```

**Response Fields Used:**
- `owner_name` → Validate against partner company name
- `maker_model` → Auto-fill vehicle details
- `gross_vehicle_weight` → Calculate capacity in tons
- `registration_date` → Vehicle age
- `fitness_valid_upto` → Track fitness expiry
- `insurance_valid_upto` → Track insurance expiry
- `insurance_company` → Insurance provider
- `permit_type` → Permit category
- `permit_valid_upto` → Permit expiry

**Error Handling:**
- API Down → Fallback to manual upload
- Invalid Vehicle → Show error, allow manual entry
- Mismatched Owner → Flag for manual review
- Expired Fitness → Block onboarding, ask to renew first

---

## 7. Transporter - Commission Agent (WITH NO-PAN OPTION)

### Test ID: TRANS_COMM_001

### Business Context
- **Does NOT own vehicles**
- Arranges transport through other lorry owners
- Small operator, may not have PAN card
- **NO VEHICLE DOCS REQUIRED**

### Required Documents (Commission Agent)

**Option A: With PAN**
1. ✅ **GST Certificate** (if applicable)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**

**Option B: Without PAN (NEW)**
1. ✅ **GST Certificate** (if applicable) OR **No-GST Declaration**
2. ❌ **No PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **No-PAN Declaration** (mandatory)

### Test Steps - Option A (With PAN)

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "transporter",
  "country": "India",
  "legal_name": "Mumbai Transport Services",
  "gstin": "27AAACC8888F1Z8",
  "pan_number": "AAACC8888F",
  "bank_account_name": "Mumbai Transport Services",
  "bank_name": "Axis Bank",
  "bank_account_number": "912345678901",
  "bank_routing_code": "UTIB0000123",
  "primary_address": "Shop 12, Transport Market, Turbhe",
  "primary_city": "Navi Mumbai",
  "primary_state": "Maharashtra",
  "primary_postal_code": "400705",
  "primary_country": "India",
  "primary_contact_name": "Anil Patil",
  "primary_contact_email": "anil@mumbaits.com",
  "primary_contact_phone": "+919922334455",
  "service_details": {
    "transporter_type": "commission_agent",
    "operates_from_city": "Navi Mumbai",
    "operates_from_state": "Maharashtra",
    "commodities_transported": ["cotton", "yarn"],
    "routes": ["Maharashtra-Gujarat", "Maharashtra-MP"]
  }
}
```

**Expected Result:**
- ✅ `transporter_type`: `commission_agent` recorded
- ✅ System does NOT ask for vehicle docs
- ✅ No vehicle registration UI shown
- ✅ Standard 3-document flow

#### Step 2: Upload Documents
- GST Certificate
- PAN Card
- Cancelled Cheque

**Expected Result:**
- ✅ Documents verified
- ✅ Status: `pending_approval`
- ✅ Can submit with only 3 docs

---

### Test Steps - Option B (Without PAN) - NEW SCENARIO

#### Step 1: Start Onboarding (No PAN)
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "transporter",
  "country": "India",
  "legal_name": "Ramesh Transport Agent",
  "has_no_pan": true,
  "no_pan_reason": "proprietorship_below_threshold",
  "proprietor_name": "Ramesh Kumar",
  "proprietor_aadhaar_number": "1234-5678-9012",
  "has_no_gst_declaration": true,
  "declaration_reason": "turnover_below_threshold",
  "bank_account_name": "Ramesh Kumar",
  "bank_name": "State Bank of India",
  "bank_account_number": "12345678901",
  "bank_routing_code": "SBIN0001234",
  "primary_address": "Shop 5, Transport Nagar",
  "primary_city": "Kalyan",
  "primary_state": "Maharashtra",
  "primary_postal_code": "421301",
  "primary_country": "India",
  "primary_contact_name": "Ramesh Kumar",
  "primary_contact_email": "ramesh@transporter.com",
  "primary_contact_phone": "+919876543210",
  "service_details": {
    "transporter_type": "commission_agent",
    "operates_from_city": "Kalyan",
    "operates_from_state": "Maharashtra",
    "commodities_transported": ["cotton"],
    "routes": ["Local-Maharashtra"]
  }
}
```

**Expected Result:**
- ✅ No PAN validation
- ✅ Aadhaar number captured (for KYC)
- ✅ No GST validation
- ✅ System prompts for declarations

#### Step 2: Upload Documents (No-PAN Flow)
1. **No-PAN Declaration** (PDF with reason and undertaking)
   - Document content:
   ```
   DECLARATION FOR NON-AVAILABILITY OF PAN CARD
   
   I, Ramesh Kumar, proprietor of Ramesh Transport Agent, hereby 
   declare that I do not possess a PAN card for the following reason:
   
   [X] Proprietorship with annual turnover below ₹5 lakhs
   [ ] Individual not liable to income tax
   [ ] Applied for PAN, awaiting allotment
   
   I undertake to obtain PAN card within 90 days and update the same.
   
   Aadhaar Number: 1234-5678-9012
   Date: November 22, 2025
   Signature: [Signed]
   ```

2. **No-GST Declaration** (if no GST)
3. **Cancelled Cheque**
4. **Aadhaar Card** (for identity verification)

**Expected Result:**
- ✅ Declaration uploaded successfully
- ✅ Reason validated: `proprietorship_below_threshold`
- ✅ Aadhaar number extracted and validated
- ✅ Cheque verified against bank account
- ✅ Status: `pending_approval`

#### Step 3: Risk Assessment (No-PAN Case)

**Expected Risk Calculation:**
- Base risk: 40 (commission agent)
- +15 (No PAN card)
- +10 (No GST)
- +5 (Aadhaar-only KYC)
- **Total: 70 (High Risk)**

**Expected Approval Route:**
- ✅ **Director Approval Required** (high risk due to no PAN)
- ✅ Email to director with No-PAN declaration attached

#### Step 4: Director Reviews

**Director sees:**
- ⚠️ No PAN card available
- ⚠️ No GST registration
- ✅ Aadhaar verified
- ✅ No-PAN declaration uploaded
- ✅ Reason: Proprietorship below threshold
- ✅ Bank account verified via cancelled cheque

**Director Decision Options:**

**Option A: Approve with Conditions**
```json
POST /api/v1/partners/{partner_id}/approve
{
  "decision": "approve",
  "notes": "Approved as small commission agent. PAN mandatory within 90 days.",
  "conditions": {
    "pan_mandatory_by": "2026-02-20",
    "max_transaction_limit": 500000,
    "require_pan_before_payment": true
  }
}
```

**Expected Result:**
- ✅ Status: `approved_conditional`
- ✅ Transaction limit: ₹5 lakhs
- ✅ Reminder set for PAN submission (90 days)
- ✅ Auto-suspend if PAN not submitted by Feb 20, 2026

**Option B: Reject**
```json
POST /api/v1/partners/{partner_id}/reject
{
  "decision": "reject",
  "notes": "Company policy requires PAN for all partners"
}
```

#### Step 5: Post-Approval Monitoring (Conditional Approval)

**System Actions:**
- ✅ Send reminder at 60 days: "PAN card due in 30 days"
- ✅ Send reminder at 80 days: "PAN card due in 10 days - URGENT"
- ✅ Send reminder at 90 days: "PAN card overdue - Account will be suspended"
- ✅ Auto-suspend at 91 days if PAN not submitted

**Partner Action: Submit PAN Later**
```json
POST /api/v1/partners/{partner_id}/documents
{
  "document_type": "pan_card",
  "document_url": "{pan_card_pdf_url}"
}
```

**Expected Result:**
- ✅ PAN extracted via OCR
- ✅ PAN verified against name
- ✅ Conditions removed
- ✅ Status: `approved` (fully approved)
- ✅ Transaction limit removed

### Verification Checklist (No-PAN Flow)
- [ ] Can onboard without PAN card
- [ ] No-PAN declaration mandatory
- [ ] Aadhaar number captured
- [ ] Higher risk score for no-PAN partners
- [ ] Director approval required
- [ ] Conditional approval with 90-day deadline
- [ ] Transaction limits enforced
- [ ] Reminders sent at 60/80/90 days
- [ ] Auto-suspend at 91 days if PAN not submitted
- [ ] Can upgrade to full approval by submitting PAN
- [ ] Aadhaar verification working

### No-PAN Declaration Template

**System provides downloadable template:**

```
DECLARATION FOR NON-AVAILABILITY OF PERMANENT ACCOUNT NUMBER (PAN)

Partner Name: _________________________________
Legal Name: ___________________________________
Proprietor/Owner: _____________________________
Aadhaar Number: ________________________________

I/We hereby declare that I/we do not possess a Permanent Account Number 
(PAN) for the following reason(s):

☐ Proprietorship with annual turnover below ₹5,00,000
☐ Individual not liable to income tax under applicable laws
☐ Applied for PAN card, awaiting allotment (Application Number: ________)
☐ Other: _______________________________________________

I/We undertake to:
1. Obtain PAN card within 90 days from the date of approval
2. Submit the PAN details to the company immediately upon receipt
3. Not exceed transaction limit of ₹5,00,000 until PAN is submitted
4. Understand that failure to submit PAN within 90 days may result in 
   suspension of my/our partner account

I/We confirm that the information provided is true and correct to the 
best of my/our knowledge.

Aadhaar Number: _________________________
Date: ___________________________________
Signature: ______________________________
Place: __________________________________

Witness:
Name: ___________________________________
Signature: ______________________________
Date: ___________________________________
```

---

## COMPARISON TABLE

| Feature | Lorry Owner | Commission Agent (With PAN) | Commission Agent (No PAN) |
|---------|-------------|---------------------------|--------------------------|
| **GST** | Required | Required/Optional | Optional |
| **PAN** | Required | Required | NOT Required |
| **Aadhaar** | Optional | Optional | **MANDATORY** |
| **Vehicle Docs** | ✅ Required (M-Parivahan) | ❌ Not Required | ❌ Not Required |
| **No-PAN Declaration** | ❌ | ❌ | ✅ **MANDATORY** |
| **Risk Score** | 30-40 (Low) | 40-50 (Medium) | 60-70 (High) |
| **Approval Route** | Manager | Manager | **Director** |
| **Transaction Limit** | Unlimited | Unlimited | ₹5 Lakhs |
| **PAN Deadline** | - | - | 90 days |
| **Auto-Suspend** | No | No | Yes (if PAN not submitted) |

---

## TECHNICAL IMPLEMENTATION CHECKLIST

### M-Parivahan API Integration
- [ ] API credentials obtained from MoRTH
- [ ] API endpoint configured in settings
- [ ] Request/response models created
- [ ] Error handling implemented (API down, invalid vehicle, etc.)
- [ ] Fallback to manual upload working
- [ ] Owner name validation logic
- [ ] Fitness expiry tracking
- [ ] Insurance expiry tracking
- [ ] Permit expiry tracking
- [ ] Automated reminders for expiries
- [ ] Dashboard showing vehicle verification status

### No-PAN Declaration
- [ ] Schema updated: `has_no_pan`, `no_pan_reason`, `proprietor_aadhaar_number`
- [ ] No-PAN declaration document type added
- [ ] Declaration template created (downloadable)
- [ ] Aadhaar validation logic
- [ ] Conditional approval workflow
- [ ] Transaction limit enforcement
- [ ] 90-day reminder system
- [ ] Auto-suspend logic after 90 days
- [ ] PAN upgrade flow (submit PAN later)
- [ ] Risk scoring updated (+15 for no PAN)

---

## APPROVAL REQUIRED

**Before Deployment, Please Confirm:**

1. ✅ M-Parivahan API integration approach correct?
2. ✅ Vehicle verification flow acceptable?
3. ✅ Fallback to manual upload when API fails - OK?
4. ✅ No-PAN declaration flow appropriate?
5. ✅ 90-day deadline for PAN submission - acceptable?
6. ✅ Transaction limit of ₹5 lakhs for no-PAN partners - correct?
7. ✅ Director approval for no-PAN partners - required?
8. ✅ Auto-suspend after 90 days if no PAN - acceptable?
9. ✅ Aadhaar mandatory for no-PAN partners - OK?
10. ✅ Risk scoring adjustments correct?

**Please review and approve before implementation.**

---

**Status:** 🔍 AWAITING YOUR APPROVAL  
**Next Step:** Your confirmation to proceed with implementation  
**Deployment:** BLOCKED until approval received
