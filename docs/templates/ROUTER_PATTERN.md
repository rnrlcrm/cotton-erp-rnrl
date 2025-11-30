# Router Pattern Template - 2035-Ready Cotton ERP

**Version**: 1.0  
**Date**: 2025-11-30  
**Purpose**: Standard patterns for creating production-ready REST API endpoints

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Required Patterns](#required-patterns)
3. [Code Templates](#code-templates)
4. [Best Practices](#best-practices)
5. [Examples](#examples)

---

## 🚀 Quick Start

Every new router MUST follow these patterns for 15-year maintainability:

### ✅ Required Infrastructure

1. **Idempotency** - Prevent duplicate requests (critical for POST/PUT)
2. **Service Layer** - NO direct DB access in routers
3. **Circuit Breaker** - For all external API calls
4. **Authentication** - JWT via `get_current_user`
5. **Error Handling** - Standardized HTTP exceptions

---

## 📐 Required Patterns

### 1. Idempotency (POST/PUT endpoints)

**Why**: Prevent duplicate transactions from mobile apps, network retries, or user double-clicks.

**How**: Add `Idempotency-Key` header to all state-changing endpoints.

```python
from typing import Optional
from fastapi import Header

@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="""Create new item.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicates.
    - Same key within 24h returns cached response
    - Use UUID or transaction ID
    - Example: `Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000`
    """
)
async def create_item(
    request: ItemCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")  # ✅ ADD THIS
):
    """
    Create new item.
    
    **Idempotency**:
    - Middleware handles deduplication automatically
    - Returns cached response if key seen within 24h
    - No duplicate item created
    """
    service = ItemService(db)
    return await service.create_item(request, current_user.id)
```

**Middleware**: Already active globally in `main.py` - NO code changes needed, just add the header parameter!

---

### 2. Service Layer (NO direct DB queries in routers)

**Why**: Separation of concerns, testability, reusability.

**Bad** ❌:
```python
@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    # ❌ Direct DB queries in router
    total = await db.scalar(select(func.count(Item.id)))
    pending = await db.scalar(select(func.count(Item.id)).where(Item.status == "pending"))
    # ... 15 more queries
    return {"total": total, "pending": pending, ...}
```

**Good** ✅:
```python
@router.get("/dashboard")
async def dashboard(
    analytics: ItemAnalyticsService = Depends(get_item_analytics_service)
):
    # ✅ Clean service layer
    return await analytics.get_dashboard_stats()
```

**Service Layer Structure**:
```
backend/modules/your_module/
├── router.py              # REST endpoints only
├── services.py            # Core business logic
├── services/              # Service subdirectory
│   ├── __init__.py
│   ├── analytics.py       # ✅ Analytics queries
│   ├── documents.py       # ✅ Document management
│   └── notifications.py   # ✅ Notification logic
├── repositories.py        # DB access layer
└── models.py              # SQLAlchemy models
```

---

### 3. Circuit Breaker (External API calls)

**Why**: Prevent cascade failures when third-party APIs are down.

**When to use**:
- GST API verification
- Google Maps geocoding
- SMS/Email gateways
- Payment gateways
- Any HTTP call to external service

**Example**:
```python
from backend.core.resilience.circuit_breaker import api_circuit_breaker

class ExternalService:
    @api_circuit_breaker  # ✅ 3 retries, 60s timeout, exponential backoff
    async def call_external_api(self, param: str):
        """
        Call external API with circuit breaker.
        
        **Circuit Breaker**: Auto-retry on failure (3 attempts).
        If API is down, fail fast to prevent cascade failures.
        """
        # In production: httpx.post('https://external-api.com/verify', ...)
        response = await httpx.post(
            "https://external-api.com/verify",
            json={"param": param},
            timeout=30.0
        )
        return response.json()
```

**Available Decorators**:
- `@api_circuit_breaker` - External APIs (3 retries, 60s timeout)
- `@database_circuit_breaker` - DB calls (3 retries, 30s timeout)
- `@redis_circuit_breaker` - Redis calls (2 retries, 10s timeout)
- `@ai_circuit_breaker` - AI models (2 retries, 120s timeout)

---

### 4. Authentication & Authorization

**Always** use `get_current_user` dependency:

```python
from backend.core.auth.dependencies import get_current_user, require_permissions

@router.post("/items")
async def create_item(
    request: ItemCreateRequest,
    current_user=Depends(get_current_user),  # ✅ JWT validation
    db: AsyncSession = Depends(get_db)
):
    # Extract user context
    user_id = current_user.id
    organization_id = current_user.organization_id
    
    # Validate permissions
    if current_user.user_type != "INTERNAL":
        raise HTTPException(403, "Only internal users can create items")
    
    service = ItemService(db)
    return await service.create_item(request, user_id, organization_id)
```

**RBAC** (Role-Based Access Control):
```python
@router.delete("/items/{item_id}")
@require_permissions(["items:delete"])  # ✅ Check specific permission
async def delete_item(
    item_id: UUID,
    current_user=Depends(get_current_user)
):
    ...
```

---

### 5. Error Handling

**Standard HTTP exceptions**:

```python
from fastapi import HTTPException, status

@router.get("/items/{item_id}")
async def get_item(item_id: UUID, service: ItemService = Depends(...)):
    item = await service.get_item(item_id)
    
    # ✅ Standard 404
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found"
        )
    
    # ✅ Standard 403
    if item.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return item
```

**Domain Errors** (custom exceptions):
```python
from backend.core.errors.exceptions import DomainError

class ItemAlreadyExistsError(DomainError):
    """Raised when item with same code already exists"""
    pass

@router.post("/items")
async def create_item(...):
    try:
        return await service.create_item(request)
    except ItemAlreadyExistsError as e:
        # ✅ Caught by global exception handler
        raise HTTPException(400, str(e))
```

---

## 📝 Code Templates

### Complete Router Template

```python
"""
Item Management REST API

Features:
- JWT authentication via get_current_user
- Idempotency for state-changing operations
- Service layer separation
- Circuit breaker for external APIs
- Complete error handling
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.dependencies import get_current_user, require_permissions
from backend.db.async_session import get_db
from backend.modules.items.schemas import (
    ItemCreateRequest,
    ItemResponse,
    ItemUpdateRequest,
)
from backend.modules.items.services import ItemService
from backend.modules.items.services.analytics import ItemAnalyticsService

router = APIRouter(prefix="/items", tags=["Item Management"])


# ========================================================================
# DEPENDENCIES
# ========================================================================

def get_item_service(db: AsyncSession = Depends(get_db)) -> ItemService:
    """Get ItemService instance"""
    return ItemService(db)


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> ItemAnalyticsService:
    """Get ItemAnalyticsService instance"""
    return ItemAnalyticsService(db)


# ========================================================================
# REST ENDPOINTS
# ========================================================================

@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new item",
    description="""Create new item with idempotency support.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicates.
    - Same key within 24h returns cached response
    - Use UUID or transaction ID
    """
)
async def create_item(
    request: ItemCreateRequest,
    current_user=Depends(get_current_user),
    service: ItemService = Depends(get_item_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create new item.
    
    **Idempotency**: Middleware handles deduplication automatically.
    """
    return await service.create_item(request, current_user.id)


@router.get(
    "",
    response_model=List[ItemResponse],
    summary="List items",
    description="Get all items with optional filters"
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    service: ItemService = Depends(get_item_service),
    current_user=Depends(get_current_user)
):
    """List items with pagination"""
    return await service.list_items(
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        organization_id=current_user.organization_id
    )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID"
)
async def get_item(
    item_id: UUID,
    service: ItemService = Depends(get_item_service),
    current_user=Depends(get_current_user)
):
    """Get single item by ID"""
    item = await service.get_item(item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found"
        )
    
    # Check access
    if item.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return item


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="""Update item with idempotency support.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicate updates.
    """
)
async def update_item(
    item_id: UUID,
    request: ItemUpdateRequest,
    service: ItemService = Depends(get_item_service),
    current_user=Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Update item"""
    return await service.update_item(item_id, request, current_user.id)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item"
)
@require_permissions(["items:delete"])
async def delete_item(
    item_id: UUID,
    service: ItemService = Depends(get_item_service),
    current_user=Depends(get_current_user)
):
    """Delete item (admin only)"""
    await service.delete_item(item_id)
    return None


@router.get(
    "/analytics/dashboard",
    summary="Get dashboard statistics"
)
async def get_dashboard_stats(
    analytics: ItemAnalyticsService = Depends(get_analytics_service),
    current_user=Depends(get_current_user)
):
    """Get analytics dashboard stats"""
    return await analytics.get_dashboard_stats(current_user.organization_id)
```

---

## ✅ Best Practices

### 1. Use Dependency Injection

**Good** ✅:
```python
def get_item_service(db: AsyncSession = Depends(get_db)) -> ItemService:
    return ItemService(db)

@router.post("/items")
async def create_item(service: ItemService = Depends(get_item_service)):
    return await service.create_item(...)
```

**Bad** ❌:
```python
@router.post("/items")
async def create_item(db: AsyncSession = Depends(get_db)):
    service = ItemService(db)  # ❌ Creates new instance every time
    return await service.create_item(...)
```

---

### 2. Document Idempotency in OpenAPI

```python
@router.post(
    "/items",
    description="""Create new item.
    
    **Idempotency**: Supply `Idempotency-Key` header to prevent duplicates.
    - Same key within 24h returns cached response (201 → 200)
    - Use UUID: `Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000`
    - Mobile apps should ALWAYS use this for POST operations
    """
)
```

---

### 3. Separate Analytics from Core CRUD

Create `services/analytics.py` for:
- Dashboard stats
- Export queries
- Reporting
- KPI calculations

```python
# services/analytics.py
class ItemAnalyticsService:
    async def get_dashboard_stats(self, org_id: UUID) -> Dict:
        """Get all dashboard statistics in ONE query"""
        ...
    
    async def get_export_data(self, filters: ItemFilters) -> List[Dict]:
        """Get data for CSV/Excel export"""
        ...
```

---

### 4. Version Your APIs

```python
from backend.api.v1.items import router as items_v1
from backend.api.v2.items import router as items_v2

app.include_router(items_v1, prefix="/api/v1", tags=["Items v1"])
app.include_router(items_v2, prefix="/api/v2", tags=["Items v2"])
```

---

## 📚 Examples

### Example 1: Partner Onboarding Router

**Real implementation**: `backend/modules/partners/router.py`

**Key patterns**:
- ✅ Service layer (`PartnerService`, `ApprovalService`, `PartnerAnalyticsService`)
- ✅ Circuit breaker on GST API (`@api_circuit_breaker`)
- ✅ Event emission (`partner.approved`, `partner.rejected`)
- ✅ RBAC (`require_permissions(["partners:approve"])`)

### Example 2: Availability Engine Router

**Real implementation**: `backend/modules/trade_desk/routes/availability_routes.py`

**Key patterns**:
- ✅ Idempotency on `create_availability` (documented)
- ✅ Service layer (`AvailabilityService`)
- ✅ User context extraction (`get_seller_id_from_user()`)
- ✅ AI enhancements (quality normalization, price anomaly detection)

### Example 3: Requirement Engine Router

**Real implementation**: `backend/modules/trade_desk/routes/requirement_routes.py`

**Key patterns**:
- ✅ Idempotency on `create_requirement` (documented)
- ✅ Service layer (`RequirementService`)
- ✅ WebSocket integration (`ws_service` dependency)
- ✅ 12-step AI pipeline (intent extraction, risk scoring)

---

## 🎓 Team Onboarding Checklist

When creating a new router, ensure:

- [ ] Idempotency header on all POST/PUT endpoints
- [ ] Service layer (NO direct DB queries in router)
- [ ] Circuit breaker on all external API calls
- [ ] Authentication via `get_current_user`
- [ ] RBAC for sensitive operations (`require_permissions`)
- [ ] Standard HTTP exceptions (404, 403, 400, 500)
- [ ] OpenAPI documentation (summary, description)
- [ ] Pagination for list endpoints (skip, limit)
- [ ] Filter parameters as `Query()`
- [ ] Response models for all endpoints
- [ ] Dependency injection for services
- [ ] Analytics queries in separate service

---

## 🔗 Related Documentation

- [Idempotency Middleware](../backend/app/middleware/idempotency.py)
- [Circuit Breaker Patterns](../backend/core/resilience/circuit_breaker.py)
- [Service Layer Example](../backend/modules/partners/services/analytics.py)
- [AI Orchestrator](../backend/ai/orchestrators/base.py)
- [Event Versioning](../backend/core/events/versioning.py)
- [PII Sanitization](../backend/core/logging/pii_filter.py)

---

**Version**: 1.0  
**Last Updated**: 2025-11-30  
**Maintained By**: Cotton ERP Architecture Team
