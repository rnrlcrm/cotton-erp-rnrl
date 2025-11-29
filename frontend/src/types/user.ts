/**
 * User Types for Cotton ERP
 */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  organization_id: string;
  is_active: boolean;
  parent_user_id: string | null;
  role: string | null;
  created_at: string;
  updated_at: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginWith2FAResponse {
  two_fa_required: boolean;
  message: string;
  email: string;
}

export interface SendOTPRequest {
  mobile_number: string;
  country_code?: string;
}

export interface VerifyOTPRequest {
  mobile_number: string;
  otp: string;
}

export interface OTPResponse {
  success: boolean;
  message: string;
  otp_sent_at?: string;
  expires_in_seconds: number;
}
