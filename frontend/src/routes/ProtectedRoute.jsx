import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/context/AuthContext';
import { PATHS } from '@/routes/paths';

/**
 * Gate for the application shell. Requires a signed-in user (a backend session
 * with stored JWT tokens — see context/AuthContext). Unauthenticated visitors
 * are bounced to /login with the attempted path, so Login can send them back
 * after signing in.
 *
 * Optional role gate: `<ProtectedRoute allowedRoles={['provider']} />` also
 * requires the user's role (frontend values: 'provider' | 'recipient' |
 * 'rescue-partner' | 'admin') to be listed, and sends everyone else to the
 * dashboard. No route uses it yet — the backend already enforces roles on each
 * endpoint (403 FORBIDDEN_ROLE); this only hides pages that would be useless.
 */
export default function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to={PATHS.LOGIN} state={{ from: location.pathname }} replace />;
  }

  if (allowedRoles?.length && !allowedRoles.includes(user?.role)) {
    return <Navigate to={PATHS.DASHBOARD} replace />;
  }

  return <Outlet />;
}
