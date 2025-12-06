/**
 * Auth Context
 * 
 * Manages authentication state and user capabilities
 */

import { createContext, useState, useEffect, ReactNode } from 'react';
import type { User, LoginRequest, LoginWith2FAResponse } from '@/types/auth';
import { authService } from '@/services/api/authService';
import capabilitiesService from '@/services/api/capabilitiesService';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  refreshCapabilities: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  refreshCapabilities: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        await loadUserWithCapabilities();
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      localStorage.removeItem('access_token');
    } finally {
      setLoading(false);
    }
  };

  const loadUserWithCapabilities = async () => {
    try {
      // Get user profile from /auth/me
      const userProfile = await authService.getCurrentUser();
      
      // Get user capabilities from /capabilities/me
      const capabilitiesData = await capabilitiesService.getMyCapabilities();
      
      // Merge user data with capabilities
      setUser({
        ...userProfile,
        capabilities: capabilitiesData.capabilities || [],
      });
    } catch (error) {
      console.error('Failed to load user capabilities:', error);
      throw error;
    }
  };

  const login = async (credentials: LoginRequest) => {
    try {
      const response = await authService.login(credentials);
      
      // Check if 2FA is required
      if ('two_fa_required' in response && response.two_fa_required) {
        throw new Error('2FA required - not implemented yet');
      }
      
      // Type-safe access to login response
      if ('access_token' in response) {
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
        
        // Load user with capabilities
        await loadUserWithCapabilities();
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const refreshCapabilities = async () => {
    if (!user) return;
    await loadUserWithCapabilities();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        refreshCapabilities,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
