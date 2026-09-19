import { mockRequest } from './api';
import { ACTIVE_OPERATIONS } from '@/data/operations';

/** Fetch currently active rescue operations. Mock for now; same shape later. */
export function getActiveOperations() {
  return mockRequest(ACTIVE_OPERATIONS, { delay: 550 });
}
