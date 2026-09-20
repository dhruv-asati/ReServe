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
 *
 * Once NGO A is unavailable the allocation is recalculated over those same
 * candidates (utils/reallocationPlan.js, run in
 * services/reallocationDemoService.js). With the demo data that gives:
 *
 *   Shelter B         20 portions   (unchanged — already at capacity)
 *   NGO D             40 portions   (new)
 *   Night Rescue Hub  20 portions   (was 10)      → still exactly 80
 *
 * The updated numbers are not stored here: they are the output of the rule,
 * so they can only ever agree with the candidate data behind them.
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
  { key: 'allocation_recalculated', label: 'Updated allocation calculated' },
];

/** How long each mock step "takes", in ms. Six steps ≈ 3.6 seconds. */
export const REALLOCATION_STEP_MS = 600;

/**
 * The one-line explanation added to the operation's event feed (and to the
 * Dashboard activity feed) once the updated allocation is confirmed. Written
 * here so the Operations event feed, the re-matched timeline stage and the
 * Dashboard all use exactly the same sentence.
 */
export const REALLOCATION_EVENT_MESSAGE =
  'Allocation changed because the original recipient became unavailable.';

/** Title shown next to that event wherever it appears. */
export const REALLOCATION_EVENT_TITLE = 'Allocation changed';

/**
 * The rule the demo recalculation applies, in plain words. Shown next to the
 * result so it is clear how the numbers were reached. It must describe
 * utils/reallocationPlan.js — change the two together.
 */
export const REALLOCATION_RULE =
  'Recipients that are still eligible keep their existing share. The portions that lost their recipient go to the eligible recipients with the most spare capacity first, never above a recipient\u2019s capacity, so as few recipients as possible change.';

/** Said wherever the recalculated allocation appears, so it is never read as live. */
export const REALLOCATION_DISCLAIMER =
  'Demo calculation only: a small scripted rule applied to hardcoded demo recipients. It is not a live production allocation, no organization was contacted, and no confidence or optimization score is used.';

/**
 * Outcome shown if the recalculation ever cannot place every portion (for
 * example if the demo candidates are edited so capacity runs out). With the
 * current demo data every portion is placed, so this text is not reached — but
 * if it ever is, the app says so plainly instead of showing a plan that does
 * not add up.
 */
export const REALLOCATION_SHORTFALL_OUTCOME =
  'The remaining eligible recipients in the demo data cannot take all of the displaced portions, so no valid updated allocation can be shown. The operation stays in Reallocating until a new recipient is found.';
