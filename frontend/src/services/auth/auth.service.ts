/**
 * Authentication Service for Cotton ERP
 */

import apiClient from '../api/client';
import type {
  User,
  SignupRequest,
  LoginRequest,
  TokenResponse,
  LoginWith2FAResponse,
  SendOTPRequest,
  VerifyOTPRequest,
  OTPResponse,
} from '../../types/user';

const AUTH_BASE = '/settings/auth';

export const authService = {
  /**
   * Register a new user (INTERNAL users)
   */
  async signup(data: SignupRequest): Promise<User> {
    const response = await apiClient.post<User>(`${AUTH_BASE}/signup`, data);
    return response.data;
  },

  /**
   * Register a new INTERNAL user with password policy
   */
  async signupInternal(data: SignupRequest): Promise<User> {
    const response = await apiClient.post<User>(`${AUTH_BASE}/signup-internal`, data);
    return response.data;
  },

  /**
   * Login with email and password (INTERNAL users)
   */
  async login(data: LoginRequest): Promise<TokenResponse | LoginWith2FAResponse> {
    const response = await apiClient.post<TokenResponse | LoginWith2FAResponse>(
      `${AUTH_BASE}/login`,
      data
    );
    const result = response.data;

    // Store tokens if login successful (no 2FA required)
    if ('access_token' in result) {
      localStorage.setItem('access_token', result.access_token);
      localStorage.setItem('refresh_token', result.refresh_token);
    }

    return result;
  },

  /**
   * Send OTP to mobile number (EXTERNAL users)
   */
  async sendOTP(data: SendOTPRequest): Promise<OTPResponse> {
    const response = await apiClient.post<OTPResponse>(`${AUTH_BASE}/send-otp`, data);
    return response.data;
  },

  /**
   * Verify OTP and login (EXTERNAL users)
   */
  async verifyOTP(data: VerifyOTPRequest): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(`${AUTH_BASE}/verify-otp`, data);
    const result = response.data;

    // Store tokens on successful OTP verification
    localStorage.setItem('access_token', result.access_token);
    localStorage.setItem('refresh_token', result.refresh_token);

    return result;
  },

  /**
   * Verify 2FA PIN
   */
  async verify2FA(email: string, pin: string): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(`${AUTH_BASE}/2fa-verify`, {
      email,
      pin,
    });
    const result = response.data;

    localStorage.setItem('access_token', result.access_token);
    localStorage.setItem('refresh_token', result.refresh_token);

    return result;
  },

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(`${AUTH_BASE}/me`);
    return response.data;
  },

  /**
   * Logout current session
   */
  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post(`${AUTH_BASE}/logout`, null, {
          params: { token: refreshToken },
        });
      } catch {
        // Ignore logout errors - clear tokens anyway
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  /**
   * Logout from all devices
   */
  async logoutAll(): Promise<{ message: string; tokens_revoked: number }> {
    const response = await apiClient.post<{ message: string; tokens_revoked: number }>(
      `${AUTH_BASE}/logout-all`
    );
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    return response.data;
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};

export default authService;
