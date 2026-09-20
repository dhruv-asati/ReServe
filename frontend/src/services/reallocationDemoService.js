import { STATUS, URGENCY, RESOURCE_TYPE, NETWORK_ROLE } from '@/utils/theme';
import { DEMO_OPERATION } from '@/data/operationDetail';
import { MATCH_CANDIDATES, MATCH_RESOURCE } from '@/data/matching';
import {
  DEMO_ALLOCATION,
  DEMO_ALLOCATION_UNIT,
  DEMO_OPERATION_ID,
  DEMO_TOTAL_PORTIONS,
  REALLOCATION_DISCLAIMER,
  REALLOCATION_EVENT_MESSAGE,
  REALLOCATION_EVENT_TITLE,
  REALLOCATION_RULE,
  REALLOCATION_SHORTFALL_OUTCOME,
  REALLOCATION_STEPS,
  REALLOCATION_STEP_MS,
  UNAVAILABLE_RECIPIENT,
} from '@/data/reallocationDemo';
import { recalculateAllocation } from '@/utils/reallocationPlan';
import { buildMatchReasons } from '@/utils/matchReasons';
import { getRescueWindowMinutes } from './matchingService';

/**
 * Demo state for "a recipient becomes unavailable during a rescue" (RS-1024).
 *
 * FRONTEND ONLY. Nothing here contacts an organization, sends a notification
 * or calls a backend — it flips a flag in this module and lets every page
 * that shows RS-1024 read the same flag.
 *
 * Why a small store and not component state: the Operations, Matching and
 * Dashboard pages all show RS-1024, and each is a separate route. Component
 * state would be lost on navigation, so the state lives here and pages
 * subscribe through hooks/useReallocationDemo.js. It is also mirrored to
 * sessionStorage so a refresh during a demo keeps the scenario in place
 * (closing the tab clears it).
 *
 * The rest of the app's mock data is left untouched. Pages fetch it exactly
 * as before and pass it through the `applyDemoTo…` functions below, which
 * return the data unchanged until the scenario is triggered.
 *
 * State shape: `{ unavailable, progress }`
 *   unavailable  the recipient has been marked unavailable
 *   progress     how many of REALLOCATION_STEPS the mock progress has finished
 *
 * Phases: idle → running (the mock steps tick; NGO A's 50 portions have no
 * recipient) → settled (the steps are done and the recalculated allocation is
 * shown). The recalculation itself runs once, at module load, over the demo
 * candidates (see RESULT below); the phase only decides when it is revealed.
 * Every page reads the result through this module, so the Operations list,
 * summary, tracker and map, Smart Matching and the Dashboard all show the
 * same allocation — Shelter B 20, NGO D 40, Night Rescue Hub 20 with today's
 * demo data — and none of them holds a copy of those numbers.
 */

/* ------------------------------------------------------------------ */
/* Store                                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = 'reserve.demo.rs1024.recipient-unavailable';
const STEP_COUNT = REALLOCATION_STEPS.length;

const INITIAL_STATE = Object.freeze({ unavailable: false, progress: 0 });

/**
 * Read the mirrored state. A refresh in the middle of the mock progress
 * simply lands on the finished state instead of resuming the animation.
 */
function readStoredState() {
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (stored?.unavailable === true) {
      return Object.freeze({ unavailable: true, progress: STEP_COUNT });
    }
  } catch {
    // Storage blocked or corrupt — start from the initial state.
  }
  return INITIAL_STATE;
}

let state = readStoredState();
let timer = null;
const listeners = new Set();

function setState(next) {
  state = Object.freeze(next);
  try {
    if (state.unavailable) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage blocked — the in-memory state still works for this page load.
  }
  listeners.forEach((listener) => listener());
}

function scheduleNextStep() {
  timer = setTimeout(() => {
    setState({ unavailable: true, progress: state.progress + 1 });
    if (state.progress < STEP_COUNT) scheduleNextStep();
    else timer = null;
  }, REALLOCATION_STEP_MS);
}

/** Current state. Same object until something changes (safe for useSyncExternalStore). */
export function getReallocationDemoState() {
  return state;
}

export function subscribeReallocationDemo(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * "Simulate Recipient Unavailable": marks NGO A unavailable, which moves
 * RS-1024 to Reallocating on every page, and starts the mock progress.
 * Does nothing if the scenario is already active.
 */
export function simulateRecipientUnavailable() {
  if (state.unavailable) return;
  clearTimeout(timer);
  setState({ unavailable: true, progress: 0 });
  scheduleNextStep();
}

/** Put RS-1024 back to its original allocation and status. */
export function resetReallocationDemo() {
  clearTimeout(timer);
  timer = null;
  setState(INITIAL_STATE);
}

/** 'idle' (nothing happened), 'running' (mock progress ticking) or 'settled' (progress finished). */
export function getReallocationPhase(demo) {
  if (!demo.unavailable) return 'idle';
  return demo.progress < STEP_COUNT ? 'running' : 'settled';
}

/* ------------------------------------------------------------------ */
/* The recalculated allocation                                          */
/* ------------------------------------------------------------------ */

/**
 * The resource being re-allocated, as Smart Matching sees it — including the
 * rescue window derived from its urgency, so the deadline check here and the
 * "Rescue Window" shown on the Matching page use the same number.
 */
const DEMO_RESOURCE = Object.freeze({
  ...MATCH_RESOURCE,
  rescueWindowMinutes: getRescueWindowMinutes(MATCH_RESOURCE.urgency),
});

/**
 * Recalculate the allocation once, with NGO A out, over the demo candidates
 * (utils/reallocationPlan.js). Static input → static output, so this is
 * computed at module load and simply revealed when the mock steps finish.
 *
 * Each recipient that ends up with a share also carries the constraint checks
 * behind it, read from the same candidate fields the Matching page's "Why
 * This Match?" uses (utils/matchReasons.js) — no scores, only the data.
 */
function buildResult() {
  const plan = recalculateAllocation({
    candidates: MATCH_CANDIDATES,
    resource: DEMO_RESOURCE,
    previous: DEMO_ALLOCATION,
    unavailableIds: [UNAVAILABLE_RECIPIENT.id],
  });
  const candidateById = new Map(MATCH_CANDIDATES.map((candidate) => [candidate.id, candidate]));

  const rows = plan.rows.map((row) => ({
    ...row,
    unit: plan.unit,
    checks:
      row.updated > 0
        ? buildMatchReasons(
            { ...candidateById.get(row.id), allocatedQuantity: row.updated },
            DEMO_RESOURCE,
          )
        : [],
  }));

  return {
    complete: plan.status === 'complete',
    total: plan.total,
    unit: plan.unit,
    displaced: plan.displaced,
    unplaced: plan.unplaced,
    windowMinutes: DEMO_RESOURCE.rescueWindowMinutes,
    rows,
    /** Recipients that hold a share in the updated allocation, in candidate order. */
    updated: rows.filter((row) => row.updated > 0),
    /** Candidates that took no part, each with the constraint that ruled them out. */
    excluded: plan.evaluations.filter((entry) => !entry.eligible),
  };
}

const RESULT = buildResult();

/**
 * The recalculated allocation, but only once the mock steps have finished and
 * only if it is a valid plan (every portion placed). Null otherwise — pages
 * then keep showing the "no recipient yet" state.
 */
function getUpdate(demo) {
  return getReallocationPhase(demo) === 'settled' && RESULT.complete ? RESULT : null;
}

/* ---------- Wording helpers ---------- */

/** "A, B and C" */
function joinList(items) {
  if (items.length <= 1) return items.join('');
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

/** "NGO A 50, Shelter B 20" — compact allocation, used inside sentences. */
const splitText = (entries, portionsOf) =>
  entries.map((entry) => `${entry.name} ${portionsOf(entry)}`).join(', ');

const PREVIOUS_SPLIT = splitText(DEMO_ALLOCATION, (item) => item.portions);
const UPDATED_SPLIT = splitText(RESULT.updated, (row) => row.updated);
const UPDATED_NAMES = RESULT.updated.map((row) => row.name);

/** How one recipient's share moved, as a clause: "NGO D takes 40 portions". */
function changeClause(row) {
  const unit = row.unit;
  switch (row.change) {
    case 'new':
      return `${row.name} takes ${row.updated} ${unit}`;
    case 'increased':
      return `${row.name} rises from ${row.previous} to ${row.updated} ${unit}`;
    case 'decreased':
      return `${row.name} drops from ${row.previous} to ${row.updated} ${unit}`;
    default:
      return `${row.name} keeps its ${row.updated} ${unit}`;
  }
}

/* ------------------------------------------------------------------ */
/* Allocation summary for the operation details view                    */
/* ------------------------------------------------------------------ */

/**
 * The compact "who gets how much" panel shown inside OperationSummaryCard on
 * the Operations details view. Three versions of the same shape — original,
 * while reallocating, and updated — so the details view always states the
 * allocation the rest of the page is describing.
 *
 * Shape: `{ title, badge, rows, total, placed, unplaced, unit, footnote }`
 * where each row is `{ id, name, quantity, unit, note, tone }`.
 */

const ALLOCATION_FOOTNOTE =
  'Demo allocation for this illustrative rescue — not a live allocation, and no organization was contacted.';

/** The original allocation, as the operation reads before anything changes. */
export const BASE_ALLOCATION_SUMMARY = Object.freeze({
  title: 'Allocation',
  badge: { tone: 'neutral', label: 'Original plan' },
  rows: DEMO_ALLOCATION.map((item) => ({
    id: item.id,
    name: item.name,
    quantity: item.portions,
    unit: item.unit,
    note: null,
    tone: 'allocated',
  })),
  total: DEMO_TOTAL_PORTIONS,
  placed: DEMO_TOTAL_PORTIONS,
  unplaced: 0,
  unit: DEMO_ALLOCATION_UNIT,
  footnote: ALLOCATION_FOOTNOTE,
});

/** While the recipient is down and no updated plan exists yet. */
function buildReallocatingSummary() {
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const placed = DEMO_TOTAL_PORTIONS - portions;

  return {
    title: 'Allocation (being recalculated)',
    badge: { tone: 'urgent', label: 'Reallocating' },
    rows: DEMO_ALLOCATION.map((item) => {
      const down = item.id === UNAVAILABLE_RECIPIENT.id;
      return {
        id: item.id,
        name: item.name,
        quantity: item.portions,
        unit: item.unit,
        note: down ? 'Unavailable — these portions need a new recipient' : null,
        tone: down ? 'unavailable' : 'allocated',
      };
    }),
    total: DEMO_TOTAL_PORTIONS,
    placed,
    unplaced: DEMO_TOTAL_PORTIONS - placed,
    unit: DEMO_ALLOCATION_UNIT,
    footnote: `${name} can no longer receive its ${portions} ${DEMO_ALLOCATION_UNIT}. ${ALLOCATION_FOOTNOTE}`,
  };
}

/** How one recipient's share moved, as a short note under its name. */
function changeNote(row) {
  switch (row.change) {
    case 'new':
      return 'New recipient';
    case 'increased':
      return `Increased from ${row.previous} ${row.unit}`;
    case 'decreased':
      return `Reduced from ${row.previous} ${row.unit}`;
    default:
      return 'Unchanged';
  }
}

/** The recalculated allocation, once the mock reallocation has finished. */
function buildUpdatedSummary(update) {
  return {
    title: 'Updated allocation',
    badge: { tone: 'brand', label: 'Updated (demo)' },
    rows: update.updated.map((row) => ({
      id: row.id,
      name: row.name,
      quantity: row.updated,
      unit: row.unit,
      note: changeNote(row),
      tone: row.change === 'unchanged' ? 'allocated' : 'changed',
    })),
    total: DEMO_TOTAL_PORTIONS,
    placed: DEMO_TOTAL_PORTIONS,
    unplaced: 0,
    unit: DEMO_ALLOCATION_UNIT,
    footnote: `Previously ${PREVIOUS_SPLIT}. ${REALLOCATION_EVENT_MESSAGE} ${ALLOCATION_FOOTNOTE}`,
  };
}

/* ------------------------------------------------------------------ */
/* View model for the demo card and warning                            */
/* ------------------------------------------------------------------ */

/**
 * Everything the demo UI needs, worded in one place so the Operations,
 * Matching and Dashboard banners can never contradict each other.
 *
 * `rows` is the original (previous) allocation; `updated` is the recalculated
 * one and is null until the phase is 'settled' (and stays null if the
 * recalculation could not place every portion).
 */
export function getReallocationView(demo) {
  const phase = getReallocationPhase(demo);
  const update = getUpdate(demo);
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;

  const rows = DEMO_ALLOCATION.map((item) => ({
    ...item,
    state: demo.unavailable && item.id === UNAVAILABLE_RECIPIENT.id ? 'unavailable' : 'allocated',
  }));
  const placed = update
    ? update.updated.reduce((sum, row) => sum + row.updated, 0)
    : rows.filter((row) => row.state === 'allocated').reduce((sum, row) => sum + row.portions, 0);

  const otherExcluded = RESULT.excluded
    .filter((entry) => entry.id !== UNAVAILABLE_RECIPIENT.id)
    .map((entry) => entry.name);

  const whyChanged = `${name} became unavailable, so its ${portions} ${unit} could no longer be delivered as planned. The demo re-checked every recipient against capacity, availability, distance, the ${RESULT.windowMinutes}-minute rescue window, pickup feasibility and resource eligibility, then placed the ${RESULT.displaced} displaced ${unit}: ${joinList(
    RESULT.updated.map(changeClause),
  )}.${otherExcluded.length ? ` ${joinList(otherExcluded)} did not qualify (see the constraint checks).` : ''}`;

  const warning = update
    ? {
        title: `Allocation updated because ${name} became unavailable`,
        message: `${name} is unavailable and can no longer receive its ${portions} ${unit}, so the original allocation for ${DEMO_OPERATION_ID} could not be delivered as planned. The allocation was recalculated and all ${DEMO_TOTAL_PORTIONS} ${unit} have a recipient again — a demo calculation, not a live allocation. The previous and updated allocations are compared below.`,
        short: `${DEMO_OPERATION_ID}: ${name} became unavailable, so the allocation changed (demo). Previous: ${PREVIOUS_SPLIT}. Updated: ${UPDATED_SPLIT} — all ${DEMO_TOTAL_PORTIONS} ${unit} placed.`,
      }
    : {
        title: 'Original allocation is no longer feasible',
        message: `${name} is unavailable and can no longer receive its ${portions} ${unit}. The plan for ${DEMO_OPERATION_ID} (${PREVIOUS_SPLIT}) cannot be delivered as allocated, so ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} have no recipient until the plan is recalculated.`,
        short: `${DEMO_OPERATION_ID}: ${name} is unavailable, so its ${portions} ${unit} have no recipient. The original allocation is no longer feasible and the operation is Reallocating.`,
      };

  return {
    phase,
    unavailable: demo.unavailable,
    operationId: DEMO_OPERATION_ID,
    recipientName: name,
    unit,
    total: DEMO_TOTAL_PORTIONS,
    placed,
    unplaced: DEMO_TOTAL_PORTIONS - placed,
    rows,
    steps: REALLOCATION_STEPS,
    completedSteps: demo.progress,
    warning,

    // The recalculated allocation (null until the mock steps finish).
    updated: update ? update.updated : null,
    excluded: update ? update.excluded : [],
    windowMinutes: RESULT.windowMinutes,
    whyChanged,
    rule: REALLOCATION_RULE,
    disclaimer: REALLOCATION_DISCLAIMER,

    // Shown when the steps finished but no valid updated allocation exists.
    outcome: REALLOCATION_SHORTFALL_OUTCOME,

    // Smart Matching: what its "Recalculate Match" note says while the scenario is on.
    matchingNote: update
      ? `${name} is unavailable, so the updated demo allocation places all ${DEMO_TOTAL_PORTIONS} ${unit} with ${joinList(UPDATED_NAMES)}.`
      : `${name} is still unavailable, so ${DEMO_TOTAL_PORTIONS - placed} ${unit} remain unallocated.`,
  };
}

/* ------------------------------------------------------------------ */
/* Overlays: the same mock data, as it reads once the scenario is on    */
/* ------------------------------------------------------------------ */

/** The operation the demo runs on (RS-1024) — pages use it to know where to show the demo card. */
export { DEMO_OPERATION_ID };

const isDemoOperation = (operation) => operation?.id === DEMO_OPERATION_ID;

/** "NGO A (unavailable)" — what a Recipient cell reads while NGO A's portions have no recipient. */
const UNAVAILABLE_LABEL = `${UNAVAILABLE_RECIPIENT.name} (unavailable)`;

/**
 * One operation row (Operations list, Dashboard active operations). Any
 * operation other than RS-1024 — or RS-1024 before the scenario — is
 * returned as the very same object.
 *
 * While NGO A's portions have no recipient the row is Reallocating. Once the
 * updated allocation exists the operation is Matched again, to the updated
 * recipients; it has no ETA yet because no new routes are planned in the demo.
 */
export function applyDemoToOperation(operation, demo) {
  if (!demo.unavailable || !isDemoOperation(operation)) return operation;

  const update = getUpdate(demo);
  if (update) {
    return {
      ...operation,
      status: STATUS.MATCHED,
      recipient: update.updated.map((row) => row.name).join(', '),
      eta: 'Awaiting new route plan',
    };
  }

  return {
    ...operation,
    status: STATUS.REALLOCATING,
    recipient: UNAVAILABLE_LABEL,
    eta: 'Recalculating',
  };
}

/** A list of operation rows. Returns the same array when nothing changes. */
export function applyDemoToOperations(operations, demo) {
  if (!operations || !demo.unavailable) return operations;
  return operations.map((operation) => applyDemoToOperation(operation, demo));
}

/* ---------- Timeline stages added while the scenario is on ---------- */

/**
 * The stages the scenario inserts into the operation's lifecycle tracker,
 * between In Transit and Delivered — the reallocation is the newest thing to
 * have happened, so it reads correctly in chronological order.
 *
 *   running  Reallocating is the current stage.
 *   settled  Reallocating is completed and "Matched (updated allocation)"
 *            becomes the current stage, which is the operation's status
 *            (Matched) expressed in the tracker.
 *
 * Exactly one stage is current in either case, so the tracker still renders a
 * single active step.
 */
function buildReallocationStages(update) {
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;

  const reallocating = {
    key: 'reallocating',
    label: 'Reallocating',
    state: update ? 'completed' : 'current',
    timestamp: update
      ? 'Completed just now (illustrative)'
      : 'Started just now (illustrative)',
    description: update
      ? `${name} became unavailable, so the allocation was recalculated over the demo recipients: ${UPDATED_SPLIT}.`
      : `${name} became unavailable, so ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} need a new recipient. Recalculating the allocation (demo).`,
  };

  if (!update) return [reallocating];

  return [
    reallocating,
    {
      key: 'rematched',
      label: 'Matched (updated allocation)',
      state: 'current',
      timestamp: 'Updated just now (illustrative)',
      description: `${REALLOCATION_EVENT_MESSAGE} Updated allocation: ${UPDATED_SPLIT} — all ${DEMO_TOTAL_PORTIONS} ${unit} have a recipient again. Waiting on delivery routes, which this demo does not plan.`,
    },
  ];
}

/* ---------- Events added while the scenario is on ---------- */

/**
 * The events the scenario prepends to the operation's feed, newest first.
 * The cause is always recorded; once the updated allocation is confirmed the
 * feed also carries the plain-language explanation of what changed.
 */
function buildReallocationEvents(update) {
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;

  const cause = {
    id: 'rs1024-event-recipient-unavailable',
    stage: 'reallocating',
    status: STATUS.REALLOCATING,
    title: 'Recipient unavailable',
    description: `${name} was marked unavailable and can no longer receive its ${portions} ${unit} (demo scenario).`,
    time: 'Just now (illustrative)',
  };

  if (!update) {
    return [
      {
        id: 'rs1024-event-reallocation-started',
        stage: 'reallocating',
        status: STATUS.REALLOCATING,
        title: 'Reallocation started',
        description: `The original allocation for ${DEMO_OPERATION_ID} is no longer feasible, so ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} are being re-planned.`,
        time: 'Just now (illustrative)',
      },
      cause,
    ];
  }

  return [
    {
      id: 'rs1024-event-allocation-changed',
      stage: 'rematched',
      status: STATUS.MATCHED,
      title: REALLOCATION_EVENT_TITLE,
      description: REALLOCATION_EVENT_MESSAGE,
      meta: `Previously ${PREVIOUS_SPLIT}. Now ${UPDATED_SPLIT} — all ${DEMO_TOTAL_PORTIONS} ${unit} placed (demo calculation).`,
      time: 'Just now (illustrative)',
    },
    {
      id: 'rs1024-event-reallocation-complete',
      stage: 'reallocating',
      status: STATUS.REALLOCATING,
      title: 'Reallocation completed',
      description: `The demo rule re-checked every recipient and placed the ${portions} displaced ${unit}.`,
      time: 'Just now (illustrative)',
    },
    cause,
  ];
}

/**
 * The Operations details payload
 * `{ operation, stages, events, locations, route, zoom }`.
 *
 * Stage history is kept: the earlier stages did happen. The match stage is
 * annotated with what changed, In Transit becomes a completed (held) stage so
 * the inserted Reallocating stage can be the current one, the event feed
 * records what changed and why, the operation carries the updated allocation
 * summary, and the route to the unavailable recipient is withdrawn from the
 * map. No routes are drawn to the updated recipients — the demo does not plan
 * them.
 */
export function applyDemoToOperationDetail(detail, demo) {
  if (!detail || !demo.unavailable || !isDemoOperation(detail.operation)) return detail;

  const update = getUpdate(demo);
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;
  const partner = detail.operation.partner;
  const others = DEMO_ALLOCATION.filter((item) => item.id !== UNAVAILABLE_RECIPIENT.id);
  const othersPortions = others.reduce((sum, item) => sum + item.portions, 0);

  const operation = {
    ...applyDemoToOperation(detail.operation, demo),
    allocation: update ? buildUpdatedSummary(update) : buildReallocatingSummary(),
    etaNote: update
      ? 'No ETA yet — routes to the updated recipients are not planned in this demo.'
      : 'ETA is being recalculated while a new recipient is found (demo).',
    summary: update
      ? `${name} became unavailable, so the allocation for ${DEMO_OPERATION_ID} changed. It was recalculated over the demo data: ${UPDATED_SPLIT} (previously ${PREVIOUS_SPLIT}), so all ${DEMO_TOTAL_PORTIONS} ${unit} have a recipient again. ${partner} is holding the delivery until routes to the updated recipients are planned — a demo scenario, not a live allocation.`
      : `${name} became unavailable, so the original allocation is no longer feasible. ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} have no recipient; ${others
          .map((item) => `${item.name} (${item.portions})`)
          .join(' and ')} still hold ${othersPortions} ${unit}. ${partner} is holding the delivery while the plan is recalculated — a demo scenario.`,
  };

  const stages = detail.stages.map((stage) => {
    switch (stage.key) {
      case 'matched':
        return update
          ? {
              ...stage,
              timestamp: 'Updated just now (illustrative)',
              description: `Re-matched after ${name} became unavailable (demo): ${UPDATED_SPLIT}. Originally ${PREVIOUS_SPLIT}.`,
            }
          : {
              ...stage,
              description: `Original allocation: ${PREVIOUS_SPLIT}. ${name} has since become unavailable.`,
            };
      case 'in_transit':
        // Held, not current: the inserted Reallocating / Matched (updated)
        // stage below is what the operation is doing now, and the tracker
        // shows exactly one current stage.
        return {
          ...stage,
          state: stage.state === 'current' ? 'completed' : stage.state,
          timestamp: 'Paused just now (illustrative)',
          description: update
            ? `Paused — the route to ${name} is no longer valid, and routes to ${joinList(UPDATED_NAMES)} are not planned in this demo. ${partner} holds the delivery.`
            : `Paused — the route to ${name} is no longer valid. ${partner} holds the delivery until a new plan is ready (demo).`,
        };
      case 'delivered':
        return {
          ...stage,
          description: update
            ? 'Waiting on delivery routes to the updated recipients before drop-off.'
            : 'Waiting on a new recipient before drop-off.',
        };
      default:
        return stage;
    }
  });

  // The reallocation goes in just before Delivered — it is the newest thing
  // to have happened, and Delivered is still ahead of the operation.
  const inserted = buildReallocationStages(update);
  const deliveredIndex = stages.findIndex((stage) => stage.key === 'delivered');
  const stagesWithReallocation =
    deliveredIndex === -1
      ? [...stages, ...inserted]
      : [...stages.slice(0, deliveredIndex), ...inserted, ...stages.slice(deliveredIndex)];

  const events = [...buildReallocationEvents(update), ...(detail.events ?? [])];

  const locations = detail.locations.map((location) =>
    location.role === NETWORK_ROLE.RECIPIENT
      ? { ...location, name: `${name} (unavailable · demo)` }
      : location,
  );

  return {
    ...detail,
    operation,
    stages: stagesWithReallocation,
    events,
    locations,
    route: null,
    routeSubtitle: `Route to ${name} withdrawn — the recipient is unavailable (demo).`,
    mapFootnote: update
      ? `The mock route to ${name} was withdrawn because the recipient is unavailable. Routes to ${joinList(UPDATED_NAMES)} are not drawn — this demo does not plan routes — and marker positions are illustrative only, not a live GPS feed or vehicle location.`
      : `The mock route to ${name} was withdrawn because the recipient is unavailable. Marker positions are illustrative only for this demo — not a live GPS feed or vehicle location.`,
  };
}

/**
 * Smart Matching candidates: the unavailable recipient can no longer be
 * selected or allocated. Once the updated allocation exists, its shares are
 * written onto the candidates, so the Proposed Allocation cards, the totals
 * and the plan validation all read the same 80 portions the Operations page
 * shows.
 */
export function applyDemoToMatchCandidates(candidates, demo) {
  if (!candidates || !demo.unavailable) return candidates;

  const update = getUpdate(demo);
  const updatedShares = update ? new Map(update.updated.map((row) => [row.id, row.updated])) : null;

  return candidates.map((candidate) => {
    if (candidate.id === UNAVAILABLE_RECIPIENT.id) {
      return {
        ...candidate,
        availability: 'no',
        pickupFeasibility: null,
        selectable: false,
        unselectableReason: `Marked unavailable in the ${DEMO_OPERATION_ID} demo scenario — cannot receive its ${UNAVAILABLE_RECIPIENT.portions} ${DEMO_ALLOCATION_UNIT}.`,
        allocatedQuantity: null,
      };
    }
    return updatedShares?.has(candidate.id)
      ? { ...candidate, allocatedQuantity: updatedShares.get(candidate.id) }
      : candidate;
  });
}

/**
 * Dashboard stat cards: RS-1024 counts as at risk only while some of its
 * portions have no recipient. Once the updated allocation covers everything
 * it is no longer counted.
 */
export function applyDemoToDashboardStats(stats, demo) {
  if (!stats || !demo.unavailable || getUpdate(demo)) return stats;
  return {
    ...stats,
    atRiskResources: {
      ...stats.atRiskResources,
      value: stats.atRiskResources.value + 1,
      delta: `${stats.atRiskResources.delta} · incl. ${DEMO_OPERATION_ID}`,
    },
  };
}

/** Dashboard at-risk cards: while unplaced, RS-1024's portions come first; once re-allocated it drops off. */
export function applyDemoToAtRiskResources(resources, demo) {
  if (!resources || !demo.unavailable || getUpdate(demo)) return resources;
  const { portions } = UNAVAILABLE_RECIPIENT;
  return [
    {
      id: DEMO_OPERATION_ID,
      resource: DEMO_OPERATION.resource,
      resourceType: RESOURCE_TYPE.FOOD,
      quantity: `${portions} ${DEMO_ALLOCATION_UNIT} need a recipient · ${DEMO_OPERATION_ID}`,
      deadline: `Deadline ${DEMO_OPERATION.deadline}`,
      urgency: URGENCY.HIGH,
      status: STATUS.REALLOCATING,
    },
    ...resources,
  ];
}

/** Dashboard activity feed: newest events on top. Times are fixed labels, never a live clock. */
export function applyDemoToActivity(activity, demo) {
  if (!activity || !demo.unavailable) return activity;
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const phase = getReallocationPhase(demo);
  const update = getUpdate(demo);

  const cause = {
    id: 'rs1024-recipient-unavailable',
    stage: 'reallocating',
    status: STATUS.REALLOCATING,
    title: 'Recipient unavailable',
    description: `${name} marked unavailable for ${DEMO_OPERATION_ID} (demo)`,
    time: 'Just now',
  };

  // Newest first: the current reallocation state, then the event that caused it.
  const latest = update
    ? {
        id: 'rs1024-allocation-updated',
        stage: 'rematched',
        status: STATUS.MATCHED,
        title: REALLOCATION_EVENT_TITLE,
        description: `${DEMO_OPERATION_ID}: ${REALLOCATION_EVENT_MESSAGE}`,
        time: 'Just now',
      }
    : {
        id: 'rs1024-reallocation',
        stage: 'reallocating',
        status: STATUS.REALLOCATING,
        title: phase === 'settled' ? 'Awaiting new recipient' : 'Reallocation in progress',
        description: `${DEMO_OPERATION_ID}: ${portions} ${DEMO_ALLOCATION_UNIT} need a new recipient`,
        time: 'Just now',
      };

  return [latest, cause, ...activity];
}
