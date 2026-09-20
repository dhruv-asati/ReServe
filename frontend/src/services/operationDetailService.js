import { mockRequest } from './api';
import {
  DEMO_OPERATION,
  DEMO_OPERATION_STAGES,
  DEMO_OPERATION_EVENTS,
  DEMO_OPERATION_LOCATIONS,
  DEMO_OPERATION_ROUTE,
} from '@/data/operationDetail';
import { BASE_ALLOCATION_SUMMARY } from './reallocationDemoService';

/**
 * Fetch the demo rescue operation (RS-1024) for the Operations Control
 * Center. Mock for now — hardcoded illustrative data, same shape a real
 * "get operation by id" endpoint would return later.
 *
 * The operation carries its allocation summary (who holds how many portions),
 * so the details view can state the allocation the rest of the page talks
 * about. It is built from the same demo allocation the Smart Matching page
 * reads, and is replaced with the updated one while the recipient-unavailable
 * scenario is running (see services/reallocationDemoService.js).
 */
export function getDemoOperation() {
  return mockRequest({ ...DEMO_OPERATION, allocation: BASE_ALLOCATION_SUMMARY }, { delay: 450 });
}

/** Fetch the demo operation's full 7-stage lifecycle (completed/current/upcoming). */
export function getDemoOperationStages() {
  return mockRequest(DEMO_OPERATION_STAGES, { delay: 500 });
}

/** Fetch the demo operation's event feed — what has happened, newest first. */
export function getDemoOperationEvents() {
  return mockRequest(DEMO_OPERATION_EVENTS, { delay: 500 });
}

/** Fetch the demo operation's map points (provider, recipient, partner). */
export function getDemoOperationLocations() {
  return mockRequest(DEMO_OPERATION_LOCATIONS, { delay: 500 });
}

/** Fetch the demo operation's illustrative route waypoints (Hotel XYZ → NGO A). */
export function getDemoOperationRoute() {
  return mockRequest(DEMO_OPERATION_ROUTE, { delay: 500 });
}
