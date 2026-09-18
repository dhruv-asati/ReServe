import { mockRequest } from './api';
import { DASHBOARD_STATS } from '@/data/dashboard';

/**
 * Fetch the dashboard overview stats.
 *
 * Resolves mock data through the same simulated-latency path every other
 * service will use, so the loading state on Dashboard.jsx is exercised now
 * and nothing changes there when a real endpoint lands.
 */
export function getDashboardOverview() {
  return mockRequest(DASHBOARD_STATS, { delay: 500 });
}
