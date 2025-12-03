# 🚨 MODULE VISIBILITY - COMPLETE ANALYSIS FOR MOBILE + BACK OFFICE

## ❌ **CRITICAL: NOT IMPLEMENTED FOR EITHER MOBILE OR BACK OFFICE**

**Last Updated**: December 3, 2025
**Status**: ⚠️ **0% IMPLEMENTED** - Module/Screen visibility logic missing for BOTH platforms

---

## 📊 EXECUTIVE SUMMARY

| Platform | Infrastructure | API Exposure | UI Implementation | Overall Status |
|----------|----------------|--------------|-------------------|----------------|
| **Mobile App** | 60% (entity_class field exists) | 0% ❌ | 0% ❌ (navigation files empty) | **NOT READY** |
| **Back Office** | 95% (allowed_modules exists) | 0% ❌ | 0% ❌ (no module registry) | **NOT READY** |

### Critical Findings

1. **Mobile Users**: System has `entity_class` and `capabilities` in database, but:
   - `/me` endpoint doesn't return `business_partner_id`
   - No API to get partner's `entity_class` (farmer, trader, mill, ginner, etc.)
   - No screen configuration based on entity type
   - Navigation files are completely empty

2. **Back Office Users**: System has `allowed_modules` field, but:
   - `/me` endpoint doesn't return `allowed_modules`
   - No module registry (which modules exist in system)
   - No capability → module mapping
   - No API to get accessible modules list

---

## 🔍 PART 1: MOBILE APP USER VISIBILITY

### Current System Design

**User Model**:
```python
class User(Base):
    id: UUID
    user_type: str  # SUPER_ADMIN, INTERNAL, EXTERNAL
    
    # For EXTERNAL users (mobile app users)
    business_partner_id: UUID | None  # Points to BusinessPartner
    
    # For INTERNAL users (back office staff)
    organization_id: UUID | None
    allowed_modules: list[str] | None
```

**BusinessPartner Model**:
```python
class BusinessPartner(Base):
    id: UUID
    
    # NEW: Capability-Driven Partner System (CDPS)
    entity_class: str  # "business_entity" or "service_provider"
    
    business_entity_type: str  # For trading entities
    # Examples: 
    # - Farmers (proprietorship)
    # - Mills (private_limited)
    # - Ginners (partnership)
    # - Traders (llp, corporation)
    
    service_provider_type: str  # For non-trading service providers
    # Examples:
    # - Brokers
    # - Transporters
    # - Controllers
    # - Financers
    
    capabilities: JSON  # Trading capabilities
    # {
    #   "domestic_buy_india": true,
    #   "domestic_sell_india": true,
    #   "import_allowed": false,
    #   "export_allowed": false
    # }
```

### What Mobile Users Should See

Different screens for different partner types:

#### 1. **Farmers** (Sellers Only)
**entity_class**: `business_entity`
**capabilities**: `{"domestic_sell_india": true}`

**Screens**:
- ✅ Dashboard (sales overview)
- ✅ Post Availability (sell cotton)
- ✅ My Listings
- ✅ Incoming Orders
- ✅ Invoices (sales invoices)
- ✅ Payments Received
- ❌ Requirements (can't buy)
- ❌ Purchase Orders
- ❌ Quality Inspections (unless also quality provider)

#### 2. **Mills** (Buyers + Sellers)
**entity_class**: `business_entity`
**capabilities**: `{"domestic_buy_india": true, "domestic_sell_india": true}`

**Screens**:
- ✅ Dashboard (comprehensive)
- ✅ Post Requirement (buy raw cotton)
- ✅ Post Availability (sell processed cotton/yarn)
- ✅ My Requirements
- ✅ My Availabilities
- ✅ Purchase Orders
- ✅ Sales Orders
- ✅ Invoices (both buy/sell)
- ✅ Payments (both receivable/payable)
- ✅ Quality Inspections (for purchases)

#### 3. **Ginners** (Buyers + Processors + Sellers)
**entity_class**: `business_entity`
**capabilities**: `{"domestic_buy_india": true, "domestic_sell_india": true}`

**Screens**:
- ✅ Dashboard
- ✅ Post Requirement (buy raw cotton)
- ✅ Post Availability (sell ginned cotton)
- ✅ My Requirements
- ✅ My Availabilities
- ✅ Purchase Orders
- ✅ Sales Orders
- ✅ Processing Status (ginning process)
- ✅ Invoices
- ✅ Payments
- ✅ Quality Inspections

#### 4. **Traders** (Pure Buy-Sell)
**entity_class**: `business_entity`
**capabilities**: `{"domestic_buy_india": true, "domestic_sell_india": true}`

**Screens**:
- ✅ Dashboard (trading margins, volumes)
- ✅ Post Requirement
- ✅ Post Availability
- ✅ My Requirements
- ✅ My Availabilities
- ✅ Active Trades
- ✅ Trade Matching
- ✅ Purchase Orders
- ✅ Sales Orders
- ✅ Invoices
- ✅ Payments
- ✅ Market Trends (price analysis)

#### 5. **Brokers** (Service Providers - No Trading)
**entity_class**: `service_provider`
**service_provider_type**: `broker`

**Screens**:
- ✅ Dashboard (commission overview)
- ✅ Active Deals
- ✅ Commission Tracker
- ✅ Buyer Connections
- ✅ Seller Connections
- ✅ Match Facilitation
- ✅ Invoices (for commission)
- ❌ Post Requirement (can't trade)
- ❌ Post Availability (can't trade)
- ❌ Purchase Orders (not a buyer)

#### 6. **Transporters** (Service Providers)
**entity_class**: `service_provider`
**service_provider_type**: `transporter`

**Screens**:
- ✅ Dashboard (trips, earnings)
- ✅ Trip Requests
- ✅ Active Trips
- ✅ Vehicle Management
- ✅ Driver Management
- ✅ Trip History
- ✅ Invoices (freight bills)
- ✅ Payments
- ❌ Trading screens (can't trade)

---

## ❌ WHAT'S MISSING FOR MOBILE

### 1. User Profile API Missing Partner Info

**Current `/me` Response**:
```json
{
  "id": "uuid",
  "mobile_number": "9876543210",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "role": "partner_user",
  "is_active": true,
  "profile_complete": true,
  "created_at": "2025-12-03T10:00:00Z"
  
  // ❌ MISSING: business_partner_id
  // ❌ MISSING: partner info (entity_class, capabilities)
}
```

**Required Response**:
```json
{
  "id": "uuid",
  "mobile_number": "9876543210",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "role": "partner_user",
  "user_type": "EXTERNAL",
  "is_active": true,
  "profile_complete": true,
  "created_at": "2025-12-03T10:00:00Z",
  
  // ✅ NEW: Partner context for mobile users
  "business_partner": {
    "id": "partner-uuid",
    "legal_name": "Ramesh Cotton Mills Pvt Ltd",
    "trade_name": "Ramesh Mills",
    "entity_class": "business_entity",
    "business_entity_type": "private_limited",
    "capabilities": {
      "domestic_buy_india": true,
      "domestic_sell_india": true,
      "import_allowed": false,
      "export_allowed": false
    },
    "can_buy": true,
    "can_sell": true,
    "partner_category": "mill"  // Derived: farmer, mill, ginner, trader
  }
}
```

### 2. Screen Configuration System Missing

**Required**: `backend/core/mobile/screen_registry.py`

```python
from backend.core.auth.capabilities.definitions import Capabilities

MOBILE_SCREEN_REGISTRY = {
    # ============================================
    # BUSINESS ENTITIES (Can Trade)
    # ============================================
    
    "farmer": {
        "entity_class": "business_entity",
        "description": "Farmers selling raw cotton",
        "capabilities": {
            "domestic_sell_india": True,  # Can sell
            "domestic_buy_india": False   # Cannot buy
        },
        "screens": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "icon": "home",
                "route": "/dashboard",
                "visible": True
            },
            {
                "id": "post_availability",
                "title": "Sell Cotton",
                "icon": "add_circle",
                "route": "/availability/create",
                "visible": True,
                "required_capabilities": [Capabilities.AVAILABILITY_CREATE]
            },
            {
                "id": "my_availabilities",
                "title": "My Listings",
                "icon": "list",
                "route": "/availabilities",
                "visible": True
            },
            {
                "id": "incoming_orders",
                "title": "Orders",
                "icon": "shopping_bag",
                "route": "/orders/sales",
                "visible": True
            },
            {
                "id": "invoices",
                "title": "Invoices",
                "icon": "receipt",
                "route": "/invoices",
                "visible": True
            },
            {
                "id": "payments",
                "title": "Payments",
                "icon": "payment",
                "route": "/payments",
                "visible": True
            }
        ]
    },
    
    "mill": {
        "entity_class": "business_entity",
        "description": "Cotton mills - buy raw cotton, sell processed cotton/yarn",
        "capabilities": {
            "domestic_buy_india": True,
            "domestic_sell_india": True
        },
        "screens": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "icon": "home",
                "route": "/dashboard",
                "visible": True
            },
            {
                "id": "post_requirement",
                "title": "Buy Cotton",
                "icon": "add_shopping_cart",
                "route": "/requirement/create",
                "visible": True,
                "required_capabilities": [Capabilities.REQUIREMENT_CREATE]
            },
            {
                "id": "post_availability",
                "title": "Sell Products",
                "icon": "add_circle",
                "route": "/availability/create",
                "visible": True,
                "required_capabilities": [Capabilities.AVAILABILITY_CREATE]
            },
            {
                "id": "my_requirements",
                "title": "My Requirements",
                "icon": "list",
                "route": "/requirements",
                "visible": True
            },
            {
                "id": "my_availabilities",
                "title": "My Listings",
                "icon": "inventory",
                "route": "/availabilities",
                "visible": True
            },
            {
                "id": "purchase_orders",
                "title": "Purchase Orders",
                "icon": "shopping_cart",
                "route": "/orders/purchase",
                "visible": True
            },
            {
                "id": "sales_orders",
                "title": "Sales Orders",
                "icon": "shopping_bag",
                "route": "/orders/sales",
                "visible": True
            },
            {
                "id": "quality_inspections",
                "title": "Quality Control",
                "icon": "verified",
                "route": "/quality",
                "visible": True
            },
            {
                "id": "invoices",
                "title": "Invoices",
                "icon": "receipt",
                "route": "/invoices",
                "visible": True
            },
            {
                "id": "payments",
                "title": "Payments",
                "icon": "payment",
                "route": "/payments",
                "visible": True
            }
        ]
    },
    
    "ginner": {
        "entity_class": "business_entity",
        "description": "Cotton ginners - buy raw cotton, process, sell ginned cotton",
        "capabilities": {
            "domestic_buy_india": True,
            "domestic_sell_india": True
        },
        "screens": [
            # Same as mill + processing screens
            {
                "id": "processing_status",
                "title": "Ginning Status",
                "icon": "manufacturing",
                "route": "/processing",
                "visible": True
            }
        ]
    },
    
    "trader": {
        "entity_class": "business_entity",
        "description": "Cotton traders - pure buy and sell",
        "capabilities": {
            "domestic_buy_india": True,
            "domestic_sell_india": True
        },
        "screens": [
            # Full trading screens
            {
                "id": "market_trends",
                "title": "Market Trends",
                "icon": "trending_up",
                "route": "/market",
                "visible": True
            },
            {
                "id": "trade_matching",
                "title": "Smart Matching",
                "icon": "compare_arrows",
                "route": "/matching",
                "visible": True
            }
        ]
    },
    
    # ============================================
    # SERVICE PROVIDERS (Cannot Trade)
    # ============================================
    
    "broker": {
        "entity_class": "service_provider",
        "service_provider_type": "broker",
        "description": "Brokers facilitating trades",
        "capabilities": {},  # No trading capabilities
        "screens": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "icon": "home",
                "route": "/dashboard",
                "visible": True
            },
            {
                "id": "active_deals",
                "title": "Active Deals",
                "icon": "handshake",
                "route": "/deals",
                "visible": True
            },
            {
                "id": "commission_tracker",
                "title": "Commission",
                "icon": "account_balance_wallet",
                "route": "/commission",
                "visible": True
            },
            {
                "id": "buyer_connections",
                "title": "Buyers",
                "icon": "people",
                "route": "/connections/buyers",
                "visible": True
            },
            {
                "id": "seller_connections",
                "title": "Sellers",
                "icon": "store",
                "route": "/connections/sellers",
                "visible": True
            },
            {
                "id": "invoices",
                "title": "Invoices",
                "icon": "receipt",
                "route": "/invoices",
                "visible": True
            }
        ]
    },
    
    "transporter": {
        "entity_class": "service_provider",
        "service_provider_type": "transporter",
        "description": "Transporters for logistics",
        "capabilities": {},
        "screens": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "icon": "home",
                "route": "/dashboard",
                "visible": True
            },
            {
                "id": "trip_requests",
                "title": "Trip Requests",
                "icon": "local_shipping",
                "route": "/trips/requests",
                "visible": True
            },
            {
                "id": "active_trips",
                "title": "Active Trips",
                "icon": "directions_car",
                "route": "/trips/active",
                "visible": True
            },
            {
                "id": "vehicle_management",
                "title": "Vehicles",
                "icon": "airport_shuttle",
                "route": "/vehicles",
                "visible": True
            },
            {
                "id": "trip_history",
                "title": "Trip History",
                "icon": "history",
                "route": "/trips/history",
                "visible": True
            },
            {
                "id": "invoices",
                "title": "Freight Bills",
                "icon": "receipt",
                "route": "/invoices",
                "visible": True
            }
        ]
    }
}


def derive_partner_category(partner: BusinessPartner) -> str:
    """
    Automatically determine partner category from business entity type
    and capabilities.
    
    Examples:
    - Farmer: business_entity + can_sell_only
    - Mill: business_entity + can_buy_and_sell + "mill" in name
    - Ginner: business_entity + can_buy_and_sell + "ginner" in name
    - Trader: business_entity + can_buy_and_sell + no processing
    - Broker: service_provider + type=broker
    """
    if partner.entity_class == "service_provider":
        return partner.service_provider_type  # broker, transporter, etc.
    
    # Business entities - derive from capabilities and name
    caps = partner.capabilities or {}
    can_buy = caps.get("domestic_buy_india", False)
    can_sell = caps.get("domestic_sell_india", False)
    
    name_lower = (partner.legal_name or "").lower()
    
    if "mill" in name_lower:
        return "mill"
    elif "ginn" in name_lower:
        return "ginner"
    elif can_buy and can_sell:
        return "trader"
    elif can_sell and not can_buy:
        return "farmer"
    elif can_buy and not can_sell:
        return "buyer"
    
    return "trader"  # Default
```

### 3. Mobile API Endpoint Missing

**Required**: `GET /api/v1/mobile/screens`

```python
@router.get("/screens")
async def get_accessible_screens(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of screens mobile user can access based on their
    partner entity type and capabilities.
    """
    if current_user.user_type != "EXTERNAL":
        raise HTTPException(400, "This endpoint is for mobile users only")
    
    if not current_user.business_partner_id:
        raise HTTPException(400, "User not linked to business partner")
    
    # Get partner
    partner = await db.get(BusinessPartner, current_user.business_partner_id)
    
    # Derive category
    category = derive_partner_category(partner)
    
    # Get screen config
    screen_config = MOBILE_SCREEN_REGISTRY.get(category, {})
    
    # Get user capabilities
    capability_service = CapabilityService(db)
    user_capabilities = await capability_service.get_user_capabilities(current_user.id)
    
    # Filter screens by capabilities
    accessible_screens = []
    for screen in screen_config.get("screens", []):
        required_caps = screen.get("required_capabilities", [])
        
        # If no caps required, or user has all required caps
        if not required_caps or all(cap.value in user_capabilities for cap in required_caps):
            accessible_screens.append(screen)
    
    return {
        "partner_category": category,
        "entity_class": partner.entity_class,
        "capabilities": partner.capabilities,
        "screens": accessible_screens
    }
```

---

## 🔍 PART 2: BACK OFFICE USER VISIBILITY

### What Back Office Staff Should See

Different modules for different roles:

#### 1. **Super Admin**
**User Type**: `SUPER_ADMIN`

**Modules**:
- ✅ ALL MODULES (no restrictions)

#### 2. **Trade Desk Manager**
**User Type**: `INTERNAL`
**allowed_modules**: `["trade-desk", "partners", "invoices", "reports"]`

**Modules**:
- ✅ Trade Desk (availabilities, requirements, matching)
- ✅ Partners (view all partners)
- ✅ Invoices (trade-related)
- ✅ Reports (trade analytics)
- ❌ Accounting (finance-only)
- ❌ Settings (admin-only)

#### 3. **Finance Manager**
**User Type**: `INTERNAL`
**allowed_modules**: `["invoices", "payments", "accounting", "reports", "settings"]`

**Modules**:
- ✅ Invoices (all invoices)
- ✅ Payments (payment tracking)
- ✅ Accounting (ledgers, reconciliation)
- ✅ Reports (financial reports)
- ✅ Settings (financial settings)
- ❌ Trade Desk (operations-only)
- ❌ Quality (QC-only)

#### 4. **Quality Inspector**
**User Type**: `INTERNAL`
**allowed_modules**: `["quality", "trade-desk", "reports"]`

**Modules**:
- ✅ Quality (inspections, reports)
- ✅ Trade Desk (view trades for inspection)
- ✅ Reports (quality metrics)
- ❌ Accounting
- ❌ Settings

---

## ❌ WHAT'S MISSING FOR BACK OFFICE

(Same as MODULE_VISIBILITY_STATUS.md - already documented)

1. `/me` endpoint doesn't return `allowed_modules`
2. No module registry configuration
3. No capability → module mapping
4. No `/api/v1/modules/accessible` endpoint

---

## 🎯 COMPLETE IMPLEMENTATION PLAN

### Phase 1: Mobile User Visibility (3-4 hours)

#### Step 1.1: Update UserProfileResponse for Mobile Users

**File**: `backend/modules/user_onboarding/schemas/auth_schemas.py`

```python
class PartnerInfo(BaseModel):
    """Business partner information for mobile users"""
    id: UUID
    legal_name: str
    trade_name: Optional[str] = None
    entity_class: str  # business_entity or service_provider
    business_entity_type: Optional[str] = None
    service_provider_type: Optional[str] = None
    capabilities: Dict[str, bool]
    can_buy: bool
    can_sell: bool
    partner_category: str  # farmer, mill, ginner, trader, broker, transporter


class UserProfileResponse(BaseModel):
    """User profile information"""
    id: UUID
    mobile_number: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: str
    user_type: str  # SUPER_ADMIN, INTERNAL, EXTERNAL
    is_active: bool
    profile_complete: bool
    created_at: datetime
    
    # For EXTERNAL users (mobile)
    business_partner: Optional[PartnerInfo] = None
    
    # For INTERNAL users (back office)
    organization_id: Optional[UUID] = None
    allowed_modules: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    
    class Config:
        from_attributes = True
```

#### Step 1.2: Update `/me` Endpoint for Mobile

**File**: `backend/modules/user_onboarding/routes/auth_router.py`

```python
@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_details(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information with partner/module context"""
    
    partner_info = None
    allowed_modules = None
    user_capabilities = []
    
    # For EXTERNAL users (mobile) - include partner info
    if current_user.user_type == "EXTERNAL" and current_user.business_partner_id:
        partner = await db.get(BusinessPartner, current_user.business_partner_id)
        
        if partner:
            from backend.core.mobile.screen_registry import derive_partner_category
            
            capabilities = partner.capabilities or {}
            partner_info = PartnerInfo(
                id=partner.id,
                legal_name=partner.legal_name,
                trade_name=partner.trade_name,
                entity_class=partner.entity_class,
                business_entity_type=partner.business_entity_type,
                service_provider_type=partner.service_provider_type,
                capabilities=capabilities,
                can_buy=capabilities.get("domestic_buy_india", False),
                can_sell=capabilities.get("domestic_sell_india", False),
                partner_category=derive_partner_category(partner)
            )
    
    # For INTERNAL users (back office) - include modules and capabilities
    if current_user.user_type in ["INTERNAL", "SUPER_ADMIN"]:
        from backend.core.auth.capabilities.service import CapabilityService
        
        capability_service = CapabilityService(db)
        user_capabilities = await capability_service.get_user_capabilities(current_user.id)
        
        allowed_modules = current_user.allowed_modules
        if not allowed_modules and current_user.user_type != "SUPER_ADMIN":
            # Auto-derive from capabilities
            from backend.core.modules.registry import derive_allowed_modules_from_capabilities
            allowed_modules = await derive_allowed_modules_from_capabilities(
                current_user.id, db
            )
    
    return UserProfileResponse(
        id=current_user.id,
        mobile_number=current_user.mobile_number,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        profile_complete=bool(current_user.full_name and current_user.email),
        created_at=current_user.created_at,
        
        # Mobile context
        business_partner=partner_info,
        
        # Back office context
        organization_id=current_user.organization_id,
        allowed_modules=allowed_modules,
        capabilities=list(user_capabilities)
    )
```

#### Step 1.3: Create Mobile Screen Registry

**New File**: `backend/core/mobile/screen_registry.py`

(See code example above in "What's Missing for Mobile" section)

#### Step 1.4: Create Mobile Screens API

**New File**: `backend/api/v1/routers/mobile_screens.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.auth.dependencies import get_current_user
from backend.modules.partners.models import BusinessPartner
from backend.core.mobile.screen_registry import MOBILE_SCREEN_REGISTRY, derive_partner_category
from backend.core.auth.capabilities.service import CapabilityService

router = APIRouter(prefix="/mobile/screens", tags=["Mobile"])


@router.get("/accessible")
async def get_accessible_screens(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get screens accessible to mobile user based on partner type"""
    
    if current_user.user_type != "EXTERNAL":
        raise HTTPException(400, "This endpoint is for mobile users only")
    
    if not current_user.business_partner_id:
        raise HTTPException(400, "User not linked to business partner")
    
    # Get partner
    partner = await db.get(BusinessPartner, current_user.business_partner_id)
    if not partner:
        raise HTTPException(404, "Business partner not found")
    
    # Derive category
    category = derive_partner_category(partner)
    
    # Get screen config
    screen_config = MOBILE_SCREEN_REGISTRY.get(category, {})
    
    # Get user capabilities
    capability_service = CapabilityService(db)
    user_capabilities = await capability_service.get_user_capabilities(current_user.id)
    
    # Filter screens by capabilities
    accessible_screens = []
    for screen in screen_config.get("screens", []):
        required_caps = screen.get("required_capabilities", [])
        
        # If no caps required, or user has all required caps
        if not required_caps or all(cap.value in user_capabilities for cap in required_caps):
            accessible_screens.append(screen)
    
    return {
        "partner_category": category,
        "entity_class": partner.entity_class,
        "business_entity_type": partner.business_entity_type,
        "service_provider_type": partner.service_provider_type,
        "capabilities": partner.capabilities,
        "can_buy": (partner.capabilities or {}).get("domestic_buy_india", False),
        "can_sell": (partner.capabilities or {}).get("domestic_sell_india", False),
        "screens": accessible_screens,
        "total_screens": len(accessible_screens)
    }
```

### Phase 2: Back Office Module Visibility (2-3 hours)

(Implementation already detailed in MODULE_VISIBILITY_STATUS.md)

1. Create `backend/core/modules/registry.py` - module registry
2. Update `UserProfileResponse` to include `allowed_modules` and `capabilities`
3. Update `/me` endpoint to return module access info
4. Create `/api/v1/modules/accessible` endpoint

---

## 📱 MOBILE UI IMPLEMENTATION EXAMPLE

### React Native Navigation with Dynamic Screens

```typescript
// mobile/src/navigation/AppNavigator.tsx

import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

import { apiClient } from '../services/api';

const Tab = createBottomTabNavigator();

export const AppNavigator = () => {
  const [screens, setScreens] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAccessibleScreens();
  }, []);

  const loadAccessibleScreens = async () => {
    try {
      const response = await apiClient.get('/mobile/screens/accessible');
      setScreens(response.data.screens);
    } catch (error) {
      console.error('Failed to load screens', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <NavigationContainer>
      <Tab.Navigator>
        {screens.map(screen => (
          <Tab.Screen
            key={screen.id}
            name={screen.id}
            component={getScreenComponent(screen.id)}
            options={{
              title: screen.title,
              tabBarIcon: ({ color, size }) => (
                <Icon name={screen.icon} color={color} size={size} />
              ),
            }}
          />
        ))}
      </Tab.Navigator>
    </NavigationContainer>
  );
};

// Map screen IDs to components
const getScreenComponent = (screenId: string) => {
  const SCREEN_MAP = {
    'dashboard': DashboardScreen,
    'post_availability': PostAvailabilityScreen,
    'post_requirement': PostRequirementScreen,
    'my_availabilities': MyAvailabilitiesScreen,
    'my_requirements': MyRequirementsScreen,
    'invoices': InvoicesScreen,
    'payments': PaymentsScreen,
    'active_deals': ActiveDealsScreen,
    'trip_requests': TripRequestsScreen,
    // ... more screens
  };
  
  return SCREEN_MAP[screenId] || NotFoundScreen;
};
```

---

## 🎯 SUMMARY

### What Exists (Infrastructure)

✅ **Database Schema**:
- User model has `user_type`, `business_partner_id`, `organization_id`, `allowed_modules`
- BusinessPartner has `entity_class`, `capabilities`

✅ **Security Context**:
- Middleware loads user type and partner context
- Capability-based authorization works

### What's Missing (Critical)

❌ **Mobile Users**:
1. `/me` doesn't return `business_partner` info
2. No screen configuration system
3. No `/mobile/screens/accessible` API
4. Navigation files completely empty

❌ **Back Office Users**:
1. `/me` doesn't return `allowed_modules`
2. No module registry
3. No `/modules/accessible` API
4. No capability → module mapping

### Action Required

**TOTAL IMPLEMENTATION TIME**: 6-7 hours

**Priority 1 (Mobile)** - 3-4 hours:
1. Update `/me` to return partner info
2. Create mobile screen registry
3. Create `/mobile/screens/accessible` API
4. Implement React Native dynamic navigation

**Priority 2 (Back Office)** - 2-3 hours:
1. Create module registry
2. Update `/me` to return allowed_modules
3. Create `/modules/accessible` API
4. Implement frontend module guards

---

**RECOMMENDATION**: Implement BOTH mobile and back office visibility together as they share the same `/me` endpoint enhancement.

---

*Document generated: December 3, 2025*
*Status: 0% implemented - critical blocker for both mobile and back office UI*
*Priority: CRITICAL (blocks ALL UI development)*
