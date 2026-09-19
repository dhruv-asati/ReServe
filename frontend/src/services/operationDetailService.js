import { mockRequest } from './api';
import {
  DEMO_OPERATION,
  DEMO_OPERATION_STAGES,
  DEMO_OPERATION_LOCATIONS,
  DEMO_OPERATION_ROUTE,
} from '@/data/operationDetail';

/**
 * Fetch the demo rescue operation (RS-1024) for the Operations Control
 * Center. Mock for now — hardcoded illustrative data, same shape a real
 * "get operation by id" endpoint would return later.
 */
export function getDemoOperation() {
  return mockRequest(DEMO_OPERATION, { delay: 450 });
}

/** Fetch the demo operation's full 7-stage lifecycle (completed/current/upcoming). */
export function getDemoOperationStages() {
  return mockRequest(DEMO_OPERATION_STAGES, { delay: 500 });
}

/** Fetch the demo operation's map points (provider, recipient, partner). */
export function getDemoOperationLocations() {
  return mockRequest(DEMO_OPERATION_LOCATIONS, { delay: 500 });
}

/** Fetch the demo operation's illustrative route waypoints (Hotel XYZ → NGO A). */
export function getDemoOperationRoute() {
  return mockRequest(DEMO_OPERATION_ROUTE, { delay: 500 });
}
