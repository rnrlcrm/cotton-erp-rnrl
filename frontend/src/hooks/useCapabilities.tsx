/**
 * Capability-based Permission Hooks
 * 
 * Replaces role-based permission system with fine-grained capabilities
 */

import { useContext, useMemo } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import type { CapabilityCode } from '@/types/capability';

/**
 * Hook to check if current user has a specific capability
 */
export function useHasCapability(capabilityCode: string | CapabilityCode): boolean {
  const { user } = useContext(AuthContext);
  
  return useMemo(() => {
    if (!user?.capabilities) return false;
    return user.capabilities.includes(capabilityCode);
  }, [user?.capabilities, capabilityCode]);
}

/**
 * Hook to check if current user has ANY of the specified capabilities
 */
export function useHasAnyCapability(capabilityCodes: (string | CapabilityCode)[]): boolean {
  const { user } = useContext(AuthContext);
  
  return useMemo(() => {
    if (!user?.capabilities) return false;
    return capabilityCodes.some(code => user.capabilities.includes(code));
  }, [user?.capabilities, capabilityCodes]);
}

/**
 * Hook to check if current user has ALL of the specified capabilities
 */
export function useHasAllCapabilities(capabilityCodes: (string | CapabilityCode)[]): boolean {
  const { user } = useContext(AuthContext);
  
  return useMemo(() => {
    if (!user?.capabilities) return false;
    return capabilityCodes.every(code => user.capabilities.includes(code));
  }, [user?.capabilities, capabilityCodes]);
}

/**
 * Hook to get all capabilities of current user
 */
export function useUserCapabilities(): string[] {
  const { user } = useContext(AuthContext);
  return user?.capabilities || [];
}

/**
 * Hook for admin-level capability check
 */
export function useIsAdmin(): boolean {
  return useHasAnyCapability([
    CapabilityCode.ADMIN_VIEW_ALL_DATA,
    CapabilityCode.ADMIN_MANAGE_USERS,
    CapabilityCode.ADMIN_MANAGE_ROLES,
    CapabilityCode.ADMIN_MANAGE_CAPABILITIES,
  ]);
}

/**
 * Hook to check capability with component guard
 * Returns { hasCapability, CapabilityGuard } for conditional rendering
 */
export function useCapabilityGuard(capabilityCode: string | CapabilityCode) {
  const hasCapability = useHasCapability(capabilityCode);
  
  const CapabilityGuard = ({ children }: { children: React.ReactNode }) => {
    if (!hasCapability) return null;
    return <>{children}</>;
  };
  
  return { hasCapability, CapabilityGuard };
}

/**
 * Component to conditionally render based on capability
 */
export function RequireCapability({
  capability,
  children,
  fallback = null,
}: {
  capability: string | CapabilityCode;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const hasCapability = useHasCapability(capability);
  
  if (!hasCapability) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}

/**
 * Component to conditionally render based on ANY capability
 */
export function RequireAnyCapability({
  capabilities,
  children,
  fallback = null,
}: {
  capabilities: (string | CapabilityCode)[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const hasAnyCapability = useHasAnyCapability(capabilities);
  
  if (!hasAnyCapability) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}

/**
 * Component to conditionally render based on ALL capabilities
 */
export function RequireAllCapabilities({
  capabilities,
  children,
  fallback = null,
}: {
  capabilities: (string | CapabilityCode)[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const hasAllCapabilities = useHasAllCapabilities(capabilities);
  
  if (!hasAllCapabilities) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}
