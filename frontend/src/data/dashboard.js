/**
 * Mock dashboard overview stats.
 *
 * Shape mirrors what the real endpoint will return, so swapping the service
 * call in dashboardService.js for a live request later needs no change here
 * or in Dashboard.jsx.
 */
export const DASHBOARD_STATS = {
  resourcesRescued: {
    value: 1284,
    unit: 'kg',
    delta: '+164 kg this week',
    tone: 'brand',
  },
  activeRescues: {
    value: 12,
    delta: '4 awaiting match',
    tone: 'active',
  },
  atRiskResources: {
    value: 5,
    delta: 'Expiring within 3 hours',
    tone: 'urgent',
  },
  successfulAllocations: {
    value: 342,
    delta: '96% success rate',
    tone: 'success',
  },
};
