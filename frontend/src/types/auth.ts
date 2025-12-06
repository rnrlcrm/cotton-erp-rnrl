/**
 * Auth Types - Matching Backend Schemas
 * Based on backend/modules/settings/router.py and backend/modules/auth/router.py
 */

export interface User {
  id: string;
  email: string;
  full_name: string;
  user_type: 'SUPER_ADMIN' | 'INTERNAL' | 'EXTERNAL';
  role?: string; // Deprecated - use capabilities instead
  capabilities: string[]; // Array of capability codes
  is_active: boolean;
  organization_id?: string;
  business_partner_id?: string;
  allowed_modules?: string[];
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'bearer';
}

export interface LoginWith2FAResponse {
  two_fa_required: true;
  message: string;
  email: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'bearer';
}

export interface UserSession {
  id: string;
  device_name: string;
  device_type: 'mobile' | 'desktop' | 'tablet';
  device_os: string;
  browser_name: string;
  browser_version: string;
  ip_address: string;
  last_active: string;
  created_at: string;
  is_current: boolean;
}

export interface SessionListResponse {
  sessions: UserSession[];
  total: number;
}

export interface LogoutResponse {
  message: string;
  sessions_revoked: number;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  message: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthError {
  message: string;
  code?: string;
  details?: Record<string, string[]>;
}
