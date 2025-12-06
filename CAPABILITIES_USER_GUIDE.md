# Capability-Based Authorization System - User Guide

## Overview

The Cotton ERP system uses a **pure capability-based authorization model** instead of traditional role-based permissions. This provides fine-grained control over what each user can do in the system.

### Key Concepts

- **Capability**: A specific permission to perform an action (e.g., `PARTNER_CREATE`, `MATCHING_APPROVE_MATCH`)
- **Direct Grant**: Capability assigned directly to a user
- **Expiry**: Optional expiration date for temporary permissions
- **91 Capabilities**: Available across 11 categories (auth, organization, partner, commodity, etc.)

### Important Notes

- ❌ **No role-based permissions** - Backend does not have role management API
- ✅ **Direct capability assignment only** - Assign capabilities directly to users
- ✅ **100% capability-based** - Frontend and backend fully aligned

---

## Frontend Components

### 1. Capabilities Overview Page

**Location**: `/backoffice/capabilities`

**Purpose**: Browse and explore all available capabilities

**Features**:
- View all 91 capabilities organized by category
- Search capabilities by name, code, or description
- Filter by category
- View capability stats and distribution
- Permission matrix view

**Access**: Available to all authenticated users (read-only)

---

### 2. User Capabilities Management Page

**Location**: `/backoffice/user-capabilities`

**Purpose**: Assign and manage capabilities for individual users

**Required Capability**: `ADMIN_MANAGE_USERS`

#### Features

##### User List (Left Panel)
- Search users by name, email, or ID
- View user type (SUPER_ADMIN, INTERNAL, EXTERNAL)
- See capability count for each user
- Click to select and view details

##### Capability Details (Right Panel)
- **Stats Display**:
  - Total capabilities assigned
  - Direct capability grants
  - Temporary grants with expiry
  
- **Direct Capabilities List**:
  - View all capabilities granted to user
  - See grant details (who granted, when, expiry)
  - Expired capabilities highlighted in red
  - One-click revoke button

##### Assign Capability Modal
- Search through available capabilities
- Filter by category with color coding
- Click capability card to assign instantly
- Auto-refresh after assignment
- Success/error notifications

#### Workflow

1. **Select User**: Click on a user from the left panel
2. **View Capabilities**: See all assigned capabilities in right panel
3. **Assign New Capability**:
   - Click "Assign Capability" button
   - Search for desired capability
   - Click capability card to assign
   - Confirmation message appears
4. **Revoke Capability**:
   - Click X button next to capability
   - Capability removed immediately
   - Confirmation message appears

---

## Backend API Endpoints

### Capability Endpoints

```http
GET /api/v1/capabilities
```
List all available capabilities
- Query params: `category`, `is_system`
- Returns: Array of 91 capabilities

```http
GET /api/v1/capabilities/me
```
Get current user's capabilities
- Returns: UserCapabilitiesResponse with capability codes and full objects

```http
GET /api/v1/capabilities/users/{user_id}
```
Get specific user's capabilities
- Required: `ADMIN_MANAGE_USERS`
- Returns: All capabilities for the user

```http
POST /api/v1/capabilities/users/{user_id}/grant
```
Grant capability to user
- Required: `ADMIN_MANAGE_USERS`
- Body: `{ "capability_code": "PARTNER_CREATE", "expires_at": "2025-12-31", "reason": "Temporary access" }`

```http
POST /api/v1/capabilities/users/{user_id}/revoke
```
Revoke capability from user
- Required: `ADMIN_MANAGE_USERS`
- Body: `{ "capability_code": "PARTNER_CREATE", "reason": "Access no longer needed" }`

```http
POST /api/v1/capabilities/users/{user_id}/check
```
Check if user has capability
- Required: `ADMIN_MANAGE_USERS`
- Body: `{ "capability_code": "PARTNER_CREATE" }`

---

## Capability Categories

### 1. Authentication (`auth`)
- `AUTH_LOGIN`, `AUTH_LOGOUT`, `AUTH_CHANGE_PASSWORD`
- `AUTH_ENABLE_2FA`, `AUTH_MANAGE_SESSIONS`

### 2. Organization (`organization`)
- `ORGANIZATION_VIEW`, `ORGANIZATION_CREATE`, `ORGANIZATION_EDIT`
- `ORGANIZATION_DELETE`, `ORGANIZATION_MANAGE_BRANCHES`

### 3. Business Partners (`partner`)
- `PARTNER_VIEW`, `PARTNER_CREATE`, `PARTNER_EDIT`, `PARTNER_DELETE`
- `PARTNER_APPROVE`, `PARTNER_VIEW_FINANCIALS`

### 4. Commodities (`commodity`)
- `COMMODITY_VIEW`, `COMMODITY_CREATE`, `COMMODITY_EDIT`, `COMMODITY_DELETE`
- `COMMODITY_MANAGE_GRADES`, `COMMODITY_MANAGE_SPECIFICATIONS`

### 5. Locations (`location`)
- `LOCATION_VIEW`, `LOCATION_CREATE`, `LOCATION_EDIT`, `LOCATION_DELETE`
- `LOCATION_MANAGE_HIERARCHY`

### 6. Availability (`availability`)
- `AVAILABILITY_VIEW`, `AVAILABILITY_CREATE`, `AVAILABILITY_EDIT`
- `AVAILABILITY_DELETE`, `AVAILABILITY_APPROVE`, `AVAILABILITY_PUBLISH`

### 7. Requirements (`requirement`)
- `REQUIREMENT_VIEW`, `REQUIREMENT_CREATE`, `REQUIREMENT_EDIT`
- `REQUIREMENT_DELETE`, `REQUIREMENT_APPROVE`, `REQUIREMENT_PUBLISH`

### 8. Matching (`matching`)
- `MATCHING_VIEW_MATCH`, `MATCHING_CREATE_MATCH`, `MATCHING_EDIT_MATCH`
- `MATCHING_DELETE_MATCH`, `MATCHING_APPROVE_MATCH`, `MATCHING_EXECUTE_MATCH`

### 9. Settings (`settings`)
- `SETTINGS_VIEW`, `SETTINGS_EDIT`, `SETTINGS_MANAGE_SYSTEM`

### 10. Administrative (`admin`)
- `ADMIN_VIEW_ALL_DATA`, `ADMIN_MANAGE_USERS`, `ADMIN_MANAGE_ROLES`
- `ADMIN_MANAGE_CAPABILITIES`, `ADMIN_MANAGE_SYSTEM`, `ADMIN_VIEW_AUDIT_LOGS`
- `ADMIN_MANAGE_INTEGRATIONS`, `ADMIN_MANAGE_NOTIFICATIONS`

### 11. System (`invoice`, `contract`, `payment`, `shipment`, `data`, `privacy`, `audit`)
- Various specialized capabilities for specific modules

---

## Usage Examples

### Example 1: Grant Commodity Management Access

**Scenario**: Sales manager needs to create and edit commodity records

**Steps**:
1. Navigate to `/backoffice/user-capabilities`
2. Search for user "Sales Manager"
3. Click "Assign Capability"
4. Search for "commodity"
5. Click on `COMMODITY_CREATE` and `COMMODITY_EDIT`
6. User can now create and edit commodities

### Example 2: Temporary Partner Approval Access

**Scenario**: Give user temporary approval rights while regular approver is on leave

**Steps**:
1. Navigate to `/backoffice/user-capabilities`
2. Select the user
3. Click "Assign Capability"
4. Find `PARTNER_APPROVE`
5. Assign with expiry date (e.g., 2 weeks)
6. After expiry, user automatically loses approval rights

### Example 3: Audit User Permissions

**Scenario**: Check what a specific user can do

**Steps**:
1. Navigate to `/backoffice/user-capabilities`
2. Select the user
3. View Direct Capabilities section
4. See all assigned capabilities with:
   - Capability name and code
   - Grant date and granted by
   - Expiry status (if applicable)
   - Reason for grant

---

## Frontend Components Reference

### Types

```typescript
// Main capability type
interface Capability {
  id: string;
  code: string;
  name: string;
  description?: string;
  category: string;
  is_system: boolean;
}

// User capability assignment
interface UserCapability {
  id: string;
  user_id: string;
  capability: Capability;  // Full capability object
  granted_at: string;
  granted_by: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  revoked_by: string | null;
  reason: string | null;
}

// Response from /capabilities/me or /capabilities/users/{id}
interface UserCapabilitiesResponse {
  user_id: string;
  capabilities: string[];  // Simple array of codes
  direct_capabilities: UserCapability[];  // Full objects
  role_capabilities: RoleCapability[];  // Empty (no roles in backend)
}
```

### Hooks

```typescript
import { useHasCapability, useIsAdmin } from '@/hooks/useCapabilities';

// Check single capability
const canCreatePartner = useHasCapability('PARTNER_CREATE');

// Check if user is admin
const isAdmin = useIsAdmin();

// Use in JSX
{canCreatePartner && (
  <button onClick={handleCreate}>Create Partner</button>
)}
```

### Services

```typescript
import capabilitiesService from '@/services/api/capabilitiesService';

// Get all capabilities
const capabilities = await capabilitiesService.getAllCapabilities();

// Get user capabilities
const userCaps = await capabilitiesService.getUserCapabilities(userId);

// Grant capability
await capabilitiesService.grantCapabilityToUser(userId, {
  capability_code: 'PARTNER_CREATE',
  expires_at: '2025-12-31T23:59:59Z',
  reason: 'Temporary access for project'
});

// Revoke capability
await capabilitiesService.revokeCapabilityFromUser(userId, 'PARTNER_CREATE');
```

---

## Database Schema

### Capabilities Table
```sql
CREATE TABLE capabilities (
  id UUID PRIMARY KEY,
  code VARCHAR(128) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(50) NOT NULL,
  is_system BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
-- 91 rows seeded
```

### User Capabilities Table
```sql
CREATE TABLE user_capabilities (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  capability_id UUID NOT NULL REFERENCES capabilities(id),
  granted_at TIMESTAMP NOT NULL,
  granted_by UUID REFERENCES users(id),
  expires_at TIMESTAMP,
  revoked_at TIMESTAMP,
  revoked_by UUID REFERENCES users(id),
  reason TEXT,
  UNIQUE(user_id, capability_id)
);
```

---

## Security Considerations

### Backend Protection

All capability-protected endpoints use the `@RequireCapability` decorator:

```python
from modules.capabilities.decorator import RequireCapability
from modules.capabilities.constants import Capabilities

@router.post("/partners")
@RequireCapability(Capabilities.PARTNER_CREATE)
async def create_partner(...):
    # Only users with PARTNER_CREATE can access
    pass
```

### Frontend Protection

Components can check capabilities before rendering:

```tsx
import { RequireCapability } from '@/hooks/useCapabilities';

<RequireCapability capability="PARTNER_CREATE">
  <CreatePartnerButton />
</RequireCapability>
```

### Best Practices

1. **Least Privilege**: Grant only capabilities needed for the job
2. **Temporary Access**: Use expiry dates for temporary permissions
3. **Audit Trail**: All grants/revokes are logged with reasons
4. **Regular Review**: Periodically audit user capabilities
5. **Documentation**: Document reason when granting capabilities

---

## Troubleshooting

### User Can't See Feature

**Problem**: User claims they can't access a feature

**Solution**:
1. Navigate to User Capabilities page
2. Search for the user
3. Check if they have the required capability
4. If missing, assign the capability
5. Ask user to refresh browser

### Capability Not Working After Assignment

**Problem**: Granted capability but user still can't perform action

**Solution**:
1. Check if capability has expired
2. Verify user's session is still valid
3. Ask user to log out and log back in
4. Check browser console for errors
5. Verify backend endpoint has correct `@RequireCapability` decorator

### Can't Revoke Capability

**Problem**: Can't revoke a capability from user

**Solution**:
1. Check if you have `ADMIN_MANAGE_USERS` capability
2. Verify capability was directly granted (not via role - though roles don't exist in this system)
3. Check browser console for API errors
4. Verify user_id is correct

---

## Future Enhancements

### Planned Features (Not Yet Implemented)

1. **Bulk Operations**
   - Assign multiple capabilities at once
   - Copy capabilities from one user to another
   - Capability templates/presets

2. **Advanced Filtering**
   - Filter by expiry status
   - Filter by grantor
   - Date range filters

3. **Reporting**
   - Capability usage analytics
   - User capability reports
   - Audit logs export

4. **Role Templates** (Maybe)
   - While backend has no role management, could create frontend-only templates
   - Quick-assign common capability sets
   - Industry-standard role templates

---

## Contact & Support

For questions or issues with the capabilities system:

- **Technical Issues**: Check backend logs and frontend console
- **Permission Issues**: Contact system administrator
- **Feature Requests**: Submit via project management system

---

## Changelog

### Version 1.0 (December 6, 2024)
- ✅ Initial implementation of pure capability-based system
- ✅ 91 capabilities seeded in database
- ✅ Frontend UI for capability management
- ✅ Backend API endpoints
- ✅ User Capabilities Management page
- ✅ Capability assignment/revocation
- ✅ Search and filtering
- ✅ Expiry tracking
- ✅ Success/error notifications
- ❌ Role-based permissions removed (backend has no role API)
- ✅ Complete frontend-backend alignment

---

**System Status**: 100% Production Ready ✅

All components tested and verified with real backend API.

