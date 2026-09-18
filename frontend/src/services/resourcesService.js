import { mockRequest } from './api';
import { AT_RISK_RESOURCES } from '@/data/resources';

/** Fetch resources approaching their rescue deadline. Mock for now. */
export function getAtRiskResources() {
  return mockRequest(AT_RISK_RESOURCES, { delay: 550 });
}
