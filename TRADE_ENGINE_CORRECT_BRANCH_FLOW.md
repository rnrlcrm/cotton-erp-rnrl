# TRADE ENGINE - CORRECT FLOW (Multi-Branch Address Selection)

## 🎯 CORRECT UNDERSTANDING

### What You're Saying:

```
❌ WRONG (What I explained):
   User creates requirement → Branch auto-tagged
   Trade auto-selects branch address
   
✅ CORRECT (What you want):
   User trades using MAIN partner ID (no branch tagging during trade)
   When contract generated → User SELECTS which branch address
   AI suggests best branch (based on state matching)
   User can change address later (with amendment)
```

---

## 🔄 CORRECT FLOW

### Phase 1: Trading (Business as Usual)

```
User: Amit (works for Ramesh Textiles)
Partner ID: PART-001 (Ramesh Textiles - main ID)

Action: Create Requirement
Data saved:
{
    "partner_id": "PART-001",  ← Single partner ID only
    "commodity": "cotton",
    "quantity": 50,
    "delivery_city": "Ahmedabad"
    
    NO branch_id!  ← Trade happens at partner level
}

Action: Negotiation
{
    "buyer_partner_id": "PART-001",  ← Main ID
    "seller_partner_id": "SELL-001",  ← Main ID
    
    NO branch IDs during negotiation!
}

Result: Negotiation ACCEPTED ✅
```

### Phase 2: Contract Generation (Branch Selection Happens Here)

```
User clicks: "Create Contract"

Screen shown:
┌────────────────────────────────────────────────────┐
│  Contract Generation - TR-2025-00001              │
├────────────────────────────────────────────────────┤
│                                                    │
│  Trade Details:                                   │
│  Buyer: Ramesh Textiles (PART-001)               │
│  Seller: Suresh Cotton Co (SELL-001)             │
│  Commodity: Cotton, 50 quintals @ ₹7,150          │
│  Delivery State: Gujarat (Ahmedabad)              │
│                                                    │
│  ═══════════════════════════════════════════════  │
│                                                    │
│  📍 SELECT DELIVERY ADDRESS (Ship-to):            │
│                                                    │
│  🤖 AI Recommendation:                            │
│  ✨ Ahmedabad Branch (AHD-01)                     │
│     Reason: Trade delivery is in Gujarat          │
│     Your branch GSTIN: 24XXXXX (Gujarat)          │
│     ✅ State matches - No inter-state GST          │
│                                                    │
│  Your Available Branches:                         │
│                                                    │
│  ○ Mumbai Head Office (MUM-HO)                    │
│     123 Industrial Estate, Mumbai - 400001        │
│     GSTIN: 27XXXXX (Maharashtra)                  │
│     ⚠️  Different state - Inter-state GST apply    │
│                                                    │
│  ● Ahmedabad Factory (AHD-01) 👈 AI Recommended   │
│     Plot 45, GIDC, Ahmedabad - 380001            │
│     GSTIN: 24XXXXX (Gujarat)                      │
│     ✅ Same state as delivery                      │
│     Warehouse: 3000 qtls available               │
│                                                    │
│  ○ Surat Warehouse (SUR-02)                       │
│     Sector 12, Pandesara, Surat - 395010         │
│     GSTIN: 24XXXXX (Gujarat)                      │
│     ✅ Same state as delivery                      │
│     Warehouse: 8000 qtls available               │
│                                                    │
│  ○ Enter different address manually              │
│                                                    │
│  ─────────────────────────────────────────────    │
│                                                    │
│  📄 SELECT BILLING ADDRESS (Bill-to):             │
│                                                    │
│  ● Same as delivery address (AHD-01)              │
│  ○ Mumbai Head Office (Registered office)         │
│  ○ Different address                              │
│                                                    │
│  ─────────────────────────────────────────────    │
│                                                    │
│  GST Implications:                                │
│  ✅ Intra-state supply (Gujarat to Gujarat)       │
│     CGST + SGST applicable                        │
│                                                    │
│  [Generate Contract]                              │
└────────────────────────────────────────────────────┘
```

**Key Points**:
1. ✅ User trades with MAIN partner ID only
2. ✅ Branch selection happens ONLY at contract generation
3. ✅ AI suggests best branch (state matching)
4. ✅ User can override AI suggestion
5. ✅ Separate selection for Ship-to and Bill-to

---

## 🤖 AI SUGGESTION LOGIC

```python
class BranchSuggestionService:
    """
    AI suggests best branch for delivery address
    """
    
    def suggest_delivery_branch(
        self,
        partner_id: UUID,
        delivery_city: str,
        delivery_state: str,
        commodity: str,
        quantity: Decimal
    ) -> BranchSuggestion:
        """
        Suggest best branch based on multiple factors
        """
        
        # Get all active branches
        branches = get_partner_branches(
            partner_id=partner_id,
            is_active=True,
            can_receive_shipments=True
        )
        
        suggestions = []
        
        for branch in branches:
            score = 0
            reasons = []
            warnings = []
            
            # Factor 1: State Matching (Highest Priority - 40 points)
            if branch.state == delivery_state:
                score += 40
                reasons.append(f"✅ Same state ({delivery_state}) - Intra-state GST")
            else:
                warnings.append(f"⚠️ Different state - Inter-state GST applicable")
            
            # Factor 2: City Matching (30 points)
            if branch.city == delivery_city:
                score += 30
                reasons.append(f"✅ Same city ({delivery_city}) - Minimal transport")
            else:
                # Calculate distance
                distance_km = calculate_distance(
                    branch.latitude, branch.longitude,
                    delivery_city_lat, delivery_city_lon
                )
                if distance_km < 50:
                    score += 20
                    reasons.append(f"✅ Nearby ({distance_km} km)")
                elif distance_km < 200:
                    score += 10
                    reasons.append(f"⚠️ Moderate distance ({distance_km} km)")
            
            # Factor 3: Warehouse Capacity (20 points)
            if branch.has_warehouse:
                available_capacity = (
                    branch.warehouse_capacity_qtls - 
                    get_pending_deliveries(branch.id)
                )
                
                if available_capacity >= quantity:
                    capacity_ratio = available_capacity / quantity
                    if capacity_ratio > 2:
                        score += 20
                        reasons.append(f"✅ Ample capacity ({available_capacity} qtls)")
                    else:
                        score += 10
                        reasons.append(f"✅ Sufficient capacity ({available_capacity} qtls)")
                else:
                    warnings.append(f"⚠️ Low capacity (only {available_capacity} qtls)")
            
            # Factor 4: Commodity Handling (10 points)
            if commodity in branch.commodities_handled:
                score += 10
                reasons.append(f"✅ Handles {commodity}")
            
            # Factor 5: Facility Type (Bonus points)
            if branch.facility_type == "WAREHOUSE":
                score += 5
                reasons.append("✅ Dedicated warehouse")
            elif branch.facility_type == "FACTORY":
                score += 3
                reasons.append("✅ Factory with storage")
            
            suggestions.append({
                "branch": branch,
                "score": score,
                "reasons": reasons,
                "warnings": warnings
            })
        
        # Sort by score (highest first)
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "recommended": suggestions[0] if suggestions else None,
            "alternatives": suggestions[1:],
            "all_suggestions": suggestions
        }
```

---

## 📝 CONTRACT GENERATION FLOW

```python
@router.post("/trades/create-from-negotiation")
async def create_trade_from_negotiation(
    request: CreateTradeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Step 1: Validate negotiation
    Step 2: Let user select branch addresses
    Step 3: Generate contract with selected addresses
    """
    
    negotiation = get_negotiation(request.negotiation_id)
    
    if negotiation.status != "ACCEPTED":
        raise ValueError("Negotiation not accepted yet")
    
    # Get delivery location from negotiation
    delivery_city = negotiation.delivery_city
    delivery_state = negotiation.delivery_state
    
    # AI suggests best branches
    buyer_suggestion = branch_suggestion_service.suggest_delivery_branch(
        partner_id=negotiation.buyer_partner_id,
        delivery_city=delivery_city,
        delivery_state=delivery_state,
        commodity=negotiation.commodity,
        quantity=negotiation.quantity
    )
    
    seller_suggestion = branch_suggestion_service.suggest_dispatch_branch(
        partner_id=negotiation.seller_partner_id,
        delivery_city=delivery_city,
        delivery_state=delivery_state,
        commodity=negotiation.commodity,
        quantity=negotiation.quantity
    )
    
    # Return suggestions to frontend
    return {
        "negotiation": negotiation,
        "buyer_branch_suggestions": buyer_suggestion,
        "seller_branch_suggestions": seller_suggestion,
        "message": "Please select delivery and billing addresses"
    }


@router.post("/trades/confirm-with-addresses")
async def confirm_trade_with_addresses(
    request: ConfirmTradeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    User has selected branches, now create trade
    """
    
    # Validate selected branches
    ship_to_branch = get_branch(request.ship_to_branch_id)
    bill_to_branch = get_branch(request.bill_to_branch_id)
    ship_from_branch = get_branch(request.ship_from_branch_id)
    
    # Validate branch belongs to partner
    if ship_to_branch.partner_id != negotiation.buyer_partner_id:
        raise ValueError("Ship-to branch doesn't belong to buyer")
    
    # Create trade with selected addresses
    trade = Trade(
        negotiation_id=request.negotiation_id,
        buyer_partner_id=negotiation.buyer_partner_id,
        seller_partner_id=negotiation.seller_partner_id,
        
        # Store selected branches
        ship_to_branch_id=request.ship_to_branch_id,
        bill_to_branch_id=request.bill_to_branch_id,
        ship_from_branch_id=request.ship_from_branch_id,
        
        # Full address details (from selected branches)
        ship_to_address={
            "branch_id": ship_to_branch.id,
            "branch_name": ship_to_branch.branch_name,
            "branch_code": ship_to_branch.branch_code,
            "address_line1": ship_to_branch.address_line1,
            "address_line2": ship_to_branch.address_line2,
            "city": ship_to_branch.city,
            "state": ship_to_branch.state,
            "pincode": ship_to_branch.pincode,
            "gstin": ship_to_branch.branch_gstin,
            "contact_person": ship_to_branch.branch_manager_name,
            "contact_mobile": ship_to_branch.branch_contact_mobile
        },
        
        bill_to_address={...},
        ship_from_address={...},
        
        # GST calculation
        gst_type=calculate_gst_type(ship_from_branch.state, ship_to_branch.state),
        
        status="DRAFT",
        created_at=datetime.utcnow()
    )
    
    db.add(trade)
    db.commit()
    
    # Generate contract PDF with selected addresses
    contract_pdf = generate_contract_pdf(trade)
    
    return {
        "trade": trade,
        "contract_pdf_url": contract_pdf.url,
        "message": "Contract generated successfully"
    }
```

---

## 🔄 ADDRESS AMENDMENT FLOW (After Contract Generated)

### Scenario: User wants to change address after contract created

```
Current Contract:
  Ship-to: Ahmedabad Branch
  Status: DRAFT (not yet signed)

User: "Wait, I want to ship to Surat instead!"
```

### Amendment Process:

```python
@router.post("/trades/{trade_id}/request-address-change")
async def request_address_change(
    trade_id: UUID,
    request: AddressChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    User requests to change delivery address
    """
    
    trade = get_trade(trade_id)
    
    # Check if amendment allowed
    if trade.status not in ["DRAFT", "PENDING_SIGNATURE"]:
        raise ValueError("Cannot change address after contract is active")
    
    # Get new branch
    new_branch = get_branch(request.new_ship_to_branch_id)
    
    # Validate
    if new_branch.partner_id != trade.buyer_partner_id:
        raise ValueError("Branch doesn't belong to buyer")
    
    if not new_branch.can_receive_shipments:
        raise ValueError("This branch cannot receive shipments")
    
    # Create amendment record
    amendment = TradeAmendment(
        trade_id=trade_id,
        amendment_type="ADDRESS_CHANGE",
        old_value={
            "ship_to_branch_id": trade.ship_to_branch_id,
            "ship_to_address": trade.ship_to_address
        },
        new_value={
            "ship_to_branch_id": request.new_ship_to_branch_id,
            "ship_to_address": {
                "branch_name": new_branch.branch_name,
                "address_line1": new_branch.address_line1,
                ...
            }
        },
        change_reason=request.reason,
        requested_by=current_user.id,
        requested_at=datetime.utcnow(),
        
        # Approval needed if contract already shared
        requires_counterparty_approval=(trade.status == "PENDING_SIGNATURE"),
        status="PENDING" if trade.status == "PENDING_SIGNATURE" else "AUTO_APPROVED"
    )
    
    db.add(amendment)
    
    # If contract not yet shared, auto-approve
    if trade.status == "DRAFT":
        # Update trade immediately
        trade.ship_to_branch_id = request.new_ship_to_branch_id
        trade.ship_to_address = amendment.new_value["ship_to_address"]
        
        # Regenerate contract PDF
        regenerate_contract_pdf(trade)
        
        amendment.status = "AUTO_APPROVED"
        amendment.approved_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Address updated successfully",
            "trade": trade
        }
    
    else:
        # Contract already shared, need counterparty approval
        notify_counterparty_about_amendment(trade, amendment)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Amendment request sent to seller for approval",
            "amendment": amendment
        }


@router.post("/trades/amendments/{amendment_id}/approve")
async def approve_amendment(
    amendment_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Counterparty approves address change
    """
    
    amendment = get_amendment(amendment_id)
    trade = get_trade(amendment.trade_id)
    
    # Validate user is counterparty
    if current_user.partner_id not in [trade.buyer_partner_id, trade.seller_partner_id]:
        raise PermissionError("Not authorized")
    
    # Approve amendment
    amendment.status = "APPROVED"
    amendment.approved_by = current_user.id
    amendment.approved_at = datetime.utcnow()
    
    # Apply changes to trade
    if amendment.amendment_type == "ADDRESS_CHANGE":
        trade.ship_to_branch_id = amendment.new_value["ship_to_branch_id"]
        trade.ship_to_address = amendment.new_value["ship_to_address"]
    
    # Regenerate contract with updated address
    regenerate_contract_pdf(trade)
    
    # Log event
    log_trade_event(
        trade_id=trade.id,
        event_type="ADDRESS_AMENDED",
        event_data={
            "amendment_id": amendment_id,
            "old_address": amendment.old_value,
            "new_address": amendment.new_value,
            "approved_by": current_user.id
        }
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Amendment approved. Contract regenerated.",
        "trade": trade
    }
```

---

## 📊 DATABASE SCHEMA

### Trades Table (Corrected)

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_number VARCHAR(50) UNIQUE NOT NULL,
    negotiation_id UUID REFERENCES negotiations(id),
    
    -- Parties (MAIN partner IDs only)
    buyer_partner_id UUID NOT NULL REFERENCES business_partners(id),
    seller_partner_id UUID NOT NULL REFERENCES business_partners(id),
    
    -- Selected branches (chosen at contract generation)
    ship_to_branch_id UUID REFERENCES partner_branches(id),  -- Buyer's receiving branch
    bill_to_branch_id UUID REFERENCES partner_branches(id),  -- Buyer's billing branch
    ship_from_branch_id UUID REFERENCES partner_branches(id),  -- Seller's dispatch branch
    
    -- Full address snapshots (frozen at time of contract)
    ship_to_address JSON NOT NULL,
    bill_to_address JSON NOT NULL,
    ship_from_address JSON NOT NULL,
    
    -- GST details
    gst_type VARCHAR(20),  -- INTRA_STATE, INTER_STATE
    buyer_gstin VARCHAR(15),  -- From selected branch
    seller_gstin VARCHAR(15),  -- From selected branch
    
    -- Commodity & pricing
    commodity_id UUID REFERENCES commodities(id),
    quantity DECIMAL(15, 3),
    price_per_unit DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    
    -- Contract
    contract_pdf_url TEXT,
    contract_hash VARCHAR(64),
    contract_version INTEGER DEFAULT 1,  -- Increments on amendment
    
    -- Status
    status VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Trade Amendments Table (NEW!)

```sql
CREATE TABLE trade_amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id),
    
    -- Amendment details
    amendment_type VARCHAR(50) NOT NULL,  -- ADDRESS_CHANGE, QUANTITY_CHANGE, PRICE_CHANGE
    old_value JSON NOT NULL,
    new_value JSON NOT NULL,
    change_reason TEXT,
    
    -- Request tracking
    requested_by UUID REFERENCES users(id),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Approval workflow
    requires_counterparty_approval BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    rejected_by UUID REFERENCES users(id),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Status
    status VARCHAR(20),  -- PENDING, APPROVED, REJECTED, AUTO_APPROVED
    
    -- Contract regeneration
    new_contract_pdf_url TEXT,
    old_contract_pdf_url TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookup
CREATE INDEX idx_amendments_trade ON trade_amendments(trade_id);
CREATE INDEX idx_amendments_status ON trade_amendments(status);
```

---

## 🎨 UPDATED UI FLOW

### Step 1: Negotiation Accepted

```
✅ Negotiation #NEG-2025-00123 Accepted

Next step: [Create Contract]  👈 User clicks
```

### Step 2: Branch Selection Screen (AI Suggestions)

```
┌──────────────────────────────────────────────────┐
│  🤖 AI-Powered Address Selection                │
├──────────────────────────────────────────────────┤
│                                                  │
│  Trade: 50 quintals cotton to Ahmedabad         │
│                                                  │
│  📍 DELIVERY ADDRESS (Ship-to):                 │
│                                                  │
│  AI Recommends: Ahmedabad Factory (AHD-01)      │
│  ✅ Same state (Gujarat) - Save GST             │
│  ✅ Warehouse capacity available                │
│  ✅ Handles cotton commodity                    │
│                                                  │
│  [✓ Use Recommended] [Choose Different]         │
│                                                  │
│  ──────────────────────────────────────────────  │
│                                                  │
│  📄 BILLING ADDRESS (Bill-to):                  │
│                                                  │
│  ○ Same as delivery (AHD-01)                    │
│  ● Head Office Mumbai (MUM-HO) ← Selected       │
│  ○ Different address                            │
│                                                  │
│  ──────────────────────────────────────────────  │
│                                                  │
│  GST Summary:                                    │
│  Seller (Surat, Gujarat) → Buyer (Ahmedabad, GJ)│
│  Type: Intra-state                              │
│  CGST: 9% | SGST: 9% | Total: 18%              │
│                                                  │
│  [Generate Contract]                             │
└──────────────────────────────────────────────────┘
```

### Step 3: Contract Generated

```
✅ Contract TR-2025-00001 Generated

Addresses:
  Ship-to: Ahmedabad Factory (AHD-01)
  Bill-to: Mumbai Head Office (MUM-HO)

[Download PDF] [Sign Contract]

Need to change address? [Request Amendment]
```

### Step 4: Amendment Request (If Needed)

```
┌──────────────────────────────────────────────────┐
│  Request Address Change                         │
├──────────────────────────────────────────────────┤
│                                                  │
│  Current: Ahmedabad Factory (AHD-01)            │
│                                                  │
│  Change to:                                     │
│  ● Surat Warehouse (SUR-02)                     │
│  ○ Mumbai Head Office (MUM-HO)                  │
│                                                  │
│  Reason:                                        │
│  [Ahmedabad warehouse is full____________]      │
│                                                  │
│  ⚠️  Seller must approve this change            │
│                                                  │
│  [Request Change]                               │
└──────────────────────────────────────────────────┘
```

---

## ✅ SUMMARY - CORRECT FLOW

### Phase 1: Trading (No Branch Involvement)
```
✅ User creates requirement with MAIN partner ID
✅ Negotiation happens at partner level
✅ NO branch selection during trading
```

### Phase 2: Contract Generation (Branch Selection)
```
✅ User selects branches for:
   - Ship-to address (delivery location)
   - Bill-to address (billing location)
   - Ship-from address (dispatch location)

✅ AI suggests best branch based on:
   - State matching (GST optimization)
   - Distance from delivery city
   - Warehouse capacity
   - Commodity handling capability

✅ User can override AI suggestion
```

### Phase 3: Amendment (After Generation)
```
✅ If contract status = DRAFT:
   - User can change immediately
   - No approval needed
   - Contract regenerated

✅ If contract status = PENDING_SIGNATURE:
   - Amendment requires counterparty approval
   - Approval workflow triggered
   - Contract regenerated after approval
```

---

## 🚀 IMPLEMENTATION CHECKLIST

1. ✅ AI branch suggestion algorithm
2. ✅ Branch selection UI at contract generation
3. ✅ Separate Ship-to and Bill-to selection
4. ✅ Amendment workflow
5. ✅ Counterparty approval system
6. ✅ Contract regeneration on amendment
7. ✅ GST type calculation (intra vs inter-state)
8. ✅ Audit trail for amendments

**This is the CORRECT flow you wanted! Shall I start?** 🎯
