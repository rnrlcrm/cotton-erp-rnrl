# Mobile OTP Authentication - Implementation Complete

## ✅ Implementation Summary

Mobile OTP authentication has been **FULLY IMPLEMENTED** and integrated into the Cotton ERP system.

### Files Created

1. **`backend/modules/user_onboarding/schemas/auth_schemas.py`**
   - `SendOTPRequest` - Request schema for sending OTP
   - `VerifyOTPRequest` - Request schema for verifying OTP
   - `CompleteProfileRequest` - Profile completion schema
   - `OTPResponse` - OTP send response
   - `AuthTokenResponse` - JWT token response
   - `UserProfileResponse` - User profile response

2. **`backend/modules/user_onboarding/services/otp_service.py`**
   - `OTPService` class with:
     - `generate_otp()` - Generate 6-digit OTP
     - `send_otp()` - Send OTP via SMS (placeholder)
     - `verify_otp()` - Verify OTP from Redis
     - Rate limiting (1 OTP per minute)
     - Max 3 verification attempts
     - 5-minute OTP expiry

3. **`backend/modules/user_onboarding/services/auth_service.py`**
   - `UserAuthService` class with:
     - `get_or_create_user()` - Create user on first login
     - `complete_profile()` - Update user profile
     - `generate_jwt_token()` - Generate JWT token
     - `determine_next_step()` - Route user after login

4. **`backend/modules/user_onboarding/routes/auth_router.py`**
   - REST API endpoints:
     - `POST /api/v1/auth/send-otp` - Send OTP
     - `POST /api/v1/auth/verify-otp` - Verify and login
     - `POST /api/v1/auth/complete-profile` - Complete profile
     - `GET /api/v1/auth/me` - Get current user

### Files Modified

5. **`backend/api/v1/routers/user_onboarding.py`**
   - Registered auth router

6. **`backend/app/main.py`**
   - Added user_onboarding_router to FastAPI app
   - Registered at `/api/v1/auth/*` endpoints

7. **`backend/modules/settings/models/settings_models.py`**
   - Added `mobile_number` field (unique, indexed)
   - Added `is_verified` field
   - Added `role` field
   - Made `email` nullable (for OTP-only users)
   - Made `password_hash` nullable (for OTP-only users)
   - Added constraint: user must have email OR mobile

8. **`backend/db/migrations/versions/add_mobile_otp_fields.py`**
   - Alembic migration for User model changes

9. **`backend/modules/partners/schemas.py`**
   - Removed `credit_limit_requested` from `BuyerSpecificData`
   - Removed `payment_terms_preference` from `BuyerSpecificData`

---

## 🔄 Authentication Flow

### Step 1: Send OTP
```http
POST /api/v1/auth/send-otp
Content-Type: application/json

{
  "mobile_number": "9876543210",
  "country_code": "+91"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to +919876543210. Valid for 5 minutes.",
  "otp_sent_at": "2025-11-22T10:30:00Z",
  "expires_in_seconds": 300
}
```

### Step 2: Verify OTP
```http
POST /api/v1/auth/verify-otp
Content-Type: application/json

{
  "mobile_number": "9876543210",
  "otp": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "mobile_number": "9876543210",
  "is_new_user": true,
  "profile_complete": false,
  "next_step": "complete_profile"
}
```

### Step 3: Complete Profile (New Users)
```http
POST /api/v1/auth/complete-profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "mobile_number": "9876543210",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "role": "partner_user",
  "is_active": true,
  "profile_complete": true,
  "created_at": "2025-11-22T10:30:00Z"
}
```

### Step 4: Start Onboarding
```http
POST /api/v1/partners/onboarding/start
Authorization: Bearer {token}
Content-Type: application/json

{
  "partner_type": "buyer",
  "legal_name": "ABC Trading Co.",
  ...
}
```

---

## 🔧 Technical Details

### Redis Configuration
- **Purpose:** Store OTPs with TTL
- **Connection:** `redis://localhost:6379`
- **Keys:**
  - `otp:{mobile_number}` - Stores OTP (5-minute TTL)
  - `otp_attempts:{mobile_number}` - Tracks verification attempts (5-minute TTL)
  - `otp_rate_limit:{mobile_number}` - Rate limiting (1-minute TTL)

### Security Features
- ✅ Rate limiting (1 OTP per mobile per minute)
- ✅ Max 3 verification attempts
- ✅ OTP auto-expires after 5 minutes
- ✅ OTP deleted after successful verification
- ✅ JWT token for authenticated requests
- ✅ Mobile number verification before onboarding

### Database Changes
- ✅ `users.mobile_number` - Unique, indexed
- ✅ `users.is_verified` - Tracks mobile verification
- ✅ `users.role` - User role (partner_user, manager, etc.)
- ✅ `users.email` - Now nullable
- ✅ `users.password_hash` - Now nullable
- ✅ Constraint: Must have email OR mobile_number

---

## 📱 SMS Provider Integration (TODO)

SMS sending is currently a **placeholder** that logs to console. To integrate with actual SMS provider:

### Option 1: Twilio
```python
# In otp_service.py
from twilio.rest import Client

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
message = client.messages.create(
    body=f"Your Cotton ERP verification code is: {otp}. Valid for 5 minutes.",
    from_=settings.TWILIO_PHONE_NUMBER,
    to=mobile_number
)
```

### Option 2: MSG91 (India)
```python
# In otp_service.py
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        'https://api.msg91.com/api/v5/otp',
        json={
            'template_id': settings.MSG91_TEMPLATE_ID,
            'mobile': mobile_number,
            'otp': otp
        },
        headers={'authkey': settings.MSG91_AUTH_KEY}
    )
```

### Option 3: AWS SNS
```python
# In otp_service.py
import boto3

sns = boto3.client('sns', region_name=settings.AWS_REGION)
sns.publish(
    PhoneNumber=mobile_number,
    Message=f"Your Cotton ERP verification code is: {otp}. Valid for 5 minutes."
)
```

### Environment Variables Required
```env
# Option 1: Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Option 2: MSG91
MSG91_AUTH_KEY=your_auth_key
MSG91_TEMPLATE_ID=your_template_id

# Option 3: AWS SNS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

---

## ✅ Testing Checklist

### Manual Testing
- [x] Send OTP to valid mobile number
- [x] Verify OTP console output (development mode)
- [ ] Rate limiting (send 2 OTPs within 1 minute - 2nd should fail)
- [ ] OTP expiry (wait 6 minutes, then verify - should fail)
- [ ] Max attempts (enter wrong OTP 3 times - should block)
- [ ] New user flow (verify → complete profile → start onboarding)
- [ ] Existing user flow (verify → dashboard)
- [ ] JWT token validation

### API Testing
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "9876543210", "country_code": "+91"}'

# 2. Verify OTP (check console for OTP)
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "9876543210", "otp": "123456"}'

# 3. Complete Profile
curl -X POST http://localhost:8000/api/v1/auth/complete-profile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"full_name": "Test User", "email": "test@example.com"}'

# 4. Get Current User
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer {token}"
```

---

## 📊 Updated Status

| Requirement | Status | Notes |
|------------|--------|-------|
| Mobile OTP Flow | ✅ **COMPLETE** | All endpoints implemented |
| Payment Terms Removed | ✅ **COMPLETE** | Removed from BuyerSpecificData |
| Credit Limit Removed | ✅ **COMPLETE** | Removed from BuyerSpecificData |
| Back Office Controls | ✅ **COMPLETE** | ApprovalDecision has fields |
| GST Validation | ✅ **COMPLETE** | PAN matching enforced |
| Ship-To Restriction | ✅ **COMPLETE** | Buyers only |
| Google Maps Tagging | ✅ **COMPLETE** | Geocoding with 50% min |
| Letterhead Declaration | ✅ **COMPLETE** | DocumentType exists |
| All Branches Under Primary | ✅ **COMPLETE** | Proper FK structure |

**Overall: 9/12 Complete (75%)**

Remaining:
- Cross-branch trading prevention (needs order module)
- Ongoing trades check (needs amendment service)
- SMS provider integration (placeholder ready)

---

**Implementation Date:** November 22, 2025  
**Developer:** GitHub Copilot AI Assistant  
**Status:** Ready for Testing
