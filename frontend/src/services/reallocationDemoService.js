import { STATUS, URGENCY, RESOURCE_TYPE, NETWORK_ROLE } from '@/utils/theme';
import { DEMO_OPERATION } from '@/data/operationDetail';
import {
  DEMO_ALLOCATION,
  DEMO_ALLOCATION_UNIT,
  DEMO_OPERATION_ID,
  DEMO_TOTAL_PORTIONS,
  REALLOCATION_OUTCOME,
  REALLOCATION_STEPS,
  REALLOCATION_STEP_MS,
  UNAVAILABLE_RECIPIENT,
} from '@/data/reallocationDemo';

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
/* View model for the demo card and warning                            */
/* ------------------------------------------------------------------ */

/**
 * Everything the demo UI needs, worded in one place so the Operations,
 * Matching and Dashboard banners can never contradict each other.
 */
export function getReallocationView(demo) {
  const phase = getReallocationPhase(demo);
  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;

  const rows = DEMO_ALLOCATION.map((item) => ({
    ...item,
    state: demo.unavailable && item.id === UNAVAILABLE_RECIPIENT.id ? 'unavailable' : 'allocated',
  }));
  const placed = rows
    .filter((row) => row.state === 'allocated')
    .reduce((sum, row) => sum + row.portions, 0);

  const split = DEMO_ALLOCATION.map((item) => `${item.name} ${item.portions}`).join(', ');

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
    outcome: REALLOCATION_OUTCOME,
    warning: {
      title: 'Original allocation is no longer feasible',
      message: `${name} is unavailable and can no longer receive its ${portions} ${unit}. The plan for ${DEMO_OPERATION_ID} (${split}) cannot be delivered as allocated, so ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} have no recipient until the plan is recalculated.`,
      short: `${DEMO_OPERATION_ID}: ${name} is unavailable, so its ${portions} ${unit} have no recipient. The original allocation is no longer feasible and the operation is Reallocating.`,
    },
  };
}

/* ------------------------------------------------------------------ */
/* Overlays: the same mock data, as it reads once the scenario is on    */
/* ------------------------------------------------------------------ */

/** The operation the demo runs on (RS-1024) — pages use it to know where to show the demo card. */
export { DEMO_OPERATION_ID };

const isDemoOperation = (operation) => operation?.id === DEMO_OPERATION_ID;

/** "NGO A (unavailable)" — what a Recipient cell reads during the scenario. */
const UNAVAILABLE_LABEL = `${UNAVAILABLE_RECIPIENT.name} (unavailable)`;

/**
 * One operation row (Operations list, Dashboard active operations). Any
 * operation other than RS-1024 — or RS-1024 before the scenario — is
 * returned as the very same object.
 */
export function applyDemoToOperation(operation, demo) {
  if (!demo.unavailable || !isDemoOperation(operation)) return operation;
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

/**
 * The Operations details payload `{ operation, stages, locations, route, zoom }`.
 *
 * Stage history is kept: the earlier stages did happen. The match stage is
 * annotated with what changed, In Transit becomes a paused current stage,
 * and the route to the unavailable recipient is withdrawn from the map.
 */
export function applyDemoToOperationDetail(detail, demo) {
  if (!detail || !demo.unavailable || !isDemoOperation(detail.operation)) return detail;

  const { name, portions } = UNAVAILABLE_RECIPIENT;
  const unit = DEMO_ALLOCATION_UNIT;
  const others = DEMO_ALLOCATION.filter((item) => item.id !== UNAVAILABLE_RECIPIENT.id);
  const othersPortions = others.reduce((sum, item) => sum + item.portions, 0);

  const operation = {
    ...applyDemoToOperation(detail.operation, demo),
    etaNote: 'ETA is being recalculated while a new recipient is found (demo).',
    summary: `${name} became unavailable, so the original allocation is no longer feasible. ${portions} of ${DEMO_TOTAL_PORTIONS} ${unit} have no recipient; ${others
      .map((item) => `${item.name} (${item.portions})`)
      .join(' and ')} still hold ${othersPortions} ${unit}. ${detail.operation.partner} is holding the delivery while the plan is recalculated — a demo scenario.`,
  };

  const stages = detail.stages.map((stage) => {
    switch (stage.key) {
      case 'matched':
        return {
          ...stage,
          description: `Original allocation: ${DEMO_ALLOCATION.map(
            (item) => `${item.name} ${item.portions}`,
          ).join(', ')}. ${name} has since become unavailable.`,
        };
      case 'in_transit':
        return {
          ...stage,
          timestamp: 'Paused just now (illustrative)',
          description: `Paused — the route to ${name} is no longer valid. ${detail.operation.partner} holds the delivery until a new plan is ready (demo).`,
        };
      case 'delivered':
        return { ...stage, description: 'Waiting on a new recipient before drop-off.' };
      default:
        return stage;
    }
  });

  const locations = detail.locations.map((location) =>
    location.role === NETWORK_ROLE.RECIPIENT
      ? { ...location, name: `${name} (unavailable · demo)` }
      : location,
  );

  return {
    ...detail,
    operation,
    stages,
    locations,
    route: null,
    routeSubtitle: `Route to ${name} withdrawn — the recipient is unavailable (demo).`,
    mapFootnote: `The mock route to ${name} was withdrawn because the recipient is unavailable. Marker positions are illustrative only for this demo — not a live GPS feed or vehicle location.`,
  };
}

/** Smart Matching candidates: the unavailable recipient can no longer be selected or allocated. */
export function applyDemoToMatchCandidates(candidates, demo) {
  if (!candidates || !demo.unavailable) return candidates;
  return candidates.map((candidate) =>
    candidate.id === UNAVAILABLE_RECIPIENT.id
      ? {
          ...candidate,
          availability: 'no',
          pickupFeasibility: null,
          selectable: false,
          unselectableReason: `Marked unavailable in the ${DEMO_OPERATION_ID} demo scenario — cannot receive its ${UNAVAILABLE_RECIPIENT.portions} ${DEMO_ALLOCATION_UNIT}.`,
          allocatedQuantity: null,
        }
      : candidate,
  );
}

/** Dashboard stat cards: RS-1024 now counts as at risk. */
export function applyDemoToDashboardStats(stats, demo) {
  if (!stats || !demo.unavailable) return stats;
  return {
    ...stats,
    atRiskResources: {
      ...stats.atRiskResources,
      value: stats.atRiskResources.value + 1,
      delta: `${stats.atRiskResources.delta} · incl. ${DEMO_OPERATION_ID}`,
    },
  };
}

/** Dashboard at-risk cards: the unplaced portions of RS-1024 come first. */
export function applyDemoToAtRiskResources(resources, demo) {
  if (!resources || !demo.unavailable) return resources;
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

  // Newest first: the current reallocation state, then the event that caused it.
  const events = [
    {
      id: 'rs1024-reallocation',
      stage: 'matched',
      status: STATUS.REALLOCATING,
      title: phase === 'settled' ? 'Awaiting new recipient' : 'Reallocation in progress',
      description: `${DEMO_OPERATION_ID}: ${portions} ${DEMO_ALLOCATION_UNIT} need a new recipient`,
      time: 'Just now',
    },
    {
      id: 'rs1024-recipient-unavailable',
      stage: 'matched',
      status: STATUS.REALLOCATING,
      title: 'Recipient unavailable',
      description: `${name} marked unavailable for ${DEMO_OPERATION_ID} (demo)`,
      time: 'Just now',
    },
  ];

  return [...events, ...activity];
}
