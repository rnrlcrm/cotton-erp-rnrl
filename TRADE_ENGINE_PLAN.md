# TRADE ENGINE - Phase 5 COMPLETE ARCHITECTURE

## 🎯 STRATEGIC VISION

The Trade Engine is **NOT a standalone module** - it's the **ORCHESTRATOR** that:
1. **Creates binding contracts** from negotiations
2. **Coordinates separate modules**: Quality, Logistics, Payments, Documents
3. **Tracks trade lifecycle** from contract → delivery → completion
4. **Integrates AI** for risk assessment, fraud detection, pricing validation
5. **Links everything** via `trade_id` (the central reference)

---

## 🏗️ ARCHITECTURE OVERVIEW

### Central Entity: TRADE (Smart Contract Core)

```
                    ┌─────────────────────────┐
                    │   TRADE (Smart Core)    │
                    │   - trade_id (UUID)     │
                    │   - negotiation_id      │
                    │   - status              │
                    │   - contract_hash       │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌────────────────┐     ┌────────────────┐
│  QUALITY      │      │   LOGISTICS    │     │   PAYMENTS     │
│  MODULE       │      │   MODULE       │     │   MODULE       │
│  (separate)   │      │   (separate)   │     │   (separate)   │
└───────────────┘      └────────────────┘     └────────────────┘
   trade_id ───────────────► trade_id ◄──────────── trade_id
```

### Why This Separation?

**Trade Engine = THIN ORCHESTRATOR**
- Creates trade record (contract)
- Tracks status (PENDING → ACTIVE → COMPLETED)
- Coordinates other modules
- **Does NOT** implement quality/logistics/payments logic

**Separate Modules = SPECIALIZED SERVICES**
- Quality Module: Inspection, testing, certification
- Logistics Module: Shipment, tracking, delivery
- Payments Module: Transactions, refunds, escrow
- Each links via `trade_id`

---

## 📋 REVISED IMPLEMENTATION PLAN

### PHASE 5: TRADE ENGINE (Smart Contract Core)

**Scope**: Create the "contract" and orchestration layer ONLY
**What we BUILD**: Trade entity, status tracking, AI validation
**What we DON'T build**: Quality/Logistics/Payments (separate modules later)

---

## 🎯 Phase 5 Objectives (REVISED)

1. **Smart Contract Creation** (AI-validated terms)
2. **Trade Entity** (central reference point)
3. **Status Orchestration** (lifecycle management)
4. **AI Integration** (fraud detection, risk scoring, price validation)
5. **Document Generation** (PDF contracts with digital signatures)
6. **Integration Hooks** (for future Quality/Logistics/Payments modules)
7. **Event Sourcing** (complete audit trail)

---

## 📋 Implementation Phases

### PHASE 5A: Core Trade Model & Service (Foundation)
**Goal**: Create trade entity and basic lifecycle management

#### Files to Create:
1. **Model**: `backend/modules/trade_desk/models/trade.py`
   - Trade entity (links to negotiation)
   - Contract terms (frozen at agreement)
   - Payment milestones
   - Delivery schedule
   - Status tracking (PENDING → ACTIVE → DELIVERED → COMPLETED → DISPUTED → CANCELLED)

2. **Service**: `backend/modules/trade_desk/services/trade_service.py`
   - Create trade from negotiation
   - Update trade status
   - Payment tracking
   - Delivery tracking
   - Query methods (user trades, admin view)

3. **Schemas**: `backend/modules/trade_desk/schemas/trade_schemas.py`
   - CreateTradeRequest
   - TradeResponse
   - PaymentUpdate
   - DeliveryUpdate
   - TradeListResponse

4. **Routes**: `backend/modules/trade_desk/routes/trade_routes.py`
   - Create trade from negotiation
   - Get trade details
   - List user trades
   - Update payment status
   - Update delivery status
   - Admin monitoring

5. **Migration**: `backend/db/migrations/versions/xxx_add_trades_table.py`
   - trades table
   - trade_payments table
   - trade_deliveries table
   - Foreign keys to negotiations, business_partners

#### Database Schema:

**trades** table:
```sql
- id (UUID, PK)
- negotiation_id (UUID, FK → negotiations, UNIQUE)
- requirement_id (UUID, FK → requirements)
- availability_id (UUID, FK → availabilities)
- buyer_partner_id (UUID, FK → business_partners)
- seller_partner_id (UUID, FK → business_partners)

-- Contract Terms (frozen from negotiation)
- final_price_per_unit (NUMERIC)
- quantity (NUMERIC)
- total_amount (NUMERIC)
- delivery_terms (JSONB)
- payment_terms (JSONB)
- quality_conditions (JSONB)

-- Status & Tracking
- status (VARCHAR: PENDING, ACTIVE, DELIVERED, COMPLETED, DISPUTED, CANCELLED)
- contract_signed_at (TIMESTAMP)
- expected_delivery_date (DATE)
- actual_delivery_date (DATE)
- completed_at (TIMESTAMP)
- cancelled_at (TIMESTAMP)

-- Documents
- contract_url (VARCHAR - S3/storage link)
- invoice_url (VARCHAR)
- delivery_note_url (VARCHAR)
- quality_certificate_url (VARCHAR)

-- Timestamps
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

**trade_payments** table:
```sql
- id (UUID, PK)
- trade_id (UUID, FK → trades)
- payment_type (VARCHAR: ADVANCE, MILESTONE, FINAL)
- amount (NUMERIC)
- due_date (DATE)
- paid_date (DATE)
- payment_method (VARCHAR: BANK_TRANSFER, LETTER_OF_CREDIT, etc.)
- payment_reference (VARCHAR)
- status (VARCHAR: PENDING, PAID, OVERDUE, REFUNDED)
- created_at (TIMESTAMP)
```

**trade_deliveries** table:
```sql
- id (UUID, PK)
- trade_id (UUID, FK → trades)
- shipment_date (DATE)
- expected_arrival_date (DATE)
- actual_arrival_date (DATE)
- location (VARCHAR)
- transporter (VARCHAR)
- tracking_number (VARCHAR)
- status (VARCHAR: PREPARING, SHIPPED, IN_TRANSIT, DELIVERED, ACCEPTED, REJECTED)
- inspection_date (DATE)
- inspection_result (VARCHAR: PENDING, PASSED, FAILED)
- quality_notes (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

---

### PHASE 5B: Document Generation
**Goal**: Auto-generate legal contracts and trade documents

#### Files to Create:
1. **Service**: `backend/modules/trade_desk/services/document_service.py`
   - Generate PDF contract
   - Generate invoice
   - Generate delivery note
   - Generate quality certificate
   - Store in S3/file storage
   - Email to parties

2. **Templates**: `backend/modules/trade_desk/templates/`
   - contract_template.html (Jinja2)
   - invoice_template.html
   - delivery_note_template.html
   - quality_certificate_template.html

#### Features:
- PDF generation from HTML (WeasyPrint/ReportLab)
- Digital signatures (optional)
- Multi-language support (English, Hindi, regional)
- Company letterhead
- Legal terms & conditions
- QR codes for verification

---

### PHASE 5C: Payment Tracking & Integration
**Goal**: Track payment milestones and integrate with payment gateways

#### Files to Create:
1. **Service**: `backend/modules/trade_desk/services/payment_service.py`
   - Create payment milestones
   - Record payment
   - Verify payment
   - Send payment reminders
   - Handle refunds

2. **Integration**: Payment gateway hooks
   - Razorpay/Stripe webhooks
   - Bank transfer verification
   - Letter of Credit tracking

#### Features:
- Multi-stage payments (advance, milestone, final)
- Auto-reminders for overdue payments
- Payment verification
- Refund management
- Currency conversion (if international)

---

### PHASE 5D: Delivery & Quality Management
**Goal**: Track logistics and quality inspection

#### Files to Create:
1. **Service**: `backend/modules/trade_desk/services/delivery_service.py`
   - Schedule delivery
   - Track shipment
   - Record inspection
   - Handle acceptance/rejection

2. **Integration**: Logistics APIs
   - Transporter tracking
   - GPS location updates
   - Delivery confirmation

#### Features:
- Real-time shipment tracking
- Quality inspection workflow
- Photo upload for delivery
- Acceptance/rejection with reasons
- Dispute escalation

---

### PHASE 5E: Dispute Resolution & Completion
**Goal**: Handle issues and finalize trades

#### Files to Create:
1. **Model**: `backend/modules/trade_desk/models/trade_dispute.py`
   - Dispute entity
   - Evidence attachments
   - Resolution tracking

2. **Service**: `backend/modules/trade_desk/services/dispute_service.py`
   - Raise dispute
   - Add evidence
   - Mediation workflow
   - Resolution & refund

3. **Completion**:
   - Buyer/seller ratings
   - Feedback collection
   - Update match_outcomes table
   - ML model training data

---

## 🔄 Trade Lifecycle Flow

```
1. NEGOTIATION ACCEPTED
   ↓
2. CREATE TRADE (status: PENDING)
   ↓
3. GENERATE CONTRACT
   ↓
4. PARTIES SIGN CONTRACT (status: ACTIVE)
   ↓
5. BUYER PAYS ADVANCE
   ↓
6. SELLER PREPARES GOODS
   ↓
7. SHIPMENT DISPATCHED (status: IN_TRANSIT)
   ↓
8. BUYER RECEIVES GOODS
   ↓
9. QUALITY INSPECTION
   ↓
10a. ACCEPTED → Final Payment → COMPLETED
10b. REJECTED → Dispute → Resolution
```

---

## 📊 API Endpoints to Create

### Regular Endpoints (Buyers/Sellers):
```
POST   /api/v1/trade-desk/trades                    # Create from negotiation
GET    /api/v1/trade-desk/trades                    # List user's trades
GET    /api/v1/trade-desk/trades/{id}               # Get trade details
PUT    /api/v1/trade-desk/trades/{id}/sign          # Sign contract
POST   /api/v1/trade-desk/trades/{id}/payments      # Record payment
PUT    /api/v1/trade-desk/trades/{id}/delivery      # Update delivery
POST   /api/v1/trade-desk/trades/{id}/inspect       # Quality inspection
POST   /api/v1/trade-desk/trades/{id}/accept        # Accept delivery
POST   /api/v1/trade-desk/trades/{id}/reject        # Reject delivery
POST   /api/v1/trade-desk/trades/{id}/dispute       # Raise dispute
POST   /api/v1/trade-desk/trades/{id}/complete      # Mark complete & rate
GET    /api/v1/trade-desk/trades/{id}/documents     # Download docs
```

### Admin Endpoints (Back Office):
```
GET    /api/v1/trade-desk/admin/trades              # Monitor all trades
GET    /api/v1/trade-desk/admin/trades/{id}         # View any trade
GET    /api/v1/trade-desk/admin/disputes            # All disputes
PUT    /api/v1/trade-desk/admin/disputes/{id}       # Mediate dispute
```

---

## 🔐 Authorization & Data Isolation

**External Users (Buyers/Sellers)**:
- ✅ Can ONLY see/modify their own trades
- ✅ Buyer: payments, acceptance, ratings
- ✅ Seller: delivery updates, shipment
- ✅ Both: dispute raising, document access

**Internal Users (Back Office)**:
- ✅ View ALL trades (monitoring)
- ✅ Mediate disputes
- ✅ READ-ONLY on trade data
- ✅ Can update dispute resolutions

---

## 🧪 Testing Requirements

1. **Migration Test**: Verify trades tables created
2. **Trade Creation**: From accepted negotiation
3. **Payment Flow**: Advance → Milestone → Final
4. **Delivery Tracking**: Status updates
5. **Quality Inspection**: Pass/Fail scenarios
6. **Dispute Resolution**: Full workflow
7. **Data Isolation**: User-level access control
8. **Admin Monitoring**: Back office access

---

## 📦 Dependencies to Add

```toml
# Document generation
weasyprint = "^60.0"  # PDF from HTML
pillow = "^10.0"      # Image processing
qrcode = "^7.4"       # QR code generation

# Optional: Payment integrations
razorpay = "^1.3"     # India payments
stripe = "^7.0"       # International payments
```

---

## 🎯 Success Metrics

- ✅ Trade created from every accepted negotiation
- ✅ Contract PDF generated automatically
- ✅ Payment milestones tracked
- ✅ Delivery status real-time
- ✅ Quality inspection workflow
- ✅ Dispute resolution <48 hours
- ✅ Trade completion rate >90%
- ✅ User satisfaction ratings collected

---

## ⏱️ Estimated Timeline

| Phase | Tasks | Time | Lines of Code |
|-------|-------|------|---------------|
| 5A: Core Trade | Models, Service, Routes, Migration | 3-4 hours | ~1,200 |
| 5B: Documents | PDF generation, templates | 2-3 hours | ~600 |
| 5C: Payments | Payment tracking, integrations | 2-3 hours | ~500 |
| 5D: Delivery | Logistics, quality inspection | 2-3 hours | ~500 |
| 5E: Disputes | Dispute management, completion | 2-3 hours | ~400 |
| **TOTAL** | **Full Trade Engine** | **11-16 hours** | **~3,200** |

---

## 🚀 Phase 5A: Let's Start!

### First Step: Create Trade Model

**Ready to start with Phase 5A?**

I'll create:
1. ✅ Trade model (with payments & deliveries)
2. ✅ Trade service (full business logic)
3. ✅ Trade schemas (request/response)
4. ✅ Trade routes (regular + admin)
5. ✅ Migration (3 tables)
6. ✅ Tests

**Shall we begin?**
