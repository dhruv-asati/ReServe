import { api, mockRequest, USE_MOCKS } from './api';
import { RECENT_ACTIVITY } from '@/data/activity';

/**
 * Fetch the recent rescue activity feed.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js). The real request stays
 * dormant until the backend is live and `VITE_USE_MOCKS=false` is set.
 */
export function getRecentActivity() {
  if (USE_MOCKS) return mockRequest(RECENT_ACTIVITY, { delay: 550 });
  return api.get('/activity/recent').then((response) => response.data);
}
