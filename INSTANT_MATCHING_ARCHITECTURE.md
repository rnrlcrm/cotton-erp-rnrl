# Instant Matching Architecture

## Overview

The Cotton ERP system uses **INSTANT AUTOMATIC MATCHING** instead of traditional marketplace listing patterns. When users post availabilities or requirements, the system immediately finds and notifies about matches in real-time.

**Key Principle:** No manual browsing or searching - the system does all matching automatically using AI scoring and risk assessment.

---

## Architecture Change

### ❌ OLD: Marketplace Pattern (Deprecated)
```
Buyer posts requirement → Buyer searches availabilities → Buyer browses listings → Buyer selects match → Negotiation starts
Seller posts availability → Waits for buyers to search → Listing visible to all → Manual selection
```

**Problems:**
- Stale inventory browsing
- Manual search required
- Slower matching process
- Information overload for users
- Risk of showing already-matched items

### ✅ NEW: Instant Automatic Matching
```
Buyer posts requirement → Risk Check → INSTANT MATCH (AI-powered) → Notifications sent → Direct peer-to-peer
Seller posts availability → Risk Check → INSTANT MATCH (AI-powered) → Notifications sent → Direct peer-to-peer
```

**Benefits:**
- Real-time matching (sub-second)
- No manual searching needed
- AI-optimized matches (scoring + risk assessment)
- Direct peer-to-peer communication
- No stale inventory
- Better user experience

---

## Implementation Details

### 1. Availability Creation Flow

**File:** `backend/modules/trade_desk/services/availability_service.py`

```python
async def create_availability(self, request: CreateAvailabilityRequest, seller_id: UUID) -> Availability:
    # Step 1-12: Validation, persistence, risk check...
    
    # Step 13: INSTANT AUTOMATIC MATCHING
    try:
        matching_service = MatchingService(
            db=self.db,
            matching_engine=MatchingEngine(self.db),
            validator=MatchValidator(self.db),
            config=MatchingConfig(),
            redis_client=self.redis_client
        )
        
        # Trigger instant matching with HIGH priority (synchronous)
        await matching_service.on_availability_created(
            availability_id=availability.id,
            priority=MatchPriority.HIGH  # Bypasses normal queue
        )
        
        logger.info(f"Instant matching triggered for availability {availability.id}")
        
    except Exception as e:
        # Don't fail creation if matching fails - event-driven fallback will handle
        logger.warning(f"Instant matching failed for {availability.id}, fallback to event-driven: {e}")
    
    # Event emitted for fallback/async processing
    await self.event_bus.emit('availability.created', {...})
    
    return availability
```

**Matching Priority:**
- **HIGH Priority**: User-triggered creation (instant synchronous matching)
- **MEDIUM Priority**: Background reprocessing, periodic checks
- **LOW Priority**: Bulk imports, system maintenance

### 2. Requirement Creation Flow

**File:** `backend/modules/trade_desk/services/requirement_service.py`

```python
async def create_requirement(self, request: CreateRequirementRequest, buyer_id: UUID) -> Requirement:
    # Step 1-13: Validation, persistence, risk check, intent routing...
    
    # Step 14: INSTANT AUTOMATIC MATCHING
    try:
        matching_service = MatchingService(
            db=self.db,
            matching_engine=MatchingEngine(self.db),
            validator=MatchValidator(self.db),
            config=MatchingConfig(),
            redis_client=self.redis_client
        )
        
        # Trigger instant matching with HIGH priority
        await matching_service.on_requirement_created(
            requirement_id=requirement.id,
            priority=MatchPriority.HIGH  # Instant matching
        )
        
        logger.info(f"Instant matching triggered for requirement {requirement.id}")
        
    except Exception as e:
        logger.warning(f"Instant matching failed for {requirement.id}, fallback to event-driven: {e}")
    
    # Event emitted for fallback
    await self.event_bus.emit('requirement.created', {...})
    
    return requirement
```

### 3. Matching Service (Existing Infrastructure)

**File:** `backend/modules/trade_desk/services/matching_service.py`

The MatchingService already exists and handles:

- **Priority Queue System**: HIGH/MEDIUM/LOW priority matching
- **AI-Powered Scoring**: Uses MatchingEngine for compatibility scoring
- **Risk Assessment**: MatchValidator checks counterparty risk, compliance
- **Automatic Routing**: Intent-based routing (SPOT, BOOKING, CONTRACT, OTC)
- **WebSocket Notifications**: Real-time match notifications via WebSocket
- **Event-Driven Fallback**: If synchronous matching fails, events trigger retry

**Key Methods:**
```python
async def on_availability_created(self, availability_id: UUID, priority: MatchPriority = MatchPriority.MEDIUM):
    """
    Triggered when availability is created.
    Finds all compatible requirements and creates matches.
    """
    
async def on_requirement_created(self, requirement_id: UUID, priority: MatchPriority = MatchPriority.MEDIUM):
    """
    Triggered when requirement is created.
    Finds all compatible availabilities and creates matches.
    """
```

### 4. Intent-Based Routing (Automatic)

When a requirement or availability is created, the system automatically routes to the correct engine based on `intent_type`:

**File:** `requirement_service.py` - Step 9: Intent Routing

```python
# Automatic routing based on intent
intent_router = IntentRouter(db=self.db, redis_client=self.redis_client)

routing_result = await intent_router.route_requirement(
    requirement_id=requirement.id,
    intent_type=requirement.intent_type,
    commodity_id=requirement.commodity_id,
    quantity=requirement.quantity,
    budget_range=(requirement.min_price_per_unit, requirement.max_price_per_unit),
    urgency=requirement.urgency_level
)
```

**Intent Types:**
- `DIRECT_BUY` → Instant Matching Engine (real-time matching)
- `NEGOTIATION` → Negotiation Queue (multi-round negotiation)
- `AUCTION_REQUEST` → Reverse Auction Engine (competitive bidding)
- `PRICE_DISCOVERY_ONLY` → Market Insights (no matching, just data)

**Result:** Users don't need to manually search by intent - system handles it automatically.

---

## Deprecated Endpoints

The following marketplace-style search endpoints are **DEPRECATED** and return `HTTP 410 GONE`:

### 1. POST /availabilities/search
**Old Purpose:** Search for availabilities by commodity, quality, price, location  
**Deprecated Because:** Marketplace listing pattern - users should not browse availabilities  
**Replacement:** POST /requirements (system finds matches automatically)

**Response:**
```json
{
  "error": "ENDPOINT_DEPRECATED",
  "message": "Marketplace-style search is deprecated. Use INSTANT AUTOMATIC MATCHING instead.",
  "recommendation": "Post a requirement (POST /requirements) and receive instant matches via notifications.",
  "reason": "System moved from marketplace listing to real-time peer-to-peer matching for better efficiency and accuracy."
}
```

### 2. POST /requirements/search
**Old Purpose:** Search for requirements by commodity, quantity, budget  
**Deprecated Because:** Sellers should not browse requirements manually  
**Replacement:** POST /availabilities (system finds matches automatically)

**Response:**
```json
{
  "error": "ENDPOINT_DEPRECATED",
  "message": "Marketplace-style search is deprecated. Use INSTANT AUTOMATIC MATCHING instead.",
  "recommendation": "Post an availability (POST /availabilities) and receive instant matches via notifications.",
  "reason": "System moved from marketplace listing to real-time peer-to-peer matching for better efficiency and accuracy."
}
```

### 3. POST /requirements/search/by-intent
**Old Purpose:** Search requirements by intent type (DIRECT_BUY, NEGOTIATION, etc.)  
**Deprecated Because:** Intent routing is now automatic  
**Replacement:** POST /availabilities (system routes by intent automatically)

**Response:**
```json
{
  "error": "ENDPOINT_DEPRECATED",
  "message": "Intent-based search is deprecated. Use INSTANT AUTOMATIC MATCHING with automatic intent routing.",
  "recommendation": "Post an availability (POST /availabilities) and system will automatically match requirements based on intent type (DIRECT_BUY/NEGOTIATION/AUCTION/PRICE_DISCOVERY).",
  "reason": "System moved to automatic intent-based routing with real-time matching."
}
```

---

## Active Endpoints

### For Buyers (Creating Requirements)

**POST /requirements**
- Creates a requirement
- Triggers instant automatic matching with availabilities
- Returns created requirement + instant match notifications
- Intent routing happens automatically
- No need to search - matches delivered via WebSocket

**GET /requirements/buyer/my-requirements**
- Lists buyer's own requirements
- Shows match status, negotiation status
- No search needed - all information in one place

### For Sellers (Creating Availabilities)

**POST /availabilities**
- Creates an availability
- Triggers instant automatic matching with requirements
- Returns created availability + instant match notifications
- Intent routing happens automatically
- No need to search - matches delivered via WebSocket

**GET /availabilities/seller/my-availabilities**
- Lists seller's own availabilities
- Shows match status, sales pipeline
- No search needed - all information in one place

### Match Notifications

**WebSocket:** `/ws/matches/{user_id}`
- Real-time notifications when matches are found
- Includes match score, compatibility details, next steps
- Direct peer-to-peer communication channel

**Event Bus:**
- `match.created` - New match found
- `match.validated` - Match passed risk validation
- `match.routed` - Match routed to correct engine (negotiation/auction/direct)

---

## Matching Algorithm

### Scoring Factors (AI-Powered)

The MatchingEngine uses multiple factors to score compatibility:

1. **Quality Match** (30%)
   - Quality parameter compatibility
   - Tolerance levels (buyer's acceptable range vs seller's offering)
   - Certification requirements

2. **Price Compatibility** (25%)
   - Buyer's budget vs seller's asking price
   - Market price analysis
   - Historical pricing patterns

3. **Quantity Match** (15%)
   - Buyer's quantity needs vs seller's available quantity
   - Minimum order quantity compatibility
   - Bulk discount opportunities

4. **Location Proximity** (10%)
   - Geo-spatial distance calculation
   - Delivery cost estimation
   - Regional market preferences

5. **Timeline Alignment** (10%)
   - Delivery date compatibility
   - Urgency level matching
   - Seasonal patterns

6. **Risk Score** (10%)
   - Counterparty risk assessment
   - Payment term compatibility
   - Historical relationship quality

**Match Threshold:** 0.6 (60% compatibility minimum)

### Risk Validation

Before creating a match, the MatchValidator checks:

1. **Counterparty Risk**
   - Credit score, payment history
   - Outstanding disputes
   - Trade compliance status

2. **Regulatory Compliance**
   - Export/import restrictions
   - Quality certifications required
   - Regional regulations

3. **Business Rules**
   - Peer-to-peer only (no self-matching)
   - Market visibility rules (PUBLIC vs PRIVATE vs GROUP)
   - Blocked business partners

**Result:** Only valid, low-risk matches are created and notified.

---

## Example Flows

### Example 1: Buyer Posts Requirement (Instant Matching)

```
1. Buyer creates requirement via POST /requirements
   {
     "commodity_id": "uuid-cotton",
     "quantity": 1000,
     "unit": "BALES",
     "quality_requirements": {...},
     "max_price_per_unit": 50000,
     "delivery_date": "2025-01-15",
     "intent_type": "DIRECT_BUY"
   }

2. System validates and persists requirement (Steps 1-8)

3. Risk check passes (Step 10)

4. Intent router assigns to Matching Engine (Step 9)

5. INSTANT MATCHING triggered (Step 14):
   - MatchingService finds 3 compatible availabilities
   - Scores: 0.92, 0.87, 0.73 (all above 0.6 threshold)
   - Risk validation passes for all 3

6. Matches created and notifications sent (< 1 second):
   - WebSocket notification to buyer: "3 matches found!"
   - WebSocket notification to 3 sellers: "Your availability matched!"
   - Event: match.created emitted 3 times

7. Buyer receives instant response with matches:
   {
     "requirement": {...},
     "matches": [
       {"seller_id": "...", "match_score": 0.92, "availability": {...}},
       {"seller_id": "...", "match_score": 0.87, "availability": {...}},
       {"seller_id": "...", "match_score": 0.73, "availability": {...}}
     ]
   }

8. Buyer and sellers can now negotiate directly (peer-to-peer)
```

**Time to Match:** < 1 second (instant)

### Example 2: Seller Posts Availability (Instant Matching)

```
1. Seller creates availability via POST /availabilities
   {
     "commodity_id": "uuid-cotton",
     "quantity": 500,
     "unit": "BALES",
     "quality_params": {...},
     "price_per_unit": 48000,
     "delivery_start_date": "2025-01-10",
     "intent_type": "SPOT"
   }

2. System validates and persists availability (Steps 1-12)

3. Risk check passes

4. INSTANT MATCHING triggered (Step 13):
   - MatchingService finds 2 compatible requirements
   - Scores: 0.88, 0.79
   - Risk validation passes for both

5. Matches created and notifications sent (< 1 second):
   - WebSocket notification to seller: "2 buyers interested!"
   - WebSocket notification to 2 buyers: "New availability matches your need!"
   - Event: match.created emitted 2 times

6. Seller receives instant response with matches:
   {
     "availability": {...},
     "matches": [
       {"buyer_id": "...", "match_score": 0.88, "requirement": {...}},
       {"buyer_id": "...", "match_score": 0.79, "requirement": {...}}
     ]
   }

7. Seller and buyers can now negotiate directly
```

**Time to Match:** < 1 second (instant)

---

## Fallback Mechanisms

### Event-Driven Fallback

If synchronous instant matching fails (timeout, service error, etc.), the system falls back to event-driven matching:

```python
# In services - if instant matching fails
try:
    await matching_service.on_availability_created(availability.id, priority=HIGH)
except Exception as e:
    logger.warning(f"Instant matching failed, fallback to event-driven: {e}")

# Event is ALWAYS emitted (regardless of instant matching result)
await self.event_bus.emit('availability.created', {
    'availability_id': availability.id,
    'seller_id': seller_id,
    'commodity_id': commodity_id,
    ...
})
```

**Event Subscribers:**
- MatchingService (retry matching with MEDIUM priority)
- Analytics Service (demand/supply tracking)
- Notification Service (general alerts)

### Priority Queue System

MatchingService uses a priority queue to handle matching requests:

- **HIGH Priority**: User-triggered creation (instant, synchronous)
  - Processed immediately
  - Bypasses queue
  - Result returned in API response

- **MEDIUM Priority**: Event-driven retry, background reprocessing
  - Normal queue processing
  - Processed within 5-10 seconds
  - Result sent via WebSocket

- **LOW Priority**: Bulk operations, system maintenance
  - Processed during off-peak hours
  - No SLA guarantees

**Result:** Even if instant matching fails, users get matches within seconds via events.

---

## Performance Considerations

### Instant Matching Performance

**Target SLA:**
- Matching calculation: < 500ms
- Total API response time: < 1000ms (including DB writes, notifications)

**Optimizations:**
1. **Database Indexes:**
   - `availabilities(commodity_id, status, delivery_start_date)`
   - `requirements(commodity_id, status, delivery_date)`
   - `business_partners(risk_score, compliance_status)`

2. **Redis Caching:**
   - Commodity details cached (TTL: 1 hour)
   - Business partner risk scores cached (TTL: 15 minutes)
   - Quality parameter metadata cached (TTL: 24 hours)

3. **Parallel Processing:**
   - Risk validation runs in parallel with scoring
   - Match creation is batched (single DB transaction)
   - Notifications sent asynchronously (non-blocking)

4. **Query Optimization:**
   - Pre-filter by commodity_id, status
   - Use JSONB indexes for quality_params
   - Limit to top 10 candidates before detailed scoring

**Monitoring:**
- Prometheus metrics: `matching_duration_seconds`
- Alert if p95 latency > 1 second
- Dashboard: Match success rate, avg scoring time

---

## Migration from Marketplace Pattern

### For Existing Code

**Old Code (Search Pattern):**
```python
# Buyer searching for availabilities (DEPRECATED)
availabilities = await availability_service.search_availabilities(
    commodity_id=commodity_id,
    quality_requirements=quality_requirements,
    max_price=max_price
)

# Manual selection
selected = availabilities[0]
```

**New Code (Instant Matching):**
```python
# Buyer creates requirement (matches found automatically)
requirement = await requirement_service.create_requirement(
    request=CreateRequirementRequest(
        commodity_id=commodity_id,
        quality_requirements=quality_requirements,
        max_price_per_unit=max_price,
        ...
    ),
    buyer_id=buyer_id
)

# Matches are delivered via WebSocket automatically
# No need to search or select manually
```

### For Frontend Applications

**Old Frontend Flow:**
1. User clicks "Search Availabilities"
2. Search form with filters
3. Browse results
4. Click "View Details"
5. Click "Make Offer"

**New Frontend Flow:**
1. User clicks "Post Requirement"
2. Requirement form (same fields as search)
3. Submit → Instant matches appear in notifications
4. Click notification → View match details
5. Click "Start Negotiation"

**UI Changes Needed:**
- Remove "Search" buttons and forms
- Add "Post Requirement"/"Post Availability" prominent CTAs
- Show match notifications in real-time (WebSocket)
- Match list instead of search results
- Emphasize "matches found automatically" messaging

---

## Testing Instant Matching

### Unit Tests

```python
# Test instant matching is triggered
async def test_create_availability_triggers_instant_matching():
    availability = await service.create_availability(request, seller_id)
    
    # Verify MatchingService.on_availability_created was called
    mock_matching_service.on_availability_created.assert_called_once_with(
        availability_id=availability.id,
        priority=MatchPriority.HIGH
    )

# Test fallback if instant matching fails
async def test_create_availability_fallback_on_matching_failure():
    mock_matching_service.on_availability_created.side_effect = Exception("Matching failed")
    
    availability = await service.create_availability(request, seller_id)
    
    # Availability still created
    assert availability.id is not None
    
    # Event still emitted for fallback
    mock_event_bus.emit.assert_called_with('availability.created', ...)
```

### Integration Tests

```python
# Test end-to-end instant matching
async def test_instant_matching_end_to_end():
    # Create requirement
    requirement = await create_requirement(buyer_id, commodity_id, quality_params)
    
    # Create matching availability
    availability = await create_availability(seller_id, commodity_id, quality_params)
    
    # Verify match was created instantly (< 1 second)
    matches = await get_matches(requirement.id)
    assert len(matches) == 1
    assert matches[0].availability_id == availability.id
    assert matches[0].match_score > 0.6
    
    # Verify notifications sent
    buyer_notifications = await get_notifications(buyer_id)
    seller_notifications = await get_notifications(seller_id)
    assert any(n.type == "MATCH_FOUND" for n in buyer_notifications)
    assert any(n.type == "MATCH_FOUND" for n in seller_notifications)
```

### Performance Tests

```python
# Test instant matching performance
async def test_instant_matching_performance():
    start = time.time()
    
    requirement = await create_requirement(buyer_id, commodity_id, quality_params)
    
    end = time.time()
    duration = end - start
    
    # Verify total time < 1 second (including matching)
    assert duration < 1.0
    
    # Verify matches were found
    matches = await get_matches(requirement.id)
    assert len(matches) > 0
```

---

## Troubleshooting

### Issue: "No matches found instantly"

**Possible Causes:**
1. No compatible availabilities/requirements in database
2. Match score below threshold (< 0.6)
3. Risk validation failed
4. Market visibility restrictions

**Debug Steps:**
```python
# Check if any availabilities exist
availabilities = await db.query(Availability).filter(
    Availability.commodity_id == commodity_id,
    Availability.status == "ACTIVE"
).all()

# Check match scores manually
for availability in availabilities:
    score = await matching_engine.calculate_match_score(requirement, availability)
    logger.info(f"Match score with {availability.id}: {score}")

# Check risk validation
risk_result = await match_validator.validate_match(requirement, availability)
logger.info(f"Risk validation: {risk_result}")
```

### Issue: "Instant matching is slow (> 1 second)"

**Possible Causes:**
1. Database query optimization needed
2. Too many candidates being scored
3. Redis cache not populated
4. Network latency

**Debug Steps:**
```python
# Enable query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Check query execution time
with db.query_timing():
    availabilities = await matching_service.find_compatible_availabilities(requirement)

# Check Redis cache hit rate
cache_stats = await redis_client.info('stats')
logger.info(f"Cache hit rate: {cache_stats['keyspace_hits'] / cache_stats['keyspace_misses']}")
```

### Issue: "Deprecated endpoint still being used"

**Solution:**
1. Check API gateway logs for deprecated endpoint usage
2. Identify calling services/frontends
3. Update clients to use new flow:
   - Remove search API calls
   - Add requirement/availability creation
   - Add WebSocket listeners for match notifications

---

## Summary

**Key Points:**
1. ✅ **No marketplace browsing** - System matches automatically
2. ✅ **Instant matching** - Matches found in < 1 second
3. ✅ **AI-powered scoring** - Quality, price, location, risk all considered
4. ✅ **Intent routing** - Automatic routing to Matching/Negotiation/Auction
5. ✅ **Real-time notifications** - WebSocket delivery of matches
6. ✅ **Fallback mechanisms** - Event-driven retry if instant matching fails
7. ✅ **Deprecated endpoints** - Search endpoints return HTTP 410 GONE

**User Experience:**
- Buyers post requirements → Matches delivered instantly
- Sellers post availabilities → Matches delivered instantly
- No manual searching or browsing needed
- Direct peer-to-peer communication
- Faster, more efficient trading

**Next Steps:**
1. Apply database migrations (`alembic upgrade head`)
2. Test instant matching end-to-end
3. Update frontend to remove search UI
4. Monitor matching performance metrics
5. Create EOD cron jobs for expiry handling
