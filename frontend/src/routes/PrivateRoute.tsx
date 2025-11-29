/**
 * Private Route Component
 *
 * Protects routes that require authentication.
 * Redirects to login if not authenticated.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../services/auth/auth.service';

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();

  if (!isAuthenticated) {
    // Redirect to login with return URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateRoute;
