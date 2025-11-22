# Business Partner Module - Comprehensive Test Scenarios

**Last Updated:** November 22, 2025  
**Status:** Ready for Testing

## Overview

This document provides detailed test scenarios for all 11 partner types with **CORRECTED** requirements:
- ✅ Transporters: Commission agents DON'T need vehicle docs (only lorry owners)
- ✅ Brokers/Sub-Brokers: NO license required (only GST if applicable, or PAN)
- ✅ KYC Expiry: System does NOT auto-suspend (only sends notifications)
- ✅ Ship-To Addresses: Buyers can add multiple ship-to locations

---

## Test Scenario Index

1. [India Seller - Ginning Unit](#1-india-seller---ginning-unit)
2. [India Buyer - Spinning Mill](#2-india-buyer---spinning-mill)
3. [India Trader - Both Buy & Sell](#3-india-trader---both-buy--sell)
4. [International Buyer - USA Textile Manufacturer](#4-international-buyer---usa-textile-manufacturer)
5. [International Seller - Egyptian Cotton Exporter](#5-international-seller---egyptian-cotton-exporter)
6. [Transporter - Lorry Owner](#6-transporter---lorry-owner)
7. [Transporter - Commission Agent](#7-transporter---commission-agent)
8. [Broker - Cotton Commodity Broker](#8-broker---cotton-commodity-broker)
9. [Sub-Broker - Working Under Parent Broker](#9-sub-broker---working-under-parent-broker)
10. [Controller - Private Lab](#10-controller---private-lab)
11. [Financer - NBFC](#11-financer---nbfc)
12. [Shipping Agent - CHA License Holder](#12-shipping-agent---cha-license-holder)
13. [Multi-Location Scenarios](#13-multi-location-scenarios)
14. [KYC Renewal Scenarios](#14-kyc-renewal-scenarios)
15. [Amendment Scenarios](#15-amendment-scenarios)

---

## 1. India Seller - Ginning Unit

### Test ID: SELLER_IND_001

### Business Context
- Cotton ginning unit in Gujarat
- Has GST registration
- Production capacity: 50 MT/day
- Can arrange own transport

### Required Documents (India)
1. ✅ **GST Certificate** - Will auto-fetch from GSTIN API
2. ✅ **PAN Card** - Manual upload
3. ✅ **Cancelled Cheque** - Manual upload

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
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

**Expected Result:**
- ✅ GST auto-fetched from GSTIN API
- ✅ Address auto-geocoded
- ✅ Returns `application_id`
- ✅ Status: `pending_documents`

#### Step 2: Upload Documents
```bash
POST /api/v1/partners/onboarding/{application_id}/documents
- Upload PAN Card PDF
- Upload Cancelled Cheque image
```

**Expected Result:**
- ✅ OCR extracts PAN number, validates against entered PAN
- ✅ OCR extracts account number from cheque, validates against bank details
- ✅ Documents status: `verified`

#### Step 3: Submit for Approval
```json
POST /api/v1/partners/onboarding/{application_id}/submit
```

**Expected Result:**
- ✅ Risk score calculated: ~40 (Medium - new seller, Gujarat state risk)
- ✅ Approval route: **Manager** (medium risk)
- ✅ Email sent to manager
- ✅ Status: `pending_approval`

#### Step 4: Manager Approval
```json
POST /api/v1/partners/{partner_id}/approve
{
  "decision": "approve",
  "notes": "Good production capacity, verified location"
}
```

**Expected Result:**
- ✅ Status: `approved`
- ✅ Partner code generated: `BP-IND-SEL-0001`
- ✅ KYC expiry set to: November 22, 2026 (1 year)
- ✅ Email/SMS sent to seller
- ✅ User account activated

### Verification Checklist
- [ ] GST auto-fetched correctly
- [ ] PAN validated from uploaded document
- [ ] Bank account verified from cancelled cheque
- [ ] Geocoding successful (confidence > 90%)
- [ ] Risk score in expected range (35-45)
- [ ] Manager approval flow worked
- [ ] KYC expiry set correctly
- [ ] User can login and see dashboard

---

## 2. India Buyer - Spinning Mill

### Test ID: BUYER_IND_001

### Business Context
- Large spinning mill in Tamil Nadu
- Buys 1000 MT cotton/month
- Needs credit facility
- Has 3 ship-to locations

### Required Documents (India)
1. ✅ **GST Certificate**
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "buyer",
  "country": "India",
  "legal_name": "Coimbatore Spinners Ltd",
  "gstin": "33AAACC5678G1Z1",
  "pan_number": "AAACC5678G",
  "bank_account_name": "Coimbatore Spinners Ltd",
  "bank_name": "State Bank of India",
  "bank_account_number": "12345678901",
  "bank_routing_code": "SBIN0001234",
  "primary_address": "123 Textile Park, Tirupur Road",
  "primary_city": "Coimbatore",
  "primary_state": "Tamil Nadu",
  "primary_postal_code": "641602",
  "primary_country": "India",
  "primary_contact_name": "Suresh Kumar",
  "primary_contact_email": "suresh@coimbatorespinners.com",
  "primary_contact_phone": "+919988776655",
  "commodities": ["cotton"],
  "monthly_purchase_volume": "1000 MT",
  "credit_limit": 50000000,
  "payment_terms_days": 30
}
```

**Expected Result:**
- ✅ Application created
- ✅ Risk score: ~45 (Medium-High - large credit requested)

#### Step 2: Upload Documents & Submit

#### Step 3: Director Approval (High Credit)
```json
POST /api/v1/partners/{partner_id}/approve
{
  "decision": "approve",
  "notes": "Established mill, good financial standing",
  "credit_limit": 50000000,
  "payment_terms_days": 30
}
```

**Expected Result:**
- ✅ Approved with credit limit
- ✅ Status: `approved`

#### Step 4: Add Ship-To Addresses
```json
POST /api/v1/partners/{partner_id}/locations
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
- ✅ Ship-to location added
- ✅ Geocoded automatically
- ✅ Event emitted: `partner.location.added`
- ✅ Visible in buyer's location list

**Repeat for 2 more ship-to addresses**

### Verification Checklist
- [ ] High credit limit required director approval
- [ ] Credit limit saved correctly
- [ ] Can add multiple ship-to addresses
- [ ] Ship-to addresses don't require GST
- [ ] Geocoding successful for all locations
- [ ] Buyer can view all ship-to addresses
- [ ] Ship-to addresses available in order creation

---

## 3. India Trader - Both Buy & Sell

### Test ID: TRADER_IND_001

### Business Context
- Trades both raw cotton and yarn
- Sometimes processes (ginning/spinning)
- Has warehouse + factory

### Test Steps
Similar to Seller + Buyer combined:
- Upload same 3 docs (GST, PAN, Cheque)
- Specify commodities for both buying and selling
- Add both production capacity AND purchase volume
- Can add warehouse AND factory locations

**Key Difference:**
- ✅ `partner_type`: `"trader"`
- ✅ Has fields from both buyer and seller

---

## 4. International Buyer - USA Textile Manufacturer

### Test ID: BUYER_INTL_001

### Business Context
- US-based textile manufacturer
- Imports cotton from India
- No GST (foreign entity)
- Uses EIN (Tax ID)

### Required Documents (International)
1. ✅ **Tax ID Certificate** (EIN in USA)
2. ✅ **Business Registration Certificate**
3. ✅ **Bank Statement** (last 3 months)
4. ✅ **Address Proof** (utility bill/lease agreement)

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "buyer",
  "trade_classification": "importer",
  "country": "USA",
  "legal_name": "Texas Cotton Mills Inc",
  "has_tax_registration": true,
  "tax_id_type": "EIN",
  "tax_id_number": "12-3456789",
  "bank_account_name": "Texas Cotton Mills Inc",
  "bank_name": "Bank of America",
  "bank_account_number": "987654321",
  "bank_routing_code": "026009593",
  "primary_address": "1500 Cotton Drive",
  "primary_city": "Dallas",
  "primary_state": "Texas",
  "primary_postal_code": "75201",
  "primary_country": "USA",
  "primary_contact_name": "John Smith",
  "primary_contact_email": "john@texascotton.com",
  "primary_contact_phone": "+1-214-555-0123",
  "primary_currency": "USD",
  "commodities": ["cotton"],
  "monthly_purchase_volume": "500 MT",
  "credit_limit": 1000000,
  "payment_terms_days": 45
}
```

**Expected Result:**
- ✅ No GST fetch (international)
- ✅ Manual tax ID entry
- ✅ Currency: USD

#### Step 2: Upload International Documents
1. Upload EIN certificate PDF
2. Upload business registration
3. Upload bank statements (3 months)
4. Upload address proof

**Expected Result:**
- ✅ OCR extracts EIN, validates
- ✅ OCR extracts bank account from statement
- ✅ Documents verified

#### Step 3: Risk Assessment
**Expected Result:**
- ✅ Risk score: ~55 (Higher - international, country risk for USA)
- ✅ Approval route: **Director** (international partner)

### Verification Checklist
- [ ] No GST validation attempted
- [ ] Tax ID accepted (non-Indian)
- [ ] International bank details accepted (no IFSC required)
- [ ] Currency set to USD
- [ ] Country risk factor applied
- [ ] Director approval required for international partner

---

## 5. International Seller - Egyptian Cotton Exporter

### Test ID: SELLER_INTL_001

### Business Context
- Egyptian cotton exporter
- Sells to Indian importers
- No GST, uses Egyptian Tax Registry Number

### Required Documents (International)
1. ✅ **Tax ID Certificate**
2. ✅ **Business Registration**
3. ✅ **Bank Statement**
4. ✅ **Address Proof**

### Test Steps
Similar to International Buyer but `partner_type: "seller"` and `trade_classification: "exporter"`

**Key Points:**
- ✅ No production capacity needed (just re-exporting)
- ✅ May have port location instead of factory

---

## 6. Transporter - Lorry Owner

### Test ID: TRANS_LORRY_001

### Business Context
- Owns 10 trucks
- Transports cotton Gujarat to Maharashtra
- Each truck needs RC, Insurance, Fitness

### Required Documents (Lorry Owner)
1. ✅ **GST Certificate** (if applicable)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **Vehicle RC** (for each vehicle)
5. ✅ **Vehicle Insurance** (for each vehicle)
6. ✅ **Fitness Certificate** (for each vehicle)
7. ✅ **Permits** (All India Permit)

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
- ✅ System knows vehicle docs are required

#### Step 2: Upload Base Documents
- GST, PAN, Cancelled Cheque

#### Step 3: Add Vehicles (Repeat for 10 vehicles)
```json
POST /api/v1/partners/{partner_id}/vehicles
{
  "vehicle_number": "GJ01AB1234",
  "vehicle_type": "20-ton truck",
  "capacity_tons": 20,
  "owner_name": "Gujarat Roadways Pvt Ltd",
  "maker_model": "Tata LPT 2518"
}
```

**Expected Result:**
- ✅ Vehicle registered
- ✅ System prompts for RC, Insurance, Fitness docs

#### Step 4: Upload Vehicle Documents
```bash
POST /api/v1/partners/{partner_id}/vehicles/{vehicle_id}/documents
- Upload RC PDF
- Upload Insurance certificate
- Upload Fitness certificate
```

**Expected Result:**
- ✅ OCR extracts vehicle number from RC
- ✅ Validates against entered vehicle number
- ✅ RTO API called to verify (if available)
- ✅ Insurance expiry date extracted
- ✅ Fitness expiry date extracted

#### Step 5: Submit for Approval

**Expected Result:**
- ✅ Risk score: ~35 (Low-Medium - verified vehicles)
- ✅ Approval route: Manager

### Verification Checklist
- [ ] Vehicle documents required for lorry owner
- [ ] All 10 vehicles registered
- [ ] RC verification via RTO API
- [ ] Insurance expiry tracked
- [ ] Fitness expiry tracked
- [ ] Permits uploaded
- [ ] Risk score considers verified fleet

---

## 7. Transporter - Commission Agent

### Test ID: TRANS_COMM_001

### Business Context
- **Does NOT own vehicles**
- Arranges transport through other lorry owners
- Only needs basic business documents
- **NO VEHICLE DOCS REQUIRED**

### Required Documents (Commission Agent)
1. ✅ **GST Certificate** (if applicable)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ❌ **NO Vehicle RC**
5. ❌ **NO Insurance**
6. ❌ **NO Fitness Certificate**

### Test Steps

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

#### Step 2: Upload Only Base Documents
- GST, PAN, Cancelled Cheque

**Expected Result:**
- ✅ No vehicle documents required
- ✅ Can submit with only 3 docs

#### Step 3: Submit for Approval

**Expected Result:**
- ✅ Risk score: ~50 (Medium - commission agent, no owned assets)
- ✅ Approval works without vehicle docs

### Verification Checklist
- [ ] System recognizes commission agent type
- [ ] Vehicle docs NOT required
- [ ] Can't add vehicles (UI disabled or error)
- [ ] Approval works with only 3 docs
- [ ] Risk scoring appropriate for commission agent

---

## 8. Broker - Cotton Commodity Broker

### Test ID: BROKER_001

### Business Context
- Facilitates cotton trades
- Earns commission from both buyer and seller
- **NO BROKER LICENSE REQUIRED**
- Only needs GST (if applicable) or PAN

### Required Documents (Broker)
1. ✅ **GST Certificate** (if has GST) OR **PAN Card** (if no GST)
2. ✅ **Cancelled Cheque**
3. ❌ **NO Broker License**
4. ❌ **NO Exchange Registration**

### Test Steps

#### Step 1: Start Onboarding (With GST)
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "broker",
  "country": "India",
  "legal_name": "Cotton Brokers Pvt Ltd",
  "gstin": "24AAACC7777F1Z7",
  "pan_number": "AAACC7777F",
  "bank_account_name": "Cotton Brokers Pvt Ltd",
  "bank_name": "HDFC Bank",
  "bank_account_number": "50100111222333",
  "bank_routing_code": "HDFC0000456",
  "primary_address": "Broker Street, Cotton Market",
  "primary_city": "Ahmedabad",
  "primary_state": "Gujarat",
  "primary_postal_code": "380001",
  "primary_country": "India",
  "primary_contact_name": "Kiran Shah",
  "primary_contact_email": "kiran@cottonbrokers.com",
  "primary_contact_phone": "+919123456789",
  "service_details": {
    "specialization": ["cotton", "cotton_yarn"],
    "commission_buyer_side": 0.5,
    "commission_seller_side": 0.5
  }
}
```

**Expected Result:**
- ✅ No license fields required
- ✅ Only commission structure needed

#### Step 2: Start Onboarding (Without GST - Below Threshold)
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "broker",
  "country": "India",
  "legal_name": "Rajesh Cotton Broker",
  "has_no_gst_declaration": true,
  "declaration_reason": "turnover_below_threshold",
  "pan_number": "BBBCC1234D",
  "pan_name": "Rajesh Kumar",
  "bank_account_name": "Rajesh Kumar",
  "bank_name": "SBI",
  "bank_account_number": "12341234123412",
  "bank_routing_code": "SBIN0005678",
  "primary_address": "Shop 5, Broker Lane",
  "primary_city": "Rajkot",
  "primary_state": "Gujarat",
  "primary_postal_code": "360001",
  "primary_country": "India",
  "primary_contact_name": "Rajesh Kumar",
  "primary_contact_email": "rajesh@broker.com",
  "primary_contact_phone": "+919876512345",
  "service_details": {
    "specialization": ["cotton"],
    "commission_buyer_side": 1.0,
    "commission_seller_side": 0
  }
}
```

**Expected Result:**
- ✅ Accepts without GST
- ✅ PAN becomes primary identifier
- ✅ No GST declaration uploaded

#### Step 3: Upload Documents
- If has GST: Upload GST certificate, PAN, Cheque
- If no GST: Upload PAN, Cheque, No-GST declaration

**Expected Result:**
- ✅ No broker license asked
- ✅ Submission successful with only GST/PAN + Cheque

### Verification Checklist
- [ ] No broker license required
- [ ] Works with GST + PAN + Cheque
- [ ] Works with only PAN + Cheque (no GST case)
- [ ] Commission structure saved correctly
- [ ] Can specify buyer-side and seller-side commission
- [ ] Approval works without license

---

## 9. Sub-Broker - Working Under Parent Broker

### Test ID: SUB_BROKER_001

### Business Context
- Works as agent of parent broker
- Shares commission with parent
- **NO LICENSE REQUIRED**
- Only needs GST/PAN

### Required Documents (Sub-Broker)
1. ✅ **GST/PAN** (same as broker)
2. ✅ **Cancelled Cheque**
3. ✅ **Parent Broker Agreement** (authorization letter)
4. ❌ **NO License**

### Test Steps

#### Step 1: Parent Broker Onboarding First
- Follow Test Scenario #8 to create parent broker

#### Step 2: Sub-Broker Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "sub_broker",
  "country": "India",
  "legal_name": "Suresh Cotton Agent",
  "pan_number": "CCCDD5678E",
  "pan_name": "Suresh Patel",
  "bank_account_name": "Suresh Patel",
  "bank_name": "ICICI Bank",
  "bank_account_number": "445566778899",
  "bank_routing_code": "ICIC0002345",
  "primary_address": "Near Market Yard",
  "primary_city": "Rajkot",
  "primary_state": "Gujarat",
  "primary_postal_code": "360002",
  "primary_country": "India",
  "primary_contact_name": "Suresh Patel",
  "primary_contact_email": "suresh@agent.com",
  "primary_contact_phone": "+919988112233",
  "service_details": {
    "parent_broker_id": "{parent_broker_partner_id}",
    "commission_share_percentage": 40,
    "specialization": ["cotton"]
  }
}
```

**Expected Result:**
- ✅ Links to parent broker
- ✅ Commission share calculated
- ✅ No license fields

#### Step 3: Upload Documents
- PAN Card
- Cancelled Cheque
- Parent broker authorization letter

**Expected Result:**
- ✅ Parent broker link verified
- ✅ No license required

### Verification Checklist
- [ ] Links to parent broker correctly
- [ ] Commission sharing configured
- [ ] No license required
- [ ] Authorization from parent broker uploaded
- [ ] Can track sub-broker under parent

---

## 10. Controller - Private Lab

### Test ID: CONTROLLER_001

### Business Context
- Private quality testing lab
- Tests cotton fiber parameters
- Accredited by Textile Ministry

### Required Documents (Controller)
1. ✅ **GST Certificate** (if applicable)
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **Lab Accreditation Certificate**
5. ✅ **Equipment Calibration Certificates**
6. ✅ **Inspector Qualification Certificates**
7. ✅ **Lab Insurance**

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "controller",
  "country": "India",
  "legal_name": "Precision Fiber Labs Pvt Ltd",
  "gstin": "27AAACC6666F1Z6",
  "pan_number": "AAACC6666F",
  "bank_account_name": "Precision Fiber Labs Pvt Ltd",
  "bank_name": "HDFC Bank",
  "bank_account_number": "50100999888777",
  "bank_routing_code": "HDFC0000789",
  "primary_address": "Plot 23, Industrial Area",
  "primary_city": "Mumbai",
  "primary_state": "Maharashtra",
  "primary_postal_code": "400001",
  "primary_country": "India",
  "primary_contact_name": "Dr. Amit Mehta",
  "primary_contact_email": "amit@precisionlabs.com",
  "primary_contact_phone": "+912212345678",
  "service_details": {
    "accreditation_body": "NABL",
    "accreditation_number": "TC-1234",
    "parameters_tested": ["UHML", "Micronaire", "Strength", "Uniformity"],
    "equipment": ["HVI", "AFIS"],
    "inspector_count": 5
  }
}
```

#### Step 2: Upload Documents
1. GST, PAN, Cheque
2. Lab accreditation certificate
3. Equipment calibration certs (for HVI, AFIS)
4. Inspector qualification certificates (5 inspectors)
5. Lab insurance policy

**Expected Result:**
- ✅ All documents verified
- ✅ Accreditation number validated
- ✅ Equipment list recorded

### Verification Checklist
- [ ] Lab accreditation required
- [ ] Equipment calibration certs required
- [ ] Inspector qualifications verified
- [ ] Parameters tested recorded
- [ ] Can assign controller to contracts

---

## 11. Financer - NBFC

### Test ID: FINANCER_001

### Business Context
- NBFC providing trade finance
- Finances cotton purchases
- Needs RBI license

### Required Documents (Financer)
1. ✅ **GST Certificate**
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **NBFC License** (RBI)
5. ✅ **Financial Statements** (last 3 years)
6. ✅ **Credit Rating Certificate**
7. ✅ **Board Resolution** (to enter into financing)

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "financer",
  "country": "India",
  "legal_name": "Cotton Finance Corp Ltd",
  "gstin": "27AAACC5555F1Z5",
  "pan_number": "AAACC5555F",
  "bank_account_name": "Cotton Finance Corp Ltd",
  "bank_name": "State Bank of India",
  "bank_account_number": "12345678901234",
  "bank_routing_code": "SBIN0009876",
  "primary_address": "Finance Tower, BKC",
  "primary_city": "Mumbai",
  "primary_state": "Maharashtra",
  "primary_postal_code": "400051",
  "primary_country": "India",
  "primary_contact_name": "Rahul Verma",
  "primary_contact_email": "rahul@cottonfinance.com",
  "primary_contact_phone": "+912267890123",
  "service_details": {
    "nbfc_license_number": "RBI/NBFC/2020/1234",
    "license_valid_till": "2030-12-31",
    "credit_rating": "AA+",
    "rating_agency": "CRISIL",
    "financing_types": ["purchase_finance", "working_capital"]
  }
}
```

#### Step 2: Upload Documents
1. GST, PAN, Cheque
2. NBFC license from RBI
3. Audited financials (3 years)
4. Credit rating certificate
5. Board resolution

**Expected Result:**
- ✅ NBFC license verified
- ✅ Credit rating recorded
- ✅ Financials reviewed

### Verification Checklist
- [ ] NBFC license required
- [ ] License expiry tracked
- [ ] Credit rating recorded
- [ ] Financial strength assessed in risk score
- [ ] Can provide financing to buyers/sellers

---

## 12. Shipping Agent - CHA License Holder

### Test ID: SHIPPING_001

### Business Context
- Customs House Agent
- Handles import/export clearances
- Has CHA license

### Required Documents (Shipping Agent)
1. ✅ **GST Certificate**
2. ✅ **PAN Card**
3. ✅ **Cancelled Cheque**
4. ✅ **CHA License**
5. ✅ **Shipping Line Agreements**
6. ✅ **Port Registration Certificates**

### Test Steps

#### Step 1: Start Onboarding
```json
POST /api/v1/partners/onboarding/start
{
  "partner_type": "shipping_agent",
  "country": "India",
  "legal_name": "Global Shipping Services Pvt Ltd",
  "gstin": "27AAACC4444F1Z4",
  "pan_number": "AAACC4444F",
  "bank_account_name": "Global Shipping Services Pvt Ltd",
  "bank_name": "HDFC Bank",
  "bank_account_number": "50100555444333",
  "bank_routing_code": "HDFC0001111",
  "primary_address": "Port Area, JNPT",
  "primary_city": "Navi Mumbai",
  "primary_state": "Maharashtra",
  "primary_postal_code": "400707",
  "primary_country": "India",
  "primary_contact_name": "Vikram Nair",
  "primary_contact_email": "vikram@globalshipping.com",
  "primary_contact_phone": "+912227123456",
  "service_details": {
    "cha_license_number": "CHA/2015/1234",
    "license_valid_till": "2030-06-30",
    "ports_covered": ["JNPT", "Mumbai Port", "Mundra"],
    "shipping_lines": ["Maersk", "MSC", "CMA CGM"]
  }
}
```

#### Step 2: Upload Documents
1. GST, PAN, Cheque
2. CHA license
3. Shipping line agreements
4. Port registration certificates

**Expected Result:**
- ✅ CHA license verified
- ✅ Ports covered recorded
- ✅ Shipping lines verified

### Verification Checklist
- [ ] CHA license required
- [ ] Port registrations verified
- [ ] Shipping line agreements recorded
- [ ] Can assign to import/export orders

---

## 13. Multi-Location Scenarios

### Test ID: LOCATION_001

### Scenario: Buyer with Multiple Ship-To Addresses

#### Context
Spinning mill has:
- 1 Principal place (Coimbatore - head office)
- 1 Warehouse (Tirupur)
- 2 Ship-to addresses (Factory 1, Factory 2)
- 1 Bill-to address (Accounts office)

#### Test Steps

**Step 1: After Approval, Add Warehouse**
```json
POST /api/v1/partners/{partner_id}/locations
{
  "location_type": "warehouse",
  "location_name": "Tirupur Warehouse",
  "gstin_for_location": "33AAACC5678G1Z1",
  "address": "Plot 10, SIDCO",
  "city": "Tirupur",
  "state": "Tamil Nadu",
  "postal_code": "641604",
  "country": "India",
  "requires_gst": true
}
```

**Expected:**
- ✅ Location added
- ✅ Geocoded
- ✅ GST same as principal (same state)

**Step 2: Add Ship-To Address 1**
```json
POST /api/v1/partners/{partner_id}/locations
{
  "location_type": "ship_to",
  "location_name": "Factory 1 - Spinning Unit",
  "address": "123 Factory Road",
  "city": "Coimbatore",
  "state": "Tamil Nadu",
  "postal_code": "641601",
  "country": "India",
  "contact_person": "Ravi",
  "contact_phone": "+919876543210",
  "requires_gst": false
}
```

**Expected:**
- ✅ Ship-to added
- ✅ No GST required
- ✅ Contact person saved

**Step 3: Get All Locations**
```bash
GET /api/v1/partners/{partner_id}/locations
```

**Expected Response:**
```json
[
  {
    "id": "...",
    "location_type": "warehouse",
    "location_name": "Tirupur Warehouse",
    ...
  },
  {
    "id": "...",
    "location_type": "ship_to",
    "location_name": "Factory 1 - Spinning Unit",
    ...
  },
  {
    "id": "...",
    "location_type": "ship_to",
    "location_name": "Factory 2 - Weaving Unit",
    ...
  }
]
```

#### Verification
- [ ] Can add unlimited ship-to addresses
- [ ] Each location geocoded
- [ ] Ship-to addresses don't require GST
- [ ] Contact persons saved per location
- [ ] Locations visible in order creation flow

---

## 14. KYC Renewal Scenarios

### Test ID: KYC_RENEWAL_001

### Scenario: KYC Expiry Notifications (NO Auto-Suspend)

#### Context
Partner approved on Nov 22, 2024. KYC expires Nov 22, 2025.

#### Test Timeline

**Day 1: 90 Days Before Expiry (Aug 24, 2025)**
- ✅ Daily job runs at 9 AM
- ✅ Email/SMS sent: "KYC expires in 90 days"
- ✅ Status remains: `approved`
- ✅ **NO suspension**

**Day 2: 60 Days Before Expiry (Sep 23, 2025)**
- ✅ Email/SMS: "KYC expires in 60 days"
- ✅ Status: `approved`

**Day 3: 30 Days Before Expiry (Oct 23, 2025)**
- ✅ Email/SMS: "KYC expires in 30 days - URGENT"
- ✅ Status: `approved`

**Day 4: 7 Days Before Expiry (Nov 15, 2025)**
- ✅ Email/SMS: "KYC expires in 7 days - CRITICAL"
- ✅ Status: `approved`

**Day 5: Expiry Date (Nov 22, 2025)**
- ✅ Daily job runs at 00:01 AM
- ✅ Email/SMS: "KYC has EXPIRED - Please renew immediately"
- ✅ Status: **STILL `approved`** (NO auto-suspend)
- ✅ Event emitted: `KYCExpiredEvent`
- ✅ Dashboard shows warning

**Day 6: Post-Expiry (Nov 23, 2025)**
- ✅ Partner can still transact
- ✅ Dashboard shows red warning
- ✅ Emails continue every 7 days
- ✅ **Manual suspension required by admin**

#### Verification
- [ ] 90-day notification sent
- [ ] 60-day notification sent
- [ ] 30-day notification sent
- [ ] 7-day notification sent
- [ ] Expiry notification sent
- [ ] **System does NOT auto-suspend**
- [ ] Partner can still login and transact
- [ ] Dashboard shows KYC expired warning
- [ ] Admin can manually suspend if needed

### Test ID: KYC_RENEWAL_002

### Scenario: Partner Initiates KYC Renewal

#### Test Steps

**Step 1: Partner Initiates Renewal (Before Expiry)**
```json
POST /api/v1/partners/{partner_id}/kyc/renew
```

**Expected:**
- ✅ KYC renewal record created
- ✅ Status: `renewal_in_progress`
- ✅ Documents re-upload UI shown

**Step 2: Re-upload Documents**
- Upload fresh GST certificate
- Upload updated bank statement
- Upload new cancelled cheque

**Step 3: Re-verification**
- ✅ GST re-fetched from API
- ✅ Bank account re-verified
- ✅ Risk score re-calculated

**Step 4: Approval**
- ✅ Auto-approved if low risk
- ✅ Manager approval if medium/high risk

**Step 5: KYC Renewed**
- ✅ `kyc_expiry_date` extended by 1 year
- ✅ Status: `approved`
- ✅ Email/SMS: "KYC renewed successfully"

#### Verification
- [ ] Renewal can be initiated before expiry
- [ ] Documents re-upload flow works
- [ ] Auto-approval for low-risk renewals
- [ ] KYC expiry extended correctly
- [ ] Notification sent on renewal

---

## 15. Amendment Scenarios

### Test ID: AMENDMENT_001

### Scenario: Change Bank Account

#### Test Steps

**Step 1: Request Amendment**
```json
POST /api/v1/partners/{partner_id}/amendments
{
  "amendment_type": "change_bank",
  "reason": "Closed old account, opened new account in same bank",
  "new_value": {
    "bank_account_number": "NEW123456789",
    "bank_routing_code": "HDFC0000999"
  },
  "supporting_documents": ["{new_cancelled_cheque_doc_id}"]
}
```

**Expected:**
- ✅ Amendment request created
- ✅ Status: `pending_approval`
- ✅ Risk assessed: Low (same bank)
- ✅ Approval route: Manager

**Step 2: Manager Approval**
```json
POST /api/v1/partners/amendments/{amendment_id}/approve
{
  "notes": "Verified new cancelled cheque"
}
```

**Expected:**
- ✅ Bank details updated
- ✅ Amendment status: `approved`
- ✅ Old bank details saved in `old_value`
- ✅ Audit trail maintained

#### Verification
- [ ] Amendment request created
- [ ] Supporting docs attached
- [ ] Risk-based routing works
- [ ] Old values preserved
- [ ] Partner notified

---

## Test Execution Checklist

### Pre-Testing Setup
- [ ] Database reset with fresh migrations
- [ ] Test organization created
- [ ] Test users created (manager, director, external)
- [ ] Email/SMS services configured (or mocked)
- [ ] External APIs mocked (GST, RTO, Geocoding)
- [ ] Scheduler running

### Testing Sequence
1. [ ] Run all 11 partner type scenarios in order
2. [ ] Run multi-location scenarios
3. [ ] Run KYC renewal scenarios
4. [ ] Run amendment scenarios
5. [ ] Run negative test cases (invalid data, missing docs)
6. [ ] Run performance tests (100 partners, 1000 locations)

### Post-Testing Verification
- [ ] All partner types created successfully
- [ ] Documents verified correctly
- [ ] Risk scores in expected ranges
- [ ] Approval flows worked
- [ ] Notifications sent correctly
- [ ] KYC expiry tracking works
- [ ] NO auto-suspension on KYC expiry
- [ ] Locations added successfully
- [ ] Ship-to addresses available in orders
- [ ] Audit trail complete

---

## Known Corrections Applied

1. ✅ **Transporter - Commission Agent**: NO vehicle docs required
2. ✅ **Broker/Sub-Broker**: NO license required, only GST/PAN
3. ✅ **KYC Expiry**: System does NOT auto-suspend, only sends notifications
4. ✅ **Ship-To Addresses**: Buyers can add multiple ship-to locations via API

---

## Success Criteria

### Functional
- [ ] All 11 partner types onboard successfully
- [ ] Document requirements correct for each type
- [ ] Risk scoring appropriate
- [ ] Approval routing correct
- [ ] KYC tracking works
- [ ] NO auto-suspension on KYC expiry
- [ ] Location management works

### Technical
- [ ] All APIs respond < 500ms
- [ ] No database errors
- [ ] Event system working
- [ ] Notifications sent correctly
- [ ] Geocoding successful
- [ ] OCR extraction accurate

### Business
- [ ] Correct documents for India vs International
- [ ] Lorry owners vs commission agents differentiated
- [ ] Brokers work without license
- [ ] Ship-to addresses available
- [ ] Manual KYC suspension control

---

**Document Status:** ✅ Ready for Testing  
**Last Review:** November 22, 2025  
**Next Review:** After first test run
