import { mockRequest } from './api';
import { INCOMING_REQUESTS, OUTGOING_REQUESTS, COMPLETED_REQUESTS } from '@/data/requests';

/** Fetch incoming rescue requests. Mock for now; same shape later. */
export function getIncomingRequests() {
  return mockRequest(INCOMING_REQUESTS, { delay: 450 });
}

/** Fetch outgoing rescue requests. Mock for now; same shape later. */
export function getOutgoingRequests() {
  return mockRequest(OUTGOING_REQUESTS, { delay: 450 });
}

/** Fetch completed rescue requests. Mock for now; same shape later. */
export function getCompletedRequests() {
  return mockRequest(COMPLETED_REQUESTS, { delay: 450 });
}
