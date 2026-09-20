import { api, mockRequest, USE_MOCKS } from './api';
import {
  getDemoOperation,
  getDemoOperationStages,
  getDemoOperationEvents,
  getDemoOperationLocations,
  getDemoOperationRoute,
} from './operationDetailService';
import { RESCUE_OPERATIONS } from '@/data/rescueOperations';
import { DEMO_OPERATION } from '@/data/operationDetail';
import { STATUS, NETWORK_ROLE } from '@/utils/theme';

/**
 * Mock service for the Operations page (`/app/operations`): the list of
 * rescue operations, and the details view of whichever one is selected.
 *
 * Frontend only — no backend, no live GPS, no real dispatch. Same
 * mockRequest pattern as the other services, so swapping in real endpoints
 * later only changes the bodies of these functions.
 */

/**
 * Fetch every rescue operation for the Operations list.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js); the real request stays
 * dormant until the backend is live and `VITE_USE_MOCKS=false` is set.
 */
export function getRescueOperations() {
  if (USE_MOCKS) return mockRequest(RESCUE_OPERATIONS, { delay: 450 });
  return api.get('/operations').then((response) => response.data);
}

/**
 * Fetch the details view data for one operation:
 * `{ operation, stages, events, locations, route, zoom }`.
 *
 * `stages` is the full lifecycle (completed, current and upcoming);
 * `events` is the chronological record of what has already happened, newest
 * first, which is where a mid-operation change such as a reallocation is
 * recorded.
 *
 * The demo operation (RS-1024) resolves through the operationDetailService
 * calls, so its details are exactly what this page showed before the list
 * existed. Every other operation gets the same shapes derived from its list
 * entry — see the helpers below.
 */
export async function getRescueOperationDetail(id) {
  if (id === DEMO_OPERATION.id) {
    const [operation, stages, events, locations, route] = await Promise.all([
      getDemoOperation(),
      getDemoOperationStages(),
      getDemoOperationEvents(),
      getDemoOperationLocations(),
      getDemoOperationRoute(),
    ]);
    return { operation, stages, events, locations, route, zoom: 14 };
  }

  const entry = RESCUE_OPERATIONS.find((operation) => operation.id === id);
  if (!entry) return null;

  const { locations, route, zoom } = buildMap(entry);
  const stages = buildStages(entry);
  return mockRequest(
    {
      operation: buildOperation(entry),
      stages,
      events: buildEvents(entry, stages),
      locations,
      route,
      zoom,
    },
    { delay: 500 },
  );
}

/* ------------------------------------------------------------------ */
/* Derived details for operations other than the demo operation        */
/* ------------------------------------------------------------------ */

const ETA_NOTE_LIVE =
  'Illustrative estimate for this demo — not calculated from live traffic or GPS data.';

const ETA_NOTES = {
  [STATUS.CREATED]: 'No ETA yet — one is estimated once a rescue partner is assigned (demo).',
  [STATUS.MATCHING]: 'No ETA yet — one is estimated once a rescue partner is assigned (demo).',
  [STATUS.MATCHED]: 'No ETA yet — waiting for a rescue partner to be assigned (demo).',
  [STATUS.REALLOCATING]: 'ETA is being recalculated while a new match is found (demo).',
  [STATUS.DELIVERED]: 'Delivered — the demo shows no remaining ETA.',
  [STATUS.CANCELLED]: 'Cancelled — there is no ETA.',
  [STATUS.EXPIRED]: 'Expired — there is no ETA.',
};

/** "35 boxes of bakery surplus" — used mid-sentence in summaries. */
function itemsLabel({ quantity, unit, resource }) {
  return `${quantity} ${unit} of ${resource.toLowerCase()}`;
}

function buildOperation(entry) {
  const { id, resource, resourceType, quantity, unit, provider, recipient, partner } = entry;
  const { status, eta, deadline, location } = entry;

  return {
    id,
    resource,
    resourceType,
    quantity,
    unit,
    headline: `${quantity} ${unit} of ${resource}`,
    provider,
    recipient,
    location,
    partner,
    status,
    eta,
    etaNote: ETA_NOTES[status] ?? ETA_NOTE_LIVE,
    deadline,
    summary: buildSummary(entry),
  };
}

function buildSummary(entry) {
  const { provider, partner, deadline, status, note } = entry;
  const items = itemsLabel(entry);
  const to = entry.recipient ?? 'a recipient';
  const by = partner ?? 'A rescue partner';

  switch (status) {
    case STATUS.CREATED:
      return `${provider} logged ${items}. Analysis and matching haven't started yet.`;
    case STATUS.MATCHING:
      return `Finding a recipient for ${items} from ${provider} — analysis is in progress.`;
    case STATUS.MATCHED:
      return `${items} from ${provider} are matched to ${to}. A rescue partner hasn't been assigned yet.`;
    case STATUS.PARTNER_ASSIGNED:
      return `${by} is assigned to move ${items} from ${provider} to ${to}. Pickup hasn't started yet.`;
    case STATUS.PICKUP_IN_PROGRESS:
      return `${by} is picking up ${items} from ${provider} for delivery to ${to}.`;
    case STATUS.IN_TRANSIT:
      return `${by} is in transit with ${items} from ${provider} to ${to} — targeting arrival before the ${deadline} rescue deadline.`;
    case STATUS.DELIVERED:
      return `${items} from ${provider} were delivered to ${to}.`;
    case STATUS.REALLOCATING:
      return `${note} The planner is looking for a new recipient for ${items} from ${provider} before the ${deadline} deadline.`;
    case STATUS.CANCELLED:
    case STATUS.EXPIRED:
      return `${note} ${items} from ${provider} were not moved.`;
    default:
      return undefined;
  }
}

/* ---------- Stages ---------- */

/**
 * The same 7-stage lifecycle the demo operation uses. `offset` is minutes
 * after creation and only feeds the illustrative timestamps.
 */
const STAGES = [
  { key: 'created', label: 'Created', offset: 0 },
  { key: 'analyzed', label: 'AI Analyzed', offset: 12 },
  { key: 'matched', label: 'Matched', offset: 25 },
  { key: 'assigned', label: 'Partner Assigned', offset: 45 },
  { key: 'pickup', label: 'Pickup Started', offset: 70 },
  { key: 'in_transit', label: 'In Transit', offset: 85 },
  { key: 'delivered', label: 'Delivered', offset: 110 },
];

/** Index of the furthest stage each status has reached. */
const REACHED = {
  [STATUS.CREATED]: 0,
  [STATUS.MATCHING]: 1,
  [STATUS.MATCHED]: 2,
  [STATUS.PARTNER_ASSIGNED]: 3,
  [STATUS.PICKUP_IN_PROGRESS]: 4,
  [STATUS.IN_TRANSIT]: 5,
  [STATUS.DELIVERED]: 6,
  [STATUS.REALLOCATING]: 2,
  [STATUS.CANCELLED]: 1,
  [STATUS.EXPIRED]: 1,
};

/** How long after creation a cancelled or expired operation ended (minutes). */
const ENDED_OFFSET = 60;

/** Fixed, illustrative "3 hr 5 min ago" text — never a live clock. */
function agoLabel(minutes) {
  if (minutes < 2) return 'moments ago (illustrative)';
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const mins = minutes % 60;
  const parts = [];
  if (days) parts.push(`${days} day${days === 1 ? '' : 's'}`);
  if (hours) parts.push(`${hours} hr`);
  if (mins && !days) parts.push(`${mins} min`);
  return `${parts.join(' ')} ago (illustrative)`;
}

function stageDescription(key, state, entry) {
  const { provider, resource } = entry;
  const to = entry.recipient ?? 'a compatible recipient';
  const by = entry.partner ?? 'a rescue partner';
  const items = itemsLabel(entry);
  const done = state !== 'upcoming';

  switch (key) {
    case 'created':
      return `${provider} logged ${items} as surplus.`;
    case 'analyzed':
      return done
        ? state === 'current'
          ? 'Scoring the batch and searching for a compatible recipient — demo analysis, not a live AI call.'
          : 'Batch scored for allocation priority — demo analysis, not a live AI call.'
        : 'Waiting on allocation analysis.';
    case 'matched':
      if (!done) return 'Waiting for a compatible recipient.';
      if (entry.status === STATUS.REALLOCATING) {
        return 'Match is being recalculated — the previous recipient can no longer take the delivery (demo scenario).';
      }
      return state === 'current'
        ? `${resource} matched to ${to}. Waiting for a rescue partner.`
        : `${resource} matched to ${to}.`;
    case 'assigned':
      if (done) return `${entry.partner} assigned for pickup — illustrative assignment only.`;
      return entry.partner
        ? `${entry.partner} is on hold until a new match is found (demo).`
        : 'Waiting for a rescue partner to be assigned.';
    case 'pickup':
      if (!done) return `Pickup at ${provider} hasn't started.`;
      return state === 'current'
        ? `${by} is collecting the items from ${provider}.`
        : `${by} collected the items from ${provider}.`;
    case 'in_transit':
      if (!done) return 'Starts once pickup is complete.';
      return state === 'current'
        ? `En route to ${to} — demo position, not live tracking.`
        : `${by} carried the items to ${to}.`;
    case 'delivered':
      if (done) return `Drop-off confirmed at ${to}.`;
      return entry.recipient
        ? `Awaiting drop-off confirmation at ${entry.recipient}.`
        : 'Awaiting a recipient match before drop-off.';
    default:
      return undefined;
  }
}

function buildStages(entry) {
  const { status, createdMinutesAgo } = entry;
  const reached = REACHED[status];
  const ended = status === STATUS.CANCELLED || status === STATUS.EXPIRED;
  const delivered = status === STATUS.DELIVERED;

  const stateOf = (index) => {
    if (index < reached || (delivered && index === reached)) return 'completed';
    if (index === reached) return 'current';
    return 'upcoming';
  };

  const timestampOf = (offset) => agoLabel(Math.max(createdMinutesAgo - offset, 0));

  // Cancelled and expired operations stop where they ended: the stages they
  // reached, then one terminal stage — no "upcoming" stages that never happen.
  const shown = ended ? STAGES.slice(0, reached + 1) : STAGES;

  const stages = shown.map((stage, index) => {
    const state = ended ? 'completed' : stateOf(index);
    return {
      key: stage.key,
      label: stage.label,
      state,
      timestamp: state === 'upcoming' ? null : timestampOf(stage.offset),
      description: stageDescription(stage.key, state, entry),
    };
  });

  if (ended) {
    stages.push({
      key: status,
      label: status === STATUS.CANCELLED ? 'Cancelled' : 'Expired',
      state: 'ended',
      timestamp: timestampOf(ENDED_OFFSET),
      description: entry.note,
    });
  }

  return stages;
}

/* ---------- Events ---------- */

/** The status each lifecycle stage represents, for the event feed's badge. */
const STAGE_STATUS = {
  created: STATUS.CREATED,
  analyzed: STATUS.ANALYZING,
  matched: STATUS.MATCHED,
  assigned: STATUS.PARTNER_ASSIGNED,
  pickup: STATUS.PICKUP_IN_PROGRESS,
  in_transit: STATUS.IN_TRANSIT,
  delivered: STATUS.DELIVERED,
};

/**
 * The event feed for one operation: the stages it has actually reached,
 * newest first. Derived from the same stages the tracker shows, so the two
 * can never disagree — the feed simply drops what hasn't happened yet.
 */
function buildEvents(entry, stages) {
  return stages
    .filter((stage) => stage.state !== 'upcoming')
    .map((stage) => ({
      id: `${entry.id}-${stage.key}`,
      stage: stage.state === 'ended' ? 'completed' : stage.key,
      status: stage.state === 'ended' ? entry.status : (STAGE_STATUS[stage.key] ?? entry.status),
      title: stage.label,
      description: stage.description,
      time: stage.timestamp,
    }))
    .reverse();
}

/* ---------- Map ---------- */

/** Statuses that show a route once a recipient is known. */
const ROUTED = new Set([
  STATUS.MATCHED,
  STATUS.PARTNER_ASSIGNED,
  STATUS.PICKUP_IN_PROGRESS,
  STATUS.IN_TRANSIT,
  STATUS.DELIVERED,
]);

// Small fixed sideways nudges so the dashed line reads as a hand-placed
// route rather than a ruler-straight one (same idea as the demo route).
const ROUTE_STEPS = [
  { t: 0, nudge: 0 },
  { t: 0.25, nudge: 0.0008 },
  { t: 0.5, nudge: -0.0006 },
  { t: 0.75, nudge: 0.0007 },
  { t: 1, nudge: 0 },
];

function lerpPoint(from, to, t, nudge = 0) {
  return { lat: from.lat + (to.lat - from.lat) * t + nudge, lng: from.lng + (to.lng - from.lng) * t };
}

/** Zoom that keeps every marker in the map's frame, from the widest span. */
function zoomFor(points) {
  const lats = points.map((point) => point.lat);
  const lngs = points.map((point) => point.lng);
  const span = Math.max(Math.max(...lats) - Math.min(...lats), Math.max(...lngs) - Math.min(...lngs));
  if (span <= 0.012) return 14;
  if (span <= 0.025) return 13;
  if (span <= 0.05) return 12;
  return 11;
}

function buildMap(entry) {
  const { id, provider, recipient, partner, status, geo } = entry;
  const slug = id.toLowerCase();

  const locations = [
    {
      id: `${slug}-provider`,
      role: NETWORK_ROLE.PROVIDER,
      name: `${provider} (provider · demo)`,
      ...geo.provider,
    },
  ];

  const routed = Boolean(recipient && geo.recipient && ROUTED.has(status));
  const route = routed
    ? ROUTE_STEPS.map(({ t, nudge }) => lerpPoint(geo.provider, geo.recipient, t, nudge))
    : null;

  if (recipient && geo.recipient) {
    locations.push({
      id: `${slug}-recipient`,
      role: NETWORK_ROLE.RECIPIENT,
      name: `${recipient} (recipient · demo)`,
      ...geo.recipient,
    });
  }

  // The partner marker only appears while a partner is on the move, and sits
  // at a fixed spot along the route — an illustration, not a GPS fix.
  if (routed && partner && status === STATUS.PICKUP_IN_PROGRESS) {
    locations.push(partnerMarker(slug, partner, lerpPoint(geo.provider, geo.recipient, 0.12)));
  }
  if (routed && partner && status === STATUS.IN_TRANSIT) {
    locations.push(partnerMarker(slug, partner, route[2]));
  }

  return { locations, route, zoom: zoomFor(locations) };
}

function partnerMarker(slug, partner, position) {
  return {
    id: `${slug}-partner`,
    role: NETWORK_ROLE.PARTNER,
    name: `${partner} (illustrative position · demo)`,
    lat: position.lat,
    lng: position.lng,
  };
}
