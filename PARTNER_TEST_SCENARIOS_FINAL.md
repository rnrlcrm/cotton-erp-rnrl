# Business Partner Module - FINAL CORRECTED Test Scenarios

**Date:** November 22, 2025  
**Status:** ✅ CORRECTED - Ready for Review  

---

## CRITICAL CORRECTIONS APPLIED

### 1. ✅ Mobile OTP Login Flow Added (STEP 0)
- User starts with mobile number
- OTP sent and verified
- Then onboarding begins

### 2. ✅ Payment Terms & Credit Limit REMOVED from Onboarding
- Users CANNOT set payment terms during onboarding
- Users CANNOT request credit limit
- Back office assigns credit limit based on:
  - Risk score
  - AI recommendation
  - Financial assessment

### 3. ✅ Transporter No-GST Declaration Fixed
- If no GST: Must upload declaration on letterhead
- Declaration + PAN + Cancelled Cheque required

### 4. ✅ Amendment Request Validation Added
- System checks all ongoing trades before amendment
- Blocks critical amendments if trades active
- Shows warning with trade count

### 5. ✅ Branch Addition with GST Validation
- Branches in other states require different GSTIN
- System validates GSTIN belongs to same PAN
- All branches under primary partner_id
- No cross-branch trading allowed

---

## COMPLETE ONBOARDING FLOW

### STEP 0: Mobile OTP Login & Registration

#### Test ID: AUTH_001

**Scenario:** New Partner - First Time Registration

#### Step 0a: Mobile Number Entry
```http
POST /api/v1/auth/send-otp
Content-Type: application/json

{
  "mobile_number": "+919876543210",
  "country_code": "+91"
}
```

**Expected Result:**
- ✅ OTP sent via SMS
- ✅ Response: `{"message": "OTP sent", "expires_in": 300}`
- ✅ OTP valid for 5 minutes

**Sample OTP SMS:**
```
Your Cotton ERP OTP is: 123456
Valid for 5 minutes.
Do not share with anyone.
```

#### Step 0b: OTP Verification
```http
POST /api/v1/auth/verify-otp
Content-Type: application/json

{
  "mobile_number": "+919876543210",
  "otp": "123456"
}
```

**Expected Result (New User):**
```json
{
  "status": "new_user",
  "mobile_verified": true,
  "temp_token": "eyJhbGc...",
  "next_step": "complete_profile"
}
```

**Expected Result (Existing User):**
```json
{
  "status": "login_success",
  "user_id": "uuid",
  "partner_id": "uuid",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "onboarding_status": "approved",
  "dashboard_url": "/dashboard"
}
```

#### Step 0c: Complete Basic Profile (New Users Only)
```http
POST /api/v1/auth/complete-profile
Authorization: Bearer {temp_token}
Content-Type: application/json

{
  "full_name": "Ramesh Patel",
  "email": "ramesh@cottongin.com",
  "partner_type": "seller",
  "business_name": "Ahmedabad Cotton Ginners Pvt Ltd",
  "state": "Gujarat"
}
```

**Expected Result:**
- ✅ User account created
- ✅ Temporary profile saved
- ✅ Redirected to full onboarding
- ✅ Response:
```json
{
  "user_id": "uuid",
  "onboarding_application_id": "uuid",
  "status": "profile_created",
  "next_step": "start_onboarding"
}
```

---

## TEST SCENARIO 1: India Seller - Ginning Unit

### Test ID: SELLER_IND_001

### Business Context
- Cotton ginning unit in Gujarat
- Has GST registration
- First time registration via mobile OTP

### STEP 0: Authentication (Covered Above)
- Mobile: +919876543210
- OTP verification ✓
- Profile created ✓

### STEP 1: Start Onboarding
```http
POST /api/v1/partners/onboarding/start
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "partner_type": "seller",
  "country": "India",
  "legal_name": "Ahmedabad Cotton Ginners Pvt Ltd",
  "trade_name": "ACG Cotton",
  "gstin": "24AAACC1234F1Z5",
  "pan_number": "AAACC1234F",
  "bank_account_name": "Ahmedabad Cotton Ginners Pvt Ltd",
  "bank_name": "HDFC Bank",
  "bank_account_number": "50100123456789",
  "bank_routing_code": "HDFC0000123",
  "primary_address": "Plot 15, GIDC Estate, Naroda",
  "primary_city": "Ahmedabad",
  "primary_state": "Gujarat",
  "primary_postal_code": "382330",
  "primary_country": "India",
  "primary_contact_name": "Ramesh Patel",
  "primary_contact_email": "ramesh@acgcotton.com",
  "primary_contact_phone": "+919876543210",
  "commodities": ["cotton", "cotton_seed"],
  "production_capacity": "50 MT per day",
  "can_arrange_transport": true,
  "has_quality_lab": false
}
```

**❌ REMOVED (Not in onboarding):**
- ~~credit_limit~~
- ~~payment_terms_days~~
- ~~payment_terms_preference~~

**Expected Result:**
- ✅ GST auto-fetched from GSTIN API
- ✅ Business details verified
- ✅ Address geocoded
- ✅ Application ID returned
- ✅ Status: `pending_documents`

### STEP 2: Upload Documents
```http
POST /api/v1/partners/onboarding/{application_id}/documents
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

document_type=gst_certificate
file=gst_cert.pdf
```

**Documents Required:**
1. GST Certificate
2. PAN Card
3. Cancelled Cheque

**Expected Result:**
- ✅ OCR extracts data
- ✅ Validates against entered details
- ✅ Status updated after all 3 docs uploaded

### STEP 3: Submit for Approval
```http
POST /api/v1/partners/onboarding/{application_id}/submit
Authorization: Bearer {access_token}
```

**Expected Backend Processing:**
- ✅ Risk score calculated (based on docs, GST turnover, location)
- ✅ AI analyzes application
- ✅ Approval route determined (Manager/Director)
- ✅ **AI suggests credit limit** (NOT shown to user)
- ✅ Email sent to approver

**Expected Result:**
```json
{
  "application_id": "uuid",
  "status": "pending_approval",
  "submitted_at": "2025-11-22T10:30:00Z",
  "message": "Your application is under review. You will be notified within 24-48 hours."
}
```

**❌ NOT SHOWN TO USER:**
- Risk score
- AI credit limit recommendation
- Approval route
- Manager/Director details

### STEP 4: Back Office - Manager Reviews Application

**Manager Dashboard Shows:**
```json
{
  "application_id": "uuid",
  "partner_type": "seller",
  "legal_name": "Ahmedabad Cotton Ginners Pvt Ltd",
  "gstin": "24AAACC1234F1Z5",
  "risk_score": 42,
  "risk_category": "medium",
  "ai_recommendation": {
    "approval": "approve",
    "credit_limit": 10000000,
    "reasoning": "Established business, GST turnover ₹50Cr, good compliance history"
  },
  "documents_verified": true,
  "gst_turnover_last_year": 500000000,
  "business_age_years": 5
}
```

**Manager Decision:**
```http
POST /api/v1/partners/{partner_id}/approve
Authorization: Bearer {manager_token}
Content-Type: application/json

{
  "decision": "approve",
  "notes": "Good production capacity, verified GST",
  "credit_limit": 10000000,
  "payment_terms_days": 30,
  "assigned_by_backoffice": true
}
```

**Expected Result:**
- ✅ Partner status: `approved`
- ✅ Credit limit: ₹1 Crore (assigned by manager)
- ✅ Payment terms: 30 days (assigned by manager)
- ✅ KYC expiry: Nov 22, 2026
- ✅ SMS/Email to partner: "Congratulations! Your account is approved."

---

## TEST SCENARIO 2: India Buyer - Spinning Mill (With Ship-To)

### Test ID: BUYER_IND_001

### STEP 0-3: Same as Seller (Mobile OTP → Onboarding → Submit)

### STEP 4: Back Office Assigns Credit Limit

**Manager sees AI recommendation:**
```json
{
  "ai_recommendation": {
    "credit_limit": 50000000,
    "reasoning": "Large established mill, excellent payment history with suppliers, low risk"
  }
}
```

**Manager approves:**
```json
{
  "decision": "approve",
  "credit_limit": 50000000,
  "payment_terms_days": 30
}
```

### STEP 5: Buyer Adds Ship-To Addresses (Post-Approval)

```http
POST /api/v1/partners/{partner_id}/locations
Authorization: Bearer {buyer_token}
Content-Type: application/json

{
  "location_type": "ship_to",
  "location_name": "Warehouse 1 - Tirupur",
  "address": "Plot 45, SIDCO Industrial Estate",
  "city": "Tirupur",
  "state": "Tamil Nadu",
  "postal_code": "641604",
  "country": "India",
  "contact_person": "Ganesh",
  "contact_phone": "+919876543211",
  "requires_gst": false
}
```

**Expected Result:**
- ✅ Ship-to added
- ✅ Geocoded
- ✅ No GST required for ship-to
- ✅ Available in order creation

---

## TEST SCENARIO 3: Transporter - Commission Agent (No GST)

### Test ID: TRANS_COMM_NO_GST_001

### Business Context
- Commission agent
- No GST registration (turnover below threshold)
- No vehicles owned

### STEP 0: Mobile OTP Login ✓

### STEP 1: Start Onboarding (No GST)
```http
POST /api/v1/partners/onboarding/start

{
  "partner_type": "transporter",
  "country": "India",
  "legal_name": "Ramesh Transport Agent",
  "proprietor_name": "Ramesh Kumar",
  "has_no_gst_declaration": true,
  "declaration_reason": "turnover_below_threshold",
  "pan_number": "BBBCC1234D",
  "pan_name": "Ramesh Kumar",
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

### STEP 2: Upload Documents (No-GST Case)

**Required Documents:**
1. ✅ **No-GST Declaration** (on letterhead - MANDATORY)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**

**No-GST Declaration Format (Letterhead):**
```
[Company Letterhead]

DECLARATION FOR NON-REGISTRATION UNDER GST

To,
Cotton ERP Platform
Date: November 22, 2025

Subject: Declaration for non-availability of GST registration

Dear Sir/Madam,

I, Ramesh Kumar, proprietor of Ramesh Transport Agent, hereby declare that:

1. My business turnover is below the threshold limit for GST registration 
   (₹40 lakhs for services as per current GST regulations)
   
2. I am not registered under the Goods and Services Tax Act, 2017

3. My annual turnover for FY 2024-25: Approximately ₹25,00,000

4. I undertake to inform you immediately if:
   - My turnover exceeds the GST threshold
   - I obtain GST registration for any reason

5. I understand that I may be required to obtain GST registration if my 
   business volume increases

PAN Number: BBBCC1234D
Aadhaar Number: 1234-5678-9012

Place: Kalyan
Date: November 22, 2025

Signature: ____________________
Ramesh Kumar
Proprietor
```

**Upload Process:**
```http
POST /api/v1/partners/onboarding/{application_id}/documents

document_type=no_gst_declaration
file=no_gst_declaration_on_letterhead.pdf
```

**Expected Validation:**
- ✅ Must be on letterhead
- ✅ Must be signed
- ✅ Must state turnover reason
- ✅ Must include PAN number
- ✅ OCR extracts PAN and validates

### STEP 3: Risk Assessment

**Risk Score Calculation:**
- Base: 40 (commission agent)
- +15 (No GST registration)
- Total: 55 (Medium-High)

**Approval Route:**
- ✅ Manager approval (medium-high risk)

### STEP 4: Manager Approval
```json
{
  "decision": "approve",
  "notes": "Small local transporter, declaration valid",
  "transaction_limit_monthly": 1000000,
  "monitor_turnover": true
}
```

**Expected Result:**
- ✅ Approved with monitoring
- ✅ Monthly transaction limit: ₹10 lakhs
- ✅ System monitors volume
- ✅ Alert if approaching GST threshold

---

## TEST SCENARIO 4: Branch Addition (Different State) with Google Maps

### Test ID: BRANCH_ADD_001

### Business Context
- Existing approved partner in Gujarat
- Opening branch in Maharashtra
- Requires new GSTIN for Maharashtra
- **Google Maps validation and tagging mandatory**

### STEP 1: Partner Requests Branch Addition
```http
POST /api/v1/partners/{partner_id}/locations
Authorization: Bearer {partner_token}

{
  "location_type": "branch_different_state",
  "location_name": "Mumbai Branch Office",
  "gstin_for_location": "27AAACC1234F1Z8",
  "address": "Office 123, Andheri East",
  "city": "Mumbai",
  "state": "Maharashtra",
  "postal_code": "400069",
  "country": "India",
  "contact_person": "Suresh Patil",
  "contact_phone": "+912212345678",
  "requires_gst": true
}
```

**Backend Validation Flow:**
1. ✅ Extract PAN from new GSTIN: `AAACC1234F`
2. ✅ Compare with primary PAN: `AAACC1234F`
3. ✅ Call GST API to verify GSTIN is active
4. ✅ Verify business name matches primary
5. ✅ Verify state is different from primary
6. ✅ **Call Google Maps API to geocode address**
7. ✅ **Tag location on Google Maps**
8. ✅ **Store lat/long coordinates**

**Google Maps API Call:**
```python
google_maps_service.geocode_address(
    address="Office 123, Andheri East, Mumbai, Maharashtra, 400069, India"
)
```

**Google Maps Response:**
```json
{
  "status": "OK",
  "results": [{
    "formatted_address": "Office 123, Andheri East, Mumbai, Maharashtra 400069, India",
    "geometry": {
      "location": {
        "lat": 19.1136,
        "lng": 72.8697
      },
      "location_type": "ROOFTOP"
    },
    "place_id": "ChIJYTN9T-C5wjsRww4t5...",
    "types": ["street_address"]
  }],
  "confidence": 95
}
```

**Expected Result (Success):**
```json
{
  "location_id": "uuid",
  "status": "active",
  "gstin_validated": true,
  "pan_matches_primary": true,
  "google_maps_tagged": true,
  "latitude": 19.1136,
  "longitude": 72.8697,
  "geocode_confidence": 95,
  "place_id": "ChIJYTN9T-C5wjsRww4t5...",
  "message": "Branch added successfully with Google Maps validation"
}
```

**Expected Result (Failure - Invalid Address):**
```json
{
  "error": "GEOCODING_FAILED",
  "message": "Could not verify address via Google Maps. Please check address details.",
  "confidence": 30,
  "suggestion": "Please provide more specific address details"
}
```

**Expected Result (Failure - PAN Mismatch):**
```json
{
  "error": "PAN_MISMATCH",
  "message": "GSTIN PAN (XXXXX7890F) does not match primary PAN (AAACC1234F). Branch GSTIN must belong to same business.",
  "primary_pan": "AAACC1234F",
  "branch_pan": "XXXXX7890F"
}
```

### STEP 2: Google Maps Tagging Verification

**System stores complete Google Maps data:**
```sql
INSERT INTO partner_locations (
  id, partner_id, location_type, location_name,
  gstin_for_location, address, city, state, postal_code, country,
  latitude, longitude, geocoded, geocode_confidence,
  google_place_id, location_type_from_google,
  status
) VALUES (
  'uuid', 'partner_id', 'branch_different_state', 'Mumbai Branch Office',
  '27AAACC1234F1Z8', 'Office 123, Andheri East', 'Mumbai', 'Maharashtra', '400069', 'India',
  19.1136, 72.8697, true, 95,
  'ChIJYTN9T-C5wjsRww4t5...', 'street_address',
  'active'
);
```

**Dashboard Map View:**
- ✅ Shows all locations on Google Maps
- ✅ Primary location: Blue marker
- ✅ Branches: Green markers
- ✅ Ship-to addresses: Red markers
- ✅ Click marker shows location details
- ✅ Directions between locations

### STEP 3: Data Isolation Verification

**Database Structure:**
```sql
business_partners (id=primary_partner_id, pan=AAACC1234F, gstin=24AAACC1234F1Z5, state=Gujarat)

partner_locations:
  - id=loc1, partner_id=primary_partner_id, gstin=24AAACC1234F1Z5, state=Gujarat, lat=23.0225, lng=72.5714 (principal)
  - id=loc2, partner_id=primary_partner_id, gstin=27AAACC1234F1Z8, state=Maharashtra, lat=19.1136, lng=72.8697 (branch)
```

**Expected Behavior:**
- ✅ Both locations under same partner_id
- ✅ Each location has its own GSTIN
- ✅ Each location has Google Maps coordinates
- ✅ User sees all locations on map
- ✅ Orders can be created from any location
- ✅ **No cross-branch trading** (enforced in order module)

### STEP 4: Cross-Branch Trading Prevention

**Order Creation Attempt:**
```http
POST /api/v1/orders/create

{
  "seller_partner_id": "partner_A",
  "seller_location_id": "location_Gujarat",
  "buyer_partner_id": "partner_A",  // ❌ SAME PARTNER
  "buyer_location_id": "location_Maharashtra",
  "quantity": 100
}
```

**Expected Validation Error:**
```json
{
  "error": "CROSS_BRANCH_TRADING_NOT_ALLOWED",
  "message": "Cannot create order between branches of same partner",
  "seller_partner_id": "partner_A",
  "buyer_partner_id": "partner_A",
  "rule": "A partner cannot trade with itself across different branches"
}
```

---

## TEST SCENARIO 5: Buyer Adding Ship-To Address (ONLY)

### Test ID: SHIP_TO_BUYER_001

### Business Context
- **Only BUYERS can add ship-to addresses**
- Sellers/Brokers CANNOT add ship-to
- **GST NOT required for ship-to**
- **Google Maps validation mandatory**

### STEP 1: Buyer Adds Ship-To Address
```http
POST /api/v1/partners/{buyer_partner_id}/locations
Authorization: Bearer {buyer_token}

{
  "location_type": "ship_to",
  "location_name": "Factory 1 - Spinning Unit",
  "address": "Plot 45, SIDCO Industrial Estate, Tirupur Road",
  "city": "Coimbatore",
  "state": "Tamil Nadu",
  "postal_code": "641601",
  "country": "India",
  "contact_person": "Ravi Kumar",
  "contact_phone": "+919876543210",
  "requires_gst": false  // Ship-to does NOT need GST
}
```

**Backend Validation:**
1. ✅ Check partner type: Must be "buyer" or "trader"
2. ✅ If not buyer/trader → REJECT
3. ✅ Force requires_gst = false (ship-to never needs GST)
4. ✅ Call Google Maps API
5. ✅ Tag location on map

**Expected Result (Success - Buyer):**
```json
{
  "location_id": "uuid",
  "location_type": "ship_to",
  "location_name": "Factory 1 - Spinning Unit",
  "google_maps_tagged": true,
  "latitude": 11.0168,
  "longitude": 76.9558,
  "geocode_confidence": 92,
  "requires_gst": false,
  "message": "Ship-to address added successfully"
}
```

**Expected Result (Failure - Not a Buyer):**
```http
POST /api/v1/partners/{seller_partner_id}/locations

{
  "location_type": "ship_to",
  ...
}
```

```json
{
  "error": "INVALID_PARTNER_TYPE_FOR_SHIP_TO",
  "message": "Only buyers and traders can add ship-to addresses",
  "partner_type": "seller",
  "allowed_types": ["buyer", "trader"]
}
```

### STEP 2: Ship-To Addresses in Order Creation

**When creating order, buyer selects ship-to:**
```http
POST /api/v1/orders/create

{
  "seller_partner_id": "seller_uuid",
  "buyer_partner_id": "buyer_uuid",
  "buyer_ship_to_location_id": "ship_to_uuid",  // Selected from ship-to list
  "quantity": 100,
  "commodity": "cotton"
}
```

**System uses ship-to for delivery:**
- ✅ Delivery address: Ship-to location
- ✅ Billing address: Primary buyer location
- ✅ Logistics uses ship-to coordinates for routing
- ✅ Invoice shows both addresses

---

## TEST SCENARIO 6: Trader Cross-Trading Prevention

### Test ID: TRADER_CROSS_TRADE_001

### Business Context
- Trader acts as both buyer and seller
- **CANNOT buy AND sell to same party**
- Prevents circular trading and wash trades

### STEP 1: Trader Buys from Party X

**Initial Trade:**
```http
POST /api/v1/contracts/create

{
  "seller_partner_id": "party_x_uuid",
  "buyer_partner_id": "trader_uuid",  // Trader BUYS from Party X
  "quantity": 100,
  "commodity": "cotton"
}
```

**Expected Result:**
```json
{
  "contract_id": "uuid",
  "status": "active",
  "relationship_recorded": "trader_buys_from_party_x"
}
```

### STEP 2: Trader Attempts to Sell to Same Party X (BLOCKED)

**Attempted Trade:**
```http
POST /api/v1/contracts/create

{
  "seller_partner_id": "trader_uuid",  // Trader tries to SELL to Party X
  "buyer_partner_id": "party_x_uuid",  // Same Party X
  "quantity": 50,
  "commodity": "cotton"
}
```

**Backend Validation:**
```python
validator = PartnerBusinessRulesValidator(db)
result = await validator.check_trader_cross_trading(
    trader_partner_id="trader_uuid",
    counterparty_partner_id="party_x_uuid",
    transaction_type="sell"
)
```

**Validation Result:**
```json
{
  "allowed": false,
  "reason": "Trader cannot sell to a party they already buy from (prevents circular trading)",
  "existing_relationship": "buyer",
  "existing_trades_count": 3,
  "total_volume_traded": 300
}
```

**Expected Error Response:**
```json
{
  "error": "CIRCULAR_TRADING_NOT_ALLOWED",
  "message": "Trader cannot sell to Party X. You already have 3 active buy contracts with this party.",
  "rule": "Traders cannot both buy from AND sell to the same counterparty",
  "existing_relationship": "buyer",
  "existing_trades": 3,
  "suggestion": "Please close existing buy contracts before creating sell contracts with this party"
}
```

### STEP 3: Trader Can Sell to Different Party Y (ALLOWED)

**Allowed Trade:**
```http
POST /api/v1/contracts/create

{
  "seller_partner_id": "trader_uuid",  // Trader SELLS
  "buyer_partner_id": "party_y_uuid",  // Different party (not X)
  "quantity": 50,
  "commodity": "cotton"
}
```

**Expected Result:**
```json
{
  "contract_id": "uuid",
  "status": "active",
  "relationship_recorded": "trader_sells_to_party_y",
  "message": "Contract created successfully"
}
```

### Verification Rules

**Trader Trading Matrix:**

| Trader Relationship with Party | Can Buy? | Can Sell? | Reason |
|-------------------------------|----------|-----------|---------|
| No existing trades | ✅ Yes | ✅ Yes | Fresh relationship |
| Already buying from Party X | ✅ Yes | ❌ No | Prevents circular trading |
| Already selling to Party Y | ❌ No | ✅ Yes | Prevents circular trading |

**Database Tracking:**
```sql
-- Track all trader relationships
CREATE TABLE trader_counterparty_relationships (
  id UUID PRIMARY KEY,
  trader_partner_id UUID NOT NULL,
  counterparty_partner_id UUID NOT NULL,
  relationship_type VARCHAR(20), -- 'buyer' or 'seller'
  first_trade_date TIMESTAMP,
  last_trade_date TIMESTAMP,
  total_trades INT,
  total_volume NUMERIC,
  status VARCHAR(20), -- 'active', 'closed'
  UNIQUE(trader_partner_id, counterparty_partner_id)
);
```

---

## TEST SCENARIO 5: Amendment Request with Ongoing Trades Check

### Test ID: AMENDMENT_WITH_TRADES_001

### Business Context
- Partner has 5 ongoing trades
- Wants to change bank account
- System must check impact

### STEP 1: Partner Requests Bank Amendment
```http
POST /api/v1/partners/{partner_id}/amendments
Authorization: Bearer {partner_token}

{
  "amendment_type": "change_bank",
  "reason": "Closed old bank account",
  "new_value": {
    "bank_name": "ICICI Bank",
    "bank_account_number": "NEW123456789",
    "bank_routing_code": "ICIC0001234"
  },
  "supporting_documents": ["{cancelled_cheque_doc_id}"]
}
```

**Backend Processing:**
```python
# Check ongoing trades
ongoing_trades = await check_ongoing_trades(partner_id)

{
  "pending_contracts": 3,
  "active_orders": 2,
  "pending_payments": 5,
  "total_value_at_risk": 25000000
}
```

**Expected Response (Has Ongoing Trades):**
```json
{
  "amendment_id": "uuid",
  "status": "pending_review",
  "warning": {
    "ongoing_trades": true,
    "pending_contracts": 3,
    "active_orders": 2,
    "pending_payments": 5,
    "total_value": 25000000,
    "message": "You have ongoing trades. Bank change requires director approval and will take 7-10 days to process all pending payments."
  },
  "approval_route": "director",
  "estimated_processing_days": 10
}
```

**Expected Response (No Ongoing Trades):**
```json
{
  "amendment_id": "uuid",
  "status": "pending_approval",
  "approval_route": "manager",
  "estimated_processing_days": 2
}
```

### STEP 2: Director Reviews Amendment

**Director Dashboard Shows:**
```json
{
  "amendment_id": "uuid",
  "partner_id": "uuid",
  "amendment_type": "change_bank",
  "old_bank": "HDFC Bank - ****6789",
  "new_bank": "ICICI Bank - ****6789",
  "impact_analysis": {
    "ongoing_trades": 5,
    "pending_payments_count": 5,
    "pending_payments_amount": 25000000,
    "contracts_to_update": 3,
    "estimated_effort_hours": 8,
    "risk_level": "medium"
  },
  "action_required": [
    "Update all pending payment mandates",
    "Notify all active trade counterparties",
    "Update contract bank details",
    "Reverify new bank account"
  ]
}
```

**Director Decision:**
```http
POST /api/v1/partners/amendments/{amendment_id}/approve

{
  "decision": "approve",
  "notes": "Approved. Process all pending payments to old account first, then switch.",
  "processing_instructions": {
    "complete_pending_payments_to_old_account": true,
    "notify_counterparties": true,
    "effective_date": "2025-12-01"
  }
}
```

---

## VERIFICATION MATRIX

| Feature | Status | Test Scenario |
|---------|--------|---------------|
| Mobile OTP Login | ✅ Fixed | AUTH_001 |
| Credit Limit Removed from Onboarding | ✅ Fixed | All scenarios |
| Payment Terms Removed from Onboarding | ✅ Fixed | All scenarios |
| Back Office Assigns Credit/Terms | ✅ Fixed | SELLER_IND_001 |
| No-GST Declaration on Letterhead | ✅ Fixed | TRANS_COMM_NO_GST_001 |
| Branch Addition with GST Validation | ✅ Fixed | BRANCH_ADD_001 |
| PAN Matching Across GSTINs | ✅ Fixed | BRANCH_ADD_001 |
| Cross-Branch Trading Prevention | ✅ Fixed | BRANCH_ADD_001 |
| Amendment with Ongoing Trades Check | ✅ Fixed | AMENDMENT_WITH_TRADES_001 |
| All Branches Under Primary ID | ✅ Fixed | BRANCH_ADD_001 |

---

## API ENDPOINTS SUMMARY

### Authentication
- `POST /auth/send-otp` - Send OTP to mobile
- `POST /auth/verify-otp` - Verify OTP
- `POST /auth/complete-profile` - New user profile

### Onboarding
- `POST /partners/onboarding/start` - Start onboarding (NO credit/payment fields)
- `POST /partners/onboarding/{id}/documents` - Upload docs
- `POST /partners/onboarding/{id}/submit` - Submit for approval

### Back Office
- `POST /partners/{id}/approve` - Approve with credit limit (manager/director)
- `GET /partners/{id}/ai-recommendation` - Get AI credit suggestion

### Locations
- `POST /partners/{id}/locations` - Add branch (validates GST/PAN)
- `GET /partners/{id}/locations` - List all branches

### Amendments
- `POST /partners/{id}/amendments` - Request amendment (checks ongoing trades)
- `POST /amendments/{id}/approve` - Approve amendment

---

**Status:** ✅ ALL CORRECTIONS APPLIED  
**Ready for:** Final Review & Approval  
**Next Step:** Implement after approval
