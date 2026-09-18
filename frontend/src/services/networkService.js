import { mockRequest } from './api';
import { NETWORK_LOCATIONS } from '@/data/network';

/** Fetch provider/recipient/partner/hub locations for the map. Mock for now. */
export function getNetworkLocations() {
  return mockRequest(NETWORK_LOCATIONS, { delay: 550 });
}
