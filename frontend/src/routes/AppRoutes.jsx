import { Routes, Route, Navigate } from 'react-router-dom';

import PublicLayout from '@/layouts/PublicLayout';
import AppLayout from '@/layouts/AppLayout';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import Placeholder from '@/pages/Placeholder';
import NotFound from '@/pages/NotFound';
import { PATHS } from '@/routes/paths';
import ProtectedRoute from '@/routes/ProtectedRoute';

/**
 * The full route table for ReServe.
 *
 * Every section already has its slot, so later steps swap a Placeholder for
 * a real page without touching routing. Nested paths are declared relative
 * to their layout, which is why the patterns below strip the leading segment.
 */
export default function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route element={<PublicLayout />}>
        <Route path={PATHS.LANDING} element={<Landing />} />
        <Route path={PATHS.LOGIN} element={<Login />} />
        <Route path={PATHS.REGISTER} element={<Register />} />
      </Route>

      {/* Application — gated behind the mock session */}
      <Route element={<ProtectedRoute />}>
        <Route path={PATHS.DASHBOARD} element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route
            path="rescues"
            element={
              <Placeholder
                title="Rescue Requests"
                description="Queue of incoming and active rescues."
              />
            }
          />
          <Route
            path="rescues/new"
            element={
              <Placeholder
                title="Create Rescue"
                description="Log surplus and open a rescue window."
              />
            }
          />
          <Route
            path="rescues/:rescueId"
            element={
              <Placeholder
                title="Resource Details"
                description="A single resource and its constraints."
              />
            }
          />
          <Route
            path="rescues/:rescueId/matching"
            element={
              <Placeholder
                title="Matching Results"
                description="Allocation plan with the reasoning behind each split."
              />
            }
          />
          <Route
            path="matching"
            element={
              <Placeholder
                title="Matching"
                description="Planner queue: rescues awaiting or under allocation."
              />
            }
          />
          <Route
            path="operations"
            element={
              <Placeholder
                title="Live Operations"
                description="In-flight rescues and reallocation events."
              />
            }
          />
          <Route
            path="network"
            element={
              <Placeholder
                title="Rescue Network"
                description="Map of providers, recipients, partners and hubs."
              />
            }
          />
          <Route
            path="analytics"
            element={
              <Placeholder
                title="Analytics"
                description="Impact metrics and predictive surplus windows."
              />
            }
          />
          <Route
            path="profile"
            element={
              <Placeholder
                title="Profile"
                description="Organization details and capabilities."
              />
            }
          />
        </Route>
      </Route>

      {/* Legacy / convenience redirect */}
      <Route
        path="/dashboard"
        element={<Navigate to={PATHS.DASHBOARD} replace />}
      />

      <Route path={PATHS.NOT_FOUND} element={<NotFound />} />
    </Routes>
  );
}
