/**
 * API Configuration
 */

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  API_VERSION: '/api/v1',
  TIMEOUT: 30000,
  
  // Token configuration
  TOKEN_STORAGE_KEY: 'rnrl_access_token',
  REFRESH_TOKEN_STORAGE_KEY: 'rnrl_refresh_token',
  USER_STORAGE_KEY: 'rnrl_user',
  
  // Refresh token timing (refresh 5 minutes before expiry)
  TOKEN_REFRESH_BUFFER: 5 * 60 * 1000, // 5 minutes in ms
} as const;

export const API_ENDPOINTS = {
  // Auth endpoints
  AUTH: {
    LOGIN: '/settings/auth/login',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    LOGOUT_ALL: '/auth/sessions/all',
    ME: '/settings/auth/me',
    CHANGE_PASSWORD: '/settings/auth/change-password',
    TWO_FACTOR_STATUS: '/auth/2fa/status',
    TWO_FACTOR_SETUP: '/auth/2fa/setup',
    TWO_FACTOR_VERIFY: '/auth/2fa/verify',
    TWO_FACTOR_DISABLE: '/auth/2fa',
    FORGOT_PASSWORD: '/settings/auth/forgot-password',
    RESET_PASSWORD: '/settings/auth/reset-password',
    VERIFY_EMAIL: '/settings/auth/verify-email',
  },
  
  // Session management
  SESSIONS: {
    LIST: '/auth/sessions',
    DELETE: (sessionId: string) => `/auth/sessions/${sessionId}`,
    DELETE_ALL: '/auth/sessions/all',
  },
  
  // Organization endpoints
  ORGANIZATIONS: {
    LIST: '/settings/organizations',
    CREATE: '/settings/organizations',
    GET: (orgId: string) => `/settings/organizations/${orgId}`,
    UPDATE: (orgId: string) => `/settings/organizations/${orgId}`,
    DELETE: (orgId: string) => `/settings/organizations/${orgId}`,
    
    // GST endpoints
    GST_CREATE: '/settings/organizations/gst',
    GST_GET: (gstId: string) => `/settings/organizations/gst/${gstId}`,
    GST_LIST: (orgId: string) => `/settings/organizations/${orgId}/gst`,
    GST_UPDATE: (gstId: string) => `/settings/organizations/gst/${gstId}`,
    GST_DELETE: (gstId: string) => `/settings/organizations/gst/${gstId}`,
    
    // Bank Account endpoints
    BANK_CREATE: '/settings/organizations/bank-accounts',
    BANK_GET: (accountId: string) => `/settings/organizations/bank-accounts/${accountId}`,
    BANK_LIST: (orgId: string) => `/settings/organizations/${orgId}/bank-accounts`,
    BANK_UPDATE: (accountId: string) => `/settings/organizations/bank-accounts/${accountId}`,
    BANK_DELETE: (accountId: string) => `/settings/organizations/bank-accounts/${accountId}`,
    
    // Financial Year endpoints
    FY_CREATE: '/settings/organizations/financial-years',
    FY_GET: (fyId: string) => `/settings/organizations/financial-years/${fyId}`,
    FY_LIST: (orgId: string) => `/settings/organizations/${orgId}/financial-years`,
    FY_UPDATE: (fyId: string) => `/settings/organizations/financial-years/${fyId}`,
    FY_DELETE: (fyId: string) => `/settings/organizations/financial-years/${fyId}`,
    
    // Document Series endpoints
    DOC_SERIES_CREATE: '/settings/organizations/document-series',
    DOC_SERIES_GET: (seriesId: string) => `/settings/organizations/document-series/${seriesId}`,
    DOC_SERIES_LIST: (orgId: string) => `/settings/organizations/${orgId}/document-series`,
    DOC_SERIES_UPDATE: (seriesId: string) => `/settings/organizations/document-series/${seriesId}`,
    DOC_SERIES_DELETE: (seriesId: string) => `/settings/organizations/document-series/${seriesId}`,
    NEXT_DOC_NUMBER: (orgId: string, docType: string) => `/settings/organizations/${orgId}/next-document-number/${docType}`,
  },
  
  // Commodity endpoints
  COMMODITIES: {
    LIST: '/settings/commodities',
    CREATE: '/settings/commodities',
    GET: (commodityId: string) => `/settings/commodities/${commodityId}`,
    UPDATE: (commodityId: string) => `/settings/commodities/${commodityId}`,
    DELETE: (commodityId: string) => `/settings/commodities/${commodityId}`,
    SEARCH_ADVANCED: '/settings/commodities/search/advanced',
    
    // Variety endpoints
    VARIETY_CREATE: (commodityId: string) => `/settings/commodities/${commodityId}/varieties`,
    VARIETY_LIST: (commodityId: string) => `/settings/commodities/${commodityId}/varieties`,
    VARIETY_UPDATE: (varietyId: string) => `/settings/commodities/varieties/${varietyId}`,
    
    // Parameter endpoints
    PARAMETER_CREATE: (commodityId: string) => `/settings/commodities/${commodityId}/parameters`,
    PARAMETER_LIST: (commodityId: string) => `/settings/commodities/${commodityId}/parameters`,
    PARAMETER_UPDATE: (parameterId: string) => `/settings/commodities/parameters/${parameterId}`,
    
    // System Parameters
    SYSTEM_PARAM_CREATE: '/settings/commodities/system-parameters',
    SYSTEM_PARAM_LIST: '/settings/commodities/system-parameters',
    SYSTEM_PARAM_UPDATE: (parameterId: string) => `/settings/commodities/system-parameters/${parameterId}`,
    
    // Trade Types
    TRADE_TYPE_CREATE: '/settings/commodities/trade-types',
    TRADE_TYPE_LIST: '/settings/commodities/trade-types',
    TRADE_TYPE_UPDATE: (tradeTypeId: string) => `/settings/commodities/trade-types/${tradeTypeId}`,
    
    // Bargain Types
    BARGAIN_TYPE_CREATE: '/settings/commodities/bargain-types',
    BARGAIN_TYPE_LIST: '/settings/commodities/bargain-types',
    BARGAIN_TYPE_UPDATE: (bargainTypeId: string) => `/settings/commodities/bargain-types/${bargainTypeId}`,
    
    // Terms
    PASSING_TERM_CREATE: '/settings/commodities/passing-terms',
    PASSING_TERM_LIST: '/settings/commodities/passing-terms',
    PASSING_TERM_UPDATE: (termId: string) => `/settings/commodities/passing-terms/${termId}`,
    
    WEIGHTMENT_TERM_CREATE: '/settings/commodities/weightment-terms',
    WEIGHTMENT_TERM_LIST: '/settings/commodities/weightment-terms',
    WEIGHTMENT_TERM_UPDATE: (termId: string) => `/settings/commodities/weightment-terms/${termId}`,
    
    DELIVERY_TERM_CREATE: '/settings/commodities/delivery-terms',
    DELIVERY_TERM_LIST: '/settings/commodities/delivery-terms',
    DELIVERY_TERM_UPDATE: (termId: string) => `/settings/commodities/delivery-terms/${termId}`,
    
    PAYMENT_TERM_CREATE: '/settings/commodities/payment-terms',
    PAYMENT_TERM_LIST: '/settings/commodities/payment-terms',
    PAYMENT_TERM_UPDATE: (termId: string) => `/settings/commodities/payment-terms/${termId}`,
    
    // AI Helpers
    AI_DETECT_CATEGORY: '/settings/commodities/ai/detect-category',
    AI_SUGGEST_HSN: '/settings/commodities/ai/suggest-hsn',
    AI_SUGGEST_INTERNATIONAL: '/settings/commodities/ai/suggest-international-fields',
    AI_SUGGEST_PARAMETERS: (commodityId: string) => `/settings/commodities/${commodityId}/ai/suggest-parameters`,
    
    // Unit Conversion
    CALCULATE_CONVERSION: (commodityId: string) => `/settings/commodities/${commodityId}/calculate-conversion`,
    UNITS_LIST: '/settings/commodities/units/list',
    
    // Bulk Operations
    BULK_UPLOAD: '/settings/commodities/bulk/upload',
    BULK_DOWNLOAD: '/settings/commodities/bulk/download',
    BULK_VALIDATE: '/settings/commodities/bulk/validate',
  },
  
  // Location endpoints
  LOCATIONS: {
    LIST: '/settings/locations',
    CREATE: '/settings/locations',
    GET: (locationId: string) => `/settings/locations/${locationId}`,
    UPDATE: (locationId: string) => `/settings/locations/${locationId}`,
    DELETE: (locationId: string) => `/settings/locations/${locationId}`,
    
    // Google Places integration
    SEARCH_GOOGLE: '/settings/locations/search-google',
    FETCH_DETAILS: '/settings/locations/fetch-details',
  },
} as const;
