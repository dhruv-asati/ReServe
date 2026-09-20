import { api, mockRequest, USE_MOCKS } from './api';
import { ACTIVE_OPERATIONS } from '@/data/operations';

/**
 * Fetch currently active rescue operations.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); same response shape
 * either way, so switching to the real endpoint later is a one-line change.
 */
export function getActiveOperations() {
  if (USE_MOCKS) return mockRequest(ACTIVE_OPERATIONS, { delay: 550 });
  return api.get('/operations/active').then((response) => response.data);
}
