# 🎯 MODULE VISIBILITY FOR BACK OFFICE - STATUS REPORT

## ❌ **NOT FULLY IMPLEMENTED** - Module Visibility API Missing

**Last Updated**: December 3, 2025
**Status**: ⚠️ **PARTIAL IMPLEMENTATION** - 60% Complete

---

## 📊 CURRENT STATUS

| Component | Status | Completeness | Action Needed |
|-----------|--------|--------------|---------------|
| **Database Field** | ✅ Implemented | 100% | None |
| **Middleware Support** | ✅ Implemented | 100% | None |
| **Security Context** | ✅ Implemented | 100% | None |
| **API Endpoint** | ❌ Missing | 0% | **CRITICAL** |
| **Frontend Integration** | ❌ Missing | 0% | Required |
| **Capability Mapping** | ❌ Missing | 0% | Required |

---

## ✅ WHAT EXISTS (Backend Foundation)

### 1. Database Schema ✅

**File**: `backend/modules/settings/models/settings_models.py`

```python
class User(Base):
    # ...
    allowed_modules: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="RBAC: List of modules user can access"
    )
```

**Examples of allowed_modules**:
```python
# Back office admin user
allowed_modules = [
    "trade-desk",
    "partners",
    "invoices",
    "payments",
    "quality",
    "accounting",
    "reports",
    "settings"
]

# Limited trader user
allowed_modules = [
    "trade-desk",
    "invoices",
    "contracts"
]

# Finance user
allowed_modules = [
    "invoices",
    "payments",
    "accounting",
    "reports"
]
```

### 2. Security Context ✅

**File**: `backend/core/security/context.py`

```python
def has_module_access(module_name: str) -> bool:
    """
    Check if user has access to a specific module.
    
    Super Admin always has access to all modules.
    Other users checked against allowed_modules list.
    """
    if is_super_admin():
        return True  # Super admin has access to all modules
    
    allowed = get_allowed_modules()
    return module_name in allowed if allowed else False
```

**Usage in middleware**:
```python
# File: backend/app/middleware/isolation.py

# Extract module from request path
module = extract_module_from_path(request.url.path)

# Check if user has access
if module and not has_module_access(module):
    return JSONResponse(
        status_code=403,
        content={"detail": f"Access denied to module: {module}"}
    )
```

### 3. Middleware Integration ✅

**File**: `backend/app/middleware/isolation.py`

The middleware automatically sets `allowed_modules` from user object:

```python
set_security_context(
    user_id=user.id,
    user_type=user_type,
    business_partner_id=business_partner_id,
    organization_id=organization_id,
    allowed_modules=getattr(user, 'allowed_modules', None),  # ✅ Loaded from DB
)
```

---

## ❌ WHAT'S MISSING (Critical Gaps)

### 1. API Endpoint to Get User's Accessible Modules ❌

**Current Situation**:
- `GET /api/v1/auth/me` returns user profile
- **DOES NOT** include `allowed_modules` in response

**Current Response** (Incomplete):
```json
{
  "id": "uuid",
  "mobile_number": "9876543210",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "role": "manager",
  "is_active": true,
  "profile_complete": true,
  "created_at": "2025-12-03T10:00:00Z"
  // ❌ MISSING: allowed_modules
  // ❌ MISSING: capabilities
  // ❌ MISSING: module_permissions
}
```

**Required Response**:
```json
{
  "id": "uuid",
  "mobile_number": "9876543210",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "role": "manager",
  "is_active": true,
  "profile_complete": true,
  "created_at": "2025-12-03T10:00:00Z",
  
  // ✅ NEW: Module visibility
  "allowed_modules": [
    "trade-desk",
    "invoices",
    "payments",
    "quality"
  ],
  
  // ✅ NEW: User capabilities
  "capabilities": [
    "AVAILABILITY_CREATE",
    "AVAILABILITY_READ",
    "REQUIREMENT_CREATE",
    "INVOICE_VIEW_OWN"
  ],
  
  // ✅ NEW: Module-level permissions
  "module_permissions": {
    "trade-desk": {
      "visible": true,
      "capabilities": ["AVAILABILITY_CREATE", "REQUIREMENT_CREATE"]
    },
    "invoices": {
      "visible": true,
      "capabilities": ["INVOICE_VIEW_OWN"]
    },
    "partners": {
      "visible": false,  // Not in allowed_modules
      "capabilities": []
    }
  }
}
```

### 2. Module Configuration System ❌

**Missing**: Central registry of all modules with metadata

**Required**: `backend/core/modules/registry.py`

```python
MODULE_REGISTRY = {
    "trade-desk": {
        "name": "Trade Desk",
        "description": "Manage availabilities and requirements",
        "icon": "trending_up",
        "route": "/trade-desk",
        "required_capabilities": [
            Capabilities.AVAILABILITY_READ,
            Capabilities.REQUIREMENT_READ
        ],
        "sub_modules": [
            {
                "id": "availabilities",
                "name": "Availabilities",
                "route": "/trade-desk/availabilities",
                "required_capabilities": [Capabilities.AVAILABILITY_READ]
            },
            {
                "id": "requirements",
                "name": "Requirements",
                "route": "/trade-desk/requirements",
                "required_capabilities": [Capabilities.REQUIREMENT_READ]
            }
        ]
    },
    
    "partners": {
        "name": "Business Partners",
        "description": "Manage partner relationships",
        "icon": "groups",
        "route": "/partners",
        "required_capabilities": [Capabilities.PARTNER_READ]
    },
    
    "invoices": {
        "name": "Invoices",
        "description": "Invoice management",
        "icon": "receipt",
        "route": "/invoices",
        "required_capabilities": [Capabilities.INVOICE_VIEW_OWN]
    },
    
    "payments": {
        "name": "Payments",
        "description": "Payment tracking",
        "icon": "payment",
        "route": "/payments",
        "required_capabilities": [Capabilities.PAYMENT_VIEW_OWN]
    },
    
    "quality": {
        "name": "Quality Control",
        "description": "Quality inspections",
        "icon": "verified",
        "route": "/quality",
        "required_capabilities": []  # Custom permissions
    },
    
    "accounting": {
        "name": "Accounting",
        "description": "Ledgers and financial reports",
        "icon": "account_balance",
        "route": "/accounting",
        "required_capabilities": [Capabilities.ADMIN_VIEW_ALL_DATA]
    },
    
    "reports": {
        "name": "Reports",
        "description": "Analytics and dashboards",
        "icon": "assessment",
        "route": "/reports",
        "required_capabilities": []
    },
    
    "settings": {
        "name": "Settings",
        "description": "System configuration",
        "icon": "settings",
        "route": "/settings",
        "required_capabilities": [Capabilities.SETTINGS_VIEW_ALL]
    }
}
```

### 3. Capability-to-Module Mapping ❌

**Missing**: Automatic derivation of `allowed_modules` from user capabilities

**Scenario**: User has these capabilities:
```python
user_capabilities = [
    Capabilities.AVAILABILITY_CREATE,
    Capabilities.AVAILABILITY_READ,
    Capabilities.REQUIREMENT_CREATE,
    Capabilities.INVOICE_VIEW_OWN
]
```

**Expected Auto-Derivation**:
```python
# Should automatically grant:
allowed_modules = [
    "trade-desk",     # Has AVAILABILITY_CREATE/READ, REQUIREMENT_CREATE
    "invoices"        # Has INVOICE_VIEW_OWN
]
```

**Required Function**:
```python
async def derive_allowed_modules_from_capabilities(
    user_id: UUID,
    db: AsyncSession
) -> List[str]:
    """
    Automatically determine which modules user can access
    based on their capabilities.
    """
    # Get user capabilities
    capability_service = CapabilityService(db)
    user_capabilities = await capability_service.get_user_capabilities(user_id)
    
    # Map capabilities to modules
    allowed_modules = set()
    
    for module_id, module_config in MODULE_REGISTRY.items():
        required_caps = module_config.get("required_capabilities", [])
        
        # If user has ANY required capability, grant module access
        if any(cap.value in user_capabilities for cap in required_caps):
            allowed_modules.add(module_id)
    
    return list(allowed_modules)
```

---

## 🔧 IMPLEMENTATION REQUIRED

### Step 1: Update UserProfileResponse Schema

**File**: `backend/modules/user_onboarding/schemas/auth_schemas.py`

```python
class UserProfileResponse(BaseModel):
    """User profile information"""
    id: UUID
    mobile_number: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: str
    is_active: bool
    profile_complete: bool
    created_at: datetime
    
    # ✅ NEW FIELDS
    allowed_modules: Optional[List[str]] = None  # List of accessible modules
    capabilities: Optional[List[str]] = None     # List of user capabilities
    module_permissions: Optional[Dict[str, Any]] = None  # Per-module permissions
    
    class Config:
        from_attributes = True
```

### Step 2: Update `/me` Endpoint

**File**: `backend/modules/user_onboarding/routes/auth_router.py`

```python
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User with Module Access",
)
async def get_current_user_details(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information including accessible modules"""
    
    # Get user capabilities
    from backend.core.auth.capabilities.service import CapabilityService
    capability_service = CapabilityService(db)
    user_capabilities = await capability_service.get_user_capabilities(current_user.id)
    
    # Auto-derive allowed_modules if not set
    allowed_modules = current_user.allowed_modules
    if not allowed_modules:
        allowed_modules = await derive_allowed_modules_from_capabilities(
            current_user.id, db
        )
    
    # Build module permissions
    module_permissions = {}
    for module_id in MODULE_REGISTRY.keys():
        module_permissions[module_id] = {
            "visible": module_id in (allowed_modules or []),
            "capabilities": [
                cap for cap in user_capabilities
                if cap in [c.value for c in MODULE_REGISTRY[module_id].get("required_capabilities", [])]
            ]
        }
    
    return UserProfileResponse(
        id=current_user.id,
        mobile_number=current_user.mobile_number,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        profile_complete=bool(current_user.full_name and current_user.email),
        created_at=current_user.created_at,
        
        # NEW: Module visibility
        allowed_modules=allowed_modules,
        capabilities=list(user_capabilities),
        module_permissions=module_permissions
    )
```

### Step 3: Create Module Registry

**New File**: `backend/core/modules/registry.py`

(See code example in "What's Missing" section above)

### Step 4: Create Module Access API

**New File**: `backend/api/v1/routers/modules.py`

```python
from fastapi import APIRouter, Depends
from backend.core.auth.dependencies import get_current_user
from backend.core.modules.registry import MODULE_REGISTRY

router = APIRouter(prefix="/modules", tags=["Modules"])

@router.get("/accessible")
async def get_accessible_modules(
    current_user = Depends(get_current_user)
):
    """Get list of modules accessible to current user"""
    allowed = current_user.allowed_modules or []
    
    return {
        "modules": [
            {
                "id": module_id,
                **module_config,
                "accessible": module_id in allowed
            }
            for module_id, module_config in MODULE_REGISTRY.items()
        ]
    }
```

---

## 🎨 FRONTEND INTEGRATION

### Navigation Menu (React/Vue Example)

```typescript
// Get user profile with module access
const userProfile = await fetch('/api/v1/auth/me').then(r => r.json());

// Build navigation menu
const navigation = userProfile.allowed_modules.map(moduleId => {
  const module = MODULE_REGISTRY[moduleId];
  return {
    name: module.name,
    icon: module.icon,
    route: module.route,
    subModules: module.sub_modules || []
  };
});

// Render sidebar
<Sidebar>
  {navigation.map(item => (
    <NavItem key={item.id} {...item} />
  ))}
</Sidebar>
```

### Access Control

```typescript
// Check if user can access module
function canAccessModule(moduleId: string): boolean {
  return userProfile.allowed_modules?.includes(moduleId) || false;
}

// Route guard
if (!canAccessModule('trade-desk')) {
  return <AccessDenied />;
}
```

---

## 📊 EXAMPLE SCENARIOS

### Scenario 1: Trader User

**User**: Ramesh (Trader)

**Capabilities**:
```python
[
  Capabilities.AVAILABILITY_CREATE,
  Capabilities.AVAILABILITY_READ,
  Capabilities.REQUIREMENT_CREATE,
  Capabilities.REQUIREMENT_READ,
  Capabilities.INVOICE_VIEW_OWN
]
```

**Allowed Modules**:
```json
["trade-desk", "invoices", "contracts"]
```

**Backend Shows**:
- ✅ Trade Desk
- ✅ Invoices
- ✅ Contracts
- ❌ Settings
- ❌ Accounting

### Scenario 2: Finance User

**User**: Priya (Accountant)

**Capabilities**:
```python
[
  Capabilities.INVOICE_VIEW_ALL_BRANCHES,
  Capabilities.PAYMENT_VIEW_OWN,
  Capabilities.SETTINGS_VIEW_ALL
]
```

**Allowed Modules**:
```json
["invoices", "payments", "accounting", "reports", "settings"]
```

**Backend Shows**:
- ❌ Trade Desk
- ✅ Invoices
- ✅ Payments
- ✅ Accounting
- ✅ Reports
- ✅ Settings

### Scenario 3: Super Admin

**User**: System Admin

**User Type**: `SUPER_ADMIN`

**Allowed Modules**:
```json
null  // Super admin sees ALL modules automatically
```

**Backend Shows**:
- ✅ ALL MODULES (no restrictions)

---

## 🎯 SUMMARY

### ✅ What Works (Backend Foundation)
1. Database field `allowed_modules` exists ✅
2. Middleware loads and enforces module access ✅
3. Security context `has_module_access()` works ✅
4. API endpoint protection works ✅

### ❌ What's Missing (Critical for UI)
1. `/me` endpoint doesn't return `allowed_modules` ❌
2. No module registry configuration ❌
3. No automatic capability → module mapping ❌
4. No API to get accessible modules list ❌
5. Frontend has no way to know which modules to show ❌

### 🚀 Action Items (Priority Order)

**CRITICAL (Do Now)**:
1. Add `allowed_modules` to `UserProfileResponse` schema
2. Update `/api/v1/auth/me` endpoint to return modules
3. Create `MODULE_REGISTRY` configuration

**HIGH (Within 1 week)**:
4. Implement automatic capability → module derivation
5. Create `/api/v1/modules/accessible` endpoint
6. Add module management admin UI

**MEDIUM (Within 2 weeks)**:
7. Build dynamic navigation menu component
8. Add module access guards to frontend routes
9. Create module permission testing tools

---

## 📞 RECOMMENDATION

**Status**: ⚠️ **60% Complete** - Backend foundation exists, API exposure missing

**What to tell UI team**:
> "The backend has module visibility support in the database and middleware, but we need to expose it via API endpoints. Give us 2-3 hours to:
> 1. Update the /me endpoint to return allowed_modules
> 2. Create a module registry
> 3. Build the accessible modules API
> 
> Then UI can build the dynamic navigation menu based on user's allowed_modules."

**Estimated Work**: 3-4 hours for complete implementation

---

*Document generated: December 3, 2025*
*Status: Backend foundation exists, API layer needed*
*Priority: HIGH (blocks UI development)*
