import { api, mockRequest, USE_MOCKS } from './api';
import { AT_RISK_RESOURCES, RESOURCE_DETAILS } from '@/data/resources';
import { toResourceDetails } from './resourceAdapter';

/**
 * Fetch resources approaching their rescue deadline.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); the real request is
 * dormant until `VITE_USE_MOCKS=false` and a backend is actually running.
 */
export function getAtRiskResources() {
  if (USE_MOCKS) return mockRequest(AT_RISK_RESOURCES, { delay: 550 });
  return api.get('/resources/at-risk').then((response) => response.data);
}

/**
 * Fetch one resource's full detail record by id, for the Resource Details
 * page. Mock resolves `null` when the id isn't found (rather than
 * rejecting) so the page can render a normal "not found" empty state
 * instead of treating a bad id as a failed request. The live branch relies
 * on the backend returning the same shape (404s are normalised to a
 * rejected promise by the shared api client, not to `null`).
 */
export function getResourceDetails(id) {
  if (USE_MOCKS) {
    const record = RESOURCE_DETAILS.find((item) => item.id === id) ?? null;
    return mockRequest(record, { delay: 500 });
  }
  return api
    .get(`/resources/${encodeURIComponent(id)}`)
    .then((response) => toResourceDetails(response.data));
}
