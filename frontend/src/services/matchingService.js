import { api, http, mockRequest } from './api';
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

// ---------------------------------------------------------------------------
// Live mode — the real matching engine (backend/app/api/matching.py). The mock
// functions above stay for VITE_USE_MOCKS=true; the Smart Matching page for
// live data (pages/LiveMatching.jsx) only uses what follows.
// ---------------------------------------------------------------------------

/** Resource statuses a matching run / allocation is still possible for. */
const MATCHABLE_STATUSES = ['AVAILABLE', 'MATCHING'];

/** The signed-in provider's own resources that can still be matched, newest first. */
export function listMatchableResources() {
  return api.get('/resources', { params: { mine: true, limit: 100 } }).then((response) => {
    const items = response.data?.items ?? [];
    return items.filter((item) => MATCHABLE_STATUSES.includes(item.status));
  });
}

/** POST /api/matching/{id} — runs the engine (safe to re-run) and returns MatchingResultsData. */
export function runMatching(resourceId) {
  return http.post(`/matching/${encodeURIComponent(resourceId)}`, {});
}

/** GET /api/matching/{id}/results — the latest run, or null if matching hasn't been run yet. */
export function getLatestMatching(resourceId) {
  return api
    .get(`/matching/${encodeURIComponent(resourceId)}/results`)
    .then((response) => response.data)
    .catch(() => null);
}

/**
 * Commit a plan: one POST /api/allocations per chosen candidate (sequential, so
 * the backend's remaining-quantity check sees each one), then one
 * POST /api/operations to execute them.
 *
 * On failure the rejection carries `created` (allocations already saved) and
 * `stage` ('allocation' | 'operation') so the page can say exactly what
 * happened — allocations that were saved are not rolled back.
 */
export async function confirmAllocationPlan({ rescueRequestId, allocations }) {
  const created = [];
  for (const item of allocations) {
    try {
      created.push(
        await http.post('/allocations', {
          match_id: item.matchId,
          allocated_quantity: item.quantity,
          reason: item.reason,
        }),
      );
    } catch (error) {
      throw { ...error, created, stage: 'allocation' };
    }
  }

  try {
    const operation = await http.post('/operations', { rescue_request_id: rescueRequestId });
    return { allocations: created, operation };
  } catch (error) {
    throw { ...error, created, stage: 'operation' };
  }
}
