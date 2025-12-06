/**
 * Auth Service - API calls to backend
 * All endpoints match backend/modules/settings/router.py and backend/modules/auth/router.py
 */

import apiClient from './apiClient';
import { API_CONFIG, API_ENDPOINTS } from '@/config/api';
import type {
  LoginRequest,
  LoginResponse,
  LoginWith2FAResponse,
  RefreshTokenRequest,
  TokenResponse,
  User,
  SessionListResponse,
  LogoutResponse,
  ChangePasswordRequest,
  ChangePasswordResponse,
} from '@/types/auth';

class AuthService {
  /**
   * Login with email and password (Internal users only)
   * POST /api/v1/settings/auth/login
   */
  async login(credentials: LoginRequest): Promise<LoginResponse | LoginWith2FAResponse> {
    const response = await apiClient.post<LoginResponse | LoginWith2FAResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      credentials
    );
    return response.data;
  }

  /**
   * Refresh access token
   * POST /api/v1/auth/refresh
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(
      API_ENDPOINTS.AUTH.REFRESH,
      { refresh_token: refreshToken } as RefreshTokenRequest
    );
    return response.data;
  }

  /**
   * Get current user details
   * GET /api/v1/settings/auth/me
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(API_ENDPOINTS.AUTH.ME);
    return response.data;
  }

  /**
   * Logout from current device
   * DELETE /api/v1/auth/logout
   */
  async logout(): Promise<LogoutResponse> {
    const response = await apiClient.delete<LogoutResponse>(API_ENDPOINTS.AUTH.LOGOUT);
    return response.data;
  }

  /**
   * Logout from all devices
   * DELETE /api/v1/auth/sessions/all
   */
  async logoutAll(): Promise<LogoutResponse> {
    const response = await apiClient.delete<LogoutResponse>(API_ENDPOINTS.AUTH.LOGOUT_ALL);
    return response.data;
  }

  /**
   * Get all active sessions
   * GET /api/v1/auth/sessions
   */
  async getSessions(): Promise<SessionListResponse> {
    const response = await apiClient.get<SessionListResponse>(API_ENDPOINTS.SESSIONS.LIST);
    return response.data;
  }

  /**
   * Logout from specific device
   * DELETE /api/v1/auth/sessions/{session_id}
   */
  async logoutSession(sessionId: string): Promise<LogoutResponse> {
    const response = await apiClient.delete<LogoutResponse>(
      API_ENDPOINTS.SESSIONS.DELETE(sessionId)
    );
    return response.data;
  }

  /**
   * Change password
   * POST /api/v1/settings/auth/change-password
   */
  async changePassword(data: ChangePasswordRequest): Promise<ChangePasswordResponse> {
    const response = await apiClient.post<ChangePasswordResponse>(
      API_ENDPOINTS.AUTH.CHANGE_PASSWORD,
      data
    );
    return response.data;
  }

  /**
   * Store tokens in localStorage
   */
  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(API_CONFIG.TOKEN_STORAGE_KEY, accessToken);
    localStorage.setItem(API_CONFIG.REFRESH_TOKEN_STORAGE_KEY, refreshToken);
  }

  /**
   * Store user in localStorage
   */
  storeUser(user: User): void {
    localStorage.setItem(API_CONFIG.USER_STORAGE_KEY, JSON.stringify(user));
  }

  /**
   * Get stored tokens
   */
  getStoredTokens(): { accessToken: string | null; refreshToken: string | null } {
    return {
      accessToken: localStorage.getItem(API_CONFIG.TOKEN_STORAGE_KEY),
      refreshToken: localStorage.getItem(API_CONFIG.REFRESH_TOKEN_STORAGE_KEY),
    };
  }

  /**
   * Get stored user
   */
  getStoredUser(): User | null {
    const userStr = localStorage.getItem(API_CONFIG.USER_STORAGE_KEY);
    if (!userStr) return null;
    
    try {
      return JSON.parse(userStr) as User;
    } catch {
      return null;
    }
  }

  /**
   * Clear all stored auth data
   */
  clearStorage(): void {
    localStorage.removeItem(API_CONFIG.TOKEN_STORAGE_KEY);
    localStorage.removeItem(API_CONFIG.REFRESH_TOKEN_STORAGE_KEY);
    localStorage.removeItem(API_CONFIG.USER_STORAGE_KEY);
  }

  /**
   * Get 2FA status
   */
  async get2FAStatus(): Promise<{ enabled: boolean }> {
    const response = await apiClient.get(API_ENDPOINTS.AUTH.TWO_FACTOR_STATUS);
    return response.data;
  }

  /**
   * Setup 2FA - Get QR code and secret
   */
  async setup2FA(): Promise<{ qr_code: string; secret: string }> {
    const response = await apiClient.post(API_ENDPOINTS.AUTH.TWO_FACTOR_SETUP);
    return response.data;
  }

  /**
   * Verify and enable 2FA
   */
  async verify2FA(code: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.TWO_FACTOR_VERIFY, { code });
  }

  /**
   * Disable 2FA
   */
  async disable2FA(): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.AUTH.TWO_FACTOR_DISABLE);
  }

  /**
   * Request password reset email
   */
  async forgotPassword(email: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email });
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, {
      token,
      new_password: newPassword,
    });
  }

  /**
   * Verify email with token
   */
  async verifyEmail(token: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.VERIFY_EMAIL, { token });
  }
}

export const authService = new AuthService();
