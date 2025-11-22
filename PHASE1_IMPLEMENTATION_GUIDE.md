# Phase 1: Data Isolation Foundation - Implementation Guide

**Status**: ✅ Foundation Complete - Ready for Integration  
**Branch**: `feature/phase1-data-isolation-foundation`  
**Date**: November 22, 2025

---

## 🎯 What Was Built

Complete data isolation foundation for multi-tenant Cotton ERP system with:
- Automatic business partner filtering for EXTERNAL users
- Full access for INTERNAL users (back-office)
- Super admin capabilities for SUPER_ADMIN
- GDPR, IT Act 2000, and Income Tax Act compliance built-in

---

## 📦 Components Created

### 1. Security Context (`backend/core/security/context.py`)
Thread-safe context management using ContextVars:
```python
from backend.core.security.context import (
    UserType, get_current_user_id, is_external_user,
    has_module_access, set_security_context
)
```

### 2. Base Repository (`backend/domain/repositories/base.py`)
Generic repository with automatic isolation:
```python
from backend.domain.repositories import BaseRepository

class ContractRepository(BaseRepository[Contract]):
    def __init__(self, db: Session):
        super().__init__(db, Contract)
    # All CRUD operations automatically filtered!
```

### 3. Data Isolation Middleware (`backend/app/middleware/isolation.py`)
Enforces isolation on every request:
- Sets security context from authenticated user
- Configures PostgreSQL RLS session variables
- Logs all data access (GDPR compliance)
- Enforces module-level RBAC

### 4. Database Schema
**BusinessPartner Model** (minimal):
- `id`, `name`, `partner_type`, `is_active`
- Audit trail: `created_at`, `created_by`, `updated_at`, `updated_by`
- Soft delete: `is_deleted`, `deleted_at`, `deleted_by`, `deletion_reason`

**User Model Updates**:
- `user_type`: SUPER_ADMIN | INTERNAL | EXTERNAL
- `business_partner_id`: FK to business_partners (for EXTERNAL)
- `organization_id`: FK to organizations (for INTERNAL, nullable)
- `allowed_modules`: TEXT[] for RBAC
- CHECK constraint enforcing isolation rules

### 5. Migrations
- `59d2e1f64664`: Create business_partners table
- `11c028f561fb`: Update users table with isolation fields

### 6. Enhanced Audit Logger
GDPR & IT Act compliance functions:
- `log_data_access()` - All API access
- `log_data_export()` - Data portability
- `log_data_deletion()` - Right to erasure
- `log_cross_branch_invoice()` - Income Tax compliance
- `log_isolation_violation()` - Security incidents

### 7. RBAC Permissions
Updated `PermissionCodes` with 26 new permissions for:
- Settings management
- Business partner operations
- Cross-branch operations
- GDPR compliance
- Audit & compliance

---

## 🚀 How to Use

### Step 1: Run Migrations (When Database Ready)
```bash
cd backend
alembic upgrade head
```

This creates:
- `business_partners` table
- Updates `users` table with isolation fields

### Step 2: Enable Middleware (After Auth Middleware Exists)

In `backend/app/main.py`:
```python
from backend.app.middleware.isolation import DataIsolationMiddleware

def create_app() -> FastAPI:
    app = FastAPI(...)
    
    # Middleware order is critical:
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AuthMiddleware)  # Must set request.state.user
    app.add_middleware(DataIsolationMiddleware)  # Uses request.state.user
    app.add_middleware(SecureHeadersMiddleware)
    # ... rest of middleware
```

**⚠️ CRITICAL**: Auth middleware must set `request.state.user` with:
- `user.id` (UUID)
- `user.user_type` (SUPER_ADMIN | INTERNAL | EXTERNAL)
- `user.business_partner_id` (for EXTERNAL users)
- `user.organization_id` (for INTERNAL users)
- `user.allowed_modules` (list of module names)

### Step 3: Create Module with Isolation

```python
# 1. Model (add business_partner_id for isolation)
from backend.db.session import Base

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(UUID, primary_key=True, default=uuid4)
    business_partner_id = Column(UUID, ForeignKey("business_partners.id"))
    
    # Soft delete for compliance
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID, nullable=True)
    # ... other fields

# 2. Repository (extend BaseRepository - isolation automatic!)
from backend.domain.repositories import BaseRepository

class ContractRepository(BaseRepository[Contract]):
    def __init__(self, db: Session):
        super().__init__(db, Contract)

# 3. Service (use repository)
class ContractService:
    def __init__(self, db: Session):
        self.repo = ContractRepository(db)
    
    def get_contracts(self):
        # Automatically filtered by business_partner_id for EXTERNAL users!
        return self.repo.get_all()
    
    def create_contract(self, data: dict):
        # business_partner_id auto-injected for EXTERNAL users!
        return self.repo.create(data)

# 4. Migration with RLS
def upgrade():
    op.create_table('contracts', ...)
    
    # Enable Row Level Security
    op.execute("ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;")
    
    # Create isolation policy
    op.execute("""
        CREATE POLICY bp_isolation ON contracts
        FOR ALL TO PUBLIC
        USING (
            CASE 
                WHEN current_setting('app.user_type', TRUE) = 'SUPER_ADMIN' THEN TRUE
                WHEN current_setting('app.user_type', TRUE) = 'INTERNAL' THEN TRUE
                WHEN current_setting('app.user_type', TRUE) = 'EXTERNAL' THEN
                    business_partner_id = current_setting('app.business_partner_id')::uuid
                ELSE FALSE
            END
        );
    """)
```

**That's it!** Your module now has:
- ✅ Automatic data isolation
- ✅ GDPR compliance (soft delete)
- ✅ Audit logging
- ✅ RLS protection
- ✅ Module access control

---

## 🔒 Isolation Rules

| User Type | Filter | Access Level |
|-----------|--------|--------------|
| **SUPER_ADMIN** | None | See ALL data globally |
| **INTERNAL** | None | See ALL business partners |
| **EXTERNAL** | `WHERE business_partner_id = current_bp_id` | See ONLY their data |

---

## 🧪 Testing

### Test Security Context
```python
from backend.core.security.context import set_security_context, UserType, is_external_user

# Set context (normally done by middleware)
set_security_context(
    user_id=UUID("..."),
    user_type=UserType.EXTERNAL,
    business_partner_id=UUID("..."),
    allowed_modules=['trade-desk', 'invoices']
)

# Check context
assert is_external_user() == True
assert has_module_access('trade-desk') == True
```

### Test Repository Isolation
```python
# Setup
set_security_context(user_id=user1_id, user_type=UserType.EXTERNAL, 
                      business_partner_id=bp1_id)

# Query
contracts = repo.get_all()

# Assert: Only sees contracts with business_partner_id = bp1_id
assert all(c.business_partner_id == bp1_id for c in contracts)
```

### Test Data Spoofing Prevention
```python
# Try to create contract for different BP
data = {'name': 'Test', 'business_partner_id': bp2_id}  # Different BP!

contract = repo.create(data)

# Assert: business_partner_id forced to bp1_id (from context)
assert contract.business_partner_id == bp1_id  # ✅ Spoofing prevented
```

---

## 📋 Checklist Before Integration

- [ ] PostgreSQL running
- [ ] Run migrations (`alembic upgrade head`)
- [ ] Auth middleware implemented (sets `request.state.user`)
- [ ] Create test business partners and users
- [ ] Test isolation with all 3 user types
- [ ] Enable DataIsolationMiddleware in main.py
- [ ] Test end-to-end API flow
- [ ] Verify audit logs working
- [ ] Test module access control
- [ ] Run security tests

---

## 🎓 Examples

### Example: Trade Desk Module

```python
# models.py
class Contract(Base):
    __tablename__ = "contracts"
    id = Column(UUID, primary_key=True, default=uuid4)
    business_partner_id = Column(UUID, ForeignKey("business_partners.id"))
    contract_number = Column(String(50), unique=True)
    # ... other fields
    is_deleted = Column(Boolean, default=False)

# repositories.py
from backend.domain.repositories import BaseRepository

class ContractRepository(BaseRepository[Contract]):
    pass  # Isolation automatic!

# services.py
class ContractService:
    def __init__(self, db: Session):
        self.repo = ContractRepository(db)
    
    def list_contracts(self, skip: int = 0, limit: int = 100):
        # EXTERNAL user: Only their contracts
        # INTERNAL user: All contracts
        return self.repo.get_all(skip=skip, limit=limit)

# router.py
@router.get("/contracts")
async def get_contracts(db: Session = Depends(get_db)):
    service = ContractService(db)
    return service.list_contracts()
```

**Result**:
- EXTERNAL user calls API → Gets only their contracts (automatic)
- INTERNAL user calls API → Gets all contracts (automatic)
- All access logged for audit
- RLS enforces at database level

---

## 🛡️ Security Features

### Defense in Depth (5 Layers)

1. **Application Context** - ContextVars set by middleware
2. **Middleware Validation** - Validates user, sets context, logs access
3. **Repository Auto-Filtering** - Applies BP filter in queries
4. **PostgreSQL RLS** - Database-level row filtering
5. **Audit Logging** - All access recorded for compliance

### Compliance

✅ **GDPR**:
- Article 5: Data minimization
- Article 15: Right to access
- Article 17: Right to erasure (soft delete)
- Article 20: Data portability (export)
- Article 30: Records of processing (audit logs)
- Article 32: Security of processing (isolation + RLS)

✅ **IT Act 2000 (India)**:
- Section 43A: Reasonable security practices
- Section 72A: Sensitive personal data protection
- Audit trail requirements

✅ **Income Tax Act 1961 (India)**:
- 7-year retention (soft delete with `is_deleted`, `deleted_at`)
- Cross-branch invoice tracking

---

## 📝 Files Modified/Created

**Created**:
- `backend/core/security/context.py` (272 lines)
- `backend/core/security/__init__.py`
- `backend/domain/repositories/base.py` (383 lines)
- `backend/domain/repositories/__init__.py`
- `backend/domain/__init__.py`
- `backend/app/middleware/isolation.py` (317 lines)
- `backend/modules/settings/business_partners/models.py`
- `backend/modules/settings/business_partners/__init__.py`
- `backend/db/migrations/versions/59d2e1f64664_*.py`
- `backend/db/migrations/versions/11c028f561fb_*.py`
- `DATA_ISOLATION_PLAN.md`
- `PHASE1_DATA_ISOLATION_FEATURE.md`
- `PHASE1_TASKS_3_4_BASE_REPOSITORY_MIDDLEWARE.md`

**Modified**:
- `backend/core/audit/logger.py` (+150 lines - 5 compliance functions)
- `backend/modules/settings/models/settings_models.py` (User model updated)
- `backend/core/rbac/permissions.py` (+26 permissions)
- `backend/app/main.py` (comments for middleware integration)

---

## 🚨 Important Notes

### NOT YET ACTIVE

The isolation system is **built but NOT running** because:
1. ❌ Migrations not run (PostgreSQL not started)
2. ❌ Auth middleware not implemented
3. ❌ DataIsolationMiddleware not enabled in main.py

### To Activate

1. Start PostgreSQL
2. Run `alembic upgrade head`
3. Implement auth middleware that sets `request.state.user`
4. Enable `DataIsolationMiddleware` in `main.py`
5. Create test users with different `user_type` values
6. Test isolation working

---

## 💡 Tips

- **Always extend BaseRepository** for automatic isolation
- **Add business_partner_id to all business tables** (not settings)
- **Use soft delete** for compliance (7-year retention)
- **Enable RLS** in migrations for defense in depth
- **Test with all 3 user types** (SUPER_ADMIN, INTERNAL, EXTERNAL)
- **Check audit logs** to verify access tracking

---

## 🤝 Support

For questions about data isolation:
1. Check `DATA_ISOLATION_PLAN.md` - Master plan
2. Check `PHASE1_DATA_ISOLATION_FEATURE.md` - Detailed spec
3. Check `PHASE1_TASKS_3_4_BASE_REPOSITORY_MIDDLEWARE.md` - Implementation docs
4. Review inline documentation in code files

---

**Status**: ✅ Foundation Complete  
**Next**: Integrate with auth system and test  
**Branch**: `feature/phase1-data-isolation-foundation`  
**Ready to Merge**: After testing and validation
