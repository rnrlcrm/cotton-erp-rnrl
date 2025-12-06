/**
 * Capabilities API Service
 * 
 * Handles all capability-related API calls
 */

import apiClient from './apiClient';
import type {
  Capability,
  UserCapabilitiesResponse,
  GrantCapabilityRequest,
  CapabilityCheckRequest,
  CapabilityCheckResponse,
  RoleCapability,
} from '@/types/capability';

const BASE_URL = '/capabilities';

export const capabilitiesService = {
  /**
   * Get all available capabilities
   */
  async getAllCapabilities(): Promise<Capability[]> {
    const response = await apiClient.get<Capability[]>(BASE_URL);
    return response.data;
  },

  /**
   * Get current user's capabilities
   */
  async getMyCapabilities(): Promise<UserCapabilitiesResponse> {
    const response = await apiClient.get<UserCapabilitiesResponse>(`${BASE_URL}/me`);
    return response.data;
  },

  /**
   * Get specific user's capabilities
   */
  async getUserCapabilities(userId: string): Promise<UserCapabilitiesResponse> {
    const response = await apiClient.get<UserCapabilitiesResponse>(`${BASE_URL}/users/${userId}`);
    return response.data;
  },

  /**
   * Grant capability to user
   */
  async grantCapabilityToUser(
    userId: string,
    request: GrantCapabilityRequest
  ): Promise<any> {
    const response = await apiClient.post(
      `${BASE_URL}/users/${userId}/grant`,
      request
    );
    return response.data;
  },

  /**
   * Revoke capability from user
   */
  async revokeCapabilityFromUser(
    userId: string,
    capabilityCode: string
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/users/${userId}/revoke`, {
      capability_code: capabilityCode,
    });
  },

  /**
   * Check if user has specific capability
   */
  async checkUserCapability(
    userId: string,
    capabilityCode: string
  ): Promise<CapabilityCheckResponse> {
    const response = await apiClient.post<CapabilityCheckResponse>(
      `${BASE_URL}/users/${userId}/check`,
      { capability_code: capabilityCode } as CapabilityCheckRequest
    );
    return response.data;
  },

  /**
   * Grant capability to role
   */
  async grantCapabilityToRole(
    roleId: string,
    request: GrantCapabilityRequest
  ): Promise<RoleCapability> {
    const response = await apiClient.post<RoleCapability>(
      `${BASE_URL}/roles/${roleId}/grant`,
      request
    );
    return response.data;
  },

  /**
   * Revoke capability from role
   */
  async revokeCapabilityFromRole(
    roleId: string,
    capabilityCode: string
  ): Promise<void> {
    await apiClient.delete(`${BASE_URL}/roles/${roleId}/capabilities/${capabilityCode}`);
  },

  /**
   * Get role's capabilities
   */
  async getRoleCapabilities(roleId: string): Promise<RoleCapability[]> {
    const response = await apiClient.get<RoleCapability[]>(`${BASE_URL}/roles/${roleId}`);
    return response.data;
  },

  /**
   * Get capabilities grouped by category
   */
  async getCapabilitiesByCategory(): Promise<Record<string, Capability[]>> {
    const capabilities = await this.getAllCapabilities();
    return capabilities.reduce((acc, cap) => {
      if (!acc[cap.category]) {
        acc[cap.category] = [];
      }
      acc[cap.category].push(cap);
      return acc;
    }, {} as Record<string, Capability[]>);
  },
};

export default capabilitiesService;
