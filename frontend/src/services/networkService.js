import { api, mockRequest, USE_MOCKS } from './api';
import { NETWORK_LOCATIONS } from '@/data/network';
import { NETWORK_ORGANIZATIONS } from '@/data/networkDirectory';

/**
 * Fetch provider/recipient/partner/hub locations for the map.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js). The real request stays
 * dormant until the backend is live and `VITE_USE_MOCKS=false` is set.
 */
export function getNetworkLocations() {
  if (USE_MOCKS) return mockRequest(NETWORK_LOCATIONS, { delay: 550 });
  return api.get('/network/locations').then((response) => response.data);
}

/**
 * Fetch every organization in the Network Directory (`/app/network`).
 *
 * Mock by default — hardcoded demo organizations (see
 * data/networkDirectory.js), same shape a real "list organizations" endpoint
 * would return later. The page filters and groups the result itself, so no
 * query parameters are needed here. No real directory is contacted while
 * `USE_MOCKS` is true.
 */
export function getNetworkOrganizations() {
  if (USE_MOCKS) return mockRequest(NETWORK_ORGANIZATIONS, { delay: 500 });
  return api.get('/network/organizations').then((response) => response.data);
}
