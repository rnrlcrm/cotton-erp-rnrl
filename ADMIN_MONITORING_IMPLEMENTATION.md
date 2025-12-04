# Admin Monitoring - Back Office Real-Time Access

## ✅ IMPLEMENTATION COMPLETE

### Requirement
Back office (INTERNAL/SUPER_ADMIN users) needs **READ-ONLY** access to monitor all negotiations in real-time, but **CANNOT participate** in negotiations.

### Solution Architecture

#### 1. Separate Admin Endpoints
**Path**: `/api/v1/trade-desk/admin/negotiations`

**Access Control**: 
```python
if current_user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
    raise AuthorizationException("Admin access required for monitoring")
```

#### 2. Admin Service Methods (No Authorization Filter)

**`admin_get_all_negotiations()`**
- Returns ALL negotiations across all users
- No buyer/seller filter
- Pagination support (up to 500 per page)
- Optional status filter

**`admin_get_negotiation_by_id()`**
- Returns ANY negotiation by ID
- No authorization check
- Full details with offers, messages, partners

#### 3. Endpoints Created

##### GET `/api/v1/trade-desk/admin/negotiations`
Monitor all active negotiations in real-time.

**Query Params**:
- `status`: Filter by status (optional)
- `limit`: Max results (1-500, default 100)
- `offset`: Pagination offset

**Response**:
```json
{
  "negotiations": [
    {
      "id": "uuid",
      "buyer_partner": {"id": "uuid", "business_name": "ABC Ltd"},
      "seller_partner": {"id": "uuid", "business_name": "XYZ Corp"},
      "status": "IN_PROGRESS",
      "current_round": 3,
      "last_activity_at": "2025-12-04T10:30:00Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

##### GET `/api/v1/trade-desk/admin/negotiations/{negotiation_id}`
View complete negotiation details.

**Response**:
```json
{
  "id": "uuid",
  "buyer_partner": {...},
  "seller_partner": {...},
  "status": "IN_PROGRESS",
  "current_round": 3,
  "offers": [
    {
      "round_number": 1,
      "offered_by": "BUYER",
      "price_per_unit": 7100.00,
      "quantity": 50.0,
      "message": "Initial offer for premium cotton",
      "ai_generated": true,
      "created_at": "2025-12-04T09:00:00Z"
    }
  ],
  "messages": [
    {
      "sender": "BUYER",
      "message": "Looking forward to finalizing this deal",
      "created_at": "2025-12-04T09:05:00Z"
    }
  ]
}
```

### Access Matrix

| User Type | Regular Endpoints | Admin Endpoints | Can Negotiate |
|-----------|-------------------|-----------------|---------------|
| EXTERNAL (Buyer/Seller) | ✅ Own negotiations only | ❌ 403 Forbidden | ✅ Yes |
| INTERNAL (Back Office) | ❌ 403 Forbidden (no business_partner_id) | ✅ See ALL | ❌ No - READ ONLY |
| SUPER_ADMIN | ❌ 403 Forbidden (no business_partner_id) | ✅ See ALL | ❌ No - READ ONLY |

### Security Features

1. **Authorization Check**: Every admin endpoint validates user type
2. **Read-Only**: Admin routes DO NOT expose actions (no POST/PUT/DELETE)
3. **Complete Isolation**: External users cannot access admin endpoints
4. **Audit Trail**: All admin access logged through standard FastAPI logging

### Files Modified

1. **backend/modules/trade_desk/services/negotiation_service.py**
   - Added `admin_get_all_negotiations()` method
   - Added `admin_get_negotiation_by_id()` method
   - No authorization filters for admin methods

2. **backend/modules/trade_desk/routes/negotiation_routes.py**
   - Created `admin_router` (separate from regular `router`)
   - Added 2 admin endpoints with user type validation
   - Imported `AuthorizationException`

3. **backend/app/main.py**
   - Registered `negotiation_admin_router`
   - Mounted at `/api/v1/trade-desk/admin/negotiations`

### Testing Checklist

- [ ] EXTERNAL user tries admin endpoint → 403 Forbidden
- [ ] INTERNAL user accesses admin list → See all negotiations
- [ ] INTERNAL user accesses admin detail → See full negotiation
- [ ] SUPER_ADMIN user accesses admin endpoints → Success
- [ ] Admin endpoints return negotiations from multiple users
- [ ] Regular endpoints still enforce user isolation

### Usage Example

```python
# Back office user monitoring dashboard
import httpx

headers = {"Authorization": "Bearer <INTERNAL_USER_TOKEN>"}

# Get all active negotiations
response = httpx.get(
    "https://api.example.com/api/v1/trade-desk/admin/negotiations?status=IN_PROGRESS",
    headers=headers
)

negotiations = response.json()["negotiations"]

# Drill down into specific negotiation
negotiation_id = negotiations[0]["id"]
detail = httpx.get(
    f"https://api.example.com/api/v1/trade-desk/admin/negotiations/{negotiation_id}",
    headers=headers
)

# Monitor offers, messages, status in real-time
print(f"Round {detail['current_round']}")
print(f"Latest offer: ₹{detail['offers'][-1]['price_per_unit']}")
```

### Real-Time Monitoring

Admin users can:
- ✅ See all negotiations across all buyers/sellers
- ✅ View complete offer history
- ✅ Read all messages between parties
- ✅ Monitor negotiation status changes
- ✅ Track AI-generated vs human offers
- ✅ Filter by status (IN_PROGRESS, COMPLETED, etc.)

Admin users CANNOT:
- ❌ Start negotiations
- ❌ Make offers
- ❌ Accept/reject offers
- ❌ Send messages
- ❌ Modify any negotiation data

### Next Steps

1. **Run Migration**: Apply database schema
2. **Integration Test**: Verify admin access control
3. **Move to Trade Engine**: Continue with Phase 5
