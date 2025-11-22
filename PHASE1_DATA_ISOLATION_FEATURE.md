# Phase 1: Data Isolation Foundation - Feature Specification

**Date**: November 22, 2025  
**Version**: 1.0  
**Status**: Ready for Implementation

---

## 🎯 OBJECTIVE

Build complete data isolation foundation for Cotton ERP that:
- Ensures EXTERNAL users see only their business partner's data
- Allows INTERNAL users to see all business partners
- Gives SUPER_ADMIN full system access
- Complies with GDPR, IT Act 2000, Income Tax Act 1961, GST Act
- Integrates seamlessly with existing architecture (event-driven, middleware, audit)

---

## 📋 CURRENT SYSTEM ANALYSIS

### Existing Architecture Components:

✅ **Middleware Stack**:
- `RequestIDMiddleware` - Request tracking (already uses ContextVar)
- `SecureHeadersMiddleware` - Security headers
- Rate limiting via SlowAPI
- CORS middleware

✅ **Audit System**:
- `backend/core/audit/logger.py` - Structured audit logging
- `request_id_ctx` ContextVar already in use
- JSON-formatted audit logs

✅ **Event System**:
- Event dispatchers, handlers, subscribers in `backend/events/`
- Event-driven architecture in place

✅ **Database**:
- SQLAlchemy 2.0 with declarative base
- Alembic migrations ready
- PostgreSQL as primary database

✅ **RBAC Foundation**:
- `PermissionCodes` enum in `backend/core/rbac/permissions.py`
- Basic permissions defined

✅ **Domain Layer**:
- `backend/domain/repositories/base.py` exists (empty - ready for our base repo)

---

## 🏗️ ARCHITECTURE INTEGRATION POINTS

### 1. Context Variables (Thread-Safe State)
**Pattern**: Already used by `request_id_ctx` in audit logger  
**New Addition**: Security context for user isolation  
**Integration**: Same ContextVar pattern, will work with existing async/await

### 2. Middleware Chain
**Current**: RequestID → SecureHeaders → CORS → RateLimiter  
**New**: RequestID → **Auth** → **DataIsolation** → SecureHeaders → CORS → RateLimiter  
**Integration**: Add to middleware stack in `main.py`, follows existing pattern

### 3. Audit Logging
**Current**: `audit_log()` function with correlation_id  
**Enhancement**: Add data access logging for GDPR compliance  
**Integration**: Extend existing audit logger, use same JSON format

### 4. Event System
**Current**: Event dispatchers and handlers  
**Integration**: Data isolation will work with events (isolation applied at repository level)  
**Note**: Events will respect isolation automatically via BaseRepository

### 5. Database Session
**Current**: `SessionLocal` via context manager  
**Enhancement**: Add RLS session variables via middleware  
**Integration**: Set PostgreSQL session vars after session creation

---

## 🔐 SECURITY LAYERS (Defense in Depth)

### Layer 1: Application Context (ContextVars)
- Thread-safe user context
- Set by middleware on every request
- Used by all repositories

### Layer 2: Middleware (Request-Level)
- Validates user authentication
- Sets context based on user_type
- Configures PostgreSQL RLS
- Logs all access

### Layer 3: Repository (Data Access)
- Auto-applies business_partner_id filter
- Prevents data leakage in code
- Works with existing SQLAlchemy patterns

### Layer 4: Database (PostgreSQL RLS)
- Database-level row filtering
- Protection against SQL injection
- Backup if application layer fails

### Layer 5: Audit (Compliance)
- All data access logged
- GDPR Article 30 compliance
- Incident detection

---

## 📊 DATA MODEL

### New Table: business_partners

```sql
-- External companies (buyers, sellers, brokers)
business_partners:
  - id (UUID, PK)
  - name (company name)
  - partner_type (BUYER, SELLER, BROKER, TRANSPORTER, BOTH)
  - gstin, pan, tan (tax IDs)
  - contact info, address
  - credit_limit, credit_days
  - kyc_status, kyc_verified_at
  - data_residency (GDPR)
  - consent_marketing, consent_data_sharing (GDPR)
  - data_retention_days (Income Tax: 2555 days = 7 years)
  - is_deleted, deleted_at (soft delete for compliance)
```

### Updated Table: users

```sql
users (ADD):
  - user_type (SUPER_ADMIN, INTERNAL, EXTERNAL)
  - business_partner_id (FK to business_partners, nullable)
  - organization_id (FK to organizations, nullable) 
  - allowed_modules (TEXT[], for RBAC module visibility)
  
Constraints:
  - SUPER_ADMIN: bp_id = NULL, org_id = NULL
  - INTERNAL: bp_id = NULL, org_id = NOT NULL
  - EXTERNAL: bp_id = NOT NULL, org_id = NULL
```

---

## 🔧 COMPONENTS TO BUILD

### 1. Security Context Module
**File**: `backend/core/security/context.py`

**Purpose**: Thread-safe context for user isolation

**Components**:
- `UserType` enum (SUPER_ADMIN, INTERNAL, EXTERNAL)
- ContextVars: user_id, user_type, business_partner_id, organization_id, allowed_modules
- Helper functions: get_current_user_id(), is_external_user(), has_module_access()
- SecurityError exception

**Integration**:
- Uses same ContextVar pattern as `request_id_ctx`
- Thread-safe for async operations
- Works with FastAPI dependency injection

---

### 2. Data Isolation Middleware
**File**: `backend/app/middleware/isolation.py`

**Purpose**: Set context and configure RLS on every request

**Flow**:
```
1. Check if path is public (skip isolation)
2. Get authenticated user from request.state.user
3. Validate user has required fields (id, user_type)
4. Set ContextVars based on user_type
5. Configure PostgreSQL RLS session variables
6. Log access (GDPR compliance)
7. Check module access (RBAC)
8. Process request
```

**Integration**:
- Follows pattern of `RequestIDMiddleware`
- Runs AFTER auth middleware (needs user)
- Runs BEFORE business logic
- Uses existing audit logger

---

### 3. Base Repository
**File**: `backend/domain/repositories/base.py`

**Purpose**: Auto-filter queries by business_partner_id

**Features**:
- Generic[ModelType] for type safety
- _has_business_partner_column() check
- _apply_isolation_filter() based on user_type
- _apply_soft_delete_filter() for GDPR retention
- CRUD methods: get_by_id, get_all, count, create, update, delete, restore

**Integration**:
- Uses SQLAlchemy 2.0 select() syntax (matches existing code)
- Works with existing session management
- Compatible with event dispatchers

---

### 4. Enhanced Audit Logger
**File**: `backend/core/audit/logger.py` (UPDATE)

**Additions**:
- log_data_access() for all API calls
- log_data_export() for GDPR portability
- log_data_deletion() for GDPR erasure
- log_cross_branch_invoice() for back-office actions

**Integration**:
- Extends existing audit_log() function
- Same JSON format
- Same logger instance
- Uses existing request_id_ctx

---

### 5. Business Partner Model
**File**: `backend/modules/settings/business_partners/models.py`

**Purpose**: External company entity

**Integration**:
- Uses existing Base from session_module
- Follows pattern of Organization model
- Includes GDPR compliance fields
- Soft delete support

---

### 6. User Model Updates
**File**: `backend/modules/settings/models/settings_models.py` (UPDATE)

**Changes**:
- Add user_type column
- Add business_partner_id FK
- Add organization_id FK (migrate from existing)
- Add allowed_modules array
- Add CHECK constraints for user_type validation

**Migration Strategy**:
- Existing users → user_type = 'INTERNAL' (default)
- Existing organization_id preserved
- Backward compatible

---

### 7. RBAC Enhancements
**File**: `backend/core/rbac/permissions.py` (UPDATE)

**New Permissions**:
```python
# Settings (Super Admin)
SETTINGS_VIEW_ALL
SETTINGS_MANAGE_ORGS
SETTINGS_MANAGE_COMMODITIES

# Business Partners (Internal)
BP_VIEW_ALL
BP_CREATE
BP_UPDATE
BP_VERIFY_KYC

# Cross-Branch (Back-Office)
INVOICE_CREATE_ANY_BRANCH

# External User
CONTRACT_VIEW_OWN
INVOICE_VIEW_OWN

# GDPR
DATA_EXPORT_OWN
DATA_DELETE_OWN

# Audit (Super Admin)
AUDIT_VIEW_ALL
```

---

## 🧪 TESTING STRATEGY

### Unit Tests:
- Context functions work correctly
- Isolation filter applies properly
- Audit logging captures events
- User type validation

### Integration Tests:
- EXTERNAL user sees only their BP data
- INTERNAL user sees all BP data
- SUPER_ADMIN has full access
- Cross-BP access blocked (403)
- Module access control works
- RLS policies enforce isolation

### Security Tests:
- Token manipulation fails
- SQL injection blocked by RLS
- Permission bypass fails
- Context spoofing fails

---

## 📝 ALEMBIC MIGRATIONS

### Migration 1: Create business_partners
**File**: `backend/db/migrations/versions/XXX_create_business_partners.py`

```python
def upgrade():
    op.create_table('business_partners', ...)
    op.create_index(...)
    op.create_constraint(...)

def downgrade():
    op.drop_table('business_partners')
```

### Migration 2: Update users table
**File**: `backend/db/migrations/versions/XXX_update_users_isolation.py`

```python
def upgrade():
    # Add columns
    op.add_column('users', sa.Column('user_type', ...))
    op.add_column('users', sa.Column('business_partner_id', ...))
    op.add_column('users', sa.Column('allowed_modules', ...))
    
    # Set defaults for existing users
    op.execute("UPDATE users SET user_type = 'INTERNAL'")
    
    # Add constraints
    op.create_check_constraint(...)
    op.create_foreign_key(...)
    op.create_index(...)

def downgrade():
    op.drop_column('users', 'user_type')
    op.drop_column('users', 'business_partner_id')
    op.drop_column('users', 'allowed_modules')
```

### Migration 3: Enable RLS
**File**: `backend/db/migrations/versions/XXX_enable_rls_policies.py`

```python
def upgrade():
    # Template for future tables
    # Will be applied when business tables created
    op.execute("""
        -- Example policy (to be used in future migrations)
        -- ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
        -- CREATE POLICY bp_isolation ON {table_name} ...
    """)

def downgrade():
    pass
```

---

## 🚀 IMPLEMENTATION ORDER

### Day 1: Core Security
1. ✅ Create `backend/core/security/context.py`
2. ✅ Create `backend/core/security/__init__.py`
3. ✅ Update `backend/core/audit/logger.py`
4. ✅ Create `backend/core/audit/__init__.py`
5. ✅ Unit tests for context

### Day 2: Repository & Middleware
6. ✅ Create `backend/domain/repositories/base.py`
7. ✅ Create `backend/app/middleware/isolation.py`
8. ✅ Unit tests for repository
9. ✅ Integration tests for middleware

### Day 3: Database Models
10. ✅ Create `backend/modules/settings/business_partners/`
11. ✅ Create business partner model
12. ✅ Update user model
13. ✅ Create Alembic migration 1 (business_partners)
14. ✅ Create Alembic migration 2 (users update)

### Day 4: RBAC & Integration
15. ✅ Update `backend/core/rbac/permissions.py`
16. ✅ Update `main.py` to use isolation middleware
17. ✅ Create seed data for testing
18. ✅ Integration tests (end-to-end)

### Day 5: Documentation & Template
19. ✅ Create module template with isolation
20. ✅ Create developer guide
21. ✅ Create RLS migration template
22. ✅ Final testing & validation

---

## ✅ SUCCESS CRITERIA

### Functional:
- ✅ EXTERNAL users can only query their BP data
- ✅ INTERNAL users can query all BP data
- ✅ SUPER_ADMIN has unrestricted access
- ✅ Module access controlled by RBAC
- ✅ All access logged for audit

### Security:
- ✅ No way to bypass isolation via API
- ✅ SQL injection blocked by RLS
- ✅ Context cannot be spoofed
- ✅ Proper 401/403 error codes

### Compliance:
- ✅ GDPR: consent, retention, audit logs
- ✅ IT Act: access logs, encryption
- ✅ Income Tax: 7-year retention
- ✅ GST: branch-wise invoice support

### Performance:
- ✅ No N+1 queries
- ✅ Proper indexes on business_partner_id
- ✅ Context overhead < 1ms
- ✅ RLS overhead < 5ms

### Developer Experience:
- ✅ Clear module template
- ✅ Simple: extend BaseRepository
- ✅ Auto-isolation (no extra code)
- ✅ Good documentation

---

## 🔄 FUTURE MODULE INTEGRATION

When creating new modules (Trade Desk, Logistics, etc.):

```python
# 1. Model
class Contract(Base):
    __tablename__ = "contracts"
    id = Column(UUID, primary_key=True)
    business_partner_id = Column(UUID, ForeignKey("business_partners.id"))
    # ... other fields

# 2. Repository
class ContractRepository(BaseRepository[Contract]):
    pass  # Isolation automatic!

# 3. Migration with RLS
def upgrade():
    op.create_table('contracts', ...)
    op.execute("ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY bp_isolation ON contracts
        FOR ALL TO PUBLIC
        USING (
            CASE 
                WHEN current_setting('app.user_type') = 'SUPER_ADMIN' THEN TRUE
                WHEN current_setting('app.user_type') = 'INTERNAL' THEN TRUE
                WHEN current_setting('app.user_type') = 'EXTERNAL' THEN
                    business_partner_id = current_setting('app.business_partner_id')::uuid
                ELSE FALSE
            END
        );
    """)
```

**That's it! Module has full isolation.**

---

## 🎯 POST-PHASE 1 READINESS

After Phase 1 completion:

### ✅ Ready to Build:
- Roles & Rights module (with isolation)
- Business Partner management module
- Trade Desk module
- Any business module

### ✅ All modules will automatically have:
- Data isolation
- GDPR compliance
- Audit logging
- Security layers
- RLS protection

### ✅ System will support:
- Web app (React)
- Mobile app (React Native)
- AI/Chatbot
- Event-driven workflows
- Background workers

---

## 📊 RISK MITIGATION

### Risk: Breaking existing functionality
**Mitigation**: 
- Default user_type = 'INTERNAL' for existing users
- Middleware only affects authenticated routes
- Backward compatible migration

### Risk: Performance impact
**Mitigation**:
- Proper indexes on business_partner_id
- RLS policies optimized
- Context overhead minimal (ContextVar is fast)
- Load testing before production

### Risk: RLS complexity
**Mitigation**:
- Template for RLS policies
- Clear documentation
- Helper script for applying RLS
- Testing framework

### Risk: Audit log volume
**Mitigation**:
- Structured logging
- Log rotation
- Optional: Store in separate table
- Retention policy (30 days)

---

## 🎉 DELIVERABLES

1. ✅ Security context module (context.py)
2. ✅ Data isolation middleware (isolation.py)
3. ✅ Base repository with auto-filtering (base.py)
4. ✅ Enhanced audit logger (logger.py updates)
5. ✅ Business partner model + migration
6. ✅ User model updates + migration
7. ✅ RBAC permission updates
8. ✅ Module template with isolation
9. ✅ Developer documentation
10. ✅ Complete test suite
11. ✅ RLS policy templates
12. ✅ Integration with main.py

---

**READY FOR IMPLEMENTATION** ✅

**Estimated Time**: 5 working days  
**Team**: Backend Developer(s)  
**Dependencies**: None (foundation layer)  
**Blockers**: None

---

**Approved By**: _____________  
**Date**: _____________
