/**
 * Every route in ReServe, in one place. Components and links must import
 * from here instead of writing string paths, so a rename never breaks a link.
 */
export const PATHS = {
  // Public
  LANDING: '/',
  LOGIN: '/login',
  REGISTER: '/register',

  // Application shell
  DASHBOARD: '/app',
  CREATE_RESCUE: '/app/rescues/new',
  RESCUE_REQUESTS: '/app/rescues',
  RESOURCE_DETAILS: '/app/rescues/:rescueId',
  MATCHING: '/app/matching',
  MATCHING_RESULTS: '/app/rescues/:rescueId/matching',
  LIVE_OPERATIONS: '/app/operations',
  RESCUE_NETWORK: '/app/network',
  ANALYTICS: '/app/analytics',
  PROFILE: '/app/profile',

  NOT_FOUND: '*',
};

/** Build a concrete path from a pattern: toPath(PATHS.RESOURCE_DETAILS, { rescueId: 'r-1' }) */
export function toPath(pattern, params = {}) {
  return Object.entries(params).reduce(
    (path, [key, value]) => path.replace(`:${key}`, encodeURIComponent(value)),
    pattern,
  );
}
