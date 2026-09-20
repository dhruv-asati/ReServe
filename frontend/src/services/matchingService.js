import { mockRequest } from './api';
import { MATCH_RESOURCE, MATCH_CANDIDATES } from '@/data/matching';
import { URGENCY } from '@/utils/theme';

/** Minutes granted before pickup, by urgency tier — same tiers AIAnalysis uses. */
const RESCUE_WINDOW_MINUTES = {
  [URGENCY.CRITICAL]: 30,
  [URGENCY.HIGH]: 90,
  [URGENCY.MEDIUM]: 180,
  [URGENCY.LOW]: 360,
};

/**
 * The rescue window for an urgency tier, in minutes. Synchronous and shared,
 * so the RS-1024 reallocation demo checks pickup ETAs against exactly the
 * window Smart Matching shows — the two can never use different numbers.
 */
export function getRescueWindowMinutes(urgency) {
  return RESCUE_WINDOW_MINUTES[urgency] ?? RESCUE_WINDOW_MINUTES[URGENCY.MEDIUM];
}

/**
 * Ordered checklist the mock matching process "runs" through, top to
 * bottom. This is a purely cosmetic, frontend-only simulation — no
 * matching engine, AI model or backend call is involved at any step.
 */
export const MATCHING_STEPS = [
  { key: 'resource_analyzed', label: 'Resource Analyzed' },
  { key: 'recipients_searched', label: 'Eligible Recipients Searched' },
  { key: 'capacity_checked', label: 'Capacity Checked' },
  { key: 'window_checked', label: 'Rescue Window Checked' },
  { key: 'pickup_checked', label: 'Pickup Partners Checked' },
  { key: 'allocation_optimized', label: 'Allocation Optimized' },
];

/** How long each step "takes" before the next one starts, in ms. */
export const MATCHING_STEP_DURATION_MS = 650;

/**
 * Fetch the resource the Matching page runs its (mock) process against:
 * the demo batch of 80 portions of Vegetarian Meals (see data/matching.js).
 * No API call — `rescueWindowMinutes` is derived from the urgency tier the
 * same way mockAnalysis.js derives it for AIAnalysis.
 */
export function getMatchingResource() {
  const shaped = {
    ...MATCH_RESOURCE,
    rescueWindowMinutes: getRescueWindowMinutes(MATCH_RESOURCE.urgency),
  };
  return mockRequest(shaped, { delay: 450 });
}

/**
 * Fetch the demo candidate recipients for the selected resource, including
 * the hardcoded proposed allocation (`allocatedQuantity`). Mock only — no
 * scoring, ranking or live organization lookup.
 */
export function getMatchingCandidates() {
  return mockRequest(MATCH_CANDIDATES, { delay: 600 });
}
