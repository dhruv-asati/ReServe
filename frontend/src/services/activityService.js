import { mockRequest } from './api';
import { RECENT_ACTIVITY } from '@/data/activity';

/** Fetch the recent rescue activity feed. Mock for now. */
export function getRecentActivity() {
  return mockRequest(RECENT_ACTIVITY, { delay: 550 });
}
