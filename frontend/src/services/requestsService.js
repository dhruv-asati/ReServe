import { api, mockRequest, USE_MOCKS } from './api';
import { INCOMING_REQUESTS, OUTGOING_REQUESTS, COMPLETED_REQUESTS } from '@/data/requests';

/**
 * Fetch incoming rescue requests.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); same shape later.
 */
export function getIncomingRequests() {
  if (USE_MOCKS) return mockRequest(INCOMING_REQUESTS, { delay: 450 });
  return api.get('/requests/incoming').then((response) => response.data);
}

/**
 * Fetch outgoing rescue requests.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); same shape later.
 */
export function getOutgoingRequests() {
  if (USE_MOCKS) return mockRequest(OUTGOING_REQUESTS, { delay: 450 });
  return api.get('/requests/outgoing').then((response) => response.data);
}

/**
 * Fetch completed rescue requests.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); same shape later.
 */
export function getCompletedRequests() {
  if (USE_MOCKS) return mockRequest(COMPLETED_REQUESTS, { delay: 450 });
  return api.get('/requests/completed').then((response) => response.data);
}
