# TRADE ENGINE - SIGNATURE & ADDRESS SOLUTIONS

## 🎯 YOUR TWO QUESTIONS ANSWERED

### QUESTION 1: "From where will it sign? Need provision in user profile to upload digital signature?"

**YES! We need to add signature management to user profile.**

### QUESTION 2: "Once negotiation done, trade ID generated, but any change in ship-to address can be done?"

**YES! We need editable delivery addresses even after trade creation.**

---

## 📝 SOLUTION 1: DIGITAL SIGNATURE IN USER PROFILE

### Current State (BusinessPartner Model):

```python
# backend/modules/partners/models.py
class BusinessPartner(Base):
    """
    Current fields:
    - legal_name
    - trade_name
    - GST, PAN, etc.
    
    MISSING:
    - digital_signature ❌
    - authorized_signatories ❌
    - signature_specimens ❌
    """
```

### What We Need to Add:

```python
# Add to BusinessPartner model
class BusinessPartner(Base):
    # ... existing fields ...
    
    # ============================================
    # DIGITAL SIGNATURE MANAGEMENT (NEW!)
    # ============================================
    
    # Primary authorized signatory
    primary_signatory_name = Column(
        String(200),
        nullable=True,
        comment="Full name of primary authorized person (Managing Director, Partner, Proprietor)"
    )
    
    primary_signatory_designation = Column(
        String(100),
        nullable=True,
        comment="Designation: Managing Director, Partner, Proprietor, CEO, etc."
    )
    
    primary_signatory_mobile = Column(
        String(15),
        nullable=True,
        comment="Mobile number for OTP verification"
    )
    
    primary_signatory_email = Column(
        String(200),
        nullable=True,
        comment="Email for signature notifications"
    )
    
    # Digital signature image
    digital_signature_url = Column(
        String(500),
        nullable=True,
        comment="S3 URL of uploaded signature image (PNG/JPG)"
    )
    
    digital_signature_uploaded_at = Column(
        DateTime,
        nullable=True,
        comment="When signature was uploaded"
    )
    
    # Alternative: Text-based signature
    signature_text = Column(
        String(200),
        nullable=True,
        comment="Typed signature (converted to image with cursive font)"
    )
    
    # Signature verification
    signature_verified = Column(
        Boolean,
        default=False,
        comment="True if signature verified by admin/KYC"
    )
    
    signature_verified_at = Column(
        DateTime,
        nullable=True
    )
    
    signature_verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Admin who verified signature"
    )
    
    # Multiple authorized signatories (for companies)
    authorized_signatories = Column(
        JSON,
        nullable=True,
        server_default=text("'[]'::json"),
        comment="""List of people authorized to sign contracts:
        [
            {
                "name": "Ramesh Kumar",
                "designation": "Managing Director",
                "mobile": "+91-9876543210",
                "email": "ramesh@company.com",
                "signature_url": "s3://...",
                "can_sign_alone": true,
                "max_contract_value": 5000000,
                "added_at": "2025-12-04T10:00:00Z"
            },
            {
                "name": "Suresh Patel",
                "designation": "Director",
                "mobile": "+91-9876543211",
                "email": "suresh@company.com",
                "signature_url": "s3://...",
                "can_sign_alone": false,
                "requires_co_signature_from": ["Ramesh Kumar"],
                "max_contract_value": 2000000,
                "added_at": "2025-12-04T10:00:00Z"
            }
        ]
        """
    )
    
    # Signature authority rules
    signature_rules = Column(
        JSON,
        nullable=True,
        server_default=text("'{}'::json"),
        comment="""Rules for contract signing:
        {
            "single_signature_max_value": 1000000,
            "two_signatures_max_value": 5000000,
            "board_approval_above": 10000000,
            "auto_sign_enabled": true,
            "auto_sign_max_value": 500000
        }
        """
    )
```

---

## 🖼️ SIGNATURE UPLOAD UI (User Profile)

### Screen 1: Upload Signature

```
┌────────────────────────────────────────────────────┐
│  Business Profile → Digital Signature              │
├────────────────────────────────────────────────────┤
│                                                    │
│  Authorized Signatory Details:                    │
│                                                    │
│  Full Name: [Ramesh Kumar__________________]      │
│  Designation: [Managing Director___________]      │
│  Mobile: [+91-9876543210___________________]      │
│  Email: [ramesh@company.com________________]      │
│                                                    │
│  Upload Digital Signature:                        │
│                                                    │
│  Option 1: Upload Image                           │
│  ┌──────────────────────────────────┐            │
│  │  [Browse Files]                  │            │
│  │  Accepted: PNG, JPG              │            │
│  │  Max size: 500 KB                │            │
│  │  Recommended: 300x100 px         │            │
│  └──────────────────────────────────┘            │
│                                                    │
│  Option 2: Draw Signature                         │
│  ┌──────────────────────────────────┐            │
│  │  [Draw on canvas]                │            │
│  │  ___________________________     │            │
│  │                                  │            │
│  │  [Clear] [Save]                  │            │
│  └──────────────────────────────────┘            │
│                                                    │
│  Option 3: Type Your Name (auto-styled)           │
│  [Ramesh Kumar__________________]                 │
│                                                    │
│  Preview:                                         │
│  ┌──────────────────────────────────┐            │
│  │    Ramesh Kumar                  │  👈 Cursive│
│  └──────────────────────────────────┘            │
│                                                    │
│  [Save Signature]                                 │
│                                                    │
│  ⚠️  Your signature will appear on all contracts  │
│     signed by your organization.                  │
└────────────────────────────────────────────────────┘
```

### Screen 2: Manage Multiple Signatories (For Companies)

```
┌────────────────────────────────────────────────────┐
│  Authorized Signatories                            │
├────────────────────────────────────────────────────┤
│                                                    │
│  Primary Signatory:                               │
│  ┌──────────────────────────────────────────────┐ │
│  │ Ramesh Kumar (Managing Director)            │ │
│  │ Can sign alone: ✅                           │ │
│  │ Max value: ₹50,00,000                       │ │
│  │ Signature: [Image preview]                  │ │
│  │ [Edit] [Remove]                             │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  Additional Signatories:                          │
│  ┌──────────────────────────────────────────────┐ │
│  │ Suresh Patel (Director)                     │ │
│  │ Can sign alone: ❌ (Needs co-signature)      │ │
│  │ Max value: ₹20,00,000                       │ │
│  │ Signature: [Image preview]                  │ │
│  │ [Edit] [Remove]                             │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  [+ Add Signatory]                                │
│                                                    │
│  Signature Rules:                                 │
│  • Single signature: Up to ₹10,00,000            │
│  • Two signatures: Up to ₹50,00,000              │
│  • Board approval: Above ₹1,00,00,000            │
│  • Auto-sign: Enabled for contracts <₹5,00,000   │
│                                                    │
│  [Update Rules]                                   │
└────────────────────────────────────────────────────┘
```

---

## 🏠 SOLUTION 2: EDITABLE DELIVERY ADDRESS

### The Problem:

```
Negotiation:
- Delivery: "Ahmedabad" (city only)

But at trade creation, buyer needs:
- Exact address: "Plot 45, GIDC Industrial Area"
- Landmark: "Near Highway Circle"
- Pincode: 380001
- Contact: Ramesh, +91-98765-43210
```

### Solution: Ship-to Address Management

```python
# New table: trade_delivery_addresses
CREATE TABLE trade_delivery_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id),
    
    -- Address type
    address_type VARCHAR(20) NOT NULL,  -- SHIP_TO, BILL_TO, PICKUP_FROM
    
    -- Full address
    address_line1 VARCHAR(200) NOT NULL,
    address_line2 VARCHAR(200),
    landmark VARCHAR(200),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    country VARCHAR(100) DEFAULT 'India',
    
    -- GPS coordinates (optional)
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Contact details
    contact_person_name VARCHAR(200),
    contact_person_mobile VARCHAR(15),
    contact_person_email VARCHAR(200),
    
    -- Warehouse/facility details
    facility_name VARCHAR(200),
    facility_type VARCHAR(50),  -- WAREHOUSE, FACTORY, OFFICE, FARM
    
    -- Accessibility info
    truck_accessible BOOLEAN DEFAULT TRUE,
    loading_dock_available BOOLEAN DEFAULT FALSE,
    operating_hours VARCHAR(100),
    special_instructions TEXT,
    
    -- Change tracking
    is_primary BOOLEAN DEFAULT TRUE,
    changed_from_negotiation BOOLEAN DEFAULT FALSE,
    change_reason TEXT,
    
    -- Approval (if address changed after trade creation)
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by_counterparty BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one primary address per type
    UNIQUE(trade_id, address_type, is_primary) WHERE is_primary = TRUE
);
```

---

## 🔄 COMPLETE FLOW WITH BOTH FEATURES

### Phase 1: User Profile Setup (One-Time)

```
User: Ramesh (First login)

Step 1: Complete KYC
✅ Upload PAN, GST, etc.

Step 2: Upload Digital Signature (NEW!)
┌─────────────────────────────────────┐
│  Upload your signature              │
│  [Browse] or [Draw] or [Type]       │
│                                     │
│  Preview: Ramesh Kumar              │
│                                     │
│  [Save] 👈 Clicks                   │
└─────────────────────────────────────┘

Saved to: business_partners.digital_signature_url
Status: Profile 100% complete ✅
```

### Phase 2: Negotiation (Existing)

```
Ramesh negotiates with Suresh:
- Cotton: 50 quintals @ ₹7,150
- Delivery: "Ahmedabad" 👈 Just city, not full address yet
- Payment: 30% advance

Status: ACCEPTED ✅
```

### Phase 3: Trade Creation with Address (NEW!)

```
System: "Negotiation accepted! Let's create contract..."

Screen shown to Ramesh (Buyer):
┌──────────────────────────────────────────────────┐
│  Confirm Delivery Address                        │
├──────────────────────────────────────────────────┤
│                                                  │
│  Negotiation specified: Ahmedabad               │
│  Please provide exact delivery address:         │
│                                                  │
│  Select from saved addresses:                   │
│  ○ Ramesh Textiles Mill, GIDC (Primary)         │
│  ○ Warehouse 2, Naroda                          │
│  ● Enter new address                            │
│                                                  │
│  Full Address:                                  │
│  Line 1: [Plot 45, GIDC Industrial Area_____]  │
│  Line 2: [Sector 25____________________]       │
│  Landmark: [Near Highway Circle___________]     │
│  City: [Ahmedabad_____] State: [Gujarat___]    │
│  Pincode: [380001___]                          │
│                                                  │
│  Contact Person:                                │
│  Name: [Ramesh Kumar________________]          │
│  Mobile: [+91-9876543210____________]          │
│  Email: [ramesh@company.com_________]          │
│                                                  │
│  Warehouse Details:                             │
│  Facility: [GIDC Textile Mill___________]      │
│  Type: [Factory___]                            │
│  Truck Access: ✅ Yes  ☐ No                     │
│  Loading Dock: ✅ Yes  ☐ No                     │
│  Hours: [9 AM - 6 PM_________________]         │
│                                                  │
│  ☐ Save this address for future use            │
│                                                  │
│  [Continue to Contract] 👈 Clicks               │
└──────────────────────────────────────────────────┘

System actions:
1. Create trade record
2. Save delivery address to trade_delivery_addresses
3. Generate contract PDF with FULL address
4. Auto-sign using Ramesh's uploaded signature
5. Notify Suresh
```

### Phase 4: Contract PDF (With Signature & Address)

```
┌─────────────────────────────────────────────────┐
│        COTTON PURCHASE AGREEMENT                │
│        Contract No: TR-2025-00001               │
├─────────────────────────────────────────────────┤
│                                                 │
│  DELIVERY ADDRESS:                              │
│  Ramesh Textiles Mill                          │
│  Plot 45, GIDC Industrial Area, Sector 25      │
│  Near Highway Circle                           │
│  Ahmedabad, Gujarat - 380001                   │
│  Contact: Ramesh Kumar (+91-9876543210)        │
│                                                 │
│  QUALITY: Moisture <8%, Trash <2.5%            │
│  PAYMENT: 30% advance, 70% on delivery         │
│  ...                                           │
│                                                 │
│  BUYER SIGNATURE:                               │
│  Ramesh Kumar                  👈 From upload   │
│  (Managing Director)                           │
│  Signed on: Dec 4, 2025 10:30 AM              │
│                                                 │
│  SELLER SIGNATURE:                              │
│  Suresh Patel                  👈 From upload   │
│  (Proprietor)                                  │
│  Signed on: Dec 4, 2025 10:32 AM              │
└─────────────────────────────────────────────────┘
```

### Phase 5: Address Change After Contract (If Needed)

```
Scenario: Ramesh realizes address is wrong!

Ramesh's Dashboard:
┌─────────────────────────────────────────────────┐
│  Trade TR-2025-00001                           │
│  Status: ACTIVE                                │
│                                                 │
│  Delivery Address:                             │
│  Plot 45, GIDC, Ahmedabad - 380001            │
│                                                 │
│  [Change Delivery Address]  👈 Clicks           │
└─────────────────────────────────────────────────┘

Change Address Screen:
┌─────────────────────────────────────────────────┐
│  Change Delivery Address                       │
│  ⚠️  Seller must approve this change           │
│                                                 │
│  Current Address:                              │
│  Plot 45, GIDC, Ahmedabad - 380001            │
│                                                 │
│  New Address:                                  │
│  [Plot 78, Naroda Industrial Area______]      │
│  [Ahmedabad, Gujarat - 382330__________]      │
│                                                 │
│  Reason for Change:                            │
│  [Original warehouse full, using backup____]   │
│                                                 │
│  [Request Change] 👈 Clicks                     │
└─────────────────────────────────────────────────┘

Database update:
INSERT INTO trade_delivery_addresses (
    trade_id, address_type,
    address_line1, city, pincode,
    changed_from_negotiation = TRUE,
    requires_approval = TRUE,
    change_reason = "Original warehouse full"
)

Notification to Suresh:
┌─────────────────────────────────────────────────┐
│  🔔 Address Change Request                      │
│                                                 │
│  Ramesh wants to change delivery address:      │
│                                                 │
│  From: Plot 45, GIDC, Ahmedabad - 380001       │
│  To: Plot 78, Naroda, Ahmedabad - 382330       │
│                                                 │
│  Reason: Original warehouse full               │
│                                                 │
│  [Reject]  [Approve] 👈 Suresh clicks           │
└─────────────────────────────────────────────────┘

If Suresh approves:
UPDATE trade_delivery_addresses 
SET approved_by_counterparty = TRUE,
    approved_at = NOW()

New contract addendum generated:
"ADDENDUM TO CONTRACT TR-2025-00001
Delivery address changed with mutual consent
New address: Plot 78, Naroda..."
```

---

## 📊 DATABASE SCHEMA SUMMARY

### 1. Update BusinessPartner Table

```sql
ALTER TABLE business_partners ADD COLUMN IF NOT EXISTS
    primary_signatory_name VARCHAR(200),
    primary_signatory_designation VARCHAR(100),
    primary_signatory_mobile VARCHAR(15),
    primary_signatory_email VARCHAR(200),
    digital_signature_url VARCHAR(500),
    digital_signature_uploaded_at TIMESTAMP,
    signature_text VARCHAR(200),
    signature_verified BOOLEAN DEFAULT FALSE,
    signature_verified_at TIMESTAMP,
    signature_verified_by UUID REFERENCES users(id),
    authorized_signatories JSON DEFAULT '[]',
    signature_rules JSON DEFAULT '{}';
```

### 2. New Trade Delivery Addresses Table

```sql
CREATE TABLE trade_delivery_addresses (
    id UUID PRIMARY KEY,
    trade_id UUID REFERENCES trades(id),
    address_type VARCHAR(20),
    address_line1 VARCHAR(200),
    address_line2 VARCHAR(200),
    landmark VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    contact_person_name VARCHAR(200),
    contact_person_mobile VARCHAR(15),
    facility_name VARCHAR(200),
    truck_accessible BOOLEAN,
    is_primary BOOLEAN,
    changed_from_negotiation BOOLEAN,
    change_reason TEXT,
    requires_approval BOOLEAN,
    approved_by_counterparty BOOLEAN,
    approved_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 3. Address Change Log Table

```sql
CREATE TABLE trade_address_changes (
    id UUID PRIMARY KEY,
    trade_id UUID REFERENCES trades(id),
    old_address_id UUID REFERENCES trade_delivery_addresses(id),
    new_address_id UUID REFERENCES trade_delivery_addresses(id),
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,
    requested_at TIMESTAMP,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    status VARCHAR(20)  -- PENDING, APPROVED, REJECTED
);
```

---

## ✅ IMPLEMENTATION SUMMARY

### What Gets Built:

1. **Signature Management**
   - Upload signature in user profile
   - Multiple signatories support
   - Signature verification by admin
   - Auto-use signature in contracts

2. **Address Management**
   - Full address capture at trade creation
   - Multiple saved addresses per partner
   - Change address with counterparty approval
   - GPS coordinates support
   - Warehouse/facility details

3. **Contract Generation**
   - Use uploaded signature in PDF
   - Show full delivery address
   - Include contact details
   - Professional formatting

4. **Change Management**
   - Request address change
   - Counterparty approval workflow
   - Generate addendum
   - Audit trail

### Files to Create/Modify:

1. **Migration**: Add signature & address fields
2. **Models**: Update BusinessPartner, create TradeDeliveryAddress
3. **Services**: SignatureService, AddressService
4. **Routes**: Upload signature API, address management APIs
5. **Schemas**: Signature & address request/response

### Estimated Effort:
- Signature feature: 2 hours
- Address management: 3 hours
- **Total: 5 hours additional**
- **Grand total with base Trade Engine: 9-10 hours**

---

## 🚀 FINAL QUESTION

**SHALL I START BUILDING TRADE ENGINE WITH:**
1. ✅ Digital signature upload & management
2. ✅ Auto-sign using uploaded signature
3. ✅ Full delivery address capture
4. ✅ Address change with approval workflow

**READY TO START?** 🎯
