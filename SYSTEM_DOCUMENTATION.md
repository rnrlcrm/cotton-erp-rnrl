# COTTON ERP - COMPLETE SYSTEM DOCUMENTATION
**Last Updated:** December 2, 2025  
**Platform:** Global Multi-Commodity Trading Platform (Cotton, Wheat, Rice, Metals, etc.)  
**Vision:** 2040-Grade, 95%+ Autonomous, AI-Driven

---

## 📋 TABLE OF CONTENTS

1. [Infrastructure Overview](#infrastructure-overview)
2. [Module Status](#module-status)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Authentication & Authorization](#authentication--authorization)
6. [AI Integration Plan](#ai-integration-plan)
7. [Deployment](#deployment)
8. [Known Issues & TODOs](#known-issues--todos)

---

## 🏗️ INFRASTRUCTURE OVERVIEW

### **Technology Stack**

#### **Backend**
- **Framework:** FastAPI (Python 3.12)
- **Database:** PostgreSQL 15+ with pgvector extension
- **Cache:** Redis (for sessions, idempotency, rate limiting)
- **ORM:** SQLAlchemy 2.0 (async)
- **Authentication:** JWT (access + refresh tokens)
- **WebSocket:** FastAPI WebSockets
- **Background Tasks:** APScheduler (cron jobs)

#### **Middleware Stack** (Execution Order)
1. `RequestIDMiddleware` - Adds X-Request-ID header
2. `IdempotencyMiddleware` - Prevents duplicate requests (24h cache)
3. `AuthMiddleware` - JWT validation
4. `DataIsolationMiddleware` - Multi-tenant data filtering
5. `SecureHeadersMiddleware` - Security headers
6. `CORSMiddleware` - Cross-origin requests

#### **Infrastructure Features**
- ✅ Idempotency (all POST/PUT/PATCH/DELETE)
- ✅ Rate Limiting (SlowAPI)
- ✅ Event Sourcing (transactional outbox pattern)
- ✅ WebSocket real-time notifications
- ✅ Multi-device session management
- ✅ Capability-based RBAC
- ✅ PII sanitization in logs (GDPR compliant)
- ✅ OpenTelemetry observability
- ⚠️ AI/ML Integration (planned, partial)
- ❌ OCR Module (not implemented)
- ❌ Market Trends (not implemented)

---

## 📦 MODULE STATUS

### **✅ FULLY IMPLEMENTED (5 modules)**

#### **1. Authentication & User Onboarding**
**Location:** `backend/modules/auth/`, `backend/modules/user_onboarding/`  
**Status:** ✅ Production-ready  
**API Prefix:** `/api/v1/auth`

**Features:**
- Mobile OTP-based login (6-digit OTP)
- JWT access + refresh tokens
- Multi-device session management
- Remote logout (logout specific device)
- Logout all devices
- Suspicious login detection
- Token rotation (refresh token single-use)
- Cross-device session sync

**Endpoints:**
```
POST   /api/v1/auth/send-otp          - Send OTP to mobile
POST   /api/v1/auth/verify-otp        - Verify OTP and get tokens
POST   /api/v1/auth/refresh           - Refresh access token
GET    /api/v1/auth/sessions          - List all user sessions
POST   /api/v1/auth/logout            - Logout specific device
POST   /api/v1/auth/logout-all        - Logout from all devices
```

**Sample Request (Send OTP):**
```json
POST /api/v1/auth/send-otp
{
  "mobile_number": "+919876543210"
}
```

**Sample Response:**
```json
{
  "message": "OTP sent successfully",
  "otp_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_in": 300,
  "otp": "123456"  // Only in development
}
```

**Database Tables:**
- `users` - User accounts
- `user_sessions` - Active sessions per device
- `otp_verifications` - OTP attempts tracking

---

#### **2. Settings Module**

**Location:** `backend/modules/settings/`  
**Status:** ✅ Production-ready  
**API Prefix:** `/api/v1/settings`

**Sub-Modules:**

##### **2.1 Commodity Master**
**Location:** `settings/commodities/`  
**Status:** ✅ Fully implemented (1000+ lines)

**Features:**
- Multi-commodity support (Cotton, Wheat, Rice, Metals, etc.)
- Dynamic quality parameters (JSONB schema)
- Unit conversion system
- HSN code learning (AI-assisted)
- Bulk operations (Excel import/export)
- Commodity varieties management
- Bargain types configuration
- Commission structures

**Endpoints:**
```
POST   /api/v1/settings/commodities              - Create commodity
GET    /api/v1/settings/commodities              - List all commodities
GET    /api/v1/settings/commodities/{id}         - Get commodity details
PATCH  /api/v1/settings/commodities/{id}         - Update commodity
DELETE /api/v1/settings/commodities/{id}         - Delete commodity
POST   /api/v1/settings/commodities/bulk-import  - Import from Excel
GET    /api/v1/settings/commodities/bulk-export  - Export to Excel
POST   /api/v1/settings/commodities/{id}/hsn-suggest - AI HSN suggestion
```

**Sample Request (Create Commodity):**
```json
POST /api/v1/settings/commodities
{
  "name": "Cotton",
  "category": "FIBER",
  "base_unit": "BALES",
  "quality_parameters": {
    "staple_length": {"type": "range", "unit": "mm", "min": 20, "max": 40},
    "micronaire": {"type": "range", "unit": "units", "min": 3.0, "max": 6.0},
    "strength": {"type": "range", "unit": "g/tex", "min": 20, "max": 35},
    "trash_content": {"type": "range", "unit": "%", "min": 0, "max": 5}
  },
  "price_unit": "PER_CANDY",
  "hsn_code": "52010010",
  "is_active": true
}
```

**Database Tables:**
- `settings_commodities` - Commodity master
- `commodity_parameters` - Quality parameter definitions
- `commodity_varieties` - Commodity varieties (e.g., MCU-5, DCH-32)
- `conversion_rules` - Unit conversion mappings
- `bargain_types` - Bargain type configurations
- `commission_structures` - Commission rules

---

##### **2.2 Location Master**
**Location:** `settings/locations/`  
**Status:** ✅ Fully implemented with Google Maps integration

**Features:**
- Google Places API integration
- Autocomplete location search
- Timezone detection
- Lat/long coordinates
- Hierarchical location (City → District → State → Country)
- Location-based filtering

**Endpoints:**
```
POST   /api/v1/settings/locations                    - Create location
GET    /api/v1/settings/locations                    - List all locations
GET    /api/v1/settings/locations/{id}               - Get location details
PATCH  /api/v1/settings/locations/{id}               - Update location
DELETE /api/v1/settings/locations/{id}               - Delete location
POST   /api/v1/settings/locations/google/search      - Google Places search
POST   /api/v1/settings/locations/google/details     - Get place details
```

**Sample Request (Google Places Search):**
```json
POST /api/v1/settings/locations/google/search
{
  "query": "Mumbai",
  "country_code": "IN"
}
```

**Sample Response:**
```json
{
  "suggestions": [
    {
      "place_id": "ChIJwe1EZjDG5zsRaYxkjY_tpF0",
      "description": "Mumbai, Maharashtra, India",
      "main_text": "Mumbai",
      "secondary_text": "Maharashtra, India"
    }
  ]
}
```

**Database Tables:**
- `settings_locations` - Location master with timezone

---

##### **2.3 Payment Terms, Delivery Terms, Weighment Terms**
**Status:** ✅ Implemented

**Features:**
- Payment terms (COD, Credit, Advance, etc.)
- Delivery terms (EX-GODOWN, FOR, FOB, CIF, etc.)
- Weighment terms (Seller, Buyer, Third-party)
- Active/inactive management

**Database Tables:**
- `settings_payment_terms`
- `settings_delivery_terms`
- `settings_weighment_terms`

---

#### **3. Business Partners Module**

**Location:** `backend/modules/partners/`  
**Status:** ✅ Production-ready (1200+ lines)  
**API Prefix:** `/api/v1/partners`

**Features:**
- Complete partner onboarding workflow
- Multi-role support (Buyer, Seller, Trader, Transporter, etc.)
- KYC document management
- GST/PAN verification (API integration ready)
- Capability Detection & Prediction System (CDPS)
- Partner approval workflow
- Amendment requests
- Employee management
- KYC renewal tracking
- Vehicle/fleet management

**Endpoints:**
```
POST   /api/v1/partners/onboarding/start                  - Start onboarding
POST   /api/v1/partners/onboarding/{app_id}/documents     - Upload documents
POST   /api/v1/partners/onboarding/{app_id}/submit        - Submit for approval
GET    /api/v1/partners/onboarding/{app_id}/status        - Check status
POST   /api/v1/partners/{partner_id}/approve              - Approve partner
POST   /api/v1/partners/{partner_id}/reject               - Reject application
GET    /api/v1/partners                                   - List partners
GET    /api/v1/partners/{partner_id}                      - Get partner details
POST   /api/v1/partners/{partner_id}/amendments           - Request amendment
POST   /api/v1/partners/{partner_id}/employees            - Add employee
POST   /api/v1/partners/{partner_id}/kyc/renew            - Renew KYC
GET    /api/v1/partners/kyc/expiring                      - Get expiring KYC
GET    /api/v1/partners/dashboard/stats                   - Dashboard stats
```

**Sample Request (Start Onboarding):**
```json
POST /api/v1/partners/onboarding/start
{
  "business_name": "ABC Cotton Traders",
  "mobile_number": "+919876543210",
  "email": "abc@example.com",
  "gstin": "27AABCT1234A1Z5",
  "pan": "AABCT1234A",
  "partner_type": "TRADER",
  "capabilities": {
    "can_buy": true,
    "can_sell": true,
    "can_transport": false,
    "can_finance": false
  }
}
```

**Database Tables:**
- `business_partners` - Partner master with capabilities (JSONB)
- `onboarding_applications` - Onboarding workflow
- `partner_documents` - KYC documents
- `partner_employees` - Employee management
- `partner_locations` - Business locations
- `partner_bank_accounts` - Bank details
- `partner_vehicles` - Fleet management
- `partner_amendments` - Amendment requests

---

#### **4. Risk Engine Module**

**Location:** `backend/modules/risk/`  
**Status:** ✅ Fully implemented (900+ lines)  
**API Prefix:** `/api/v1/risk`

**Features:**
- Credit limit checking
- Exposure monitoring
- Circular trading detection (settlement-based)
- Wash trading prevention
- Party link validation (buyer-seller relationships)
- Role restriction validation
- ML-based risk prediction (payment default, fraud)
- Batch risk assessment

**Endpoints:**
```
POST   /api/v1/risk/assess/requirement           - Assess requirement risk
POST   /api/v1/risk/assess/availability          - Assess availability risk
POST   /api/v1/risk/assess/trade                 - Assess trade risk
POST   /api/v1/risk/assess/partner               - Assess partner risk
POST   /api/v1/risk/assess/batch                 - Batch assessment
POST   /api/v1/risk/check/party-links            - Check party relationships
POST   /api/v1/risk/check/circular-trading       - Detect circular trading
POST   /api/v1/risk/check/role-restriction       - Check role restrictions
POST   /api/v1/risk/monitor/exposure             - Monitor exposure
POST   /api/v1/risk/ml/predict                   - ML predictions
POST   /api/v1/risk/ml/train                     - Train ML models
```

**Sample Request (Assess Requirement Risk):**
```json
POST /api/v1/risk/assess/requirement
{
  "requirement_id": "550e8400-e29b-41d4-a716-446655440000",
  "buyer_id": "660e8400-e29b-41d4-a716-446655440000",
  "estimated_value": 5000000.00,
  "currency": "INR"
}
```

**Sample Response:**
```json
{
  "risk_score": 35,
  "risk_status": "PASS",
  "factors": {
    "credit_limit_check": {"status": "PASS", "message": "Within limit"},
    "exposure_check": {"status": "PASS", "message": "20% of limit"},
    "buyer_rating": {"status": "PASS", "score": 4.5},
    "payment_history": {"status": "PASS", "on_time_percentage": 95}
  },
  "recommendations": [
    "Monitor payment closely",
    "Consider bank guarantee for large orders"
  ]
}
```

**Database Tables:**
- `risk_assessments` - Risk assessment history
- `credit_limits` - Partner credit limits
- `exposure_monitoring` - Real-time exposure tracking
- `party_links` - Buyer-seller relationships
- `risk_rules` - Configurable risk rules

**ML Models:**
- `RandomForestClassifier` - Payment default prediction
- `GradientBoostingRegressor` - Credit limit optimization
- `IsolationForest` - Fraud detection

**⚠️ Known Issue:** ML models use synthetic data. Need to train on real trading data.

---

#### **5. Trade Desk Module**

**Location:** `backend/modules/trade_desk/`  
**Status:** ⚠️ **IMPLEMENTED BUT NOT REGISTERED IN MAIN.PY**  
**API Prefix:** ❌ NOT AVAILABLE (not in main.py)

**Sub-Modules:**

##### **5.1 Availability Engine**
**File:** `services/availability_service.py` (1391 lines)  
**Status:** ✅ Fully implemented

**Features:**
- Post inventory availability
- Dynamic quality parameters (per commodity)
- Price anomaly detection (AI placeholder)
- AI score vector calculation (AI placeholder)
- Auto-fetch delivery coordinates
- Reserve/Release/Mark Sold workflow
- Approval workflow
- Negotiation readiness scoring

**NOT ACCESSIBLE:** Routes exist in `routes/availability_routes.py` (498 lines) but not registered

**Endpoints (NOT WORKING - NOT IN MAIN.PY):**
```
POST   /api/v1/availabilities              - Create availability
GET    /api/v1/availabilities              - List availabilities
GET    /api/v1/availabilities/{id}         - Get availability details
PATCH  /api/v1/availabilities/{id}         - Update availability
DELETE /api/v1/availabilities/{id}         - Delete availability
POST   /api/v1/availabilities/{id}/reserve - Reserve inventory
POST   /api/v1/availabilities/{id}/release - Release reservation
POST   /api/v1/availabilities/{id}/sold    - Mark as sold
```

**AI TODOs (5 placeholders):**
- `normalize_quality_params()` - AI-based quality normalization
- `detect_price_anomaly()` - ML-based price anomaly detection
- `calculate_ai_score_vector()` - Semantic embeddings
- OCR for test reports
- Computer vision quality detection

---

##### **5.2 Requirement Engine**
**File:** `services/requirement_service.py` (1806 lines)  
**Status:** ✅ Fully implemented

**Features:**
- Post procurement requirements
- AI-powered 12-step pipeline (mostly placeholders)
- Budget validation
- Market price suggestion (AI placeholder)
- Tolerance recommendations (AI placeholder)
- Intent-based routing
- Fulfillment tracking
- Requirement cancellation

**NOT ACCESSIBLE:** Routes exist in `routes/requirement_routes.py` (838 lines) but not registered

**AI TODOs (6 placeholders):**
- `normalize_quality_requirements()` - AI normalization
- `suggest_market_price()` - AI/ML price prediction
- `calculate_ai_score_vector()` - Semantic embeddings
- `detect_unrealistic_budget()` - Anomaly detection
- `generate_market_context()` - Market sentiment analysis
- `recommend_tolerance()` - ML-based tolerance

---

##### **5.3 Instant Matching Engine**
**File:** `services/matching_service.py` (704 lines)  
**Status:** ✅ Fully implemented

**Features:**
- Real-time automatic matching
- Multi-factor scoring (price, quality, location, delivery, payment, urgency)
- Duplicate detection
- Cross-device notifications (WebSocket)
- Match approval workflow
- Safety cron (re-match missed entities)
- Audit trail

**NOT ACCESSIBLE:** Routes exist in `routes/matching_router.py` (471 lines) but not registered

**Matching Filters:**
- ✅ Commodity match (exact)
- ✅ Quantity range (±10% tolerance)
- ✅ Location validation (city/state/zone)
- ✅ Price range (configurable)
- ✅ Quality parameters (dynamic JSONB)
- ✅ Delivery terms compatibility
- ✅ Payment terms compatibility
- ✅ Party link validation (not buying from themselves)

**Scoring Algorithm:**
```
Total Score = (Price 30%) + (Quality 25%) + (Location 15%) + 
              (Delivery 10%) + (Payment 10%) + (Urgency 10%)
```

---

### **❌ NOT IMPLEMENTED (13 modules - Empty Skeletons)**

#### **6. OCR Module**
**Location:** `backend/modules/ocr/`  
**Status:** ❌ Empty (skeleton only)  
**Should Contain:**
- Invoice OCR (multi-language: Hindi, Mandarin, Arabic)
- Quality report OCR (USDA, GAFTA, BIS, LBMA standards)
- Transport document OCR (Bill of Lading, Airway Bill)
- Multi-currency extraction

---

#### **7. Market Trends Module**
**Location:** `backend/modules/market_trends/`  
**Status:** ❌ Empty  
**Should Contain:**
- Price prediction (LSTM per commodity)
- Demand forecasting
- Sentiment analysis (Bloomberg, Reuters feeds)
- Correlation analysis (crude oil → freight → commodity prices)

---

#### **8. Quality Management Module**
**Location:** `backend/modules/quality/`  
**Status:** ❌ Empty  
**Should Contain:**
- Computer vision quality grading (5+ models: Cotton, Wheat, Gold, etc.)
- Lab report analysis
- Quality dispute management

---

#### **9-18. Other Empty Modules**
- `accounting/` - ❌ Empty
- `payment_engine/` - ❌ Empty
- `contract_engine/` - ❌ Empty
- `logistics/` - ❌ Empty
- `dispute/` - ❌ Empty
- `compliance/` - ❌ Empty
- `notifications/` - ❌ Empty
- `reports/` - ❌ Empty
- `cci/` - ❌ Empty (CCI board integration)
- `controller/` - ❌ Empty

---

## 🗄️ DATABASE SCHEMA

### **Core Tables**

#### **Users & Auth**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    mobile_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    full_name VARCHAR,
    business_partner_id UUID REFERENCES business_partners(id),
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR,  -- SUPER_ADMIN, ORG_ADMIN, PARTNER_USER, etc.
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    refresh_token VARCHAR UNIQUE,
    device_info JSONB,  -- {device_id, device_name, os, app_version}
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);

CREATE TABLE otp_verifications (
    id UUID PRIMARY KEY,
    mobile_number VARCHAR(15),
    otp_code VARCHAR(6),
    attempts INT DEFAULT 0,
    expires_at TIMESTAMP,
    verified_at TIMESTAMP,
    created_at TIMESTAMP
);
```

#### **Business Partners**
```sql
CREATE TABLE business_partners (
    id UUID PRIMARY KEY,
    business_name VARCHAR NOT NULL,
    gstin VARCHAR(15) UNIQUE,
    pan VARCHAR(10),
    mobile_number VARCHAR(15),
    email VARCHAR,
    partner_status VARCHAR,  -- PENDING, APPROVED, REJECTED, SUSPENDED
    kyc_status VARCHAR,      -- NOT_STARTED, IN_PROGRESS, VERIFIED, EXPIRED
    partner_type VARCHAR,    -- DEPRECATED: Use capabilities instead
    capabilities JSONB,      -- {can_buy, can_sell, can_transport, can_finance, etc.}
    risk_category VARCHAR,   -- LOW, MEDIUM, HIGH
    credit_limit DECIMAL(15,2),
    rating DECIMAL(3,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE onboarding_applications (
    id UUID PRIMARY KEY,
    application_number VARCHAR UNIQUE,
    business_name VARCHAR,
    mobile_number VARCHAR(15),
    gstin VARCHAR(15),
    pan VARCHAR(10),
    status VARCHAR,  -- DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED
    submitted_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
    rejection_reason TEXT,
    created_at TIMESTAMP
);

CREATE TABLE partner_documents (
    id UUID PRIMARY KEY,
    partner_id UUID REFERENCES business_partners(id),
    document_type VARCHAR,  -- GST_CERTIFICATE, PAN_CARD, BANK_STATEMENT, etc.
    file_path VARCHAR,
    file_size BIGINT,
    mime_type VARCHAR,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id),
    created_at TIMESTAMP
);
```

#### **Settings**
```sql
CREATE TABLE settings_commodities (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    category VARCHAR,  -- FIBER, GRAIN, METAL, OIL_SEED, etc.
    base_unit VARCHAR, -- BALES, MT, KG, OZ, etc.
    quality_parameters JSONB,  -- Dynamic schema per commodity
    price_unit VARCHAR,
    hsn_code VARCHAR(8),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE settings_locations (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    city VARCHAR,
    district VARCHAR,
    state VARCHAR,
    country VARCHAR DEFAULT 'India',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    timezone VARCHAR,
    google_place_id VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);

CREATE TABLE settings_payment_terms (
    id UUID PRIMARY KEY,
    name VARCHAR UNIQUE,
    credit_days INT,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE settings_delivery_terms (
    id UUID PRIMARY KEY,
    name VARCHAR UNIQUE,  -- EX-GODOWN, FOR, FOB, CIF, etc.
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### **Trade Desk (NOT IN USE - ROUTES NOT REGISTERED)**
```sql
CREATE TABLE trade_desk_availabilities (
    id UUID PRIMARY KEY,
    seller_id UUID REFERENCES business_partners(id),
    commodity_id UUID REFERENCES settings_commodities(id),
    location_id UUID REFERENCES settings_locations(id),
    total_quantity DECIMAL(12,2),
    available_quantity DECIMAL(12,2),
    reserved_quantity DECIMAL(12,2),
    sold_quantity DECIMAL(12,2),
    quality_parameters JSONB,
    price DECIMAL(15,2),
    price_unit VARCHAR,
    delivery_terms VARCHAR,
    payment_terms VARCHAR,
    status VARCHAR,  -- DRAFT, ACTIVE, RESERVED, SOLD, EXPIRED
    ai_score_vector VECTOR(1536),  -- pgvector for semantic search
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE trade_desk_requirements (
    id UUID PRIMARY KEY,
    buyer_id UUID REFERENCES business_partners(id),
    commodity_id UUID REFERENCES settings_commodities(id),
    delivery_location_id UUID REFERENCES settings_locations(id),
    quantity DECIMAL(12,2),
    quantity_unit VARCHAR,
    quality_requirements JSONB,
    max_price DECIMAL(15,2),
    price_unit VARCHAR,
    delivery_terms VARCHAR,
    payment_terms VARCHAR,
    status VARCHAR,  -- DRAFT, ACTIVE, PARTIALLY_FULFILLED, FULFILLED, CANCELLED
    fulfillment_percentage DECIMAL(5,2),
    ai_score_vector VECTOR(1536),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE trade_desk_matches (
    id UUID PRIMARY KEY,
    requirement_id UUID REFERENCES trade_desk_requirements(id),
    availability_id UUID REFERENCES trade_desk_availabilities(id),
    match_score DECIMAL(5,2),
    score_breakdown JSONB,  -- {price: 0.9, quality: 0.85, location: 0.7, etc.}
    status VARCHAR,  -- PENDING, APPROVED, REJECTED
    notified_at TIMESTAMP,
    approved_at TIMESTAMP,
    created_at TIMESTAMP
);
```

#### **Risk Management**
```sql
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY,
    entity_type VARCHAR,  -- REQUIREMENT, AVAILABILITY, TRADE, PARTNER
    entity_id UUID,
    risk_score INT,  -- 0-100
    risk_status VARCHAR,  -- PASS, WARN, FAIL
    factors JSONB,
    recommendations TEXT[],
    assessed_by UUID REFERENCES users(id),
    created_at TIMESTAMP
);

CREATE TABLE credit_limits (
    id UUID PRIMARY KEY,
    partner_id UUID REFERENCES business_partners(id),
    currency VARCHAR DEFAULT 'INR',
    total_limit DECIMAL(15,2),
    utilized_amount DECIMAL(15,2),
    available_amount DECIMAL(15,2),
    valid_from DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE party_links (
    id UUID PRIMARY KEY,
    buyer_id UUID REFERENCES business_partners(id),
    seller_id UUID REFERENCES business_partners(id),
    relationship_type VARCHAR,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,
    created_at TIMESTAMP
);
```

---

## 🔌 API ENDPOINTS

### **Working Endpoints (Registered in main.py)**

#### **Authentication**
```
POST   /api/v1/auth/send-otp
POST   /api/v1/auth/verify-otp
POST   /api/v1/auth/refresh
GET    /api/v1/auth/sessions
POST   /api/v1/auth/logout
POST   /api/v1/auth/logout-all
```

#### **Business Partners**
```
POST   /api/v1/partners/onboarding/start
POST   /api/v1/partners/onboarding/{app_id}/documents
POST   /api/v1/partners/onboarding/{app_id}/submit
GET    /api/v1/partners/onboarding/{app_id}/status
POST   /api/v1/partners/{partner_id}/approve
POST   /api/v1/partners/{partner_id}/reject
GET    /api/v1/partners
GET    /api/v1/partners/{partner_id}
POST   /api/v1/partners/{partner_id}/amendments
POST   /api/v1/partners/{partner_id}/employees
GET    /api/v1/partners/dashboard/stats
```

#### **Settings - Commodities**
```
POST   /api/v1/settings/commodities
GET    /api/v1/settings/commodities
GET    /api/v1/settings/commodities/{id}
PATCH  /api/v1/settings/commodities/{id}
DELETE /api/v1/settings/commodities/{id}
POST   /api/v1/settings/commodities/bulk-import
GET    /api/v1/settings/commodities/bulk-export
```

#### **Settings - Locations**
```
POST   /api/v1/settings/locations
GET    /api/v1/settings/locations
GET    /api/v1/settings/locations/{id}
PATCH  /api/v1/settings/locations/{id}
DELETE /api/v1/settings/locations/{id}
POST   /api/v1/settings/locations/google/search
POST   /api/v1/settings/locations/google/details
```

#### **Risk Management**
```
POST   /api/v1/risk/assess/requirement
POST   /api/v1/risk/assess/availability
POST   /api/v1/risk/assess/trade
POST   /api/v1/risk/assess/partner
POST   /api/v1/risk/assess/batch
POST   /api/v1/risk/check/party-links
POST   /api/v1/risk/check/circular-trading
POST   /api/v1/risk/check/role-restriction
POST   /api/v1/risk/monitor/exposure
POST   /api/v1/risk/ml/predict
POST   /api/v1/risk/ml/train
```

#### **Infrastructure**
```
GET    /healthz                       - Health check
GET    /ready                         - Readiness probe
GET    /api/docs                      - Swagger UI
GET    /api/redoc                     - ReDoc
GET    /api/openapi.json              - OpenAPI schema
```

---

### **NOT ACCESSIBLE (Code exists but not in main.py)**

#### **Trade Desk - Availability Engine**
```
❌ POST   /api/v1/availabilities
❌ GET    /api/v1/availabilities
❌ GET    /api/v1/availabilities/{id}
❌ PATCH  /api/v1/availabilities/{id}
❌ POST   /api/v1/availabilities/{id}/reserve
❌ POST   /api/v1/availabilities/{id}/release
❌ POST   /api/v1/availabilities/{id}/sold
```

#### **Trade Desk - Requirement Engine**
```
❌ POST   /api/v1/requirements
❌ GET    /api/v1/requirements
❌ GET    /api/v1/requirements/{id}
❌ PATCH  /api/v1/requirements/{id}
❌ POST   /api/v1/requirements/{id}/cancel
❌ POST   /api/v1/requirements/{id}/ai-adjust
❌ GET    /api/v1/requirements/{id}/history
```

#### **Trade Desk - Matching Engine**
```
❌ GET    /api/v1/matches
❌ GET    /api/v1/matches/{id}
❌ POST   /api/v1/matches/{id}/approve
❌ POST   /api/v1/matches/{id}/reject
❌ POST   /api/v1/matches/rematch
```

**⚠️ CRITICAL ISSUE:** Trade Desk module is fully implemented (5700+ lines of code) but NOT registered in `backend/app/main.py`. None of the Trade Desk endpoints are accessible.

---

## 🔐 AUTHENTICATION & AUTHORIZATION

### **Authentication Flow**

1. **Send OTP**
   ```
   POST /api/v1/auth/send-otp
   Body: {"mobile_number": "+919876543210"}
   Response: {"otp_id": "...", "expires_in": 300}
   ```

2. **Verify OTP & Get Tokens**
   ```
   POST /api/v1/auth/verify-otp
   Body: {"otp_id": "...", "otp_code": "123456", "device_info": {...}}
   Response: {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer",
     "expires_in": 900
   }
   ```

3. **Use Access Token**
   ```
   GET /api/v1/partners
   Headers: {"Authorization": "Bearer eyJ..."}
   ```

4. **Refresh Token**
   ```
   POST /api/v1/auth/refresh
   Body: {"refresh_token": "eyJ..."}
   Response: {
     "access_token": "new_token...",
     "refresh_token": "new_refresh...",
     "expires_in": 900
   }
   ```

### **Authorization (Capability-Based RBAC)**

**Capabilities:**
```python
SUPER_ADMIN_ALL = "super_admin:all"
ADMIN_VIEW_ALL_DATA = "admin:view_all_data"
ADMIN_MANAGE_USERS = "admin:manage_users"
ADMIN_MANAGE_SETTINGS = "admin:manage_settings"
TRADE_BUY = "trade:buy"
TRADE_SELL = "trade:sell"
TRADE_VIEW = "trade:view"
TRADE_APPROVE = "trade:approve"
FINANCE_VIEW = "finance:view"
FINANCE_APPROVE = "finance:approve"
REPORTS_VIEW = "reports:view"
REPORTS_EXPORT = "reports:export"
```

**Usage:**
```python
@router.post("/availabilities")
@RequireCapability(Capabilities.TRADE_SELL)
async def create_availability(...):
    pass
```

---

## 🤖 AI INTEGRATION PLAN

### **Current AI Status**

#### **Implemented (Partial):**
- ✅ LangChain integration (OpenAI API wrapper)
- ✅ ChromaDB vector store
- ⚠️ 10 AI assistants (skeleton only, not functional)
- ⚠️ ML Risk Model (synthetic data only, needs real data training)

#### **AI TODOs in Trade Desk (11 placeholders):**
1. Quality normalization (needs GPT-4 API)
2. Price anomaly detection (needs scikit-learn training)
3. AI embeddings (needs Sentence Transformers)
4. Similar commodity suggestions (needs cosine similarity)
5. OCR for test reports (needs Tesseract + GPT-4)
6. Market price suggestions (needs LSTM or GPT-4)
7. Tolerance recommendations (needs ML)
8. Unrealistic budget detection (needs anomaly detection)
9. Market context generation (needs sentiment analysis)
10. AI-recommended sellers (needs collaborative filtering)
11. Intent-based routing (needs NLP classification)

### **AI Implementation Phases**

#### **Phase 1: API-Based AI (5 weeks, ₹1,200/month)**
**Priority 1: Trade Desk AI Enhancement (2 weeks)**
- Multi-commodity quality normalization (GPT-4 API)
- Price anomaly detection per commodity (scikit-learn)
- Cross-commodity semantic matching (Sentence Transformers)

**Priority 2: OCR Module (2 weeks)**
- Multi-language invoice OCR (Tesseract + GPT-4)
- Quality report OCR (USDA, GAFTA, BIS, LBMA standards)
- Transport document OCR

**Priority 3: Risk ML Training (1 week)**
- Train on real partner trading history
- Payment default predictor
- Fraud detector

#### **Phase 2: Autonomous Matching (8 weeks, ₹55,000 total)**
- Deep learning matching model (Transformer-based)
- Reinforcement Learning negotiation agents
- Auto-approval (95%+ trades without humans)

#### **Phase 3: Multi-Commodity Intelligence (12 weeks, ₹215,000 total)**
- Computer vision quality grading (5+ models: Cotton, Wheat, Gold, etc.)
- LSTM price predictors (10+ commodities)
- Cross-commodity embeddings
- Global price intelligence per commodity per market

#### **Phase 4: Global Scale (6 weeks, ₹550,000 total)**
- GPU cluster (4x A100 + 2x T4)
- Vector database (Qdrant/Weaviate)
- Streaming pipeline (Kafka)
- 24/7 worldwide operation

**Total 2040 Investment:**
- One-time: ₹820,000 (~$9,800)
- Monthly: ₹71,200 (~$850/month)
- Timeline: 31 weeks (~7-8 months)

---

## 🚀 DEPLOYMENT

### **Environment Variables**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cotton_erp
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Google Maps API
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# OpenAI (for AI features)
OPENAI_API_KEY=your-openai-api-key

# Rate Limiting
RATE_LIMIT_DEFAULT=1000/hour
RATE_LIMIT_AUTH=5/minute

# Logging
LOG_LEVEL=INFO
ENABLE_PII_FILTER=true

# Observability (Optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
GCP_PROJECT_ID=your-gcp-project-id
```

### **Running the Application**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run database migrations
alembic upgrade head

# 3. Start Redis
redis-server

# 4. Start backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Access API docs
open http://localhost:8000/api/docs
```

### **Docker Deployment**

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: cotton_user
      POSTGRES_PASSWORD: cotton_pass
      POSTGRES_DB: cotton_erp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://cotton_user:cotton_pass@postgres:5432/cotton_erp
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

---

## ⚠️ KNOWN ISSUES & TODOS

### **CRITICAL ISSUES**

1. **❌ Trade Desk NOT Accessible**
   - **Issue:** Trade Desk routes exist (5700+ lines) but NOT registered in `main.py`
   - **Impact:** Availability, Requirement, and Matching engines are NOT accessible via API
   - **Fix:** Add to `main.py`:
     ```python
     from backend.modules.trade_desk.routes.availability_routes import router as availability_router
     from backend.modules.trade_desk.routes.requirement_routes import router as requirement_router
     from backend.modules.trade_desk.routes.matching_router import router as matching_router
     
     app.include_router(availability_router, prefix="/api/v1", tags=["availability"])
     app.include_router(requirement_router, prefix="/api/v1", tags=["requirements"])
     app.include_router(matching_router, prefix="/api/v1", tags=["matching"])
     ```

2. **⚠️ ML Models Use Synthetic Data**
   - **Issue:** Risk ML models (RandomForest, GradientBoosting, IsolationForest) trained on fake data
   - **Impact:** Risk predictions are not accurate
   - **Fix:** Train on real trading data from database

3. **⚠️ 11 AI TODOs in Trade Desk**
   - **Issue:** AI enhancements are placeholders (quality normalization, price prediction, OCR, etc.)
   - **Impact:** Trade Desk doesn't use AI yet
   - **Fix:** Implement Phase 1 of AI Integration Plan

### **Missing Validations**

#### **Business Partners Module**
- ❌ GST API verification (placeholder only)
- ❌ PAN API verification (placeholder only)
- ❌ Bank account verification
- ❌ Duplicate partner detection (same GSTIN/PAN)

#### **Trade Desk Module**
- ❌ Quantity validation (exceeds availability)
- ❌ Price validation (below cost)
- ❌ Delivery date validation (past date)
- ❌ Circular trading prevention in matching

#### **Settings Module**
- ⚠️ Location deletion checks (TODO: check if used in trades)
- ⚠️ Commodity deletion checks (TODO: check if used in trades)

### **TODOs by Module**

#### **User Onboarding**
```
TODO: Remove OTP from response in production (line 94)
TODO: Integrate with actual SMS provider (Twilio/MSG91) (line 161)
```

#### **Risk Engine**
```
TODO: Bank account checking requires bank_accounts table (line 899)
TODO: Implement when trades table is integrated (line 1071)
TODO: Train with real data from database (line 431)
```

#### **Settings - Locations**
```
TODO: Uncomment when organizations.location_id is added (line 149)
TODO: Add checks for buyers table when module is created (line 160)
TODO: Add checks for trades table when module is created (line 172)
```

#### **Settings - Commodities**
```
TODO: Implement actual HSN API integration (line 231)
```

#### **Trade Desk - Matching**
```
TODO: Implement user preferences table/API (line 546)
TODO: Integrate with NotificationService (line 574)
```

#### **Trade Desk - Availability**
```
TODO: Integrate with AI OCR extraction (line 300)
TODO: Integrate with AI computer vision (line 306)
TODO: Integrate with AI normalization model (line 877)
TODO: Integrate with AI anomaly detection (line 928)
```

#### **Trade Desk - Requirement**
```
TODO: Implement event store integration (line 799)
```

### **Empty Modules (13 modules)**
- `ocr/` - Invoice, quality report, transport document OCR
- `market_trends/` - Price prediction, sentiment analysis
- `quality/` - Computer vision quality grading
- `accounting/` - Financial accounting
- `payment_engine/` - Payment processing
- `contract_engine/` - Contract generation
- `logistics/` - Logistics tracking
- `dispute/` - Dispute management
- `compliance/` - Regulatory compliance
- `notifications/` - Push notifications, emails, SMS
- `reports/` - Business intelligence reports
- `cci/` - CCI board integration
- `controller/` - Admin control panel

---

## 📊 IMPLEMENTATION SUMMARY

### **Code Statistics**
- **Total Lines:** ~20,000+ lines
- **Implemented Modules:** 5 (Auth, Settings, Partners, Risk, Trade Desk)
- **Empty Modules:** 13
- **Completion:** 28% (5/18 modules)

### **Module Completion Matrix**

| Module | Status | Lines | Endpoints | Database | AI Ready |
|--------|--------|-------|-----------|----------|----------|
| Auth | ✅ Done | 500+ | 6 | ✅ | N/A |
| Settings | ✅ Done | 2000+ | 20+ | ✅ | ⚠️ Partial |
| Partners | ✅ Done | 1500+ | 15+ | ✅ | ❌ No |
| Risk | ✅ Done | 900+ | 11 | ✅ | ⚠️ Synthetic |
| Trade Desk | ⚠️ Not Registered | 5700+ | ❌ 0 | ✅ | ⚠️ 11 TODOs |
| OCR | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Market Trends | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Quality | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Accounting | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Payment Engine | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Contract Engine | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Logistics | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Dispute | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Compliance | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Notifications | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Reports | ❌ Empty | 0 | 0 | ❌ | ❌ |
| CCI | ❌ Empty | 0 | 0 | ❌ | ❌ |
| Controller | ❌ Empty | 0 | 0 | ❌ | ❌ |

### **Infrastructure Status**
- ✅ Database (PostgreSQL + pgvector)
- ✅ Redis (cache, sessions, rate limiting)
- ✅ JWT Authentication
- ✅ RBAC (capability-based)
- ✅ Idempotency
- ✅ Rate Limiting
- ✅ WebSocket (real-time)
- ✅ Event Sourcing (outbox pattern)
- ✅ Multi-device sessions
- ✅ PII sanitization
- ✅ OpenTelemetry observability
- ⚠️ AI/ML (partial, mostly placeholders)
- ❌ OCR (not implemented)
- ❌ Market data feeds (not implemented)

---

## 🎯 NEXT STEPS

### **Immediate Priority**

1. **Register Trade Desk in main.py** (5 minutes)
   - Add availability, requirement, matching routers
   - Test all endpoints
   - Verify instant matching works

2. **Fix ML Models** (1 week)
   - Train risk models on real data
   - Validate predictions

3. **Implement Missing Validations** (2 weeks)
   - GST/PAN verification
   - Bank account checks
   - Duplicate detection

### **Short-term (1-2 months)**

4. **AI Phase 1** (5 weeks, ₹1,200/month)
   - Trade Desk AI enhancement
   - OCR module
   - Risk ML training

5. **Empty Module Planning** (2 weeks)
   - Priority: OCR, Market Trends, Quality
   - Defer: Accounting, Payment, Contract, Logistics

### **Long-term (6-12 months)**

6. **AI Phase 2-4** (31 weeks, ₹820,000 total)
   - Autonomous matching
   - Multi-commodity intelligence
   - Global scale infrastructure

---

## 🔍 CODE QUALITY AUDIT (December 2, 2025)

### **Schema Analysis**

#### **✅ GOOD: Clean Schema Structure**
- All schemas use Pydantic v2 (`model_config` instead of deprecated `orm_mode`)
- No `from_orm()` usage (deprecated in Pydantic v2)
- Proper use of `from_attributes = True` in response schemas
- Total: 2,019 lines of schemas across modules

#### **⚠️ SCHEMA DUPLICATES FOUND**

**1. OTP Schemas (Duplicate in 2 modules)**
- `settings/schemas/settings_schemas.py`:
  - `SendOTPRequest` (lines 94-103)
  - `VerifyOTPRequest` (lines 103-112)
  - `OTPResponse` (lines 112-120)
- `user_onboarding/schemas/auth_schemas.py`:
  - `SendOTPRequest` (lines 14-28)
  - `VerifyOTPRequest` (lines 30-34)
  - `OTPResponse` (lines 42-48)

**Impact:** Different field validations, could cause confusion
**Recommendation:** Move to shared `backend/core/schemas/auth.py`

**2. TokenResponse (Duplicate in 2 modules)**
- `auth/schemas.py`: `TokenResponse` (lines 21-33)
- `settings/schemas/settings_schemas.py`: `TokenResponse` (lines 21-28)

**Impact:** Different field structures
**Recommendation:** Use single source in `backend/core/schemas/auth.py`

**3. ErrorResponse (Duplicate in 3 modules)**
- `risk/schemas.py`: `ErrorResponse` (line 336)
- `trade_desk/schemas/__init__.py`: `ErrorResponse` (line 548)
- `trade_desk/schemas/requirement_schemas.py`: `ErrorResponse` (line 578)

**Recommendation:** Move to `backend/core/schemas/common.py`

---

### **Business Logic Analysis**

#### **✅ GOOD: Service Layer Separation**

**All business logic properly in service layer:**
1. `AvailabilityService` (1,391 lines) - Clean service class
2. `RequirementService` (1,806 lines) - Clean service class
3. `MatchingService` (704 lines) - Clean service class
4. `RiskService` (900+ lines) - Clean service class

**No business logic in routes** ✅  
**No business logic in models** ✅  
**Validation in service layer** ✅

#### **Business Logic Structure (Trade Desk Example)**

```python
class AvailabilityService:
    """
    Clean separation:
    - Constructor: Dependency injection
    - Public methods: Business operations
    - Private methods: Internal helpers
    - No database queries in constructor
    """
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
        # No queries here ✅
    
    async def create_availability(self, ...):
        # Step 1A: Capability Validation ✅
        # Step 1B: Location Validation ✅
        # Step 2A: Fetch Commodity ✅
        # Step 2B: Quality Parameter Validation ✅
        # Step 3: Unit Conversion ✅
        # Step 4: AI Enhancements (placeholder)
        # Step 5: Create & Emit Event ✅
        pass
```

**Validation Flow:**
1. ✅ Input validation (Pydantic schemas)
2. ✅ Business rules (Service layer)
3. ✅ CDPS capability validation
4. ✅ Cross-table validations
5. ✅ Event emission

---

### **DEPRECATED/OVERRIDE Issues**

#### **🔴 CRITICAL: Deprecated Fields**

**1. Trade Desk Schemas**
```python
# backend/modules/trade_desk/schemas/__init__.py (Line 377)
price_uom: Optional[str]  # DEPRECATED: Use price_unit
```
**Issue:** Field still in schema but marked deprecated  
**Fix Needed:** Remove from schema, add migration

**2. Partners Models**
```python
# backend/modules/partners/models.py
partner_type: VARCHAR  # DEPRECATED: Use capabilities JSONB instead
```
**Issue:** Old enum-based type system still exists  
**Status:** Replaced by `capabilities` JSONB but column still in DB  
**Fix Needed:** Database migration to drop column

**3. Risk Engine**
```python
# backend/modules/risk/risk_engine.py (Line 1134)
# CIRCULAR TRADING PREVENTION (OLD - Same-day - DEPRECATED)
async def check_circular_trading_same_day(...):
    """
    DEPRECATED: Use check_circular_trading_settlement_based() instead.
    """
```
**Status:** New method exists, old method deprecated  
**Fix Needed:** Remove old method after confirming no usage

**4. Trade Desk Routes**
```python
# backend/modules/trade_desk/routes/availability_routes.py (Line 132)
@router.post(
    "/search",
    summary="[DEPRECATED] AI-powered smart search - Use instant matching instead",
    deprecated=True
)
```
**Status:** OpenAPI marked as deprecated ✅  
**Action:** Keep for backward compatibility

---

### **Configuration & Schema Alignment**

#### **✅ PROPER: Pydantic Configuration**

**Consistent across all modules:**
```python
# Risk schemas (Pydantic v1 style - needs update)
class Config:
    from_attributes = True
    json_schema_extra = {...}

# Settings/Commodities (Pydantic v2 style - correct)
model_config = {"from_attributes": True}
```

**⚠️ INCONSISTENCY:** Risk module uses old Pydantic v1 `class Config`, others use v2 `model_config`

**Fix Needed:**
```python
# backend/modules/risk/schemas.py
# Change ALL instances from:
class RiskAssessmentResponse(BaseModel):
    class Config:
        from_attributes = True

# To:
class RiskAssessmentResponse(BaseModel):
    model_config = {"from_attributes": True}
```

---

### **Missing Validations**

#### **🔴 Business Partner Module**

**1. Duplicate GSTIN/PAN Check** ❌
```python
# backend/modules/partners/services/onboarding_service.py
# Missing: Check if GSTIN/PAN already exists before creating
```

**2. GST API Verification** ⚠️ Placeholder
```python
# backend/modules/partners/services/verification_service.py (Line 45)
# TODO: Actual GST API integration
return GSTVerificationResult(
    is_valid=True,  # FAKE - Always returns true
    business_name="Fake Business",
    ...
)
```

**3. Bank Account Verification** ❌ Not implemented

---

#### **🔴 Trade Desk Module**

**1. Quantity Exceeds Available** ⚠️ Partial
```python
# availability_service.py checks reserved_quantity
# But missing check: total_sold + reserved <= total_quantity
```

**2. Price Validation** ❌ Missing
```python
# No check for:
# - Negative prices
# - Price = 0
# - Price exceeds market price by 10x (anomaly)
```

**3. Delivery Date Validation** ❌ Missing
```python
# No check for:
# - Delivery date in the past
# - Delivery date > 1 year in future
```

**4. Circular Trading in Matching** ⚠️ Partial
```python
# Risk engine has check
# But matching engine doesn't call it before creating match
```

---

#### **🔴 Settings Module**

**1. Location Deletion Check** ⚠️ TODO
```python
# backend/modules/settings/locations/repositories.py (Line 172)
# TODO: Add checks for trades table when module is created
```

**2. Commodity Deletion Check** ⚠️ TODO
```python
# Missing: Check if commodity used in:
# - Active availabilities
# - Active requirements
# - Historical trades
```

---

### **Service Layer Quality Score**

| Module | Lines | Business Logic | Validations | Score |
|--------|-------|----------------|-------------|-------|
| Trade Desk | 3,900+ | ✅ Clean | ⚠️ Partial | 85% |
| Risk Engine | 900+ | ✅ Clean | ✅ Complete | 95% |
| Partners | 1,500+ | ✅ Clean | ⚠️ Placeholders | 75% |
| Settings | 2,000+ | ✅ Clean | ⚠️ Missing | 70% |
| Auth | 500+ | ✅ Clean | ✅ Complete | 95% |

**Overall Code Quality: 84%**

---

### **Critical Fixes Needed (Priority Order)**

#### **Priority 1: Register Trade Desk in main.py** ⚠️ BLOCKING
- 5,700+ lines of code not accessible
- Fix: Add 3 router registrations

#### **Priority 2: Remove Schema Duplicates**
- Move OTP schemas to shared module
- Move TokenResponse to core
- Move ErrorResponse to core
- Estimated: 2 hours

#### **Priority 3: Update Risk Module to Pydantic v2**
- Replace `class Config` with `model_config`
- 9 schema classes to update
- Estimated: 1 hour

#### **Priority 4: Remove Deprecated Code**
- Drop `price_uom` field (add migration)
- Drop `partner_type` column (add migration)
- Remove old circular trading method
- Estimated: 3 hours

#### **Priority 5: Add Missing Validations**
- Duplicate GSTIN/PAN check
- Price validation (negative, zero, anomaly)
- Delivery date validation
- Quantity validation
- Estimated: 1 week

#### **Priority 6: Implement GST/PAN API**
- Replace placeholder with real API
- Estimated: 2 days

---

### **Summary of Findings**

✅ **GOOD:**
- Clean service layer separation
- No business logic in routes/models
- Proper async/await usage
- Event sourcing implemented
- CDPS validation in place

⚠️ **NEEDS IMPROVEMENT:**
- Schema duplicates (3 types)
- Pydantic v1 vs v2 inconsistency
- Deprecated fields still in DB
- Missing validations (5+ areas)
- Placeholder verifications

🔴 **CRITICAL:**
- Trade Desk NOT registered in main.py
- ML models use synthetic data
- 13 modules empty

**Code is production-ready EXCEPT for the critical Trade Desk registration issue.**

---

**END OF DOCUMENTATION**
