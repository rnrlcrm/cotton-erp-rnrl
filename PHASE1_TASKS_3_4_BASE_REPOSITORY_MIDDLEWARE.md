# Phase 1 - Tasks 3 & 4: Base Repository & Data Isolation Middleware

**Feature**: Core Data Isolation Infrastructure  
**Date**: November 22, 2025  
**Status**: ✅ COMPLETED  
**Compliance**: GDPR, IT Act 2000, Income Tax Act 1961

---

## Overview

Built the **foundation layer** for automatic data isolation across the entire Cotton ERP system. These two components work together to enforce business partner isolation at both **application level** and **database level**.

### Key Achievement
🎯 **Once integrated, ALL future modules will automatically have data isolation built-in** - no extra code needed in business logic!

---

## Task 3: Base Repository with Auto-Filtering

### File Created
- `backend/domain/repositories/base.py` (381 lines)
- `backend/domain/repositories/__init__.py` (exports)
- `backend/domain/__init__.py` (package init)

### What It Does

**Generic Repository Pattern** with automatic business partner filtering:

```python
# Future module usage example:
class ContractRepository(BaseRepository[Contract]):
    def __init__(self, db: Session):
        super().__init__(db, Contract)
    
    # That's it! All CRUD operations automatically isolated:
    # - get_by_id() - Auto-filtered by BP
    # - get_all() - Auto-filtered by BP
    # - create() - Auto-injects business_partner_id
    # - update() - Prevents BP modification
    # - delete() - Soft delete (7-year retention)
```

### Isolation Rules (Automatic)

| User Type | Filter Applied | Access Level |
|-----------|---------------|--------------|
| **SUPER_ADMIN** | None | See ALL data (global access) |
| **INTERNAL** | None | See ALL business partners (back-office) |
| **EXTERNAL** | `WHERE business_partner_id = current_bp_id` | See ONLY their data (isolated) |

### Features

**1. Automatic Filtering**
- `_apply_isolation_filter()` - Reads security context, applies BP filter for EXTERNAL users
- `_apply_soft_delete_filter()` - Filters out deleted records (GDPR retention)
- `_base_query()` - Combines all filters automatically

**2. CRUD Operations** (All with built-in isolation)
- `get_by_id(id)` - Single record
- `get_all(skip, limit, filters, order_by)` - List with pagination
- `count(filters)` - Count records
- `create(data)` - Auto-injects `business_partner_id` for EXTERNAL users (prevents spoofing)
- `update(id, data)` - Prevents `business_partner_id` modification
- `delete(id, hard_delete)` - Soft delete by default (Income Tax 7-year retention)
- `restore(id)` - Restore soft-deleted records
- `exists(id)` - Check existence

**3. Security Features**
- **Prevents Data Spoofing**: EXTERNAL users cannot set/change `business_partner_id` - forced from context
- **Type Safety**: Generic[ModelType] ensures compile-time type checking
- **Soft Delete**: Complies with Income Tax Act 7-year retention requirement
- **Validation**: Raises `SecurityError` if EXTERNAL user context missing

**4. Compliance**
- ✅ GDPR Article 32: Security of Processing (automatic isolation)
- ✅ IT Act 2000 Section 43A: Data Protection (context-based filtering)
- ✅ Income Tax Act 1961: 7-year retention (soft delete with `is_deleted`, `deleted_at`, `deleted_by`)

### Database Model Requirements

For tables that need isolation, add:
```python
class MyModel(Base):
    __tablename__ = 'my_table'
    
    id = Column(UUID, primary_key=True)
    business_partner_id = Column(UUID, ForeignKey('business_partners.id'))  # ← Add this
    
    # Soft delete (compliance)
    is_deleted = Column(Boolean, default=False)  # ← Add this
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID, nullable=True)
```

For **shared tables** (settings, global config), DON'T add `business_partner_id`:
```python
class GlobalSetting(Base):
    __tablename__ = 'global_settings'
    
    id = Column(UUID, primary_key=True)
    # No business_partner_id - shared across all users
```

---

## Task 4: Data Isolation Middleware

### File Created
- `backend/app/middleware/isolation.py` (317 lines)

### What It Does

**CRITICAL SECURITY MIDDLEWARE** - Runs on EVERY authenticated API request:

1. ✅ **Extract authenticated user** from `request.state.user` (set by auth middleware)
2. ✅ **Validate user object** has required fields (`id`, `user_type`)
3. ✅ **Set security context** (ContextVars) based on `user_type`
4. ✅ **Configure PostgreSQL RLS** - Session variables for database-level security
5. ✅ **Log all access** - GDPR Article 30 compliance
6. ✅ **Check module access** - RBAC enforcement

### Integration Flow

```
Request → Auth Middleware → DataIsolationMiddleware → Business Logic → Response
          (sets user)      (sets context & RLS)       (uses BaseRepository)
```

### Defense in Depth (3 Layers)

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Layer 1** | Application Context (ContextVars) | Thread-safe user context for Python code |
| **Layer 2** | PostgreSQL RLS | Database-level filtering (even if app bypassed) |
| **Layer 3** | Audit Logging | Compliance trail (GDPR Article 30) |

### User Type Handling

**SUPER_ADMIN**:
```python
# Context set:
user_id = user.id
user_type = SUPER_ADMIN
business_partner_id = None
organization_id = None
allowed_modules = user.allowed_modules

# PostgreSQL RLS:
SET app.user_id = 'uuid'
SET app.user_type = 'SUPER_ADMIN'
```

**INTERNAL**:
```python
# Context set:
user_id = user.id
user_type = INTERNAL
business_partner_id = None
organization_id = user.organization_id  # Required!
allowed_modules = user.allowed_modules

# PostgreSQL RLS:
SET app.user_id = 'uuid'
SET app.user_type = 'INTERNAL'
SET app.organization_id = 'uuid'
```

**EXTERNAL**:
```python
# Context set:
user_id = user.id
user_type = EXTERNAL
business_partner_id = user.business_partner_id  # Required!
organization_id = None
allowed_modules = user.allowed_modules

# PostgreSQL RLS:
SET app.user_id = 'uuid'
SET app.user_type = 'EXTERNAL'
SET app.business_partner_id = 'uuid'
```

### Public Endpoints (Skipped)

These paths bypass isolation (no auth required):
- `/health`, `/healthz`, `/ready`
- `/docs`, `/redoc`, `/openapi.json`
- `/api/v1/auth/login`, `/api/v1/auth/register`
- `/api/v1/auth/forgot-password`, `/api/v1/auth/reset-password`

### Module Access Control

Middleware extracts module from path:
```
/api/v1/trade-desk/contracts → "trade-desk"
/api/v1/logistics/shipments → "logistics"
```

Checks `has_module_access(module)` - blocks if user not allowed:
```python
# If user.allowed_modules = ['trade-desk', 'quality']
# ✅ Allowed: /api/v1/trade-desk/contracts
# ✅ Allowed: /api/v1/quality/inspections
# ❌ Blocked: /api/v1/logistics/shipments (403 Forbidden)
```

### Compliance Logging

Every request logged:
```json
{
  "event": "data_access",
  "user_id": "uuid",
  "user_type": "EXTERNAL",
  "business_partner_id": "uuid",
  "path": "/api/v1/trade-desk/contracts",
  "method": "GET",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2025-11-22T10:30:00Z"
}
```

### Security Violations

Logged when access denied:
```json
{
  "event": "isolation_violation",
  "user_id": "uuid",
  "user_type": "EXTERNAL",
  "attempted_resource": "/api/v1/logistics/shipments",
  "user_business_partner_id": "uuid-1",
  "reason": "Module access denied: logistics",
  "timestamp": "2025-11-22T10:30:00Z"
}
```

---

## Integration Points

### 1. Existing Architecture (Leveraged)

✅ **ContextVars Pattern**: Follows same pattern as `request_id_ctx` in audit logger  
✅ **Middleware Chain**: Integrates with existing `RequestIDMiddleware`, `SecureHeadersMiddleware`  
✅ **Audit Logger**: Uses existing `audit_log()` infrastructure  
✅ **Event System**: Compatible with event-driven architecture  

### 2. Required Updates (Pending)

⏳ **User Model**: Needs `user_type`, `business_partner_id`, `allowed_modules` columns  
⏳ **Business Partner Model**: Needs to be created (Task 5)  
⏳ **Auth Middleware**: Must set `request.state.user` before isolation middleware  
⏳ **main.py**: Add isolation middleware to chain (Task 11)  

---

## Testing Strategy

### Unit Tests (To Be Created - Task 13)

**BaseRepository Tests**:
```python
def test_external_user_sees_only_their_data():
    # Set context: EXTERNAL user with bp_id = 'uuid-1'
    set_security_context(user_id='user-1', user_type=UserType.EXTERNAL, 
                        business_partner_id='uuid-1')
    
    # Query all contracts
    contracts = repo.get_all()
    
    # Assert: Only sees contracts with business_partner_id = 'uuid-1'
    assert all(c.business_partner_id == 'uuid-1' for c in contracts)

def test_internal_user_sees_all_data():
    # Set context: INTERNAL user
    set_security_context(user_id='user-2', user_type=UserType.INTERNAL, 
                        organization_id='org-1')
    
    # Query all contracts
    contracts = repo.get_all()
    
    # Assert: Sees all contracts (no filter)
    assert len(contracts) > 0  # All BPs visible

def test_create_prevents_spoofing():
    # Set context: EXTERNAL user with bp_id = 'uuid-1'
    set_security_context(user_id='user-1', user_type=UserType.EXTERNAL, 
                        business_partner_id='uuid-1')
    
    # Try to create with different bp_id
    data = {'name': 'Test', 'business_partner_id': 'uuid-2'}
    contract = repo.create(data)
    
    # Assert: business_partner_id forced to 'uuid-1' (from context)
    assert contract.business_partner_id == 'uuid-1'
```

**Middleware Tests**:
```python
async def test_middleware_sets_context():
    # Mock authenticated user
    user = Mock(id='user-1', user_type='EXTERNAL', business_partner_id='bp-1')
    request.state.user = user
    
    # Process request
    await middleware.dispatch(request, call_next)
    
    # Assert: Context set correctly
    assert get_current_user_id() == 'user-1'
    assert is_external_user() == True
    assert get_current_business_partner_id() == 'bp-1'

async def test_middleware_blocks_unauthorized_module():
    # Mock user without logistics access
    user = Mock(id='user-1', user_type='EXTERNAL', 
                business_partner_id='bp-1', allowed_modules=['trade-desk'])
    request.state.user = user
    request.url.path = '/api/v1/logistics/shipments'
    
    # Assert: Raises 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        await middleware.dispatch(request, call_next)
    assert exc.value.status_code == 403
```

### Integration Tests

**End-to-End Flow**:
1. Login as EXTERNAL user → Get JWT token
2. Call `/api/v1/trade-desk/contracts` → Get only user's contracts
3. Try to access `/api/v1/logistics/shipments` → Get 403 if not allowed
4. Check audit log → Verify access logged

---

## Current Status

### ✅ Completed

1. **Backend Components**:
   - ✅ `backend/core/security/context.py` - Security context with ContextVars
   - ✅ `backend/core/audit/logger.py` - Enhanced with compliance logging
   - ✅ `backend/domain/repositories/base.py` - Generic repository with auto-filtering
   - ✅ `backend/app/middleware/isolation.py` - Data isolation middleware

2. **Architecture**:
   - ✅ Defense in depth (3 layers: context, RLS, audit)
   - ✅ Follows existing patterns (ContextVars, middleware chain)
   - ✅ Type-safe with Generic[ModelType]
   - ✅ GDPR/IT Act/Income Tax compliant

3. **Documentation**:
   - ✅ Comprehensive inline documentation
   - ✅ Usage examples in docstrings
   - ✅ Integration points documented

### ⏳ Pending (Before It Works)

1. **Database Schema** (Tasks 5-9):
   - ⏳ Create `business_partners` table
   - ⏳ Update `users` table with `user_type`, `business_partner_id`, `allowed_modules`
   - ⏳ Run Alembic migrations

2. **Integration** (Task 11):
   - ⏳ Add isolation middleware to `backend/app/main.py`
   - ⏳ Ensure auth middleware runs BEFORE isolation middleware
   - ⏳ Ensure auth middleware sets `request.state.user`

3. **Testing** (Tasks 12-13):
   - ⏳ Create unit tests for BaseRepository
   - ⏳ Create integration tests for middleware
   - ⏳ Create module template showing usage pattern

---

## ⚠️ IMPORTANT: NOT YET ACTIVE

### Current State: **FOUNDATION BUILT, NOT INTEGRATED**

The code is complete and error-free, but **NOT YET RUNNING** because:

1. ❌ **No `business_partners` table** - Foreign key doesn't exist yet
2. ❌ **User model not updated** - Missing `user_type`, `business_partner_id` columns
3. ❌ **Middleware not integrated** - Not added to `main.py` middleware chain
4. ❌ **No auth middleware** - Nothing sets `request.state.user` yet

### What Happens Now?

If you try to use it:
```python
# This WON'T work yet:
repo = ContractRepository(db)
contracts = repo.get_all()  # ❌ Error: business_partners table doesn't exist

# This WON'T run yet:
# Middleware not in chain, so it's not executed
```

---

## Next Steps to Make It Work

### **Immediate** (Tasks 5-6):
1. Create Business Partner model (with GDPR fields)
2. Update User model (add isolation columns)

### **Required** (Tasks 7-9):
3. Create `business_partners` table migration
4. Create `users` table update migration
5. Run migrations: `alembic upgrade head`

### **Integration** (Task 11):
6. Add middleware to `main.py` middleware chain
7. Ensure auth middleware sets `request.state.user`

### **Validation** (Tasks 12-13):
8. Create module template showing pattern
9. Write comprehensive tests
10. Test all 3 user types (SUPER_ADMIN, INTERNAL, EXTERNAL)

---

## When Will It Be Automatic?

### After Integration (Tasks 5-11 Complete):

✅ **Every future module automatically gets isolation:**

```python
# Step 1: Create model with business_partner_id
class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(UUID, primary_key=True)
    business_partner_id = Column(UUID, ForeignKey('business_partners.id'))
    # ... other fields

# Step 2: Create repository extending BaseRepository
class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, db: Session):
        super().__init__(db, Invoice)

# Step 3: Use it - AUTOMATIC ISOLATION!
repo = InvoiceRepository(db)

# EXTERNAL user → Only sees their invoices
# INTERNAL user → Sees all invoices
# SUPER_ADMIN → Sees all invoices

invoices = repo.get_all()  # ✅ Automatically filtered!
```

### What You DON'T Need to Write:

❌ Manual filtering in every query  
❌ User type checks in business logic  
❌ Business partner validation  
❌ Access logging  
❌ Module access control  

**All handled automatically by the foundation!**

---

## Summary

### What We Built

1. **BaseRepository** - Generic repository with automatic BP filtering, soft delete, CRUD operations
2. **DataIsolationMiddleware** - Security middleware with context, RLS, audit, module access

### What It Provides

- ✅ **Automatic data isolation** for all future modules
- ✅ **Defense in depth** (3 security layers)
- ✅ **GDPR/IT Act compliance** built-in
- ✅ **Type safety** with Generic[ModelType]
- ✅ **7-year retention** (soft delete)
- ✅ **Audit trail** for all access
- ✅ **Module-level RBAC**

### What's Needed to Activate

1. Business Partner model + table
2. User model updates + migration
3. Middleware integration in main.py
4. Auth middleware (set request.state.user)

### Timeline

- **Built**: Tasks 3-4 ✅ DONE
- **Activate**: Tasks 5-11 ⏳ PENDING
- **Validate**: Tasks 12-13 ⏳ PENDING

**Once Tasks 5-11 complete → Every new module automatically inherits isolation! 🎯**
