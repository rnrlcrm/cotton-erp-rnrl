/**
 * Capability System Types
 * 
 * Capability-based authorization (replacing role-based)
 */

export interface Capability {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCapability {
  id: string;
  user_id: string;
  capability_id: string;
  capability_code: string;
  capability_name: string;
  granted_at: string;
  granted_by: string | null;
  granted_by_name?: string;
  expires_at: string | null;
  revoked_at: string | null;
  reason: string | null;
}

export interface RoleCapability {
  id: string;
  role_id: string;
  capability_id: string;
  capability_code: string;
  capability_name: string;
  granted_at: string;
  granted_by: string | null;
  granted_by_name?: string;
}

export interface UserCapabilitiesResponse {
  user_id: string;
  user_email: string;
  user_name: string;
  capabilities: string[]; // Array of capability codes
  direct_capabilities: UserCapability[];
  role_capabilities: RoleCapability[];
  total_count: number;
}

export interface GrantCapabilityRequest {
  capability_code: string;
  expires_at?: string | null;
  reason?: string;
}

export interface CapabilityCheckRequest {
  capability_code: string;
}

export interface CapabilityCheckResponse {
  has_capability: boolean;
  capability_code: string;
  source: 'direct' | 'role' | 'none';
  expires_at?: string | null;
}

// Capability Categories
export enum CapabilityCategory {
  AUTH = 'auth',
  ORGANIZATION = 'organization',
  PARTNER = 'partner',
  COMMODITY = 'commodity',
  LOCATION = 'location',
  AVAILABILITY = 'availability',
  REQUIREMENT = 'requirement',
  MATCHING = 'matching',
  SETTINGS = 'settings',
  INVOICE = 'invoice',
  CONTRACT = 'contract',
  PAYMENT = 'payment',
  SHIPMENT = 'shipment',
  DATA = 'data',
  PRIVACY = 'privacy',
  AUDIT = 'audit',
  ADMIN = 'admin',
  SYSTEM = 'system',
  PUBLIC = 'public',
}

// Common capability codes (matches backend definitions.py)
export enum CapabilityCode {
  // Auth
  AUTH_LOGIN = 'AUTH_LOGIN',
  AUTH_REGISTER = 'AUTH_REGISTER',
  AUTH_UPDATE_PROFILE = 'AUTH_UPDATE_PROFILE',
  
  // Organization
  ORG_CREATE = 'ORG_CREATE',
  ORG_READ = 'ORG_READ',
  ORG_UPDATE = 'ORG_UPDATE',
  ORG_DELETE = 'ORG_DELETE',
  ORG_MANAGE_USERS = 'ORG_MANAGE_USERS',
  ORG_MANAGE_ROLES = 'ORG_MANAGE_ROLES',
  
  // Partner
  PARTNER_CREATE = 'PARTNER_CREATE',
  PARTNER_READ = 'PARTNER_READ',
  PARTNER_UPDATE = 'PARTNER_UPDATE',
  PARTNER_DELETE = 'PARTNER_DELETE',
  PARTNER_APPROVE = 'PARTNER_APPROVE',
  
  // Commodity
  COMMODITY_CREATE = 'COMMODITY_CREATE',
  COMMODITY_READ = 'COMMODITY_READ',
  COMMODITY_UPDATE = 'COMMODITY_UPDATE',
  COMMODITY_DELETE = 'COMMODITY_DELETE',
  
  // Location
  LOCATION_CREATE = 'LOCATION_CREATE',
  LOCATION_READ = 'LOCATION_READ',
  LOCATION_UPDATE = 'LOCATION_UPDATE',
  LOCATION_DELETE = 'LOCATION_DELETE',
  
  // Availability
  AVAILABILITY_CREATE = 'AVAILABILITY_CREATE',
  AVAILABILITY_READ = 'AVAILABILITY_READ',
  AVAILABILITY_UPDATE = 'AVAILABILITY_UPDATE',
  AVAILABILITY_DELETE = 'AVAILABILITY_DELETE',
  AVAILABILITY_APPROVE = 'AVAILABILITY_APPROVE',
  AVAILABILITY_REJECT = 'AVAILABILITY_REJECT',
  
  // Requirement
  REQUIREMENT_CREATE = 'REQUIREMENT_CREATE',
  REQUIREMENT_READ = 'REQUIREMENT_READ',
  REQUIREMENT_UPDATE = 'REQUIREMENT_UPDATE',
  REQUIREMENT_DELETE = 'REQUIREMENT_DELETE',
  REQUIREMENT_APPROVE = 'REQUIREMENT_APPROVE',
  REQUIREMENT_REJECT = 'REQUIREMENT_REJECT',
  
  // Matching
  MATCHING_EXECUTE = 'MATCHING_EXECUTE',
  MATCHING_VIEW_RESULTS = 'MATCHING_VIEW_RESULTS',
  MATCHING_APPROVE_MATCH = 'MATCHING_APPROVE_MATCH',
  MATCHING_REJECT_MATCH = 'MATCHING_REJECT_MATCH',
  
  // Settings
  SETTINGS_VIEW_ALL = 'SETTINGS_VIEW_ALL',
  SETTINGS_MANAGE_ORGANIZATIONS = 'SETTINGS_MANAGE_ORGANIZATIONS',
  SETTINGS_MANAGE_COMMODITIES = 'SETTINGS_MANAGE_COMMODITIES',
  SETTINGS_MANAGE_LOCATIONS = 'SETTINGS_MANAGE_LOCATIONS',
  
  // Admin
  ADMIN_MANAGE_USERS = 'ADMIN_MANAGE_USERS',
  ADMIN_MANAGE_ROLES = 'ADMIN_MANAGE_ROLES',
  ADMIN_MANAGE_CAPABILITIES = 'ADMIN_MANAGE_CAPABILITIES',
  ADMIN_VIEW_ALL_DATA = 'ADMIN_VIEW_ALL_DATA',
  ADMIN_VIEW_SYSTEM_LOGS = 'ADMIN_VIEW_SYSTEM_LOGS',
  
  // System
  SYSTEM_API_ACCESS = 'SYSTEM_API_ACCESS',
  SYSTEM_EXPORT_DATA = 'SYSTEM_EXPORT_DATA',
  SYSTEM_IMPORT_DATA = 'SYSTEM_IMPORT_DATA',
}
