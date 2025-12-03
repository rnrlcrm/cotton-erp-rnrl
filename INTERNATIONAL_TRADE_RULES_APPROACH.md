# COMPLETE TRADE COMPLIANCE CHECKS FOR RULE ENGINE

**Date**: December 3, 2025  
**Purpose**: Add NATIONAL + INTERNATIONAL trade validation rules to RuleEngine  
**Branch**: `feat/dual-engine-orchestrator`

---

## APPROACH: Complete Trade Compliance Checks

### CRITICAL UNDERSTANDING:

1. **Use EXISTING PartnerDocument system** for ALL license validations (National + International)
2. **Commodity Master has 39 international fields** - We use those, NOT duplicate
3. **National checks** (GST, PAN, IEC for India) - SAME document system
4. **International checks** (Sanctions, Export/Import licenses) - SAME document system

### ARCHITECTURE:

```
TradeComplianceEngine
├── NationalComplianceRules
│   ├── check_gst_registration (India domestic)
│   ├── check_pan_card (India domestic)
│   ├── check_iec_for_domestic (India inter-state)
│   └── check_internal_trading_rules (circular, wash, party links)
│
└── InternationalComplianceRules
    ├── check_export_import_license (cross-border)
    ├── check_sanctions_compliance (country restrictions)
    ├── check_phytosanitary_certificate
    ├── check_currency_compliance
    ├── check_quality_standards
    ├── check_payment_terms
    └── check_seasonal_shelf_life
```

---

## 1. NATIONAL COMPLIANCE CHECKS (India Domestic)

### Category A: MANDATORY DOCUMENTS (Using PartnerDocument System)

#### 1. GST Certificate Validation

**When Required:**
- ALL domestic trades within India
- Inter-state and intra-state transactions

**How It Works:**

```python
async def check_gst_registration(
    self,
    partner_id: UUID,
    transaction_type: str,
    buyer_state: str,
    seller_state: str
) -> Dict[str, Any]:
    """
    Check if partner has valid GST certificate using PartnerDocument system.
    
    Data Source:
    - PartnerDocument with document_type='gst_certificate'
    - OCR extracted data (GSTIN, registration date, state)
    """
    
    # Query PartnerDocument for GST certificate
    gst_doc = await self.db.execute(
        select(PartnerDocument).where(
            and_(
                PartnerDocument.partner_id == partner_id,
                PartnerDocument.document_type == "gst_certificate",
                PartnerDocument.verified == True,  # KYC approved
                PartnerDocument.is_expired == False
            )
        )
    )
    gst_certificate = gst_doc.scalar_one_or_none()
    
    # CHECK 1: GST certificate exists
    if not gst_certificate:
        return {
            "blocked": True,
            "reason": "GST registration required for domestic trade but partner doesn't have verified GST certificate",
            "violation_type": "GST_MISSING",
            "how_to_fix": "Upload GST certificate in Documents section and get it verified"
        }
    
    # CHECK 2: Extract GSTIN from OCR data
    ocr_data = gst_certificate.ocr_extracted_data or {}
    gstin = ocr_data.get("gstin") or ocr_data.get("gst_number")
    
    if not gstin:
        return {
            "blocked": True,
            "reason": "GST certificate uploaded but GSTIN not extracted from OCR",
            "violation_type": "GST_INCOMPLETE",
            "document_id": str(gst_certificate.id),
            "how_to_fix": "Re-upload clear GST certificate for OCR extraction"
        }
    
    # CHECK 3: Verify state matches transaction
    gst_state = ocr_data.get("state_code") or gstin[:2]  # First 2 digits of GSTIN
    
    if transaction_type == "SELL" and gst_state != seller_state[:2]:
        return {
            "blocked": False,  # WARN
            "warning": True,
            "reason": f"GST state code {gst_state} doesn't match seller state {seller_state}",
            "violation_type": "GST_STATE_MISMATCH",
            "gstin": gstin
        }
    
    return {
        "blocked": False,
        "gstin": gstin,
        "document_id": str(gst_certificate.id)
    }
```

#### 2. PAN Card Validation

```python
async def check_pan_card(
    self,
    partner_id: UUID
) -> Dict[str, Any]:
    """
    Check if partner has valid PAN card using PartnerDocument system.
    
    Data Source:
    - PartnerDocument with document_type='pan_card'
    - OCR extracted PAN number
    """
    
    # Query PartnerDocument for PAN card
    pan_doc = await self.db.execute(
        select(PartnerDocument).where(
            and_(
                PartnerDocument.partner_id == partner_id,
                PartnerDocument.document_type == "pan_card",
                PartnerDocument.verified == True
            )
        )
    )
    pan_document = pan_doc.scalar_one_or_none()
    
    # CHECK 1: PAN card exists
    if not pan_document:
        return {
            "blocked": True,
            "reason": "PAN card required for trading but partner doesn't have verified PAN card",
            "violation_type": "PAN_MISSING",
            "how_to_fix": "Upload PAN card in Documents section and get it verified"
        }
    
    # CHECK 2: Extract PAN number from OCR
    ocr_data = pan_document.ocr_extracted_data or {}
    pan_number = ocr_data.get("pan_number")
    
    if not pan_number:
        return {
            "blocked": True,
            "reason": "PAN card uploaded but PAN number not extracted from OCR",
            "violation_type": "PAN_INCOMPLETE",
            "document_id": str(pan_document.id),
            "how_to_fix": "Re-upload clear PAN card for OCR extraction"
        }
    
    # CHECK 3: Validate PAN format (10 chars: 5 letters + 4 digits + 1 letter)
    import re
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
        return {
            "blocked": True,
            "reason": f"Invalid PAN format: {pan_number}",
            "violation_type": "PAN_INVALID_FORMAT",
            "document_id": str(pan_document.id)
        }
    
    return {
        "blocked": False,
        "pan_number": pan_number,
        "document_id": str(pan_document.id)
    }
```

#### 3. IEC Validation (For Inter-State High-Value Trades)

```python
async def check_iec_for_domestic(
    self,
    partner_id: UUID,
    transaction_value: Decimal,
    buyer_state: str,
    seller_state: str
) -> Dict[str, Any]:
    """
    Check IEC for high-value inter-state trades (India).
    
    Some commodities require IEC even for domestic inter-state trades
    if value exceeds threshold.
    
    Data Source:
    - PartnerDocument with document_type='iec'
    """
    
    # Only check if inter-state AND high value
    if buyer_state == seller_state:
        return {"blocked": False}  # Intra-state, no IEC needed
    
    if transaction_value < Decimal("1000000"):  # Rs 10 lakhs threshold
        return {"blocked": False}  # Below threshold
    
    # Query for IEC document
    iec_doc = await self.db.execute(
        select(PartnerDocument).where(
            and_(
                PartnerDocument.partner_id == partner_id,
                PartnerDocument.document_type == "iec",
                PartnerDocument.verified == True,
                PartnerDocument.is_expired == False
            )
        )
    )
    iec_document = iec_doc.scalar_one_or_none()
    
    if not iec_document:
        return {
            "blocked": False,  # WARN for domestic
            "warning": True,
            "reason": f"High-value inter-state trade (Rs {transaction_value}) recommended to have IEC",
            "violation_type": "IEC_RECOMMENDED",
            "how_to_fix": "Upload IEC certificate for compliance"
        }
    
    return {
        "blocked": False,
        "iec_number": iec_document.ocr_extracted_data.get("license_number"),
        "document_id": str(iec_document.id)
    }
```

---

## 2. INTERNATIONAL COMPLIANCE CHECKS (Cross-Border)

## 2. INTERNATIONAL COMPLIANCE CHECKS (Cross-Border)

### Category A: INSTANT BLOCKING RULES (Critical)

#### 1. Sanctions & Country Restrictions Check

**PRIORITY: RUN THIS FIRST!**

```python
async def check_sanctions_compliance(
    self,
    commodity_id: UUID,
    buyer_country: str,
    seller_country: str,
    buyer_partner_id: UUID,
    seller_partner_id: UUID
) -> Dict[str, Any]:
    """
    Check sanctions and country restrictions.
    
    BLOCKS if:
    - Destination country in commodity.restricted_countries
    - Partner country under international sanctions
    - Commodity has export ban to specific countries
    
    Data Sources:
    - commodity.export_regulations.restricted_countries
    - commodity.import_regulations.restricted_countries
    - Global sanctions list (hardcoded or from external API)
    """
    
    # Get commodity
    commodity = await self.db.get(Commodity, commodity_id)
    
    # GLOBAL SANCTIONS LIST (Update periodically)
    SANCTIONED_COUNTRIES = [
        "IR",  # Iran
        "KP",  # North Korea
        "SY",  # Syria
        "CU",  # Cuba (partial)
        # Add more as per OFAC, UN, EU sanctions
    ]
    
    # CHECK 1: Buyer country sanctioned
    if buyer_country in SANCTIONED_COUNTRIES:
        return {
            "blocked": True,
            "reason": f"Cannot trade with {buyer_country} - Country under international sanctions",
            "violation_type": "SANCTIONED_COUNTRY",
            "country": buyer_country,
            "how_to_fix": "Cannot trade to sanctioned countries"
        }
    
    # CHECK 2: Seller country sanctioned
    if seller_country in SANCTIONED_COUNTRIES:
        return {
            "blocked": True,
            "reason": f"Cannot trade from {seller_country} - Country under international sanctions",
            "violation_type": "SANCTIONED_ORIGIN",
            "country": seller_country,
            "how_to_fix": "Cannot trade from sanctioned countries"
        }
    
    # CHECK 3: Commodity-specific restrictions
    export_regs = commodity.export_regulations or {}
    restricted_countries = export_regs.get("restricted_countries", [])
    
    if buyer_country in restricted_countries:
        restriction_reason = export_regs.get("restriction_reason", "Trade restrictions apply")
        
        return {
            "blocked": True,
            "reason": (
                f"Export of {commodity.name} to {buyer_country} is RESTRICTED. "
                f"Reason: {restriction_reason}"
            ),
            "violation_type": "COMMODITY_EXPORT_RESTRICTED",
            "commodity_name": commodity.name,
            "restricted_country": buyer_country,
            "restriction_reason": restriction_reason,
            "how_to_fix": "Cannot trade this commodity to this destination"
        }
    
    # CHECK 4: Import restrictions
    import_regs = commodity.import_regulations or {}
    import_restricted = import_regs.get("restricted_countries", [])
    
    if seller_country in import_restricted:
        return {
            "blocked": True,
            "reason": f"Import of {commodity.name} from {seller_country} is RESTRICTED",
            "violation_type": "COMMODITY_IMPORT_RESTRICTED",
            "commodity_name": commodity.name,
            "restricted_origin": seller_country
        }
    
    return {"blocked": False}
```

#### 2. Export/Import License Validation

**HOW IT WORKS:**

```
┌────────────────────────────────────────────────────────────────┐
│  STEP 1: Get Commodity Export/Import Regulations               │
│  (Already exists in Commodity Master)                          │
├────────────────────────────────────────────────────────────────┤
│  commodity.export_regulations = {                              │
│    "license_required": true,  ← Key field!                     │
│    "license_types": ["IEC", "DGFT"],  ← What licenses accepted │
│    "restricted_countries": ["XYZ"],   ← Blocked destinations   │
│    "minimum_export_value": 100000,    ← License exemption      │
│    "restriction_reason": "Trade sanctions"                     │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 2: Get Partner's License Documents                       │
│  (USE EXISTING PartnerDocument system - NO new fields!)        │
├────────────────────────────────────────────────────────────────┤
│  SELECT * FROM partner_documents                               │
│  WHERE partner_id = ? AND document_type = 'iec'                │
│  AND verified = true AND is_expired = false                    │
│                                                                 │
│  PartnerDocument {                                              │
│    document_type: "iec",  ← DocumentType.IEC (already exists!)│
│    ocr_extracted_data: {                                        │
│      "license_number": "IEC0515012345",                        │
│      "license_type": "IEC",                                    │
│      "license_countries": ["USA", "EU", "UAE"],                │
│      "issuing_authority": "DGFT"                               │
│    },                                                           │
│    issue_date: "2020-01-01",                                   │
│    expiry_date: "2026-12-31",  ← Auto-validated!              │
│    verified: true,  ← KYC approved                            │
│    is_expired: false  ← Automatically calculated              │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 3: Validation Logic                                      │
├────────────────────────────────────────────────────────────────┤
│  if commodity.export_regulations.license_required:             │
│      if partner.export_license_number is None:                 │
│          → BLOCK (no license)                                  │
│                                                                 │
│      if partner.export_license_expiry < today():               │
│          → BLOCK (license expired)                             │
│                                                                 │
│      if buyer_country not in partner.export_license_countries: │
│          → BLOCK (not licensed for this destination)           │
│                                                                 │
│      if commodity.license_types not contains partner.license_type: │
│          → BLOCK (wrong license type)                          │
└────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
# backend/modules/risk/rule_engine/international_trade_rules.py

from datetime import date
from sqlalchemy import select, and_

async def check_export_import_license(
    self,
    commodity_id: UUID,
    seller_partner_id: UUID,
    buyer_partner_id: UUID,
    buyer_country: str,
    seller_country: str,
    transaction_value: Decimal
) -> Dict[str, Any]:
    """
    Check if export/import license required and validate using EXISTING PartnerDocument system.
    
    VALIDATION STEPS:
    1. Check if commodity requires export license
    2. Query PartnerDocument for IEC/export license
    3. Check if document is verified and not expired
    4. Validate OCR extracted data (license countries, etc.)
    
    BLOCKS if:
    - License required but no verified document found
    - Document expired (is_expired = True)
    - Destination country not in ocr_extracted_data.license_countries
    - Wrong license type
    - Destination country restricted
    
    Data Sources:
    - commodity.export_regulations (ALREADY EXISTS)
    - PartnerDocument with document_type='iec' (ALREADY EXISTS)
    - PartnerDocument.ocr_extracted_data (ALREADY EXISTS)
    - PartnerDocument.verified, is_expired (ALREADY EXISTS)
    """
    
    # ========================================================================
    # STEP 1: Get commodity
    # ========================================================================
    result = await self.db.execute(
        select(Commodity).where(Commodity.id == commodity_id)
    )
    commodity = result.scalar_one_or_none()
    
    if not commodity:
        return {"blocked": False, "reason": "Commodity not found"}
    
    # ========================================================================
    # STEP 2: Check EXPORT regulations (seller side)
    # ========================================================================
    export_regs = commodity.export_regulations or {}
    
    if export_regs.get("license_required", False):
        # Get seller's IEC/export license document
        doc_result = await self.db.execute(
            select(PartnerDocument).where(
                and_(
                    PartnerDocument.partner_id == seller_partner_id,
                    PartnerDocument.document_type.in_(["iec", "foreign_export_license"]),
                    PartnerDocument.verified == True,  # KYC approved only
                    PartnerDocument.is_expired == False  # Not expired
                )
            )
        )
        license_doc = doc_result.scalar_one_or_none()
        
        # CHECK 1: Does seller have verified export license document?
        if not license_doc:
            return {
                "blocked": True,
                "reason": (
                    f"Export license required for {commodity.name} but seller "
                    f"does not have verified export license (IEC/DGFT) document"
                ),
                "violation_type": "EXPORT_LICENSE_MISSING",
                "required_license_types": export_regs.get("license_types", ["IEC"]),
                "commodity_name": commodity.name,
                "how_to_fix": "Upload IEC/DGFT certificate in Documents section and get it verified"
            }
        
        # CHECK 2: Is license expired? (Already filtered, but double-check)
        if license_doc.is_expired or (license_doc.expiry_date and license_doc.expiry_date < date.today()):
            return {
                "blocked": True,
                "reason": (
                    f"Seller has expired export license. "
                    f"License expired on {license_doc.expiry_date}"
                ),
                "violation_type": "EXPORT_LICENSE_EXPIRED",
                "license_number": license_doc.ocr_extracted_data.get("license_number") if license_doc.ocr_extracted_data else "Unknown",
                "expiry_date": license_doc.expiry_date.isoformat() if license_doc.expiry_date else None,
                "document_id": str(license_doc.id),
                "how_to_fix": "Renew export license and upload new certificate"
            }
        
        # Extract license details from OCR data
        ocr_data = license_doc.ocr_extracted_data or {}
        license_type = ocr_data.get("license_type", "IEC")
        license_countries = ocr_data.get("license_countries", [])
        
        # CHECK 3: Is license type correct?
        required_types = export_regs.get("license_types", [])
        if required_types and license_type not in required_types:
            return {
                "blocked": True,
                "reason": (
                    f"Commodity {commodity.name} requires {required_types} license, "
                    f"but seller has '{license_type}'"
                ),
                "violation_type": "WRONG_LICENSE_TYPE",
                "seller_license_type": license_type,
                "required_license_types": required_types,
                "how_to_fix": f"Obtain {required_types} license"
            }
        
        # CHECK 4: Is destination country covered by license?
        if license_countries:  # List of countries from OCR
            if buyer_country not in license_countries and "ALL" not in license_countries:
                return {
                    "blocked": True,
                    "reason": (
                        f"Seller's export license does not cover {buyer_country}. "
                        f"License valid for: {', '.join(license_countries)}"
                    ),
                    "violation_type": "DESTINATION_NOT_COVERED",
                    "destination_country": buyer_country,
                    "licensed_countries": license_countries,
                    "document_id": str(license_doc.id),
                    "how_to_fix": f"Update license to include {buyer_country} or upload worldwide license"
                }
        
        # CHECK 5: Minimum export value exemption
        min_value = export_regs.get("minimum_export_value")
        if min_value and transaction_value < Decimal(str(min_value)):
            # Small value exports may be exempt from license
            return {
                "blocked": False,
                "reason": f"Export value below license threshold (${min_value})",
                "exemption": "SMALL_VALUE_EXEMPTION"
            }
    
    # ========================================================================
    # STEP 3: Check RESTRICTED destinations (export side)
    # ========================================================================
    restricted_countries = export_regs.get("restricted_countries", [])
    if buyer_country in restricted_countries:
        restriction_reason = export_regs.get("restriction_reason", "Trade restrictions apply")
        
        return {
            "blocked": True,
            "reason": (
                f"Export of {commodity.name} to {buyer_country} is RESTRICTED. "
                f"Reason: {restriction_reason}"
            ),
            "violation_type": "RESTRICTED_DESTINATION",
            "commodity_name": commodity.name,
            "restricted_country": buyer_country,
            "restriction_reason": restriction_reason,
            "how_to_fix": "Cannot trade to this destination (regulatory restriction)"
        }
    
    # ========================================================================
    # STEP 4: Check IMPORT regulations (buyer side)
    # ========================================================================
    import_regs = commodity.import_regulations or {}
    
    if import_regs.get("license_required", False):
        # Get buyer's import license document
        buyer_doc_result = await self.db.execute(
            select(PartnerDocument).where(
                and_(
                    PartnerDocument.partner_id == buyer_partner_id,
                    PartnerDocument.document_type.in_(["iec", "foreign_import_license"]),
                    PartnerDocument.verified == True,
                    PartnerDocument.is_expired == False
                )
            )
        )
        buyer_license_doc = buyer_doc_result.scalar_one_or_none()
        
        # CHECK 6: Does buyer have import license?
        if not buyer_license_doc:
            return {
                "blocked": True,
                "reason": (
                    f"Import license required for {commodity.name} but buyer "
                    f"does not have verified import license document"
                ),
                "violation_type": "IMPORT_LICENSE_MISSING",
                "required_license_types": import_regs.get("license_types", ["IEC"]),
                "commodity_name": commodity.name,
                "how_to_fix": "Upload import license certificate and get it verified"
            }
        
        # CHECK 7: Is import license expired?
        if buyer_license_doc.is_expired or (buyer_license_doc.expiry_date and buyer_license_doc.expiry_date < date.today()):
            return {
                "blocked": True,
                "reason": (
                    f"Buyer has expired import license. "
                    f"License expired on {buyer_license_doc.expiry_date}"
                ),
                "violation_type": "IMPORT_LICENSE_EXPIRED",
                "license_number": buyer_license_doc.ocr_extracted_data.get("license_number") if buyer_license_doc.ocr_extracted_data else "Unknown",
                "expiry_date": buyer_license_doc.expiry_date.isoformat() if buyer_license_doc.expiry_date else None,
                "how_to_fix": "Renew import license"
            }
    
    # ========================================================================
    # ALL CHECKS PASSED
    # ========================================================================
    return {
        "blocked": False,
        "reason": "Export/Import license validation passed",
        "seller_license_doc_id": str(license_doc.id) if 'license_doc' in locals() else None,
        "buyer_license_doc_id": str(buyer_license_doc.id) if 'buyer_license_doc' in locals() else None,
        "seller_license_number": ocr_data.get("license_number") if 'ocr_data' in locals() else None
    }
```

**REAL-WORLD EXAMPLE:**

```python
# Scenario: Indian seller wants to export cotton to USA

commodity = {
    "name": "Cotton - Shankar-6",
    "export_regulations": {
        "license_required": True,
        "license_types": ["IEC", "DGFT"],
        "restricted_countries": ["Country X"],
        "minimum_export_value": 50000
    }
}

# Seller's IEC document (ALREADY IN SYSTEM via PartnerDocument)
seller_iec_document = PartnerDocument(
    id="uuid-doc-1",
    partner_id="uuid-seller",
    document_type="iec",  # ✅ DocumentType.IEC already exists!
    verified=True,  # ✅ KYC approved
    is_expired=False,  # ✅ Automatically calculated
    issue_date="2020-01-01",
    expiry_date="2026-12-31",  # ✅ Valid until 2026
    ocr_extracted_data={  # ✅ Extracted during upload
        "license_number": "IEC0515012345",
        "license_type": "IEC",
        "license_countries": ["USA", "EU", "UAE"],  # ✅ USA covered
        "issuing_authority": "DGFT",
        "issue_date": "2020-01-01",
        "expiry_date": "2026-12-31"
    },
    extraction_confidence=95.5,  # OCR confidence
    file_url="https://storage.example.com/iec_certificate.pdf"
)

buyer_country = "USA"
transaction_value = Decimal("200000")  # Above minimum

# VALIDATION RESULT:
check_result = await check_export_import_license(...)
# → {"blocked": False, "reason": "All checks passed", "seller_license_doc_id": "uuid-doc-1"}
```

**FAILURE EXAMPLES:**

```python
# Example 1: No license
seller.export_license_number = None
# → BLOCKED: "Export license required but seller doesn't have it"

# Example 2: License expired
seller.export_license_expiry = "2024-01-01"  # Past date
# → BLOCKED: "Seller has expired export license"

# Example 3: Destination not covered
buyer_country = "Japan"  # Not in licensed_countries
# → BLOCKED: "License does not cover Japan"

# Example 4: Restricted destination
buyer_country = "Country X"  # In restricted list
# → BLOCKED: "Export to Country X is RESTRICTED"

# Example 5: Wrong license type
commodity.export_regulations.license_types = ["DGFT"]  # Requires DGFT
seller.export_license_type = "IEC"  # Has IEC
# → BLOCKED: "Requires DGFT license, seller has IEC"
```

#### 2. Phytosanitary Certificate Validation
```python
async def check_phytosanitary_requirement(
    self,
    commodity_id: UUID,
    transaction_type: str,  # "EXPORT" or "IMPORT"
    destination_country: str
) -> Dict[str, Any]:
    """
    Check if phytosanitary certificate required for this commodity.
    
    BLOCKS if:
    - Commodity requires phytosanitary but not provided
    - Fumigation required but not done
    
    Data Source:
    - commodity.phytosanitary_required (boolean)
    - commodity.fumigation_required (boolean)
    """
    
    commodity = await self.db.get(Commodity, commodity_id)
    
    if commodity.phytosanitary_required and transaction_type == "EXPORT":
        return {
            "blocked": False,  # WARN, not block (document can be uploaded later)
            "warning": True,
            "reason": f"Phytosanitary certificate required for exporting {commodity.name}",
            "violation_type": "PHYTOSANITARY_REQUIRED",
            "required_documents": ["Phytosanitary Certificate"],
            "issuing_authority": "Department of Agriculture"
        }
    
    if commodity.fumigation_required and transaction_type == "EXPORT":
        return {
            "blocked": False,  # WARN, not block
            "warning": True,
            "reason": f"Fumigation certificate required for exporting {commodity.name}",
            "violation_type": "FUMIGATION_REQUIRED",
            "required_documents": ["Fumigation Certificate"],
            "validity_days": 21  # Typical validity
        }
    
    return {"blocked": False, "warning": False}
```

#### 3. Currency Compliance Check
```python
async def check_currency_compliance(
    self,
    commodity_id: UUID,
    proposed_currency: str,
    transaction_type: str
) -> Dict[str, Any]:
    """
    Check if proposed currency is supported for this commodity.
    
    BLOCKS if:
    - Currency not in commodity.supported_currencies
    - Domestic trade using foreign currency (forex violation)
    
    Data Source:
    - commodity.default_currency
    - commodity.supported_currencies (JSON array)
    """
    
    commodity = await self.db.get(Commodity, commodity_id)
    
    supported = commodity.supported_currencies or [commodity.default_currency]
    
    if proposed_currency not in supported:
        return {
            "blocked": True,
            "reason": f"Currency {proposed_currency} not supported for {commodity.name}",
            "violation_type": "UNSUPPORTED_CURRENCY",
            "supported_currencies": supported,
            "commodity": commodity.name
        }
    
    return {"blocked": False}
```

#### 4. Quality Standards Validation
```python
async def check_quality_standards_compliance(
    self,
    commodity_id: UUID,
    quality_standard: str,  # "USDA", "BCI", "ISO_9001"
    buyer_country: str
) -> Dict[str, Any]:
    """
    Check if quality standard is recognized for this commodity.
    
    BLOCKS if:
    - Buyer country requires specific standard (e.g., USDA for USA)
    - Standard not in commodity.quality_standards
    
    Data Source:
    - commodity.quality_standards (JSON array)
    - commodity.international_grades (JSON object)
    """
    
    commodity = await self.db.get(Commodity, commodity_id)
    
    # Check if standard is supported
    supported_standards = commodity.quality_standards or []
    
    if quality_standard not in supported_standards:
        return {
            "blocked": False,  # WARN, not block
            "warning": True,
            "reason": f"Quality standard {quality_standard} not standard for {commodity.name}",
            "violation_type": "NON_STANDARD_QUALITY",
            "supported_standards": supported_standards,
            "recommendation": "Use standard grading system"
        }
    
    return {"blocked": False}
```

#### 5. Payment Term Compliance (International)
```python
async def check_international_payment_terms(
    self,
    payment_term_id: UUID,
    buyer_country: str,
    seller_country: str,
    transaction_value: Decimal
) -> Dict[str, Any]:
    """
    Check if payment terms are compliant for cross-border trade.
    
    BLOCKS if:
    - High-value international trade without LC
    - Payment term doesn't support required currency
    - SWIFT required but not supported
    
    Data Source:
    - payment_term.supports_letter_of_credit
    - payment_term.swift_required
    - payment_term.payment_methods_supported
    """
    
    payment_term = await self.db.get(PaymentTerm, payment_term_id)
    
    # Cross-border trade?
    is_international = buyer_country != seller_country
    
    if is_international:
        # High-value trades require LC
        if transaction_value > Decimal("100000"):  # $100K threshold
            if not payment_term.supports_letter_of_credit:
                return {
                    "blocked": False,  # WARN
                    "warning": True,
                    "reason": f"High-value international trade (${transaction_value}) should use Letter of Credit",
                    "violation_type": "LC_RECOMMENDED",
                    "recommendation": "Use LC-supported payment term for risk mitigation",
                    "value_threshold": 100000
                }
        
        # SWIFT required for international TT
        payment_methods = payment_term.payment_methods_supported or []
        if "TT" in payment_methods and not payment_term.swift_required:
            return {
                "blocked": False,  # WARN
                "warning": True,
                "reason": "International TT requires SWIFT-enabled payment term",
                "violation_type": "SWIFT_REQUIRED",
                "recommendation": "Ensure bank supports SWIFT"
            }
    
    return {"blocked": False}
```

---

### Category B: ADVISORY WARNINGS (Non-blocking)

#### 6. Seasonal Commodity Check
```python
async def check_seasonal_availability(
    self,
    commodity_id: UUID,
    transaction_date: date,
    origin_country: str
) -> Dict[str, Any]:
    """
    Warn if trading commodity outside harvest season.
    
    Data Source:
    - commodity.seasonal_commodity
    - commodity.harvest_season (JSON)
    """
    
    commodity = await self.db.get(Commodity, commodity_id)
    
    if commodity.seasonal_commodity:
        harvest_season = commodity.harvest_season or {}
        country_season = harvest_season.get(origin_country, [])
        
        current_month = transaction_date.strftime("%b")
        
        if current_month not in country_season:
            return {
                "warning": True,
                "reason": f"{commodity.name} is seasonal. Current month ({current_month}) is outside harvest season for {origin_country}",
                "violation_type": "OFF_SEASON_TRADE",
                "harvest_season": country_season,
                "impact": "Prices may be higher, quality may vary"
            }
    
    return {"warning": False}
```

#### 7. Storage & Shelf Life Check
```python
async def check_storage_shelf_life(
    self,
    commodity_id: UUID,
    delivery_date: date,
    expected_usage_date: date
) -> Dict[str, Any]:
    """
    Warn if shelf life will expire before usage.
    
    Data Source:
    - commodity.shelf_life_days
    - commodity.storage_conditions
    """
    
    commodity = await self.db.get(Commodity, commodity_id)
    
    if commodity.shelf_life_days:
        storage_duration = (expected_usage_date - delivery_date).days
        
        if storage_duration > commodity.shelf_life_days:
            return {
                "warning": True,
                "reason": f"{commodity.name} has shelf life of {commodity.shelf_life_days} days, but storage duration is {storage_duration} days",
                "violation_type": "SHELF_LIFE_EXCEEDED",
                "shelf_life_days": commodity.shelf_life_days,
                "storage_duration": storage_duration,
                "storage_conditions": commodity.storage_conditions
            }
    
    return {"warning": False}
```

---

## 3. FILE STRUCTURE (Complete Trade Compliance)

```
backend/modules/risk/rule_engine/
├── __init__.py
├── risk_engine.py                      # Main orchestrator
│
├── national_compliance_rules.py        # ⭐ NEW - India domestic checks
│   ├── check_gst_registration()
│   ├── check_pan_card()
│   ├── check_iec_for_domestic()
│   └── check_domestic_trade_restrictions()
│
├── international_compliance_rules.py   # ⭐ NEW - Cross-border checks
│   ├── check_sanctions_compliance()    # ← RUN FIRST!
│   ├── check_export_import_license()
│   ├── check_phytosanitary_requirement()
│   ├── check_currency_compliance()
│   ├── check_quality_standards()
│   ├── check_payment_terms()
│   └── check_seasonal_shelf_life()
│
├── circular_trading.py                 # Existing - Extract from risk_engine.py
├── wash_trading.py                     # Existing - Extract from risk_engine.py
├── party_links.py                      # Existing - Extract from risk_engine.py
└── credit_validation.py                # Existing - Extract from risk_engine.py
```

---

## 4. COMPLETE VALIDATION FLOW

```
backend/modules/risk/rule_engine/
├── __init__.py
├── risk_engine.py                      # Existing - main engine
├── circular_trading.py                 # Extract from risk_engine.py
├── wash_trading.py                     # Extract from risk_engine.py
├── party_links.py                      # Extract from risk_engine.py
├── credit_validation.py                # Extract from risk_engine.py
├── sanctions.py                        # NEW - sanctions check
└── international_trade_rules.py        # ⭐ NEW - International checks
```

## 4. COMPLETE VALIDATION FLOW

### Decision Tree:

```
Transaction Received
        ↓
┌───────────────────────────────────────┐
│ STEP 1: Determine Trade Type         │
├───────────────────────────────────────┤
│ buyer_country == seller_country?     │
│   YES → NATIONAL (India domestic)    │
│   NO  → INTERNATIONAL (cross-border) │
└───────────────────────────────────────┘
        ↓
    ┌───┴───┐
    │       │
NATIONAL  INTERNATIONAL
    │       │
    │       └──→ [STEP 2a: Sanctions Check - BLOCKING]
    │            └─→ BLOCKED? → Return Error
    │            └─→ PASS? → Continue
    │
    └──→ [STEP 2b: National Compliance]
         ├── GST Certificate Check (BLOCKING)
         ├── PAN Card Check (BLOCKING)
         └── IEC Check (WARNING for high-value)
                ↓
         ┌──────┴──────┐
         │             │
    NATIONAL     INTERNATIONAL
         │             │
         │             └──→ [STEP 3: Export/Import License]
         │                  └─→ BLOCKED? → Return Error
         │                  └─→ PASS? → Continue
         │
         └──→ [STEP 4: Internal Trading Rules (BOTH National + International)]
              ├── Circular Trading (BLOCKING)
              ├── Wash Trading (BLOCKING)
              └── Party Links - Same PAN/GST Check (BLOCKING)
                     ↓
              ┌─────┴─────┐
              │           │
         NATIONAL    INTERNATIONAL
              │           │
              │           └──→ [STEP 5: Additional International Checks]
              │                ├── Currency Compliance (BLOCKING)
              │                ├── Phytosanitary (WARNING)
              │                ├── Quality Standards (WARNING)
              │                └── Payment Terms (WARNING)
              │
              └──→ [STEP 6: Credit & Risk Checks]
                   ├── Credit Limit Check
                   ├── Outstanding Balance
                   └── Payment History
                          ↓
                   ALL PASSED
                          ↓
                   TRANSACTION APPROVED
```

### Implementation in risk_engine.py:

```python
# backend/modules/risk/rule_engine/risk_engine.py

from backend.modules.risk.rule_engine.national_compliance_rules import NationalComplianceRules
from backend.modules.risk.rule_engine.international_compliance_rules import InternationalComplianceRules

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Initialize compliance engines
        self.national_compliance = NationalComplianceRules(db)
        self.international_compliance = InternationalComplianceRules(db)
    
    async def comprehensive_check(
        self,
        partner_id: UUID,
        transaction_type: str,  # "BUY" or "SELL"
        commodity_id: UUID,
        amount: Decimal,
        counterparty_id: Optional[UUID] = None,
        
        # Geographic details
        buyer_country: str = "IN",  # Default India
        seller_country: str = "IN",
        buyer_state: Optional[str] = None,
        seller_state: Optional[str] = None,
        
        # International trade details
        proposed_currency: Optional[str] = None,
        payment_term_id: Optional[UUID] = None,
        quality_standard: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        COMPLETE trade compliance check: National + International + Internal rules.
        """
        
        # ====================================================================
        # STEP 1: Determine if National or International
        # ====================================================================
        is_international = buyer_country != seller_country
        
        compliance_checks = {
            "trade_type": "INTERNATIONAL" if is_international else "NATIONAL",
            "national_checks": [],
            "international_checks": [],
            "internal_checks": []
        }
        
        # ====================================================================
        # STEP 2: NATIONAL or INTERNATIONAL COMPLIANCE
        # ====================================================================
        
        if is_international:
            # ----------------------------------------------------------------
            # INTERNATIONAL: Sanctions Check FIRST (Highest Priority)
            # ----------------------------------------------------------------
            sanctions_check = await self.international_compliance.check_sanctions_compliance(
                commodity_id=commodity_id,
                buyer_country=buyer_country,
                seller_country=seller_country,
                buyer_partner_id=counterparty_id if transaction_type == "SELL" else partner_id,
                seller_partner_id=partner_id if transaction_type == "SELL" else counterparty_id
            )
            compliance_checks["international_checks"].append(sanctions_check)
            
            # INSTANT BLOCK if sanctioned
            if sanctions_check.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": sanctions_check["reason"],
                    "violation_type": sanctions_check["violation_type"],
                    "tier": "SANCTIONS_COMPLIANCE",
                    "compliance_checks": compliance_checks
                }
            
            # ----------------------------------------------------------------
            # INTERNATIONAL: Export/Import License Check
            # ----------------------------------------------------------------
            license_check = await self.international_compliance.check_export_import_license(
                commodity_id=commodity_id,
                seller_partner_id=partner_id if transaction_type == "SELL" else counterparty_id,
                buyer_partner_id=counterparty_id if transaction_type == "SELL" else partner_id,
                buyer_country=buyer_country,
                seller_country=seller_country,
                transaction_value=amount
            )
            compliance_checks["international_checks"].append(license_check)
            
            # INSTANT BLOCK if license missing/invalid
            if license_check.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": license_check["reason"],
                    "violation_type": license_check["violation_type"],
                    "tier": "EXPORT_IMPORT_LICENSE",
                    "compliance_checks": compliance_checks
                }
        
        else:
            # ----------------------------------------------------------------
            # NATIONAL (India Domestic): GST + PAN Checks
            # ----------------------------------------------------------------
            
            # GST Certificate Check (BLOCKING)
            gst_check = await self.national_compliance.check_gst_registration(
                partner_id=partner_id,
                transaction_type=transaction_type,
                buyer_state=buyer_state or "MH",
                seller_state=seller_state or "MH"
            )
            compliance_checks["national_checks"].append(gst_check)
            
            if gst_check.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": gst_check["reason"],
                    "violation_type": gst_check["violation_type"],
                    "tier": "GST_COMPLIANCE",
                    "compliance_checks": compliance_checks
                }
            
            # PAN Card Check (BLOCKING)
            pan_check = await self.national_compliance.check_pan_card(
                partner_id=partner_id
            )
            compliance_checks["national_checks"].append(pan_check)
            
            if pan_check.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": pan_check["reason"],
                    "violation_type": pan_check["violation_type"],
                    "tier": "PAN_COMPLIANCE",
                    "compliance_checks": compliance_checks
                }
            
            # IEC Check for high-value inter-state (WARNING only)
            iec_check = await self.national_compliance.check_iec_for_domestic(
                partner_id=partner_id,
                transaction_value=amount,
                buyer_state=buyer_state or "MH",
                seller_state=seller_state or "MH"
            )
            compliance_checks["national_checks"].append(iec_check)
        
        # ====================================================================
        # STEP 3: INTERNAL TRADING RULES (National + International)
        # ====================================================================
        
        # Circular Trading Check
        circular = await self.check_circular_trading_settlement_based(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type
        )
        compliance_checks["internal_checks"].append(circular)
        
        if circular.get("blocked"):
            return {
                "score": 0,
                "status": "FAIL",
                "blocked": True,
                "blocking_reason": circular["reason"],
                "violation_type": "CIRCULAR_TRADING",
                "tier": "INTERNAL_RULES",
                "compliance_checks": compliance_checks
            }
        
        # Wash Trading Check
        wash = await self.check_wash_trading(
            partner_id=partner_id,
            commodity_id=commodity_id,
            transaction_type=transaction_type,
            amount=amount
        )
        compliance_checks["internal_checks"].append(wash)
        
        if wash.get("blocked"):
            return {
                "score": 0,
                "status": "FAIL",
                "blocked": True,
                "blocking_reason": wash["reason"],
                "violation_type": "WASH_TRADING",
                "tier": "INTERNAL_RULES",
                "compliance_checks": compliance_checks
            }
        
        # Party Links Check (Same PAN/GST)
        if counterparty_id:
            party_links = await self.check_party_links(
                partner_id=partner_id,
                counterparty_id=counterparty_id
            )
            compliance_checks["internal_checks"].append(party_links)
            
            if party_links.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": party_links["reason"],
                    "violation_type": "PARTY_LINKS",
                    "tier": "INTERNAL_RULES",
                    "compliance_checks": compliance_checks
                }
        
        # ====================================================================
        # STEP 4: PARTY LINKS CHECK (Applies to BOTH National + International)
        # ====================================================================
        
        # Party Links Check - Same PAN/GST trading (Applies to ALL trades)
        if counterparty_id:
            party_links = await self.check_party_links(
                partner_id=partner_id,
                counterparty_id=counterparty_id
            )
            compliance_checks["internal_checks"].append(party_links)
            
            if party_links.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": party_links["reason"],
                    "violation_type": "PARTY_LINKS",
                    "tier": "INTERNAL_RULES",
                    "compliance_checks": compliance_checks,
                    "note": "Party links check applies to both national and international trades"
                }
        
        # ====================================================================
        # STEP 5: ADDITIONAL INTERNATIONAL CHECKS (Warnings)
        # ====================================================================
        
        if is_international:
            # Currency Compliance
            if proposed_currency:
                currency_check = await self.international_compliance.check_currency_compliance(
                    commodity_id=commodity_id,
                    proposed_currency=proposed_currency,
                    transaction_type=transaction_type
                )
                compliance_checks["international_checks"].append(currency_check)
                
                if currency_check.get("blocked"):
                    return {
                        "score": 0,
                        "status": "FAIL",
                        "blocked": True,
                        "blocking_reason": currency_check["reason"],
                        "violation_type": currency_check["violation_type"],
                        "tier": "CURRENCY_COMPLIANCE",
                        "compliance_checks": compliance_checks
                    }
            
            # Phytosanitary (Warning only)
            phyto_check = await self.international_compliance.check_phytosanitary_requirement(
                commodity_id=commodity_id,
                transaction_type="EXPORT" if transaction_type == "SELL" else "IMPORT",
                destination_country=buyer_country if transaction_type == "SELL" else seller_country
            )
            compliance_checks["international_checks"].append(phyto_check)
            
            # Payment Terms (Warning only)
            if payment_term_id:
                payment_check = await self.international_compliance.check_international_payment_terms(
                    payment_term_id=payment_term_id,
                    buyer_country=buyer_country,
                    seller_country=seller_country,
                    transaction_value=amount
                )
                compliance_checks["international_checks"].append(payment_check)
        
        # ====================================================================
        # STEP 6: Credit & Risk Scoring (Existing logic)
        # ====================================================================
        
        credit_check = await self.check_credit_limit(partner_id, amount)
        # ... existing scoring logic ...
        
        # ====================================================================
        # ALL CHECKS PASSED
        # ====================================================================
        
        return {
            "score": 85,  # Example score
            "status": "PASS",
            "blocked": False,
            "compliance_checks": compliance_checks,
            "risk_factors": [],
            "warnings": [
                check for check in 
                compliance_checks["national_checks"] + 
                compliance_checks["international_checks"] + 
                compliance_checks["internal_checks"]
                if check.get("warning")
            ]
        }
```

---

## 5. USING EXISTING DOCUMENT SYSTEM (SUMMARY)

```python
# backend/modules/risk/rule_engine/international_trade_rules.py

from typing import Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.modules.settings.commodities.models import Commodity, PaymentTerm
from backend.modules.partners.models import BusinessPartner


class InternationalTradeRules:
    """
    International trade compliance checks.
    
    Validates:
    - Export/Import licenses
    - Phytosanitary certificates
    - Currency compliance
    - Quality standards
    - Payment terms (LC, SWIFT)
    - Seasonal availability
    - Shelf life
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_export_import_license(...):
        # Implementation above
        pass
    
    async def check_phytosanitary_requirement(...):
        # Implementation above
        pass
    
    async def check_currency_compliance(...):
        # Implementation above
        pass
    
    async def check_quality_standards_compliance(...):
        # Implementation above
        pass
    
    async def check_international_payment_terms(...):
        # Implementation above
        pass
    
    async def check_seasonal_availability(...):
        # Implementation above
        pass
    
    async def check_storage_shelf_life(...):
        # Implementation above
        pass
```

### Step 2: Update `risk_engine.py` to Include International Checks

```python
# backend/modules/risk/rule_engine/risk_engine.py

from backend.modules.risk.rule_engine.international_trade_rules import InternationalTradeRules

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Initialize international trade rules
        self.international_rules = InternationalTradeRules(db)
    
    async def comprehensive_check(
        self,
        partner_id: UUID,
        transaction_type: str,
        commodity_id: UUID,
        amount: Decimal,
        counterparty_id: Optional[UUID] = None,
        # ⭐ NEW PARAMETERS FOR INTERNATIONAL
        buyer_country: Optional[str] = None,
        seller_country: Optional[str] = None,
        proposed_currency: Optional[str] = None,
        payment_term_id: Optional[UUID] = None,
        quality_standard: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive risk check including international trade rules.
        """
        
        # Existing checks
        circular = await self.check_circular_trading_settlement_based(...)
        wash = await self.check_wash_trading(...)
        party_links = await self.check_party_links(...)
        
        # ====================================================================
        # NEW: INTERNATIONAL TRADE CHECKS
        # ====================================================================
        
        international_checks = []
        
        # Only run if cross-border trade
        if buyer_country and seller_country and buyer_country != seller_country:
            
            # Check 1: Export/Import License
            license_check = await self.international_rules.check_export_import_license(
                commodity_id=commodity_id,
                seller_country=seller_country,
                buyer_country=buyer_country,
                seller_partner_id=partner_id if transaction_type == "SELL" else counterparty_id
            )
            international_checks.append(license_check)
            
            # INSTANT BLOCK if license missing
            if license_check.get("blocked"):
                return {
                    "score": 0,
                    "status": "FAIL",
                    "blocked": True,
                    "blocking_reason": license_check["reason"],
                    "violation_type": license_check["violation_type"],
                    "tier": "INTERNATIONAL_COMPLIANCE"
                }
            
            # Check 2: Phytosanitary
            phyto_check = await self.international_rules.check_phytosanitary_requirement(
                commodity_id=commodity_id,
                transaction_type="EXPORT" if transaction_type == "SELL" else "IMPORT",
                destination_country=buyer_country if transaction_type == "SELL" else seller_country
            )
            international_checks.append(phyto_check)
            
            # Check 3: Currency Compliance
            if proposed_currency:
                currency_check = await self.international_rules.check_currency_compliance(
                    commodity_id=commodity_id,
                    proposed_currency=proposed_currency,
                    transaction_type=transaction_type
                )
                international_checks.append(currency_check)
                
                if currency_check.get("blocked"):
                    return {
                        "score": 0,
                        "status": "FAIL",
                        "blocked": True,
                        "blocking_reason": currency_check["reason"],
                        "violation_type": currency_check["violation_type"],
                        "tier": "CURRENCY_COMPLIANCE"
                    }
            
            # Check 4: Payment Terms
            if payment_term_id:
                payment_check = await self.international_rules.check_international_payment_terms(
                    payment_term_id=payment_term_id,
                    buyer_country=buyer_country,
                    seller_country=seller_country,
                    transaction_value=amount
                )
                international_checks.append(payment_check)
        
        # Continue with existing scoring...
        
        return {
            "score": ...,
            "status": ...,
            "blocked": False,
            "international_checks": international_checks,  # ⭐ NEW
            "risk_factors": ...
        }
```

---

## 4. USING EXISTING DOCUMENT SYSTEM

### ✅ NO NEW FIELDS NEEDED in BusinessPartner!

**We already have a complete document management system:**

```python
# backend/modules/partners/models.py - PartnerDocument (ALREADY EXISTS)

class PartnerDocument(Base):
    """Documents uploaded by partner with OCR extraction"""
    
    __tablename__ = "partner_documents"
    
    id = Column(UUID)
    partner_id = Column(UUID, ForeignKey("business_partners.id"))
    
    document_type = Column(String)  # ✅ "iec", "foreign_export_license", etc.
    country = Column(String)
    
    file_url = Column(String)
    file_name = Column(String)
    
    # ✅ OCR EXTRACTION (Already implemented!)
    ocr_extracted_data = Column(JSON)  # ← License details extracted here!
    extraction_confidence = Column(Numeric)
    
    # ✅ VALIDITY (Already implemented!)
    issue_date = Column(Date)
    expiry_date = Column(Date)
    is_expired = Column(Boolean)  # ← Automatically calculated!
    
    # ✅ VERIFICATION (Already implemented!)
    verified = Column(Boolean)  # ← KYC approval
    verified_by = Column(UUID)
    verified_at = Column(DateTime)
```

**DocumentType enum ALREADY has international licenses:**

```python
# backend/modules/partners/enums.py - DocumentType (ALREADY EXISTS)

class DocumentType(str, Enum):
    # ✅ Indian Import/Export
    IEC = "iec"  # Import Export Code
    
    # ✅ Foreign Entity Documents
    FOREIGN_IMPORT_LICENSE = "foreign_import_license"
    FOREIGN_EXPORT_LICENSE = "foreign_export_license"
    FOREIGN_TAX_ID = "foreign_tax_id"
    
    # ✅ Other international docs
    TAX_ID_CERTIFICATE = "tax_id_certificate"
    BUSINESS_REGISTRATION = "business_registration"
    ADDRESS_PROOF = "address_proof"
```

### How License Validation Works:

```python
# 1️⃣ Partner uploads IEC certificate PDF
# PartnerDocumentService processes it with OCR
await partner_doc_service.upload_document(
    partner_id=seller_id,
    document_type=DocumentType.IEC,
    file=uploaded_file,
    uploaded_by=admin_id
)

# 2️⃣ OCR extracts license data automatically
# (Already implemented in DocumentProcessingService)
ocr_data = {
    "license_number": "IEC0515012345",
    "license_type": "IEC",
    "license_countries": ["USA", "EU", "UAE"],
    "issuing_authority": "DGFT",
    "issue_date": "2020-01-01",
    "expiry_date": "2026-12-31"
}

# 3️⃣ Admin verifies document
await partner_doc_service.update_document_status(
    document_id=doc_id,
    status="approved",
    verified_by=admin_id
)

# 4️⃣ RuleEngine queries PartnerDocument
license_doc = await db.execute(
    select(PartnerDocument).where(
        PartnerDocument.partner_id == seller_id,
        PartnerDocument.document_type == "iec",
        PartnerDocument.verified == True,  # Only KYC approved
        PartnerDocument.is_expired == False  # Auto-checked
    )
)

# 5️⃣ Validate OCR extracted data
ocr_data = license_doc.ocr_extracted_data
if buyer_country not in ocr_data["license_countries"]:
    # BLOCK: Destination not covered
```

### Database Query for License Check:

```sql
-- Get verified, non-expired IEC/export license
SELECT 
    pd.id,
    pd.document_type,
    pd.ocr_extracted_data,
    pd.expiry_date,
    pd.verified,
    pd.is_expired
FROM partner_documents pd
WHERE pd.partner_id = ?
  AND pd.document_type IN ('iec', 'foreign_export_license')
  AND pd.verified = true  -- KYC approved only
  AND pd.is_expired = false  -- Automatically maintained
ORDER BY pd.expiry_date DESC  -- Latest license first
LIMIT 1;
```

### OCR Extracted Data Structure:

```json
{
  "license_number": "IEC0515012345",
  "license_type": "IEC",  // or "DGFT", "EXPORT_LICENSE"
  "license_countries": ["USA", "EU", "UAE", "Bangladesh"],
  "issuing_authority": "DGFT",
  "issue_date": "2020-01-01",
  "expiry_date": "2026-12-31",
  "registered_address": "...",
  "pan_number": "AAACR1234C",
  "confidence": 95.5  // OCR confidence score
}
```

---

## 5. DATA REQUIREMENTS SUMMARY

### Orchestrator will call both engines:

```python
# RuleEngine checks international compliance (TIER 1)
# MLRiskEngine predicts cross-border risk (TIER 2)

# Example:
rule_result = await rule_engine.comprehensive_check(
    partner_id=seller_id,
    transaction_type="SELL",
    commodity_id=cotton_id,
    amount=Decimal("500000"),
    buyer_country="USA",
    seller_country="IND",
    proposed_currency="USD",
    payment_term_id=lc_term_id,
    quality_standard="USDA"
)

# If blocked by international rules → ML never runs
if rule_result["blocked"]:
    return rule_result  # INSTANT BLOCK

# Otherwise, ML can add predictive insights
ml_result = await ml_engine.predict_risk(...)
```

---

## 5A. REAL DATA FLOW EXAMPLE

### Example: Indian Seller Exporting Cotton to USA

**Step-by-Step Validation:**

```python
# ============================================================================
# DATABASE STATE BEFORE TRANSACTION
# ============================================================================

# Commodity: Cotton - Shankar-6
commodity = Commodity(
    id="uuid-1",
    name="Cotton - Shankar-6",
    category="RAW_MATERIAL",
    hs_code_6digit="520100",
    export_regulations={
        "license_required": True,  # ← Export license needed!
        "license_types": ["IEC", "DGFT"],  # ← Accept either type
        "restricted_countries": ["Iran", "North Korea"],  # ← Sanctions
        "minimum_export_value": 50000,  # ← Below $50K, no license needed
        "restriction_reason": "UN trade sanctions"
    },
    import_regulations={
        "license_required": False,  # ← USA doesn't require import license for cotton
        "quota": False
    },
    phytosanitary_required=True,
    fumigation_required=True
)

# Seller: ABC Cotton Exports (India)
seller = BusinessPartner(
    id="uuid-seller",
    legal_name="ABC Cotton Exports Pvt Ltd",
    partner_type="seller",
    primary_country="India"
)

# ✅ Seller's IEC License Document (ALREADY IN SYSTEM)
seller_iec_document = PartnerDocument(
    id="uuid-doc-iec-1",
    partner_id="uuid-seller",
    
    # ✅ Document Type (already exists in enum!)
    document_type="iec",  # DocumentType.IEC
    country="India",
    
    # ✅ File details
    file_url="https://storage.example.com/abc-exports/iec_certificate.pdf",
    file_name="IEC_Certificate_ABC_Exports.pdf",
    file_size=245678,
    mime_type="application/pdf",
    
    # ✅ OCR Extracted Data (auto-extracted during upload!)
    ocr_extracted_data={
        "license_number": "IEC0515012345",
        "license_type": "IEC",
        "license_countries": ["USA", "EU", "UAE", "Bangladesh"],  # ← USA included ✅
        "issuing_authority": "DGFT India",
        "issue_date": "2020-01-01",
        "expiry_date": "2026-12-31",
        "pan_number": "AAACR1234C",
        "registered_address": "123 Export Plaza, Mumbai, India",
        "confidence": 95.5  # OCR confidence
    },
    extraction_confidence=95.5,
    
    # ✅ Validity (auto-maintained!)
    issue_date="2020-01-01",
    expiry_date="2026-12-31",
    is_expired=False,  # ← Automatically calculated ✅
    
    # ✅ Verification (KYC approved!)
    verified=True,  # ← Admin approved ✅
    verified_by="uuid-admin-1",
    verified_at="2024-11-15 10:30:00",
    
    uploaded_at="2024-11-14 14:00:00"
)

# Buyer: XYZ Textiles (USA)
buyer = BusinessPartner(
    id="uuid-buyer",
    legal_name="XYZ Textiles Inc",
    partner_type="buyer",
    primary_country="USA"
)
# No import license document needed (USA doesn't require for cotton)

# Transaction Details
transaction = {
    "commodity_id": "uuid-1",
    "seller_id": "uuid-seller",
    "buyer_id": "uuid-buyer",
    "buyer_country": "USA",
    "seller_country": "India",
    "transaction_value": Decimal("200000"),  # $200K (above minimum)
    "quantity": 100,  # bales
    "currency": "USD"
}

# ============================================================================
# VALIDATION EXECUTION
# ============================================================================

result = await international_rules.check_export_import_license(
    commodity_id=transaction["commodity_id"],
    seller_partner_id=transaction["seller_id"],
    buyer_partner_id=transaction["buyer_id"],
    buyer_country=transaction["buyer_country"],
    seller_country=transaction["seller_country"],
    transaction_value=transaction["transaction_value"]
)

# ============================================================================
# SQL QUERY EXECUTED INTERNALLY
# ============================================================================

# SELECT * FROM partner_documents
# WHERE partner_id = 'uuid-seller'
#   AND document_type IN ('iec', 'foreign_export_license')
#   AND verified = true
#   AND is_expired = false
# ORDER BY expiry_date DESC
# LIMIT 1;

# ============================================================================
# VALIDATION RESULT: ✅ PASS
# ============================================================================

{
    "blocked": False,
    "reason": "Export/Import license validation passed",
    "seller_license_doc_id": "uuid-doc-iec-1",
    "seller_license_number": "IEC0515012345",
    "buyer_license_doc_id": None,  # Not required for USA
    "checks_passed": [
        "✅ Export license document exists (PartnerDocument)",
        "✅ Document is verified (verified=True)",
        "✅ Document not expired (is_expired=False)",
        "✅ License type IEC is accepted",
        "✅ Destination USA in ocr_extracted_data.license_countries",
        "✅ USA not in restricted countries",
        "✅ Transaction value $200K above minimum $50K",
        "✅ Import license not required for USA"
    ]
}
```

### Example: BLOCKED Scenarios

#### Scenario 1: No Export License Document
```python
# No PartnerDocument with document_type='iec' AND verified=True

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": True,  # ← TRADE BLOCKED!
    "reason": "Export license required for Cotton - Shankar-6 but seller does not have verified export license (IEC/DGFT) document",
    "violation_type": "EXPORT_LICENSE_MISSING",
    "required_license_types": ["IEC", "DGFT"],
    "commodity_name": "Cotton - Shankar-6",
    "how_to_fix": "Upload IEC/DGFT certificate in Documents section and get it verified"
}
```

#### Scenario 2: License Expired
```python
seller_iec_document.expiry_date = "2024-01-01"  # ← PAST DATE
seller_iec_document.is_expired = True  # ← Auto-calculated ❌

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": True,
    "reason": "Seller has expired export license. License expired on 2024-01-01",
    "violation_type": "EXPORT_LICENSE_EXPIRED",
    "license_number": "IEC0515012345",
    "expiry_date": "2024-01-01",
    "document_id": "uuid-doc-iec-1",
    "how_to_fix": "Renew export license and upload new certificate"
}
```

#### Scenario 3: Destination Not Covered
```python
seller_iec_document.ocr_extracted_data["license_countries"] = ["EU", "UAE"]  # ← USA NOT IN LIST ❌
transaction["buyer_country"] = "USA"

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": True,
    "reason": "Seller's export license does not cover USA. License valid for: EU, UAE",
    "violation_type": "DESTINATION_NOT_COVERED",
    "destination_country": "USA",
    "licensed_countries": ["EU", "UAE"],
    "document_id": "uuid-doc-iec-1",
    "how_to_fix": "Update license to include USA or upload worldwide license"
}
```

#### Scenario 4: Restricted Destination
```python
transaction["buyer_country"] = "Iran"  # ← IN RESTRICTED LIST ❌

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": True,
    "reason": "Export of Cotton - Shankar-6 to Iran is RESTRICTED. Reason: UN trade sanctions",
    "violation_type": "RESTRICTED_DESTINATION",
    "commodity_name": "Cotton - Shankar-6",
    "restricted_country": "Iran",
    "restriction_reason": "UN trade sanctions",
    "how_to_fix": "Cannot trade to this destination (regulatory restriction)"
}
```

#### Scenario 5: Document Not Verified (KYC Pending)
```python
seller_iec_document.verified = False  # ← NOT VERIFIED BY ADMIN ❌

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": True,
    "reason": "Export license required for Cotton - Shankar-6 but seller does not have verified export license (IEC/DGFT) document",
    "violation_type": "EXPORT_LICENSE_MISSING",
    "note": "Document exists but not verified (KYC pending)",
    "how_to_fix": "Contact admin to verify uploaded IEC certificate"
}
```

### Example: Small Value Exemption
```python
transaction["transaction_value"] = Decimal("30000")  # ← Below $50K minimum

result = await check_export_import_license(...)

# RESULT:
{
    "blocked": False,  # ← ALLOWED! ✅
    "reason": "Export value below license threshold ($50000)",
    "exemption": "SMALL_VALUE_EXEMPTION",
    "transaction_value": 30000,
    "minimum_value": 50000,
    "note": "Small value exports exempt from export license requirement (as per commodity regulations)"
}
```

---

## 6. NO DATABASE MIGRATION NEEDED ✅

**All required tables and fields already exist!**

- ✅ `partner_documents` table exists
- ✅ `document_type` column exists (supports "iec", "foreign_export_license", etc.)
- ✅ `ocr_extracted_data` JSON column exists
- ✅ `verified`, `is_expired` columns exist
- ✅ `issue_date`, `expiry_date` columns exist

**DocumentType enum already has:**
- ✅ `IEC` = "iec"
- ✅ `FOREIGN_EXPORT_LICENSE` = "foreign_export_license"
- ✅ `FOREIGN_IMPORT_LICENSE` = "foreign_import_license"

**No schema changes required - just use existing system!**

---

## 7. TESTING APPROACH

### Test Scenarios:

```python
# Test 1: Export license missing
async def test_export_license_required_but_missing():
    # Cotton with export_regulations.license_required = true
    # Seller without export_license_number
    # Expected: BLOCKED
    
    result = await rule_engine.comprehensive_check(
        commodity_id=cotton_id,
        seller_country="IND",
        buyer_country="USA",
        ...
    )
    
    assert result["blocked"] == True
    assert result["violation_type"] == "EXPORT_LICENSE_MISSING"

# Test 2: Restricted destination
async def test_restricted_destination_country():
    # Cotton with restricted_countries = ["XYZ"]
    # Buyer from XYZ
    # Expected: BLOCKED
    
    result = await rule_engine.comprehensive_check(
        buyer_country="XYZ",
        ...
    )
    
    assert result["blocked"] == True
    assert result["violation_type"] == "RESTRICTED_DESTINATION"

# Test 3: Unsupported currency
async def test_unsupported_currency():
    # Cotton supports [USD, INR, EUR]
    # Trade in JPY
    # Expected: BLOCKED
    
    result = await rule_engine.comprehensive_check(
        proposed_currency="JPY",
        ...
    )
    
    assert result["blocked"] == True
    assert result["violation_type"] == "UNSUPPORTED_CURRENCY"
```

---

## 8. TIMELINE

### Week 1: Setup & National Compliance
- ✅ Create feature branch `feat/dual-engine-orchestrator`
- Create `national_compliance_rules.py`
  - GST certificate validation (using PartnerDocument)
  - PAN card validation (using PartnerDocument)
  - IEC validation for domestic high-value
- Unit tests for national checks

### Week 2: International Compliance
- Create `international_compliance_rules.py`
  - Sanctions compliance check (PRIORITY)
  - Export/Import license validation (using PartnerDocument)
  - Currency, phytosanitary, quality checks
- Update `risk_engine.py` with complete flow
- Integration tests

### Week 3: Orchestrator Layer
- Create orchestrator files
- Implement fusion layer (ML + Rules)
- Circuit breaker for ML failures
- End-to-end testing

### Week 4: Testing & Deployment
- Performance testing
- Load testing
- Deploy to staging
- Production rollout

---

## 9. COMPLETE SUMMARY

### ✅ NATIONAL COMPLIANCE (India Domestic)

**Checks Added:**
1. **GST Certificate Validation** (BLOCKING)
   - Uses: `PartnerDocument` with `document_type='gst_certificate'`
   - OCR extracts: GSTIN, state code, registration date
   - Validates: Document verified, GSTIN extracted, state match

2. **PAN Card Validation** (BLOCKING)
   - Uses: `PartnerDocument` with `document_type='pan_card'`
   - OCR extracts: PAN number
   - Validates: Document verified, PAN format correct

3. **IEC Validation for Domestic** (WARNING)
   - Uses: `PartnerDocument` with `document_type='iec'`
   - Triggered: Inter-state trades > Rs 10 lakhs
   - Validates: Recommended but not blocking

### ✅ INTERNATIONAL COMPLIANCE (Cross-Border)

**Checks Added:**
1. **Sanctions Compliance** (BLOCKING - RUN FIRST!)
   - Validates: Buyer/seller country not sanctioned
   - Validates: Commodity not restricted for destination
   - Data source: `commodity.export_regulations.restricted_countries`

2. **Export/Import License Validation** (BLOCKING)
   - Uses: `PartnerDocument` with `document_type='iec'` or `'foreign_export_license'`
   - OCR extracts: License number, license countries, expiry
   - Validates: Document verified, not expired, destination covered

3. **Currency Compliance** (BLOCKING)
   - Data source: `commodity.supported_currencies`
   - Validates: Proposed currency supported

4. **Phytosanitary Certificate** (WARNING)
   - Data source: `commodity.phytosanitary_required`
   - Alerts if required for agricultural exports

5. **Quality Standards** (WARNING)
   - Data source: `commodity.quality_standards`
   - Alerts if non-standard grading used

6. **Payment Terms** (WARNING)
   - Data source: `payment_term.supports_letter_of_credit`
   - Recommends LC for high-value trades

7. **Seasonal & Shelf Life** (WARNING)
   - Data source: `commodity.harvest_season`, `commodity.shelf_life_days`
   - Alerts if off-season or shelf life issues

### ✅ INTERNAL TRADING RULES (Existing - Applies to Both National + International)

**These checks run for ALL trades regardless of domestic or cross-border:**

1. **Circular Trading** (BLOCKING)
   - Prevents unsettled opposite positions
   - Example: Seller has unpaid BUY position, now wants to SELL same commodity

2. **Wash Trading** (BLOCKING)
   - Prevents same-day reversals
   - Example: BUY 100 bales at 10am, SELL 100 bales at 2pm (price manipulation)

3. **Party Links** (BLOCKING - Applies to BOTH National + International)
   - **Critical**: This check runs for ALL trades (domestic India + cross-border)
   - Validates: Buyer and seller are not the same entity
   - Checks: Same PAN number, same GST number, same legal entity
   - Example: Company A selling to Company B, but both have same PAN
   - **Why for international?** Foreign entities may have Indian subsidiaries with same parent company

### ✅ DATA SOURCES (ALL EXISTING!)

**PartnerDocument Table:**
- `document_type` = "gst_certificate", "pan_card", "iec", "foreign_export_license"
- `ocr_extracted_data` JSON field with license details
- `verified` boolean for KYC approval
- `is_expired` boolean auto-calculated
- `expiry_date` for validity check

**Commodity Table:**
- `export_regulations` JSON (license_required, restricted_countries)
- `import_regulations` JSON
- `phytosanitary_required`, `fumigation_required`
- `supported_currencies` JSON array
- `quality_standards` JSON array
- `seasonal_commodity`, `harvest_season`, `shelf_life_days`

### ✅ NO DATABASE MIGRATION NEEDED!

**Everything already exists:**
- ✅ `partner_documents` table
- ✅ `document_type` column supports all document types
- ✅ `ocr_extracted_data` JSON column
- ✅ `verified`, `is_expired` columns
- ✅ `DocumentType` enum has GST, PAN, IEC, export licenses

### ✅ EXECUTION ORDER (CRITICAL!)

```
1. SANCTIONS CHECK (International only) ← HIGHEST PRIORITY
   └─→ BLOCKED? → Return Error

2. NATIONAL CHECKS (India domestic only)
   ├── GST Certificate ← BLOCKING
   ├── PAN Card ← BLOCKING
   └── IEC (high-value) ← WARNING

3. EXPORT/IMPORT LICENSE (International only) ← BLOCKING

4. INTERNAL TRADING RULES (Both National + International)
   ├── Circular Trading ← BLOCKING
   ├── Wash Trading ← BLOCKING
   └── Party Links (Same PAN/GST) ← BLOCKING (Applies to ALL trades)

5. ADDITIONAL CHECKS (Warnings)
   ├── Currency Compliance ← BLOCKING
   ├── Phytosanitary ← WARNING
   ├── Quality Standards ← WARNING
   └── Payment Terms ← WARNING

6. CREDIT & RISK SCORING
```

### ✅ VALIDATION RESPONSE STRUCTURE

```json
{
  "score": 85,
  "status": "PASS",
  "blocked": false,
  "compliance_checks": {
    "trade_type": "INTERNATIONAL",
    "national_checks": [
      {
        "check": "gst_registration",
        "blocked": false,
        "gstin": "27AABCU9603R1ZX",
        "document_id": "uuid-gst-1"
      }
    ],
    "international_checks": [
      {
        "check": "sanctions_compliance",
        "blocked": false
      },
      {
        "check": "export_import_license",
        "blocked": false,
        "seller_license_doc_id": "uuid-iec-1",
        "seller_license_number": "IEC0515012345"
      }
    ],
    "internal_checks": [
      {
        "check": "circular_trading",
        "blocked": false
      },
      {
        "check": "wash_trading",
        "blocked": false
      }
    ]
  },
  "warnings": [
    {
      "check": "phytosanitary_requirement",
      "warning": true,
      "reason": "Phytosanitary certificate required for exporting Cotton"
    }
  ]
}
```

---

## 10. READY TO IMPLEMENT?

**Confirmation Checklist:**

- ✅ National compliance uses PartnerDocument (GST, PAN, IEC)
- ✅ International compliance uses PartnerDocument (IEC, export licenses)
- ✅ Sanctions check runs FIRST for international trades
- ✅ All existing internal rules preserved (circular, wash, party links)
- ✅ No database migration needed
- ✅ OCR system already extracts license data
- ✅ KYC verification workflow already exists

**Next Steps:**
1. Create feature branch
2. Implement `national_compliance_rules.py`
3. Implement `international_compliance_rules.py` with sanctions check first
4. Update `risk_engine.py` with complete flow
5. Write unit tests
6. Integration testing

**Ready to proceed?** 🚀
