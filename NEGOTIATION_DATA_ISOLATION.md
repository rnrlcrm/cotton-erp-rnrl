# Negotiation Engine - Data Isolation Summary

## ✅ DATA ISOLATION IMPLEMENTED

### Current State: EXTERNAL Users Only

**Business Rule**: Only EXTERNAL users (buyers/sellers with `business_partner_id`) can participate in negotiations.

### Access Control

#### 1. **EXTERNAL Users (Buyers/Sellers)**
- ✅ Can ONLY see their own negotiations (as buyer OR seller)
- ✅ Can ONLY make offers in their negotiations  
- ✅ Can ONLY accept/reject offers in their negotiations
- ✅ Can ONLY send messages in their negotiations
- ✅ Authorization enforced in ALL service methods

#### 2. **INTERNAL/SUPER_ADMIN Users (Back Office)**
**Current**: ❌ Cannot access negotiation endpoints (routes require `business_partner_id`)

**To Add**: Admin read-only access

### Implementation Details

#### Routes Layer (`negotiation_routes.py`)
```python
# All routes check:
if not current_user.business_partner_id:
    raise HTTPException(status_code=403, detail="Partner access required")
```

**Effect**: INTERNAL users get 403 Forbidden

#### Service Layer (`negotiation_service.py`)
All methods enforce authorization:

1. **start_negotiation()**
   ```python
   if not is_buyer and not is_seller:
       raise AuthorizationException("You are not party to this match")
   ```

2. **make_offer()**
   ```python
   if not is_buyer and not is_seller:
       raise AuthorizationException("You are not party to this negotiation")
   ```

3. **accept_offer()** - Same check

4. **reject_offer()** - Same check

5. **send_message()** - Same check

6. **get_negotiation_by_id()**
   ```python
   if not (is_buyer or is_seller):
       raise AuthorizationException("You are not party to this negotiation")
   ```

7. **get_user_negotiations()**
   ```python
   stmt = select(Negotiation).where(
       or_(
           Negotiation.buyer_partner_id == user_partner_id,
           Negotiation.seller_partner_id == user_partner_id
       )
   )
   ```

### To Add Admin Access (Future Enhancement)

#### Option 1: Separate Admin Routes
```python
@admin_router.get("/admin/negotiations")  
async def admin_list_all_negotiations(
    current_user: User = Depends(get_current_user),
    service: NegotiationService = Depends(get_negotiation_service)
):
    # Check if INTERNAL/SUPER_ADMIN
    if current_user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get ALL negotiations (no filter)
    return await service.get_all_negotiations()
```

#### Option 2: Update Existing Service Methods
```python
async def get_negotiation_by_id(
    negotiation_id: UUID,
    user_partner_id: Optional[UUID] = None,
    bypass_authorization: bool = False  # For admin
):
    # ... load negotiation ...
    
    # Skip authorization if admin
    if not bypass_authorization and user_partner_id:
        if not (is_buyer or is_seller):
            raise AuthorizationException(...)
```

### Summary

**Current Protection**: ✅ STRONG
- External users can ONLY see/modify their own negotiations
- No way to access other users' negotiations
- Authorization checked at EVERY operation

**Admin Access**: ❌ NOT IMPLEMENTED
- INTERNAL users currently blocked at route level
- Need separate admin endpoints OR bypass flag

**Recommendation**: Keep current strict isolation. Add admin read-only routes separately when needed for back-office monitoring.
