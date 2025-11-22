# Complete Partner Onboarding Flows - All Scenarios

## 📋 Document Requirements by Partner Type & Country

### **INDIA Partners - Required Documents**

#### **ALL India Partners (Mandatory for All Types)**
1. ✅ **GST Certificate** - 15-digit GSTIN
2. ✅ **PAN Card** - 10-digit PAN
3. ✅ **Cancelled Cheque** - Bank account proof

---

### **OUTSIDE INDIA Partners - Required Documents**

#### **ALL International Partners (Mandatory)**
1. ✅ **Tax ID Document** - Country's tax identification (VAT/TIN/etc.)
2. ✅ **Business Registration Certificate** - Company incorporation proof
3. ✅ **Bank Statement** (last 3 months) - International bank account
4. ✅ **Address Proof** - Utility bill/lease agreement

---

### **Service Providers - Additional Documents**

#### **If Partner Type = TRANSPORTER**
- ✅ GST/Tax ID (as per country)
- ✅ PAN/Tax ID
- ✅ Cancelled Cheque/Bank Statement
- ✅ **Vehicle Registration Certificates (RC)** for ALL vehicles
- ✅ **Insurance Certificates** for ALL vehicles
- ✅ **Fitness Certificates** for commercial vehicles
- ✅ **Driver Licenses** (if individual drivers)
- ✅ **Goods Carriage Permit**

#### **If Partner Type = CONTROLLER (Quality Inspector)**
- ✅ GST/Tax ID
- ✅ PAN/Tax ID
- ✅ Cancelled Cheque/Bank Statement
- ✅ **Lab Accreditation Certificate** (ISO 17025 or equivalent)
- ✅ **Inspector Qualifications** - Degrees, certifications
- ✅ **Equipment Calibration Certificates**
- ✅ **Professional Liability Insurance**

#### **If Partner Type = FINANCER**
- ✅ GST/Tax ID
- ✅ PAN/Tax ID
- ✅ Cancelled Cheque/Bank Statement
- ✅ **NBFC License** (if in India) or equivalent
- ✅ **RBI/Central Bank Approval**
- ✅ **Financial Statements** (last 3 years, audited)
- ✅ **Credit Rating Report**
- ✅ **Board Resolution** for providing credit

#### **If Partner Type = SHIPPING_AGENT**
- ✅ GST/Tax ID
- ✅ PAN/Tax ID
- ✅ Cancelled Cheque/Bank Statement
- ✅ **Customs Broker License**
- ✅ **Shipping Line Agreements** (authorized agent proof)
- ✅ **Port Authority Registration**
- ✅ **Professional Indemnity Insurance**

#### **If Partner Type = BROKER or SUB_BROKER**
- ✅ GST/Tax ID
- ✅ PAN/Tax ID
- ✅ Cancelled Cheque/Bank Statement
- ✅ **Broker License** (if applicable)
- ✅ **Commission Agreement Template**
- ✅ If SUB_BROKER: **Parent Broker Agreement**

---

## 🔄 COMPLETE ONBOARDING FLOWS

---

## **FLOW 1: INDIA SELLER Onboarding**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "seller",
  "country": "India"
}
```

**System Actions**:
1. Displays GST input form
2. User enters: **GSTIN**
3. System calls **GSTN API**:
   - Fetches legal business name
   - Fetches trade name
   - Fetches PAN (auto-extracted from GSTIN)
   - Fetches primary address
   - Fetches all GST-registered locations (branches)
   - Fetches business registration date
4. System calls **Geocoding API**:
   - Geocodes primary address
   - Gets latitude, longitude
   - Calculates confidence (0-1)
   - If confidence >0.90 → auto-verify ✅
5. Creates draft application

**User Sees**:
- Pre-filled business details (from GST)
- Pre-filled locations (from GST)
- Editable fields marked
- Next: Upload documents

---

### **Step 2: Upload Documents (India Seller)**
```
Required Documents:
1. GST Certificate (PDF/Image)
2. PAN Card (PDF/Image)
3. Cancelled Cheque (PDF/Image)

Optional Documents:
4. Address Proof (if location confidence <0.90)
5. FSSAI License (if food/agriculture)
```

**For Each Document**:
```
POST /partners/onboarding/{app_id}/documents
Form Data:
  - file: [binary]
  - document_type: "GST_CERTIFICATE"
```

**System Actions (per document)**:
1. Uploads file to cloud storage (S3/Azure Blob)
2. Runs **OCR** on document:
   - **GST Certificate**: Extract GSTIN, verify matches entered GSTIN
   - **PAN Card**: Extract PAN, verify matches GST-derived PAN
   - **Cancelled Cheque**: Extract account number, IFSC, bank name
3. Calculates OCR confidence
4. If confidence >0.95 → auto-verify ✅
5. Stores document record

**User Sees**:
- Upload progress
- ✅ Document verified (if OCR confidence high)
- ⚠️ Needs review (if OCR confidence low)

---

### **Step 3: Add Seller-Specific Details**
```
Additional Fields for Seller:
- Production capacity (tons/month)
- Commodities traded (cotton varieties)
- Can arrange transport? (yes/no)
- Has quality lab? (yes/no)
- Monthly production volume range
```

---

### **Step 4: Submit for Approval**
```
POST /partners/onboarding/{app_id}/submit
```

**System Risk Scoring**:
```
Risk Factors:
1. Business Vintage (from GST registration date):
   - <6 months: +30 points
   - 6-12 months: +20 points
   - 1-3 years: +10 points
   - >3 years: +0 points

2. Document Verification:
   - All docs verified: +0 points
   - 1 doc pending: +15 points
   - 2+ docs pending: +30 points

3. Location Verification:
   - Confidence >0.90: +0 points
   - Confidence 0.70-0.90: +10 points
   - Confidence <0.70: +20 points

4. Industry Risk (Seller):
   - Cotton trading: +5 points (low risk)
   - New commodity: +15 points (medium risk)

Total Risk Score: 0-100
```

**Approval Routing**:
- **0-30 (Low)**: ✅ Auto-approve
- **31-60 (Medium)**: Manager approval
- **61-80 (High)**: Director approval
- **81-100 (Critical)**: Director + Board approval

---

### **Step 5: Back Office Approval/Rejection**

**Manager/Director Reviews**:
- Business details from GST
- Risk score breakdown
- All documents with verification status
- Production capacity claims
- Commodities

**If APPROVED**:
```
POST /partners/{id}/approve
{
  "approval_notes": "Verified GST, documents clear, low risk"
}
```

**System Actions**:
1. Creates `BusinessPartner` record
2. Sets `kyc_expiry_date = NOW() + 365 days`
3. Sets `status = "active"`
4. Creates primary location (from GST address)
5. Creates additional locations (from GST branches)
6. Sends **approval email** to seller:
   ```
   Subject: ✅ Seller Application Approved
   
   Dear [Contact Person],
   
   Your seller application has been approved!
   
   Business: [Legal Name]
   GSTIN: [GSTIN]
   KYC Valid Until: [Date]
   
   You can now:
   - List your products
   - Receive orders
   - Track shipments
   - Manage inventory
   
   Login: [portal_url]
   ```

**If REJECTED**:
```
POST /partners/{id}/reject
{
  "rejection_reason": "GSTIN verification failed"
}
```

System sends rejection email with reason.

---

## **FLOW 2: OUTSIDE INDIA BUYER Onboarding**

### **Step 1: Start Onboarding (International)**
```
POST /partners/onboarding/start
{
  "partner_type": "buyer",
  "country": "United States"
}
```

**System Actions**:
1. Detects country != India
2. Shows **Tax ID** field (instead of GSTIN)
3. User enters:
   - Tax ID (e.g., EIN for US)
   - Business name (manual entry, no auto-fetch)
   - Business address
4. System geocodes address (Google Maps works globally)
5. Creates draft application

**No GST Auto-Fetch** (not applicable outside India)

---

### **Step 2: Upload Documents (International Buyer)**
```
Required Documents:
1. Tax ID Document (EIN/VAT certificate)
2. Business Registration Certificate
3. Bank Statement (last 3 months)
4. Address Proof (utility bill/lease)

Buyer-Specific (Additional):
5. Credit References (from banks)
6. Purchase Order samples (to verify business)
```

**System OCR**:
- Tax ID Doc: Extract tax ID number
- Bank Statement: Extract account details, bank name
- Address Proof: Extract address, verify matches entered

---

### **Step 3: Add Buyer-Specific Details**
```
Additional Fields for Buyer:
- Requested credit limit (USD/INR)
- Payment terms preference (NET30/NET60/etc.)
- Monthly purchase volume estimate
- Commodities of interest
- Delivery locations
```

---

### **Step 4: Risk Scoring (International Buyer)**
```
Risk Factors:
1. Country Risk:
   - High-risk country (FATF list): +40 points
   - Medium-risk: +20 points
   - Low-risk (US, EU, etc.): +10 points

2. Credit Limit Request:
   - <$50k: +5 points
   - $50k-$200k: +15 points
   - >$200k: +30 points

3. Document Verification:
   - All verified: +0 points
   - Missing/unverified: +20 points per doc

4. Business Vintage:
   - <1 year: +30 points
   - 1-5 years: +15 points
   - >5 years: +0 points

Total: 0-100
```

**Higher approval threshold for international**:
- 0-20: Auto-approve (rare)
- 21-50: Manager + credit team
- 51-80: Director + credit team
- 81-100: Board approval required

---

## **FLOW 3: INDIA TRANSPORTER (Service Provider)**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "transporter",
  "country": "India"
}
```

**Same as Seller**: GST auto-fetch, geocoding

---

### **Step 2: Upload Documents (Transporter)**
```
Required Documents:
1. GST Certificate
2. PAN Card
3. Cancelled Cheque

Service Provider Specific:
4. Vehicle RC (for EACH vehicle)
5. Vehicle Insurance (for EACH vehicle)
6. Fitness Certificate (for commercial vehicles)
7. Goods Carriage Permit
8. Driver Licenses (if applicable)
```

---

### **Step 3: Add Vehicle Details**

**For EACH Vehicle**:
```
POST /partners/{id}/vehicles
{
  "registration_number": "MH12AB1234",
  "vehicle_type": "Container Truck",
  "manufacturer": "Tata",
  "model": "LPT 3723",
  "year_of_manufacture": 2020,
  "capacity_tons": 20,
  "insurance_valid_until": "2025-12-31",
  "fitness_valid_until": "2025-06-30"
}
```

**System Actions**:
1. Calls **RTO Parivahan API**:
   - Verifies registration number
   - Fetches owner name (must match business)
   - Fetches vehicle type, manufacturer, model
   - Fetches registration date
2. Validates insurance not expired
3. Validates fitness certificate not expired
4. Creates `PartnerVehicle` record

**Transporter can add multiple vehicles** (no limit)

---

### **Step 4: Add Transporter-Specific Details**
```
Additional Fields:
- Fleet size (number of owned vehicles)
- Fleet size (number of leased vehicles)
- Service areas (states/regions covered)
- GPS tracking available? (yes/no)
- Insurance coverage amount
- Preferred commodities (cotton, grains, etc.)
```

---

### **Step 5: Risk Scoring (Transporter)**
```
Risk Factors:
1. Vehicle Documentation:
   - All vehicles verified: +0 points
   - 1+ vehicle pending: +20 points
   - Insurance expiring <30 days: +15 points

2. Fleet Size:
   - <5 vehicles: +20 points (small operator)
   - 5-20 vehicles: +10 points
   - >20 vehicles: +0 points (established)

3. Business Vintage:
   - <2 years: +25 points
   - 2-5 years: +10 points
   - >5 years: +0 points

4. GPS Tracking:
   - Yes: +0 points
   - No: +15 points

Total: 0-100
```

---

### **Step 6: Approval**

**Manager Reviews**:
- All vehicle RCs verified
- Insurance validity
- Fleet size vs service areas (realistic?)
- GPS tracking (preferred)

**If Approved**:
- Transporter can bid on shipments
- Can track shipments
- Receives payment after delivery

---

## **FLOW 4: INDIA CONTROLLER (Quality Inspector)**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "controller",
  "country": "India"
}
```

**Same**: GST auto-fetch

---

### **Step 2: Upload Documents (Controller)**
```
Required Documents:
1. GST Certificate
2. PAN Card
3. Cancelled Cheque

Service Provider Specific:
4. Lab Accreditation Certificate (ISO 17025)
5. Equipment Calibration Certificates
6. Inspector Qualifications:
   - Degree certificates
   - Professional certifications
   - Training certificates
7. Professional Liability Insurance
8. Sample Inspection Reports (past work)
```

---

### **Step 3: Add Controller-Specific Details**
```
Additional Fields:
- Lab name and location
- Accreditation body (NABL, etc.)
- Accreditation valid until
- Testing capabilities:
  - Fiber length
  - Micronaire
  - Strength
  - Moisture content
  - Trash content
  - Color grade
- Equipment list:
  - HVI machine (yes/no)
  - Moisture meter (yes/no)
  - Strength tester (yes/no)
- Service areas (states covered)
- Turnaround time (hours/days)
- Inspection fee structure
```

---

### **Step 4: Risk Scoring (Controller)**
```
Risk Factors:
1. Accreditation:
   - NABL/ISO accredited: +0 points
   - Not accredited: +40 points (high risk)

2. Equipment Calibration:
   - All calibrated within 6 months: +0 points
   - Calibration expired: +25 points

3. Professional Liability Insurance:
   - Coverage ≥$100k: +0 points
   - Coverage <$100k: +15 points
   - No insurance: +40 points

4. Experience:
   - >5 years: +0 points
   - 2-5 years: +10 points
   - <2 years: +25 points

Total: 0-100
```

---

### **Step 5: Approval**

**Director Reviews** (Quality-critical role):
- Accreditation certificates
- Equipment calibration dates
- Sample inspection reports (quality check)
- Insurance coverage

**If Approved**:
- Controller receives inspection requests
- Uploads inspection reports
- Gets paid per inspection

---

## **FLOW 5: INDIA FINANCER (Credit Provider)**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "financer",
  "country": "India"
}
```

---

### **Step 2: Upload Documents (Financer)**
```
Required Documents:
1. GST Certificate
2. PAN Card
3. Cancelled Cheque

Service Provider Specific:
4. NBFC License (RBI approval)
5. Certificate of Registration
6. Financial Statements (last 3 years, audited):
   - Balance sheet
   - P&L statement
   - Cash flow statement
7. Credit Rating Report (from CRISIL/ICRA/CARE)
8. Board Resolution (authorizing credit provision)
9. Capital Adequacy Certificate
10. Net Worth Certificate (CA certified)
```

---

### **Step 3: Add Financer-Specific Details**
```
Additional Fields:
- Total credit portfolio size (INR)
- Available credit for cotton sector (INR)
- Interest rate range (% per annum)
- Credit tenure options (days/months)
- Minimum loan amount
- Maximum loan amount per borrower
- Collateral requirements:
  - Commodity pledge (yes/no)
  - Bank guarantee (yes/no)
  - Personal guarantee (yes/no)
- Processing fee (%)
- Prepayment charges (%)
- Credit appraisal time (days)
```

---

### **Step 4: Risk Scoring (Financer)**
```
Risk Factors:
1. RBI License:
   - Valid NBFC license: +0 points
   - No license: REJECT (cannot proceed)

2. Credit Rating:
   - AAA/AA: +0 points
   - A/BBB: +10 points
   - Below BBB: +30 points
   - No rating: +40 points

3. Net Worth:
   - >₹50 crore: +0 points
   - ₹10-50 crore: +15 points
   - <₹10 crore: +30 points

4. Capital Adequacy Ratio:
   - >15%: +0 points
   - 12-15%: +10 points
   - <12%: +25 points

Total: 0-100
```

---

### **Step 5: Approval**

**Board Review Required** (Financial risk):
- RBI license validity
- Financial statements analysis
- Credit rating
- Capital adequacy
- Loan portfolio quality

**If Approved**:
- Financer can offer credit to buyers/sellers
- Credit terms displayed on platform
- Interest calculated automatically
- Repayment tracking

---

## **FLOW 6: SHIPPING AGENT (International Trade)**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "shipping_agent",
  "country": "India"  // or international
}
```

---

### **Step 2: Upload Documents (Shipping Agent)**
```
Required Documents:
1. GST/Tax ID Certificate
2. PAN/Tax ID
3. Cancelled Cheque/Bank Statement

Service Provider Specific:
4. Customs Broker License (CHA license)
5. Shipping Line Agreements:
   - Maersk authorization
   - MSC authorization
   - CMA CGM authorization
   - etc.
6. Port Authority Registration:
   - Mumbai Port
   - Chennai Port
   - etc.
7. Professional Indemnity Insurance
8. FIATA/IATA membership (if applicable)
```

---

### **Step 3: Add Shipping Agent Details**
```
Additional Fields:
- Customs broker license number
- License valid until
- Authorized ports:
  - Mumbai
  - Chennai
  - Tuticorin
  - etc.
- Shipping lines represented:
  - Maersk
  - MSC
  - Hapag-Lloyd
  - etc.
- Services offered:
  - Customs clearance (yes/no)
  - Documentation (yes/no)
  - Warehousing (yes/no)
  - Container booking (yes/no)
  - Freight forwarding (yes/no)
- Service charges:
  - Customs clearance fee
  - Documentation fee
  - Container booking commission (%)
```

---

### **Step 4: Risk Scoring (Shipping Agent)**
```
Risk Factors:
1. CHA License:
   - Valid license: +0 points
   - No license: REJECT

2. Shipping Line Authorizations:
   - 3+ major lines: +0 points
   - 1-2 lines: +15 points
   - No authorizations: +40 points

3. Port Registrations:
   - Major ports covered: +0 points
   - Limited ports: +20 points

4. Professional Indemnity Insurance:
   - Coverage ≥$500k: +0 points
   - Coverage <$500k: +20 points
   - No insurance: +40 points

Total: 0-100
```

---

### **Step 5: Approval**

**Director Reviews** (Critical for exports/imports):
- CHA license validity
- Shipping line authorizations (verify with lines)
- Port registrations
- Insurance coverage
- Track record

**If Approved**:
- Agent receives shipping requests
- Books containers
- Handles customs clearance
- Gets commission on shipments

---

## **FLOW 7: BROKER / SUB-BROKER**

### **Step 1: Start Onboarding**
```
POST /partners/onboarding/start
{
  "partner_type": "broker",  // or "sub_broker"
  "country": "India"
}
```

---

### **Step 2: Upload Documents (Broker)**
```
Required Documents:
1. GST Certificate
2. PAN Card
3. Cancelled Cheque

Broker Specific:
4. Broker License (if regulated commodity)
5. Commission Agreement Template
6. Professional Liability Insurance (optional)

Sub-Broker Additional:
7. Parent Broker Agreement (authorization letter)
8. Parent Broker GST/details
```

---

### **Step 3: Add Broker-Specific Details**
```
Additional Fields for Broker:
- Broker license number (if applicable)
- License valid until
- Commission rate (%)
- Commission structure:
  - Flat rate (%)
  - Tiered (volume-based)
  - Custom negotiation
- Commodities handled
- Geographic coverage
- Buyer network size (estimate)
- Seller network size (estimate)

Additional for Sub-Broker:
- Parent broker name
- Parent broker GSTIN
- Sub-broker agreement date
- Commission split (% to sub-broker)
```

---

### **Step 4: Approval**

**Manager Reviews**:
- Commission rates (reasonable?)
- Parent broker verification (for sub-broker)
- Network claims

**If Approved (Broker)**:
- Can create deals
- Connects buyers and sellers
- Earns commission on completed trades

**If Approved (Sub-Broker)**:
- Works under parent broker
- Shares commission with parent
- Limited platform access (as per parent agreement)

---

## **FLOW 8: KYC RENEWAL (Yearly for ALL)**

### **90 Days Before Expiry**
```
Automated Job runs daily at 9 AM:
- Checks: kyc_expiry_date = NOW() + 90 days
- Sends EMAIL to partner:
  
  Subject: KYC Renewal Reminder
  
  Dear [Name],
  
  Your KYC expires in 90 days (on [Date]).
  
  Please start the renewal process to avoid service disruption.
  
  Documents needed:
  - Fresh GST certificate (India)
  - Fresh PAN card
  - Fresh cancelled cheque
  - [Service-specific docs if applicable]
  
  [Renew Now Button]
```

### **60 Days Before Expiry**
```
Same email, updated days remaining
```

### **30 Days Before Expiry**
```
EMAIL (High Priority):
  Subject: ⚠️ Important: KYC Expires in 30 Days
  
  URGENT: Your KYC expires in 30 days.
  Renew immediately to avoid account suspension.
```

### **7 Days Before Expiry**
```
EMAIL + SMS (Critical):
  
  Email Subject: ⚠️ URGENT: KYC Expires in 7 Days
  
  SMS: "URGENT: Your Cotton ERP KYC expires in 7 days. 
        Renew now to avoid suspension. Login: [url]"
```

### **On Expiry Date (00:01 AM)**
```
Automated Job:
- Updates status = "suspended"
- Sends EMAIL + SMS:
  
  Subject: Account Suspended - KYC Expired
  
  Your account has been suspended due to expired KYC.
  
  Renew KYC immediately to reactivate.
  
  Impact:
  - No new transactions
  - Existing orders will complete
  - Limited access to platform
```

---

### **Partner Initiates Renewal**
```
POST /partners/{id}/kyc/renew
```

**System**:
1. Creates KYC renewal request
2. Partner uploads fresh documents (same as initial)
3. System verifies documents
4. Back office reviews

---

### **Back Office Completes Renewal**
```
POST /partners/kyc/{renewal_id}/complete
{
  "verification_passed": true
}
```

**System**:
1. Updates `kyc_expiry_date = NOW() + 365 days`
2. Updates `status = "active"` (if was suspended)
3. Sends confirmation email

---

## **FLOW 9: AMENDMENT REQUESTS**

### **Partner Requests Amendment**
```
POST /partners/{id}/amendments
{
  "amendment_type": "bank_change",
  "field_name": "primary_contact_email",
  "old_value": "old@example.com",
  "new_value": "new@example.com",
  "reason": "Email account closed, new email for communication",
  "supporting_documents": [doc_id1, doc_id2]
}
```

### **System Categorizes Risk**

**High-Risk Amendments** (require Director approval):
- Bank account change
- Business address change
- Legal business name change
- Tax ID change

**Medium-Risk** (require Manager approval):
- Contact person change
- Phone/email change
- Credit limit increase request

**Low-Risk** (auto-approve):
- Minor address corrections
- Additional location addition

### **Notification to Back Office**

**High-Risk → Email to Director**:
```
Subject: HIGH RISK Amendment Request - [Partner Name]

Partner: [Legal Name] ([GSTIN])
Amendment: Bank Account Change

Current Account: HDFC Bank - 12345678
Requested Account: ICBC Bank - 87654321

Reason: Switched to new bank for better rates

Supporting Documents: 2 uploaded
Risk Category: High

[Approve] [Reject] [Review Details]
```

**Medium-Risk → Email to Manager**:
```
Subject: Amendment Request - [Partner Name]

Partner: [Legal Name]
Amendment: Contact Email Change

Action required within 24 hours.
```

---

### **Back Office Approves/Rejects**

**If Approved**:
```
POST /partners/amendments/{amendment_id}/approve
```

**System**:
1. Updates field in `BusinessPartner` table
2. Logs change in audit trail (updated_by, updated_at)
3. Sends email to partner:
   ```
   Subject: Amendment Approved
   
   Your request to change [field] has been approved.
   
   New value is now effective: [new_value]
   ```

**If Rejected**:
```
POST /partners/amendments/{amendment_id}/reject
{
  "rejection_reason": "Bank statement does not match new account details"
}
```

**System sends rejection email with reason**

---

## **SUMMARY: Complete Document Checklist**

### **INDIA - ALL PARTNERS**
- [x] GST Certificate
- [x] PAN Card
- [x] Cancelled Cheque

### **OUTSIDE INDIA - ALL PARTNERS**
- [x] Tax ID Document
- [x] Business Registration
- [x] Bank Statement (3 months)
- [x] Address Proof

### **+ TRANSPORTER**
- [x] Vehicle RC (each vehicle)
- [x] Vehicle Insurance (each)
- [x] Fitness Certificate
- [x] Driver Licenses
- [x] Goods Carriage Permit

### **+ CONTROLLER**
- [x] Lab Accreditation (ISO 17025)
- [x] Equipment Calibration Certificates
- [x] Inspector Qualifications
- [x] Professional Liability Insurance

### **+ FINANCER**
- [x] NBFC License (RBI)
- [x] Financial Statements (3 years)
- [x] Credit Rating Report
- [x] Board Resolution
- [x] Net Worth Certificate

### **+ SHIPPING AGENT**
- [x] Customs Broker License
- [x] Shipping Line Agreements
- [x] Port Authority Registration
- [x] Professional Indemnity Insurance

### **+ BROKER**
- [x] Broker License (if applicable)
- [x] Commission Agreement Template

### **+ SUB-BROKER**
- [x] Parent Broker Agreement
- [x] Parent Broker Authorization

---

**All flows follow event-based architecture, automated notifications, risk-based approval routing. Ready for implementation verification!**
