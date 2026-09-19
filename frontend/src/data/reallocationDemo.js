import { DEMO_OPERATION } from '@/data/operationDetail';
import { MATCH_CANDIDATES } from '@/data/matching';

/**
 * Static data for the "recipient becomes unavailable" demo on RS-1024.
 *
 * DEMO ONLY. Nothing here is live: no organization is contacted, no
 * notification is sent, and there is no backend. The scenario is a scripted
 * walkthrough of what the reallocation experience looks like.
 *
 * The initial allocation is read from the Smart Matching candidates
 * (data/matching.js) rather than copied, so the Operations, Matching and
 * Dashboard pages can never disagree about who holds how much:
 *
 *   NGO A             50 portions
 *   Shelter B         20 portions
 *   Night Rescue Hub  10 portions   → 80 portions in total (RS-1024's quantity)
 */

export const DEMO_OPERATION_ID = DEMO_OPERATION.id;

/** Initial allocation of RS-1024, in the order the matching page lists it. */
export const DEMO_ALLOCATION = MATCH_CANDIDATES.filter(
  (candidate) => candidate.allocatedQuantity != null,
).map(({ id, name, allocatedQuantity, unit }) => ({
  id,
  name,
  portions: allocatedQuantity,
  unit,
}));

export const DEMO_ALLOCATION_UNIT = DEMO_ALLOCATION[0]?.unit ?? 'portions';

export const DEMO_TOTAL_PORTIONS = DEMO_ALLOCATION.reduce((sum, item) => sum + item.portions, 0);

/** The recipient the simulation takes offline. */
export const UNAVAILABLE_RECIPIENT = DEMO_ALLOCATION.find((item) => item.id === 'cand-ngo-a');

/**
 * The mock reallocation "progress": each step is shown as active, then done,
 * one after the other. Purely cosmetic — nothing is actually searched.
 */
export const REALLOCATION_STEPS = [
  { key: 'change_detected', label: 'Recipient status change detected' },
  { key: 'allocation_invalidated', label: 'Original allocation invalidated' },
  { key: 'recipients_rechecked', label: 'Eligible recipients re-checked' },
  { key: 'capacity_window', label: 'Capacity and rescue window checked' },
  { key: 'pickup_checked', label: 'Pickup feasibility checked' },
];

/** How long each mock step "takes", in ms. Five steps ≈ 3 seconds. */
export const REALLOCATION_STEP_MS = 600;

/**
 * Outcome shown once the mock steps finish. It follows from the demo
 * candidates in data/matching.js: Harborview has no reachable pickup,
 * Eastside is closed, and Shelter B / Night Rescue Hub are close to their
 * stated capacity — so the operation stays in "Reallocating".
 */
export const REALLOCATION_OUTCOME =
  'No other recipient in the demo data can take the unplaced portions yet: the remaining candidates are at capacity, closed, or out of pickup reach. The operation stays in Reallocating until a new recipient is found.';
