import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';
import { PATHS } from '@/routes/paths';

/**
 * Gate for the application shell. Frontend-only: it checks the mock session
 * from AuthContext, not a real token. Unauthenticated visitors are bounced
 * to /login with the attempted path, so Login can send them back after
 * signing in.
 */
export default function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to={PATHS.LOGIN} state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
