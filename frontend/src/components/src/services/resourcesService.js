import { mockRequest } from './api';
import { AT_RISK_RESOURCES, RESOURCE_DETAILS } from '@/data/resources';

/** Fetch resources approaching their rescue deadline. Mock for now. */
export function getAtRiskResources() {
  return mockRequest(AT_RISK_RESOURCES, { delay: 550 });
}

/**
 * Fetch one resource's full detail record by id, for the Resource Details
 * page. Mock for now — resolves `null` when the id isn't found (rather than
 * rejecting) so the page can render a normal "not found" empty state
 * instead of treating a bad id as a failed request.
 */
export function getResourceDetails(id) {
  const record = RESOURCE_DETAILS.find((item) => item.id === id) ?? null;
  return mockRequest(record, { delay: 500 });
}
