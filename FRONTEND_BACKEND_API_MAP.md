# Frontend-Backend API Mapping
## Complete Module & Endpoint Reference

---

## 📂 EXISTING STRUCTURE

### **FRONTEND MODULES** (`/frontend/src/modules/`)
```
✅ accounting/
✅ ai_orchestration/
✅ cci_module/
✅ contract_engine/
✅ controller/
✅ dispute/
✅ logistics/
✅ market_trends/
✅ ocr/
✅ payment_engine/
✅ quality/
✅ reports/
✅ risk_engine/
✅ settings/
✅ sub_broker/
✅ trade_desk/
✅ user_onboarding/
```

### **BACKEND MODULES** (`/backend/modules/`)
```
✅ accounting/
✅ ai_orchestration/
✅ auth/
✅ capabilities/
✅ cci/
✅ common/
✅ compliance/
✅ contract_engine/
✅ controller/
✅ dispute/
✅ logistics/
✅ market_trends/
✅ notifications/
✅ ocr/
✅ partners/
✅ payment_engine/
✅ quality/
✅ reports/
✅ risk/
✅ settings/
✅ sub_broker/
✅ trade_desk/
✅ user_onboarding/
```

---

## 🔌 COMPLETE API ENDPOINT MAPPING

### **1. AUTHENTICATION & AUTHORIZATION**

#### **Module:** `user_onboarding` (Frontend) → `auth` (Backend)

| HTTP Method | Endpoint | Purpose |
|------------|----------|---------|
| `POST` | `/api/v1/auth/send-otp` | Send OTP for mobile verification |
| `POST` | `/api/v1/auth/verify-otp` | Verify OTP and get token |
| `POST` | `/api/v1/auth/complete-profile` | Complete user profile after OTP |
| `POST` | `/api/v1/settings/auth/signup` | User signup |
| `POST` | `/api/v1/settings/auth/signup-internal` | Internal user signup |
| `POST` | `/api/v1/settings/auth/login` | User login |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT token |
| `GET` | `/api/v1/auth/me` | Get current user info |
| `POST` | `/api/v1/settings/auth/change-password` | Change password |
| `POST` | `/api/v1/settings/auth/logout` | Logout (current session) |
| `POST` | `/api/v1/settings/auth/logout-all` | Logout all sessions |
| `DELETE` | `/api/v1/auth/logout` | Logout |

**Session Management:**
| `GET` | `/api/v1/auth/sessions` | List active sessions |
| `DELETE` | `/api/v1/auth/sessions/{session_id}` | Delete specific session |
| `DELETE` | `/api/v1/auth/sessions/all` | Delete all sessions |

**Two-Factor Authentication:**
| `POST` | `/api/v1/settings/auth/2fa-setup` | Setup 2FA |
| `POST` | `/api/v1/settings/auth/2fa-verify` | Verify 2FA token |
| `POST` | `/api/v1/settings/auth/2fa-disable` | Disable 2FA |

**Sub-Users:**
| `POST` | `/api/v1/settings/auth/sub-users` | Create sub-user |
| `GET` | `/api/v1/settings/auth/sub-users` | List sub-users |
| `DELETE` | `/api/v1/settings/auth/sub-users/{sub_user_id}` | Delete sub-user |
| `POST` | `/api/v1/settings/auth/sub-users/{sub_user_id}/disable` | Disable sub-user |
| `POST` | `/api/v1/settings/auth/sub-users/{sub_user_id}/enable` | Enable sub-user |

---

### **2. PARTNER MANAGEMENT**

#### **Module:** `partners` (Frontend & Backend)

**Partner Onboarding:**
| `POST` | `/api/v1/partners/onboarding/start` | Start partner onboarding |
| `POST` | `/api/v1/partners/onboarding/{application_id}/documents` | Upload documents |
| `GET` | `/api/v1/partners/onboarding/{application_id}/status` | Check onboarding status |
| `POST` | `/api/v1/partners/onboarding/{application_id}/submit` | Submit application |
| `POST` | `/api/v1/partners/partners/{application_id}/approve` | Approve partner |
| `POST` | `/api/v1/partners/partners/{application_id}/reject` | Reject partner |

**Partner Operations:**
| `GET` | `/api/v1/partners/` | List all partners |
| `GET` | `/api/v1/partners/{partner_id}` | Get partner details |
| `GET` | `/api/v1/partners/dashboard/stats` | Partner dashboard stats |
| `GET` | `/api/v1/partners/export` | Export partners (CSV/Excel) |

**KYC Management:**
| `GET` | `/api/v1/partners/kyc/expiring` | Get expiring KYC partners |
| `POST` | `/api/v1/partners/{partner_id}/kyc/renew` | Renew KYC |
| `POST` | `/api/v1/partners/{partner_id}/kyc/complete` | Complete KYC |
| `GET` | `/api/v1/partners/{partner_id}/kyc-register/download` | Download KYC register |

**Partner Amendments:**
| `POST` | `/api/v1/partners/{partner_id}/amendments` | Request amendment |

**Documents:**
| `GET` | `/api/v1/partners/{partner_id}/documents` | List documents |

**Locations/Branches:**
| `GET` | `/api/v1/partners/{partner_id}/locations` | List partner locations |
| `POST` | `/api/v1/partners/{partner_id}/locations` | Add location |

**Employees:**
| `GET` | `/api/v1/partners/{partner_id}/employees` | List employees |
| `POST` | `/api/v1/partners/{partner_id}/employees` | Add employee |

**Vehicles:**
| `GET` | `/api/v1/partners/{partner_id}/vehicles` | List vehicles |
| `POST` | `/api/v1/partners/{partner_id}/vehicles` | Add vehicle |

---

### **3. TRADE DESK (COMPLETE)**

#### **Module:** `trade_desk` (Frontend & Backend)

**Requirements (Buyer Side):**
| `POST` | `/api/v1/trade-desk/requirements` | Create requirement |
| `GET` | `/api/v1/trade-desk/requirements/buyer/my-requirements` | Get my requirements |
| `GET` | `/api/v1/trade-desk/requirements/{requirement_id}` | Get requirement details |
| `PUT` | `/api/v1/trade-desk/requirements/{requirement_id}` | Update requirement |
| `POST` | `/api/v1/trade-desk/requirements/{requirement_id}/publish` | Publish requirement |
| `POST` | `/api/v1/trade-desk/requirements/{requirement_id}/cancel` | Cancel requirement |
| `POST` | `/api/v1/trade-desk/requirements/{requirement_id}/ai-adjust` | AI adjust parameters |
| `GET` | `/api/v1/trade-desk/requirements/{requirement_id}/history` | Requirement history |
| `POST` | `/api/v1/trade-desk/requirements/{requirement_id}/fulfillment` | Mark fulfilled |

**Search & Analytics:**
| `POST` | `/api/v1/trade-desk/requirements/search` | Search requirements |
| `POST` | `/api/v1/trade-desk/requirements/search/by-intent` | AI intent search |
| `GET` | `/api/v1/trade-desk/requirements/statistics/demand/{commodity_id}` | Demand statistics |

**Availabilities (Seller Side):**
| `POST` | `/api/v1/trade-desk/availabilities` | Create availability |
| `GET` | `/api/v1/trade-desk/availabilities/my` | Get my availabilities |
| `GET` | `/api/v1/trade-desk/availabilities/{availability_id}` | Get availability details |
| `PUT` | `/api/v1/trade-desk/availabilities/{availability_id}` | Update availability |
| `POST` | `/api/v1/trade-desk/availabilities/{availability_id}/approve` | Approve availability |
| `POST` | `/api/v1/trade-desk/availabilities/{availability_id}/reserve` | Reserve quantity |
| `POST` | `/api/v1/trade-desk/availabilities/{availability_id}/release` | Release quantity |
| `POST` | `/api/v1/trade-desk/availabilities/{availability_id}/mark-sold` | Mark as sold |

**Search & Matching:**
| `POST` | `/api/v1/trade-desk/availabilities/search` | Search availabilities |
| `GET` | `/api/v1/trade-desk/availabilities/{availability_id}/similar` | Find similar |
| `GET` | `/api/v1/trade-desk/availabilities/{availability_id}/negotiation-score` | AI negotiation score |

**AI Matching Engine:**
| `POST` | `/api/v1/trade-desk/api/v1/matching/requirements/{requirement_id}/find-matches` | Find matches for requirement |
| `POST` | `/api/v1/trade-desk/api/v1/matching/availabilities/{availability_id}/find-matches` | Find matches for availability |
| `GET` | `/api/v1/trade-desk/api/v1/matching/matches/{requirement_id}/{availability_id}` | Get match details |
| `GET` | `/api/v1/trade-desk/api/v1/matching/health` | Matching engine health |

**Negotiation:**
| `POST` | `/api/v1/trade-desk/negotiations/start` | Start negotiation |
| `GET` | `/api/v1/trade-desk/negotiations/` | List my negotiations |
| `GET` | `/api/v1/trade-desk/negotiations/{negotiation_id}` | Get negotiation details |
| `POST` | `/api/v1/trade-desk/negotiations/{negotiation_id}/offer` | Make counter-offer |
| `POST` | `/api/v1/trade-desk/negotiations/{negotiation_id}/accept` | Accept offer |
| `POST` | `/api/v1/trade-desk/negotiations/{negotiation_id}/reject` | Reject offer |
| `POST` | `/api/v1/trade-desk/negotiations/{negotiation_id}/messages` | Send message |
| `POST` | `/api/v1/trade-desk/negotiations/{negotiation_id}/ai-suggest` | AI negotiation suggestion |

**Admin (Back Office):**
| `GET` | `/api/v1/trade-desk/admin/negotiations` | List all negotiations |
| `GET` | `/api/v1/trade-desk/admin/negotiations/{negotiation_id}` | Admin view negotiation |

---

### **4. RISK ENGINE**

#### **Module:** `risk_engine` (Frontend) → `risk` (Backend)

**Risk Assessment:**
| `POST` | `/api/v1/risk/assess/requirement` | Assess requirement risk |
| `POST` | `/api/v1/risk/assess/availability` | Assess availability risk |
| `POST` | `/api/v1/risk/assess/trade` | Assess trade risk |
| `POST` | `/api/v1/risk/assess/partner` | Assess partner risk |

**Batch Operations:**
| `POST` | `/api/v1/risk/batch/assess-requirements` | Batch assess requirements |
| `POST` | `/api/v1/risk/batch/assess-availabilities` | Batch assess availabilities |

**ML Predictions:**
| `POST` | `/api/v1/risk/ml/predict/fraud` | Predict fraud probability |
| `POST` | `/api/v1/risk/ml/predict/payment-default` | Predict payment default |
| `POST` | `/api/v1/risk/ml/train` | Train ML model |
| `POST` | `/api/v1/risk/ml/train/all` | Train all models |
| `GET` | `/api/v1/risk/ml/models/status` | Get model status |

**Validation:**
| `POST` | `/api/v1/risk/validate/circular-trading` | Detect circular trading |
| `POST` | `/api/v1/risk/validate/party-links` | Validate party links |
| `POST` | `/api/v1/risk/validate/role-restriction` | Validate role restrictions |

**Monitoring:**
| `POST` | `/api/v1/risk/monitor/exposure` | Monitor exposure |
| `GET` | `/api/v1/risk/health` | Risk engine health |

---

### **5. SETTINGS & MASTER DATA**

#### **Module:** `settings` (Frontend & Backend)

**Organizations:**
| `GET` | `/api/v1/settings/organizations/` | List organizations |
| `POST` | `/api/v1/settings/organizations/` | Create organization |
| `GET` | `/api/v1/settings/organizations/{org_id}` | Get organization |
| `PATCH` | `/api/v1/settings/organizations/{org_id}` | Update organization |
| `DELETE` | `/api/v1/settings/organizations/{org_id}` | Delete organization |

**Organization GST:**
| `GET` | `/api/v1/settings/organizations/gst` | List GST details |
| `POST` | `/api/v1/settings/organizations/{org_id}/gst` | Add GST |
| `GET` | `/api/v1/settings/organizations/gst/{gst_id}` | Get GST details |
| `PATCH` | `/api/v1/settings/organizations/gst/{gst_id}` | Update GST |
| `DELETE` | `/api/v1/settings/organizations/gst/{gst_id}` | Delete GST |

**Bank Accounts:**
| `GET` | `/api/v1/settings/organizations/bank-accounts` | List bank accounts |
| `GET` | `/api/v1/settings/organizations/{org_id}/bank-accounts` | Org bank accounts |
| `PATCH` | `/api/v1/settings/organizations/bank-accounts/{account_id}` | Update account |
| `DELETE` | `/api/v1/settings/organizations/bank-accounts/{account_id}` | Delete account |

**Financial Years:**
| `GET` | `/api/v1/settings/organizations/financial-years` | List financial years |
| `GET` | `/api/v1/settings/organizations/{org_id}/financial-years` | Org FY |
| `PATCH` | `/api/v1/settings/organizations/financial-years/{fy_id}` | Update FY |
| `DELETE` | `/api/v1/settings/organizations/financial-years/{fy_id}` | Delete FY |

**Document Series:**
| `GET` | `/api/v1/settings/organizations/document-series` | List doc series |
| `GET` | `/api/v1/settings/organizations/{org_id}/document-series` | Org doc series |
| `GET` | `/api/v1/settings/organizations/{org_id}/next-document-number/{doc_type}` | Next number |
| `PATCH` | `/api/v1/settings/organizations/document-series/{series_id}` | Update series |
| `DELETE` | `/api/v1/settings/organizations/document-series/{series_id}` | Delete series |

**Commodities:**
| `GET` | `/api/v1/settings/commodities/` | List commodities |
| `POST` | `/api/v1/settings/commodities/` | Create commodity |
| `GET` | `/api/v1/settings/commodities/{commodity_id}` | Get commodity |
| `PUT` | `/api/v1/settings/commodities/{commodity_id}` | Update commodity |
| `DELETE` | `/api/v1/settings/commodities/{commodity_id}` | Delete commodity |

**Commodity AI:**
| `POST` | `/api/v1/settings/commodities/ai/detect-category` | AI detect category |
| `POST` | `/api/v1/settings/commodities/ai/suggest-hsn` | AI suggest HSN |
| `POST` | `/api/v1/settings/commodities/ai/suggest-international-fields` | AI international |
| `POST` | `/api/v1/settings/commodities/{commodity_id}/ai/suggest-parameters` | AI parameters |

**Commodity Varieties:**
| `GET` | `/api/v1/settings/commodities/{commodity_id}/varieties` | List varieties |
| `PUT` | `/api/v1/settings/commodities/varieties/{variety_id}` | Update variety |

**Commodity Parameters:**
| `GET` | `/api/v1/settings/commodities/{commodity_id}/parameters` | List parameters |
| `POST` | `/api/v1/settings/commodities/{commodity_id}/parameters` | Add parameter |
| `PUT` | `/api/v1/settings/commodities/parameters/{parameter_id}` | Update parameter |

**Commission:**
| `GET` | `/api/v1/settings/commodities/{commodity_id}/commission` | Get commission |
| `POST` | `/api/v1/settings/commodities/{commodity_id}/commission` | Set commission |
| `PUT` | `/api/v1/settings/commodities/commission/{commission_id}` | Update commission |

**Trade Terms:**
| `GET` | `/api/v1/settings/commodities/bargain-types` | List bargain types |
| `PUT` | `/api/v1/settings/commodities/bargain-types/{bargain_type_id}` | Update |
| `GET` | `/api/v1/settings/commodities/delivery-terms` | List delivery terms |
| `PUT` | `/api/v1/settings/commodities/delivery-terms/{term_id}` | Update |
| `GET` | `/api/v1/settings/commodities/passing-terms` | List passing terms |
| `PUT` | `/api/v1/settings/commodities/passing-terms/{term_id}` | Update |
| `GET` | `/api/v1/settings/commodities/payment-terms` | List payment terms |
| `PUT` | `/api/v1/settings/commodities/payment-terms/{term_id}` | Update |
| `GET` | `/api/v1/settings/commodities/trade-types` | List trade types |
| `PUT` | `/api/v1/settings/commodities/trade-types/{trade_type_id}` | Update |
| `GET` | `/api/v1/settings/commodities/weightment-terms` | List weightment terms |
| `PUT` | `/api/v1/settings/commodities/weightment-terms/{term_id}` | Update |

**System:**
| `GET` | `/api/v1/settings/commodities/system-parameters` | System parameters |
| `PUT` | `/api/v1/settings/commodities/system-parameters/{parameter_id}` | Update param |
| `GET` | `/api/v1/settings/commodities/units/list` | List units |

**Bulk Operations:**
| `POST` | `/api/v1/settings/commodities/bulk/upload` | Bulk upload |
| `POST` | `/api/v1/settings/commodities/bulk/validate` | Validate bulk |
| `GET` | `/api/v1/settings/commodities/bulk/download` | Download template |

**Search:**
| `GET` | `/api/v1/settings/commodities/search/advanced` | Advanced search |

**Conversions:**
| `POST` | `/api/v1/settings/commodities/{commodity_id}/calculate-conversion` | Calculate conversion |

**Locations:**
| `GET` | `/api/v1/settings/locations/` | List locations |
| `POST` | `/api/v1/settings/locations/` | Create location |
| `GET` | `/api/v1/settings/locations/{location_id}` | Get location |
| `PUT` | `/api/v1/settings/locations/{location_id}` | Update location |
| `DELETE` | `/api/v1/settings/locations/{location_id}` | Delete location |
| `POST` | `/api/v1/settings/locations/fetch-details` | Fetch from pincode |
| `POST` | `/api/v1/settings/locations/search-google` | Google Maps search |

---

### **6. INFRASTRUCTURE & REAL-TIME**

**WebSocket:**
| `POST` | `/api/v1/ws/notify/{user_id}` | Send notification to user |
| `POST` | `/api/v1/ws/broadcast/{channel}` | Broadcast to channel |
| `GET` | `/api/v1/ws/channels` | List channels |
| `GET` | `/api/v1/ws/stats` | WebSocket stats |

**Webhooks:**
| `POST` | `/api/v1/webhooks/subscriptions` | Create webhook subscription |
| `DELETE` | `/api/v1/webhooks/subscriptions/{subscription_id}` | Delete subscription |
| `POST` | `/api/v1/webhooks/events/publish` | Publish event |
| `GET` | `/api/v1/webhooks/stats` | Webhook stats |
| `GET` | `/api/v1/webhooks/dlq` | Dead letter queue |
| `POST` | `/api/v1/webhooks/dlq/{delivery_id}/retry` | Retry failed webhook |

**Offline Sync:**
| `GET` | `/api/v1/sync/changes` | Get changes since timestamp |
| `POST` | `/api/v1/sync/push` | Push offline changes |
| `GET` | `/api/v1/sync/status` | Sync status |
| `POST` | `/api/v1/sync/reset` | Reset sync state |

**Privacy (GDPR):**
| `POST` | `/api/v1/privacy/consent` | Grant consent |
| `DELETE` | `/api/v1/privacy/consent/{consent_type}` | Revoke consent |
| `GET` | `/api/v1/privacy/consent/history` | Consent history |
| `POST` | `/api/v1/privacy/export` | Request data export |
| `GET` | `/api/v1/privacy/export/{request_id}` | Download export |
| `DELETE` | `/api/v1/privacy/account` | Request account deletion |
| `POST` | `/api/v1/privacy/account/deletion/{request_id}/cancel` | Cancel deletion |

---

### **7. HEALTH & MONITORING**

| `GET` | `/healthz` | Basic health check |
| `GET` | `/ready` | Readiness probe (DB check) |
| `GET` | `/api/v1/settings/health` | Settings module health |

---

## 📋 MISSING FRONTEND MODULES (Need to Create)

Based on backend modules, these frontend modules are **MISSING**:

```
❌ capabilities/          # User capability detection
❌ notifications/         # Push notifications UI
❌ compliance/            # Compliance tracking
❌ common/               # Common utilities
❌ auth/                 # Dedicated auth module (currently in settings)
```

---

## 📋 FRONTEND-ONLY MODULES (No Backend)

These exist in frontend but have no direct backend module:

```
⚠️ controller/           # What is this for?
⚠️ ai_orchestration/     # AI orchestration UI
```

---

## 🎯 RECOMMENDED FRONTEND STRUCTURE UPDATE

### **Current Issues:**
1. Auth is mixed with settings
2. No dedicated capabilities UI
3. No notifications center
4. Trade desk needs splitting (too large)

### **Proposed Structure:**
```
frontend/src/modules/
├─ auth/                 # ✨ NEW - Login, signup, 2FA, sessions
├─ dashboard/            # ✨ NEW - Main dashboard
├─ partners/             # ✨ NEW - Partner management (split from user_onboarding)
├─ trade-desk/
│  ├─ requirements/
│  ├─ availabilities/
│  ├─ matching/
│  └─ negotiations/
├─ risk/                 # ✨ RENAME from risk_engine
├─ settings/             # Master data only
├─ notifications/        # ✨ NEW - Notification center
├─ capabilities/         # ✨ NEW - User capabilities UI
├─ compliance/           # ✨ NEW - Compliance dashboard
├─ accounting/
├─ contract_engine/
├─ dispute/
├─ logistics/
├─ market_trends/
├─ ocr/
├─ payment_engine/
├─ quality/
├─ reports/
├─ sub_broker/
└─ cci/
```

---

## ✅ NEXT STEPS

1. **Verify** which frontend modules are actually being used
2. **Create** missing modules (auth, notifications, capabilities)
3. **Split** large modules (trade_desk, settings)
4. **Standardize** API client generation from OpenAPI
5. **Build** shared component library
6. **Implement** WebSocket subscriptions
7. **Add** offline sync support

---

**FRONTEND FRAMEWORK:** React + TypeScript + Vite (already exists)
**STATE MANAGEMENT:** Check current implementation
**API CLIENT:** Need to verify if OpenAPI generated client exists
**REAL-TIME:** WebSocket client needs implementation
**OFFLINE:** Sync API exists, client needs WatermelonDB integration
