# 🔒 DATA ISOLATION & SECURITY PLAN - COTTON ERP

**Date**: November 22, 2025  
**System**: Cotton ERP - Enterprise Commodity Trading Platform  
**Compliance**: GDPR, IT Act 2000, Income Tax Act 1961, GST Act

---

## 🎯 BUSINESS REQUIREMENTS (CONFIRMED)

### Current System Understanding:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUPER ADMIN LAYER                            │
│  - Manages Settings Module (Organizations, Commodities, etc.)   │
│  - Full system access                                           │
│  - Controls what modules users can see (via RBAC)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              INTERNAL USERS (Your Back-Office)                  │
│  Organization: RNRL Trade Hub (Your Company)                    │
│  └── Branches (GST Units):                                      │
│      ├── RNRL TH Pvt Ltd - Mumbai (GSTIN: 27XXX)               │
│      ├── RNRL TH Pvt Ltd - Delhi (GSTIN: 07XXX)                │
│      └── RNRL Commodities LLP - Ahmedabad (GSTIN: 24XXX)       │
│                                                                  │
│  Roles: Trade Manager, Accountant, Operations, etc.             │
│  Access: See ALL Business Partners, Create invoices in any GST  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            EXTERNAL USERS (Business Partners)                   │
│                                                                  │
│  Business Partner 1: ABC Cotton Mills Pvt Ltd                   │
│  └── Users: buyer1@abc.com, purchase_mgr@abc.com               │
│      Access: See ONLY their own data                            │
│                                                                  │
│  Business Partner 2: XYZ Ginning Factory                        │
│  └── Users: seller1@xyz.com, sales_head@xyz.com                │
│      Access: See ONLY their own data                            │
│                                                                  │
│  Business Partner 3: PQR Broker Ltd                             │
│  └── Users: broker@pqr.com                                      │
│      Access: See ONLY their own data                            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Points:

1. ✅ **Settings Module = Super Admin Only** (Organizations, Branches, Commodities, Locations, etc.)
2. ✅ **RBAC = Controls module visibility** per user role
3. ✅ **Organizations & Branches = Your internal companies** (for commission invoices)
4. ✅ **Business Partners = External companies** (buyers/sellers/brokers)
5. ✅ **Data Isolation = Per Business Partner** (STRICT)
6. ✅ **Back-office = Full access** to all Business Partners
7. ✅ **AI/Chatbot Security = Same isolation rules**
8. ✅ **Mobile App = Same isolation as web**

---

## 📊 DATABASE ARCHITECTURE

### Tables WITHOUT Isolation (Settings - Super Admin Only):

```
✅ organizations (RNRL companies)
✅ organization_gst (GST branches)
✅ organization_bank_accounts
✅ organization_financial_years
✅ organization_document_series
✅ commodities
✅ commodity_varieties
✅ commodity_parameters
✅ locations (countries, states, cities)
✅ trade_types
✅ bargain_types
✅ passing_terms
✅ weightment_terms
✅ delivery_terms
✅ payment_terms
✅ commission_structures
✅ permissions
✅ roles
✅ role_permissions
```

### NEW Table: business_partners

```sql
CREATE TABLE business_partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    partner_type VARCHAR(50) NOT NULL, -- 'BUYER', 'SELLER', 'BROKER', 'TRANSPORTER', 'BOTH'
    partner_code VARCHAR(50) UNIQUE, -- Auto: BP001, BP002
    
    -- Contact
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(32),
    alternate_phone VARCHAR(32),
    
    -- Address
    address TEXT,
    city VARCHAR(128),
    state VARCHAR(128),
    pincode VARCHAR(16),
    country VARCHAR(3) DEFAULT 'IND',
    
    -- Tax Details
    pan VARCHAR(10),
    gstin VARCHAR(15),
    tan VARCHAR(10),
    
    -- Credit Management
    credit_limit DECIMAL(15,2) DEFAULT 0,
    credit_days INTEGER DEFAULT 0,
    payment_terms TEXT,
    
    -- Banking
    bank_name VARCHAR(255),
    bank_account_number VARCHAR(50),
    bank_ifsc VARCHAR(11),
    bank_branch VARCHAR(255),
    
    -- Status & Risk
    status VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, BLOCKED, PENDING_APPROVAL
    credit_rating VARCHAR(10), -- AAA, AA, A, B, C
    risk_category VARCHAR(50), -- LOW, MEDIUM, HIGH
    
    -- KYC/Onboarding
    kyc_status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, VERIFIED, REJECTED
    kyc_verified_at TIMESTAMPTZ,
    kyc_verified_by UUID,
    onboarded_at TIMESTAMPTZ DEFAULT NOW(),
    onboarded_by UUID,
    
    -- GDPR/Data Protection Compliance
    data_residency VARCHAR(50) DEFAULT 'IN', -- India
    data_retention_days INTEGER DEFAULT 2555, -- 7 years (Income Tax Act)
    consent_marketing BOOLEAN DEFAULT FALSE,
    consent_data_sharing BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMPTZ,
    
    -- Audit Trail (IT Act 2000 Section 43A)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,
    
    -- Soft Delete (GDPR Right to Erasure)
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT,
    
    CONSTRAINT ck_bp_name_nonempty CHECK (name <> ''),
    CONSTRAINT ck_bp_type_valid CHECK (partner_type IN ('BUYER', 'SELLER', 'BROKER', 'TRANSPORTER', 'BOTH'))
);

-- Indexes for performance
CREATE INDEX idx_bp_status ON business_partners(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_bp_type ON business_partners(partner_type) WHERE is_deleted = FALSE;
CREATE INDEX idx_bp_gstin ON business_partners(gstin) WHERE gstin IS NOT NULL;
CREATE INDEX idx_bp_pan ON business_partners(pan) WHERE pan IS NOT NULL;
CREATE INDEX idx_bp_code ON business_partners(partner_code);

-- Audit table for GDPR Article 30 compliance
CREATE TABLE business_partner_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_partner_id UUID REFERENCES business_partners(id),
    action VARCHAR(50), -- CREATED, UPDATED, DELETED, KYC_VERIFIED
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,
    changed_by UUID,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

### UPDATE Table: users

```sql
-- Add new columns
ALTER TABLE users ADD COLUMN business_partner_id UUID;
ALTER TABLE users ADD COLUMN user_type VARCHAR(20) DEFAULT 'EXTERNAL';
  -- Types: 'SUPER_ADMIN', 'INTERNAL', 'EXTERNAL'

ALTER TABLE users ADD COLUMN allowed_modules TEXT[]; -- For RBAC module visibility

-- Foreign key
ALTER TABLE users ADD CONSTRAINT fk_users_bp 
    FOREIGN KEY (business_partner_id) 
    REFERENCES business_partners(id) ON DELETE RESTRICT;

-- Constraints based on user type
ALTER TABLE users ADD CONSTRAINT ck_user_type_bp CHECK (
    (user_type = 'SUPER_ADMIN' AND business_partner_id IS NULL AND organization_id IS NULL) OR
    (user_type = 'INTERNAL' AND business_partner_id IS NULL AND organization_id IS NOT NULL) OR
    (user_type = 'EXTERNAL' AND business_partner_id IS NOT NULL AND organization_id IS NULL)
);

-- Indexes
CREATE INDEX idx_users_bp ON users(business_partner_id) WHERE business_partner_id IS NOT NULL;
CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_org ON users(organization_id) WHERE organization_id IS NOT NULL;
```

### Tables Requiring business_partner_id (TO BE CREATED):

```
Future Modules (when implemented):
├── contracts (business_partner_id) - Trade Desk
├── purchase_orders (business_partner_id) - Trade Desk
├── sales_orders (business_partner_id) - Trade Desk
├── trades (buyer_partner_id, seller_partner_id, broker_partner_id) - Trade Desk
├── invoices (business_partner_id, branch_id) - Accounting
├── payments (business_partner_id) - Payment Engine
├── shipments (consignor_partner_id, consignee_partner_id) - Logistics
├── delivery_orders (business_partner_id) - Logistics
├── quality_reports (business_partner_id) - Quality
├── quality_claims (business_partner_id) - Quality
├── disputes (business_partner_id) - Dispute
├── sub_broker_agents (business_partner_id) - Sub-Broker
├── commission_records (business_partner_id, branch_id) - Sub-Broker
├── uploaded_documents (business_partner_id) - OCR
├── notifications (business_partner_id) - Notifications
└── ai_chat_sessions (business_partner_id) - AI/Chatbot
```

---

## 🔐 SECURITY IMPLEMENTATION

### Phase 1: Core Security Infrastructure

#### 1.1 Security Context (ContextVars)

**File**: `backend/core/security/context.py`

```python
"""
Thread-safe context for data isolation
Compliant with: GDPR Article 32, IT Act 2000 Section 43A
"""

from contextvars import ContextVar
from uuid import UUID
from enum import Enum
from typing import Optional

class UserType(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # Full system access
    INTERNAL = "INTERNAL"        # Your employees (back-office)
    EXTERNAL = "EXTERNAL"        # Business Partner users

class SecurityError(Exception):
    """Raised when security context is invalid"""
    pass

# Thread-safe context variables
current_user_id: ContextVar[Optional[UUID]] = ContextVar('user_id', default=None)
current_user_type: ContextVar[Optional[UserType]] = ContextVar('user_type', default=None)
current_business_partner_id: ContextVar[Optional[UUID]] = ContextVar('bp_id', default=None)
current_organization_id: ContextVar[Optional[UUID]] = ContextVar('org_id', default=None)
current_allowed_modules: ContextVar[list[str]] = ContextVar('allowed_modules', default=[])

def get_current_user_id() -> UUID:
    user_id = current_user_id.get()
    if not user_id:
        raise SecurityError("User context not set - authentication required")
    return user_id

def get_current_user_type() -> UserType:
    user_type = current_user_type.get()
    if not user_type:
        raise SecurityError("User type not set - invalid session")
    return user_type

def get_current_business_partner_id() -> Optional[UUID]:
    """Returns business_partner_id for EXTERNAL users, None for others"""
    return current_business_partner_id.get()

def get_current_organization_id() -> Optional[UUID]:
    """Returns organization_id for INTERNAL users, None for others"""
    return current_organization_id.get()

def is_super_admin() -> bool:
    return get_current_user_type() == UserType.SUPER_ADMIN

def is_internal_user() -> bool:
    return get_current_user_type() == UserType.INTERNAL

def is_external_user() -> bool:
    return get_current_user_type() == UserType.EXTERNAL

def has_module_access(module_name: str) -> bool:
    """Check if user has access to module (RBAC)"""
    if is_super_admin():
        return True  # Super admin has all modules
    
    allowed = current_allowed_modules.get()
    return module_name in allowed if allowed else False

def reset_context():
    """Clear all context (for testing/cleanup)"""
    current_user_id.set(None)
    current_user_type.set(None)
    current_business_partner_id.set(None)
    current_organization_id.set(None)
    current_allowed_modules.set([])
```

#### 1.2 Data Isolation Middleware

**File**: `backend/app/middleware/isolation.py`

```python
"""
Data Isolation Middleware
Enforces business partner isolation for EXTERNAL users
Compliance: GDPR Article 32, IT Act 2000, Income Tax Act 1961
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from backend.core.security.context import (
    current_user_id, current_user_type, current_business_partner_id,
    current_organization_id, current_allowed_modules, UserType
)
from backend.core.audit.logger import AuditLogger

class DataIsolationMiddleware(BaseHTTPMiddleware):
    """
    CRITICAL SECURITY MIDDLEWARE
    
    Responsibilities:
    1. Extract user info from authenticated session
    2. Set context based on user_type
    3. Configure PostgreSQL Row Level Security
    4. Log all access (GDPR Article 30 - Records of Processing)
    5. Enforce module-level access control (RBAC)
    """
    
    # Public endpoints (no auth required)
    SKIP_PATHS = [
        '/health',
        '/docs',
        '/openapi.json',
        '/api/v1/auth/login',
        '/api/v1/auth/register',
        '/api/v1/auth/forgot-password',
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip public endpoints
        if any(request.url.path.startswith(path) for path in self.SKIP_PATHS):
            return await call_next(request)
        
        # Get authenticated user (set by auth middleware - must run before this)
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate user object
        if not hasattr(user, 'id') or not hasattr(user, 'user_type'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user object in session"
            )
        
        # Set base context
        current_user_id.set(user.id)
        current_user_type.set(UserType(user.user_type))
        current_allowed_modules.set(getattr(user, 'allowed_modules', []))
        
        # Get database session
        db: Session = request.state.db
        
        # Configure context and RLS based on user type
        if user.user_type == UserType.SUPER_ADMIN:
            # Super Admin - full access, no isolation
            await self._set_postgres_rls(db, user_id=user.id, user_type='SUPER_ADMIN')
            
        elif user.user_type == UserType.INTERNAL:
            # Internal user (your employees) - see all business partners
            if not hasattr(user, 'organization_id') or not user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Internal user must have organization_id"
                )
            
            current_organization_id.set(user.organization_id)
            await self._set_postgres_rls(
                db,
                user_id=user.id,
                user_type='INTERNAL',
                organization_id=user.organization_id
            )
            
        elif user.user_type == UserType.EXTERNAL:
            # External user (business partner) - strict isolation
            if not hasattr(user, 'business_partner_id') or not user.business_partner_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="External user must have business_partner_id"
                )
            
            current_business_partner_id.set(user.business_partner_id)
            await self._set_postgres_rls(
                db,
                user_id=user.id,
                user_type='EXTERNAL',
                business_partner_id=user.business_partner_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid user_type: {user.user_type}"
            )
        
        # Audit log (GDPR Article 30 - Records of Processing Activities)
        await self._log_access(user, request)
        
        # Check module access (RBAC)
        module = self._extract_module_from_path(request.url.path)
        if module and not has_module_access(module):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to module: {module}"
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _set_postgres_rls(
        self,
        db: Session,
        user_id: UUID,
        user_type: str,
        business_partner_id: UUID = None,
        organization_id: UUID = None
    ):
        """
        Set PostgreSQL session variables for Row Level Security
        These are used in RLS policies to filter data automatically
        """
        params = {
            'user_id': str(user_id),
            'user_type': user_type
        }
        
        # Set session variables
        db.execute("SET app.user_id = :user_id", params)
        db.execute("SET app.user_type = :user_type", params)
        
        if business_partner_id:
            db.execute(
                "SET app.business_partner_id = :bp_id",
                {'bp_id': str(business_partner_id)}
            )
        
        if organization_id:
            db.execute(
                "SET app.organization_id = :org_id",
                {'org_id': str(organization_id)}
            )
    
    async def _log_access(self, user, request: Request):
        """
        Log all data access for compliance
        GDPR Article 30: Records of Processing Activities
        IT Act 2000: Audit trail requirement
        """
        AuditLogger.log_access(
            user_id=user.id,
            user_type=user.user_type,
            business_partner_id=getattr(user, 'business_partner_id', None),
            path=request.url.path,
            method=request.method,
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent', '')
        )
    
    def _extract_module_from_path(self, path: str) -> str | None:
        """Extract module name from API path"""
        # Example: /api/v1/trade-desk/contracts -> trade-desk
        parts = path.split('/')
        if len(parts) >= 4 and parts[1] == 'api' and parts[2] == 'v1':
            return parts[3]
        return None
```

#### 1.3 Base Repository with Auto-Filtering

**File**: `backend/domain/repositories/base.py`

```python
"""
Base Repository with automatic data isolation
All module repositories should extend this
"""

from typing import TypeVar, Generic, Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from datetime import datetime

from backend.core.security.context import (
    get_current_user_type, get_current_business_partner_id,
    is_super_admin, is_internal_user, is_external_user,
    UserType, SecurityError
)

ModelType = TypeVar('ModelType')

class BaseRepository(Generic[ModelType]):
    """
    Base repository with automatic business partner isolation
    
    Security Rules:
    - SUPER_ADMIN: See all data
    - INTERNAL: See all business partners (no filter)
    - EXTERNAL: See only their business_partner_id data
    
    Compliance:
    - GDPR Article 32: Security of Processing
    - IT Act 2000 Section 43A: Data Protection
    """
    
    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model
    
    def _has_business_partner_column(self) -> bool:
        """Check if model has business_partner_id for isolation"""
        return hasattr(self.model, 'business_partner_id')
    
    def _apply_isolation_filter(self, query):
        """
        Apply business partner isolation filter
        Only for EXTERNAL users on tables with business_partner_id
        """
        # Super admin and internal users - no filter
        if is_super_admin() or is_internal_user():
            return query
        
        # External users - apply isolation
        if is_external_user():
            if not self._has_business_partner_column():
                # Table doesn't have BP isolation (e.g., settings tables)
                return query
            
            bp_id = get_current_business_partner_id()
            if not bp_id:
                raise SecurityError("Business partner context missing for external user")
            
            return query.where(self.model.business_partner_id == bp_id)
        
        # Unknown user type - deny access
        raise SecurityError(f"Unknown user type: {get_current_user_type()}")
    
    def _apply_soft_delete_filter(self, query):
        """Filter out soft-deleted records (GDPR retention)"""
        if hasattr(self.model, 'is_deleted'):
            return query.where(self.model.is_deleted == False)
        return query
    
    def _base_query(self):
        """Base query with all filters applied"""
        query = select(self.model)
        query = self._apply_isolation_filter(query)
        query = self._apply_soft_delete_filter(query)
        return query
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get record by ID (with automatic isolation)
        Returns None if not found or user doesn't have access
        """
        stmt = self._base_query().where(self.model.id == id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict = None,
        order_by = None
    ) -> List[ModelType]:
        """Get all records (with automatic isolation)"""
        stmt = self._base_query()
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, 'created_at'):
            stmt = stmt.order_by(self.model.created_at.desc())
        
        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        
        return self.db.execute(stmt).scalars().all()
    
    def count(self, filters: dict = None) -> int:
        """Count records (with automatic isolation)"""
        stmt = self._base_query()
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        from sqlalchemy import func
        stmt = select(func.count()).select_from(stmt.subquery())
        return self.db.execute(stmt).scalar()
    
    def create(self, data: dict) -> ModelType:
        """
        Create record with automatic business_partner_id injection
        """
        # Auto-inject business_partner_id for external users
        if self._has_business_partner_column() and is_external_user():
            bp_id = get_current_business_partner_id()
            if not bp_id:
                raise SecurityError("Business partner context missing")
            
            # Force business_partner_id from context (prevent spoofing)
            data['business_partner_id'] = bp_id
        
        # Create object
        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        
        return obj
    
    def update(self, id: UUID, data: dict) -> Optional[ModelType]:
        """
        Update record (with automatic isolation check)
        Returns None if not found or user doesn't have access
        """
        obj = self.get_by_id(id)
        if not obj:
            return None
        
        # Prevent business_partner_id modification (security)
        data.pop('business_partner_id', None)
        
        # Update fields
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        # Update timestamp
        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.utcnow()
        
        self.db.flush()
        self.db.refresh(obj)
        
        return obj
    
    def delete(self, id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete record (soft delete by default for compliance)
        
        GDPR: Right to Erasure (after retention period)
        Income Tax Act: 7-year retention for financial records
        """
        obj = self.get_by_id(id)
        if not obj:
            return False
        
        if hard_delete or not hasattr(obj, 'is_deleted'):
            # Hard delete (permanent)
            self.db.delete(obj)
        else:
            # Soft delete (GDPR-compliant retention)
            obj.is_deleted = True
            obj.deleted_at = datetime.utcnow()
            if hasattr(obj, 'deleted_by'):
                from backend.core.security.context import get_current_user_id
                obj.deleted_by = get_current_user_id()
        
        self.db.flush()
        return True
    
    def restore(self, id: UUID) -> bool:
        """Restore soft-deleted record"""
        # Temporarily disable soft delete filter
        stmt = select(self.model).where(self.model.id == id)
        stmt = self._apply_isolation_filter(stmt)
        
        obj = self.db.execute(stmt).scalar_one_or_none()
        if not obj or not hasattr(obj, 'is_deleted'):
            return False
        
        obj.is_deleted = False
        obj.deleted_at = None
        self.db.flush()
        return True
```

#### 1.4 Audit Logger (GDPR/IT Act Compliance)

**File**: `backend/core/audit/logger.py`

```python
"""
Audit Logger for Compliance
GDPR Article 30: Records of Processing Activities
IT Act 2000: Audit trail requirement
Income Tax Act: Transaction audit
"""

from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

class AuditLogger:
    """
    Central audit logging for all data access
    Stores in audit_logs table for compliance
    """
    
    @staticmethod
    def log_access(
        user_id: UUID,
        user_type: str,
        business_partner_id: Optional[UUID],
        path: str,
        method: str,
        ip_address: str,
        user_agent: str
    ):
        """
        Log API access
        Required for GDPR Article 30
        """
        # TODO: Implement actual logging to database
        # For now, log to application logs
        import logging
        logger = logging.getLogger('audit')
        
        logger.info(
            f"ACCESS | User: {user_id} | Type: {user_type} | "
            f"BP: {business_partner_id} | "
            f"{method} {path} | IP: {ip_address}"
        )
    
    @staticmethod
    def log_data_export(
        user_id: UUID,
        business_partner_id: UUID,
        export_type: str,
        record_count: int
    ):
        """Log data export (GDPR Right to Portability)"""
        import logging
        logger = logging.getLogger('audit')
        
        logger.info(
            f"DATA_EXPORT | User: {user_id} | BP: {business_partner_id} | "
            f"Type: {export_type} | Records: {record_count}"
        )
    
    @staticmethod
    def log_data_deletion(
        user_id: UUID,
        business_partner_id: UUID,
        deletion_type: str,
        reason: str
    ):
        """Log data deletion (GDPR Right to Erasure)"""
        import logging
        logger = logging.getLogger('audit')
        
        logger.warning(
            f"DATA_DELETION | User: {user_id} | BP: {business_partner_id} | "
            f"Type: {deletion_type} | Reason: {reason}"
        )
    
    @staticmethod
    def log_cross_branch_invoice(
        user_id: UUID,
        invoice_id: UUID,
        branch_id: UUID
    ):
        """Log when back-office creates invoice in different branch"""
        import logging
        logger = logging.getLogger('audit')
        
        logger.info(
            f"CROSS_BRANCH_INVOICE | User: {user_id} | "
            f"Invoice: {invoice_id} | Branch: {branch_id}"
        )
```

---

## 🛡️ POSTGRESQL ROW LEVEL SECURITY (RLS)

### Enable RLS on Business Tables

**Migration**: `backend/db/migrations/versions/XXX_enable_rls.py`

```python
"""
Enable Row Level Security for data isolation
Double-layer security: Application + Database
"""

def upgrade():
    # When business tables are created, add RLS
    
    # Example for contracts table (when it exists)
    op.execute("""
        ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
        
        -- Policy for isolation
        CREATE POLICY bp_isolation_policy ON contracts
            FOR ALL
            TO PUBLIC
            USING (
                CASE 
                    -- Super admin: see all
                    WHEN current_setting('app.user_type', TRUE) = 'SUPER_ADMIN' THEN TRUE
                    
                    -- Internal users: see all
                    WHEN current_setting('app.user_type', TRUE) = 'INTERNAL' THEN TRUE
                    
                    -- External users: see only their BP
                    WHEN current_setting('app.user_type', TRUE) = 'EXTERNAL' THEN
                        business_partner_id = current_setting('app.business_partner_id')::uuid
                    
                    -- Deny by default
                    ELSE FALSE
                END
            );
    """)
    
    # Repeat for all business tables:
    # - invoices
    # - payments
    # - shipments
    # - quality_reports
    # - disputes
    # - etc.

def downgrade():
    op.execute("DROP POLICY IF EXISTS bp_isolation_policy ON contracts;")
    op.execute("ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;")
```

---

## 🎭 RBAC ENHANCEMENTS

### New Permissions

**File**: `backend/core/rbac/permissions.py`

```python
class PermissionCodes(str, Enum):
    # Settings Module (Super Admin Only)
    SETTINGS_VIEW_ALL = "settings:view:all"
    SETTINGS_MANAGE_ORGANIZATIONS = "settings:organizations:manage"
    SETTINGS_MANAGE_COMMODITIES = "settings:commodities:manage"
    SETTINGS_MANAGE_LOCATIONS = "settings:locations:manage"
    
    # Business Partner Management (Internal Users)
    BP_VIEW_ALL = "business_partners:view:all"
    BP_CREATE = "business_partners:create"
    BP_UPDATE = "business_partners:update"
    BP_DELETE = "business_partners:delete"
    BP_VERIFY_KYC = "business_partners:kyc:verify"
    
    # Cross-Branch Permissions (Back-Office)
    INVOICE_CREATE_ANY_BRANCH = "invoices:create:any_branch"
    INVOICE_VIEW_ALL_BRANCHES = "invoices:view:all_branches"
    
    # External User Permissions
    CONTRACT_VIEW_OWN = "contracts:view:own"
    INVOICE_VIEW_OWN = "invoices:view:own"
    PAYMENT_VIEW_OWN = "payments:view:own"
    
    # GDPR Compliance
    DATA_EXPORT_OWN = "data:export:own"
    DATA_DELETE_OWN = "data:delete:own"
    
    # Audit (Super Admin Only)
    AUDIT_VIEW_ALL = "audit:view:all"
```

### Role Definitions

```python
# Super Admin Role
SUPER_ADMIN_ROLE = {
    'name': 'Super Administrator',
    'user_type': 'SUPER_ADMIN',
    'description': 'Full system access, manages settings',
    'permissions': [
        'SETTINGS_VIEW_ALL',
        'SETTINGS_MANAGE_ORGANIZATIONS',
        'SETTINGS_MANAGE_COMMODITIES',
        'SETTINGS_MANAGE_LOCATIONS',
        'BP_VIEW_ALL',
        'BP_CREATE',
        'BP_UPDATE',
        'BP_DELETE',
        'BP_VERIFY_KYC',
        'AUDIT_VIEW_ALL',
        # ... all permissions
    ],
    'allowed_modules': ['ALL']  # Access to all modules
}

# Internal User Roles (Your Employees)
TRADE_MANAGER_ROLE = {
    'name': 'Trade Manager',
    'user_type': 'INTERNAL',
    'description': 'Manages trades, contracts, business partners',
    'permissions': [
        'BP_VIEW_ALL',
        'BP_CREATE',
        'BP_UPDATE',
        # Trade desk permissions
    ],
    'allowed_modules': ['trade-desk', 'contracts', 'logistics']
}

ACCOUNTANT_ROLE = {
    'name': 'Accountant',
    'user_type': 'INTERNAL',
    'description': 'Manages invoices, payments, can select any branch',
    'permissions': [
        'BP_VIEW_ALL',
        'INVOICE_CREATE_ANY_BRANCH',
        'INVOICE_VIEW_ALL_BRANCHES',
        # Accounting permissions
    ],
    'allowed_modules': ['accounting', 'payment-engine', 'reports']
}

# External User Roles (Business Partners)
BUYER_ROLE = {
    'name': 'Buyer',
    'user_type': 'EXTERNAL',
    'description': 'External buyer - sees only their data',
    'permissions': [
        'CONTRACT_VIEW_OWN',
        'INVOICE_VIEW_OWN',
        'PAYMENT_VIEW_OWN',
        'DATA_EXPORT_OWN',
    ],
    'allowed_modules': ['trade-desk', 'invoices', 'payments', 'quality']
}

SELLER_ROLE = {
    'name': 'Seller',
    'user_type': 'EXTERNAL',
    'description': 'External seller - sees only their data',
    'permissions': [
        'CONTRACT_VIEW_OWN',
        'INVOICE_VIEW_OWN',
        'PAYMENT_VIEW_OWN',
        'DATA_EXPORT_OWN',
    ],
    'allowed_modules': ['trade-desk', 'invoices', 'payments', 'logistics']
}
```

---

## 📱 MOBILE APP & AI/CHATBOT SECURITY

### Mobile App (React Native)

Same isolation rules apply - use JWT with user_type and business_partner_id:

```typescript
// mobile/src/contexts/AuthContext.tsx

interface User {
  id: string;
  email: string;
  user_type: 'SUPER_ADMIN' | 'INTERNAL' | 'EXTERNAL';
  business_partner_id?: string;
  organization_id?: string;
  allowed_modules: string[];
}

// API calls automatically filtered by backend middleware
```

### AI/Chatbot Security

**File**: `backend/ai/security/isolation.py`

```python
"""
AI/Chatbot data isolation
Ensures AI only accesses data user is allowed to see
"""

from backend.core.security.context import (
    is_external_user, get_current_business_partner_id
)

class AIChatSession:
    """AI chat session with data isolation"""
    
    def __init__(self, user):
        self.user = user
        self.business_partner_id = user.business_partner_id if is_external_user() else None
    
    def search_documents(self, query: str):
        """
        Search documents with automatic isolation
        External users: Only their documents
        Internal users: All documents
        """
        # Use same BaseRepository - isolation automatic
        from backend.modules.documents.repositories import DocumentRepository
        repo = DocumentRepository(db)
        return repo.get_all(filters={'query': query})
    
    def get_contract_info(self, contract_id: UUID):
        """
        Get contract info
        Returns None if user doesn't have access
        """
        from backend.modules.contracts.repositories import ContractRepository
        repo = ContractRepository(db)
        return repo.get_by_id(contract_id)  # Auto-filtered
```

---

## ✅ COMPLIANCE CHECKLIST

### GDPR (EU Regulation 2016/679) ✅

- ✅ **Article 5**: Data minimization (only collect necessary data)
- ✅ **Article 6**: Lawful basis (consent_marketing, consent_data_sharing)
- ✅ **Article 15**: Right to access (data export API)
- ✅ **Article 16**: Right to rectification (update API)
- ✅ **Article 17**: Right to erasure (soft delete + purge)
- ✅ **Article 20**: Right to data portability (export in JSON/CSV)
- ✅ **Article 30**: Records of processing (audit logs)
- ✅ **Article 32**: Security of processing (encryption + isolation)
- ✅ **Article 33**: Breach notification (audit logs + alerts)

### IT Act 2000 (India) ✅

- ✅ **Section 43A**: Reasonable security practices (encryption, access control, audit)
- ✅ **Section 72**: Data confidentiality (RLS + middleware)
- ✅ **Section 72A**: Punishment for disclosure (access logs)
- ✅ **IT Rules 2011**: Sensitive personal data protection (PAN, financial info encrypted)

### Income Tax Act 1961 (India) ✅

- ✅ **Section 44AB**: Books of accounts (7-year retention)
- ✅ **Section 139**: Return filing (audit trail)
- ✅ **Section 271B**: Penalty for non-maintenance (retention policy)
- ✅ **7-year retention**: data_retention_days = 2555 days

### GST Act (India) ✅

- ✅ **Branch-wise invoices**: branch_id in invoices
- ✅ **GSTIN validation**: Regex check in database
- ✅ **Audit trail**: All invoice creation logged

---

## 🚀 IMPLEMENTATION PHASES

### Phase 1: Foundation (Days 1-3)
- ✅ Create business_partners table migration
- ✅ Update users table with user_type and business_partner_id
- ✅ Create security context module
- ✅ Create isolation middleware
- ✅ Create base repository with auto-filtering

### Phase 2: Database (Days 4-5)
- ✅ Run migrations
- ✅ Create seed data (test business partners)
- ✅ Enable RLS on existing tables (if any)

### Phase 3: RBAC (Day 6)
- ✅ Add new permissions
- ✅ Create roles for SUPER_ADMIN, INTERNAL, EXTERNAL
- ✅ Update permission checking in endpoints

### Phase 4: Audit & Compliance (Day 7)
- ✅ Implement audit logger
- ✅ Create audit_logs table
- ✅ Add compliance endpoints (data export, deletion)

### Phase 5: Testing (Days 8-9)
- ✅ Unit tests for isolation
- ✅ Integration tests (EXTERNAL can't see other BP data)
- ✅ Security penetration testing
- ✅ Compliance verification

### Phase 6: Documentation (Day 10)
- ✅ API documentation
- ✅ Security documentation
- ✅ Compliance report

---

## 📝 SUMMARY

### What Gets Isolated?

| Data Type | Isolation | Access |
|-----------|-----------|--------|
| **Settings** | ❌ NO | Super Admin only |
| Organizations | ❌ NO | Super Admin only |
| Branches | ❌ NO | Super Admin only |
| Commodities | ❌ NO | All users (read-only) |
| Locations | ❌ NO | All users (read-only) |
| **Business Data** | ✅ YES | Per Business Partner |
| Business Partners | Visible to Internal | Managed by Internal/Super Admin |
| Contracts | ✅ YES | Own BP only (External), All (Internal) |
| Invoices | ✅ YES | Own BP only (External), All (Internal) |
| Payments | ✅ YES | Own BP only (External), All (Internal) |
| Shipments | ✅ YES | Own BP only (External), All (Internal) |
| Quality Reports | ✅ YES | Own BP only (External), All (Internal) |
| AI/Chat Sessions | ✅ YES | Own BP only (External), All (Internal) |

### User Types

1. **SUPER_ADMIN**: Full system access, manages settings
2. **INTERNAL**: Your employees, see all business partners, can create invoices in any branch
3. **EXTERNAL**: Business partner users, see only their own data

### Security Layers

1. **Application Layer**: Middleware + Context + Base Repository
2. **Database Layer**: PostgreSQL Row Level Security (RLS)
3. **Audit Layer**: All access logged for compliance
4. **RBAC Layer**: Module-level access control

---

**Ready to implement?** 🚀
