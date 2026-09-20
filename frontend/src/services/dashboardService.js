import { api, mockRequest, USE_MOCKS } from './api';
import { DASHBOARD_STATS } from '@/data/dashboard';

/**
 * Fetch the dashboard overview stats.
 *
 * Resolves mock data through the same simulated-latency path every other
 * service will use, so the loading state on Dashboard.jsx is exercised now
 * and nothing changes there when a real endpoint lands. While `USE_MOCKS`
 * is true (the default — see services/api.js), the real request below is
 * never made; flipping `VITE_USE_MOCKS=false` once the backend exists is
 * the only change needed here.
 */
export function getDashboardOverview() {
  if (USE_MOCKS) return mockRequest(DASHBOARD_STATS, { delay: 500 });
  return api.get('/dashboard/overview').then((response) => response.data);
}
