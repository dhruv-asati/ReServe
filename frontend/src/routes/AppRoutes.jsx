import { Routes, Route, Navigate } from 'react-router-dom';

import PublicLayout from '@/layouts/PublicLayout';
import AppLayout from '@/layouts/AppLayout';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import CreateRescue from '@/pages/CreateRescue';
import AIAnalysis from '@/pages/AIAnalysis';
import LiveAIAnalysis from '@/pages/LiveAIAnalysis';
import ResourceDetails from '@/pages/ResourceDetails';
import RescueRequests from '@/pages/RescueRequests';
import Matching from '@/pages/Matching';
import LiveMatching from '@/pages/LiveMatching';
import Operations from '@/pages/Operations';
import Network from '@/pages/Network';
import Analytics from '@/pages/Analytics';
import Profile from '@/pages/Profile';
import Placeholder from '@/pages/Placeholder';
import NotFound from '@/pages/NotFound';
import { PATHS } from '@/routes/paths';
import ProtectedRoute from '@/routes/ProtectedRoute';
import { USE_MOCKS } from '@/services/api';

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
          <Route path="rescues" element={<RescueRequests />} />
          <Route path="rescues/new" element={<CreateRescue />} />
          {/* Live data (VITE_USE_MOCKS=false) uses the real Gemini analysis and matching
              engine; mock mode keeps the original scripted demo pages. */}
          <Route path="rescues/:rescueId" element={USE_MOCKS ? <AIAnalysis /> : <LiveAIAnalysis />} />
          <Route
            path="rescues/:rescueId/matching"
            element={
              USE_MOCKS ? (
                <Placeholder
                  title="Matching Results"
                  description="Allocation plan with the reasoning behind each split."
                />
              ) : (
                <LiveMatching />
              )
            }
          />
          <Route path="matching" element={USE_MOCKS ? <Matching /> : <LiveMatching />} />
          <Route path="operations" element={<Operations />} />
          <Route path="network" element={<Network />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Route>

      {/* Resource Details — standalone route (not nested under /app), still
          gated behind the mock session and using the same app shell. */}
      <Route element={<ProtectedRoute />}>
        <Route path={PATHS.RESOURCE_DETAIL} element={<AppLayout />}>
          <Route index element={<ResourceDetails />} />
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
