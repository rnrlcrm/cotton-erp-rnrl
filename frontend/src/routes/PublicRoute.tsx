/**
 * Public Route Component
 *
 * Routes accessible without authentication.
 * Redirects to dashboard if already authenticated.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../services/auth/auth.service';

interface PublicRouteProps {
  children: React.ReactNode;
  redirectIfAuthenticated?: boolean;
}

const PublicRoute: React.FC<PublicRouteProps> = ({
  children,
  redirectIfAuthenticated = false,
}) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();
  const from = (location.state as { from?: Location })?.from?.pathname || '/dashboard';

  if (isAuthenticated && redirectIfAuthenticated) {
    return <Navigate to={from} replace />;
  }

  return <>{children}</>;
};

export default PublicRoute;
