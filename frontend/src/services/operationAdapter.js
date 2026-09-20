import { STATUS, NETWORK_ROLE } from '@/utils/theme';
import { lower } from './resourceAdapter';

/**
 * Adapters between the backend's operation shape (snake_case, UPPERCASE enums
 * — see backend/app/schemas/operation.py) and the shapes the Operations page
 * was built around (camelCase rows and a `{ operation, stages, events,
 * locations, route, zoom }` details payload, vocabulary from utils/theme.js).
 *
 * Pure functions only: no network, no React. `op` is one OperationOut from
 * GET /operations; `resource` is the ResourceOut for `op.resource_id`, or null
 * when it could not be loaded (every field then falls back to a placeholder).
 */

/* ------------------------------------------------------------------ */
/* Identity & status                                                   */
/* ------------------------------------------------------------------ */

/**
 * Short, readable operation ID for the UI ("OP-8F3A21C4"). The page keeps the
 * selected operation in the URL and shows the ID in tables, so a full UUID
 * would be unwieldy. liveOperationsService keeps the code -> operation lookup
 * and lengthens a code in the (very unlikely) event two operations share one.
 */
export function operationCode(id, length = 8) {
  return `OP-${String(id).replace(/-/g, '').slice(0, length).toUpperCase()}`;
}

/** OperationStatus -> the STATUS vocabulary the badges and filters understand. */
export function operationStatusToUi(op) {
  switch (op.status) {
    case 'PLANNED':
      return op.partner ? STATUS.PARTNER_ASSIGNED : STATUS.MATCHED;
    case 'IN_TRANSIT':
      return STATUS.IN_TRANSIT;
    case 'DELIVERED':
    case 'COMPLETED':
      return STATUS.DELIVERED;
    case 'FAILED':
      return STATUS.FAILED;
    default:
      return lower(op.status);
  }
}

const FINISHED = new Set(['DELIVERED', 'COMPLETED', 'FAILED']);

/** An in-flight operation whose resource expires within this window is flagged "at risk". */
const AT_RISK_WINDOW_MS = 60 * 60 * 1000;

/* ------------------------------------------------------------------ */
/* Small formatting helpers                                            */
/* ------------------------------------------------------------------ */

const TIME_FORMAT = { hour: 'numeric', minute: '2-digit' };
const DATE_FORMAT = { month: 'short', day: 'numeric' };

function validDate(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** "10:45 PM", "Tomorrow, 9:00 AM", "Sep 22, 9:00 AM" — or an em dash when unknown. */
export function formatDeadline(iso, now = new Date()) {
  const date = validDate(iso);
  if (!date) return '—';
  const time = date.toLocaleTimeString(undefined, TIME_FORMAT);
  const dayDiff = Math.round((startOfDay(date) - startOfDay(now)) / 86400000);
  if (dayDiff === 0) return time;
  if (dayDiff === 1) return `Tomorrow, ${time}`;
  return `${date.toLocaleDateString(undefined, DATE_FORMAT)}, ${time}`;
}

/** "Sep 20, 3:05 PM" for timestamps in the tracker and the event feed. */
export function formatWhen(iso) {
  const date = validDate(iso);
  if (!date) return null;
  return `${date.toLocaleDateString(undefined, DATE_FORMAT)}, ${date.toLocaleTimeString(undefined, TIME_FORMAT)}`;
}

/** 25 -> "25 min", 70 -> "1 hr 10 min". */
export function formatDuration(minutes) {
  const total = Math.max(1, Math.round(minutes));
  if (total < 60) return `${total} min`;
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return rest ? `${hours} hr ${rest} min` : `${hours} hr`;
}

const round2 = (value) => Math.round(value * 100) / 100;

function coords(lat, lng) {
  return typeof lat === 'number' && typeof lng === 'number' ? { lat, lng } : null;
}

/* ------------------------------------------------------------------ */
/* Allocations & route legs                                            */
/* ------------------------------------------------------------------ */

/** Allocations still carrying goods: a reallocation cancels / replaces the old one. */
function activeAllocations(op) {
  return (op.allocations ?? []).filter(
    (allocation) => allocation.status !== 'CANCELLED' && allocation.status !== 'REALLOCATED',
  );
}

/** Route legs (one per allocation) belonging to the allocations that are still active. */
function activeLegs(op) {
  const activeIds = new Set(activeAllocations(op).map((allocation) => allocation.id));
  return (op.route ?? []).filter((leg) => activeIds.has(leg.allocation_id));
}

function recipientLabel(op) {
  const allocations = activeAllocations(op);
  const names = [...new Set(activeLegs(op).map((leg) => leg.target_name).filter(Boolean))];
  if (names.length === 0) return allocations.length > 0 ? 'Matched recipient' : null;
  return names.length === 1 ? names[0] : `${names[0]} +${names.length - 1} more`;
}

function partnerLabel(partner) {
  if (!partner) return null;
  return partner.organization_name || 'Assigned rescue partner';
}

/* ------------------------------------------------------------------ */
/* List row                                                            */
/* ------------------------------------------------------------------ */

/**
 * One OperationOut (+ its resource) -> a row of the Operations list.
 * `options.code` overrides the displayed ID (see operationCode); `options.now`
 * exists so tests can pin the clock.
 */
export function toOperationRow(op, resource, { now = new Date(), code } = {}) {
  const finished = FINISHED.has(op.status);
  const allocated = activeAllocations(op).reduce(
    (total, allocation) => total + Number(allocation.allocated_quantity ?? 0),
    0,
  );
  const durations = activeLegs(op)
    .map((leg) => leg.estimated_duration_minutes)
    .filter((minutes) => typeof minutes === 'number');
  const deadlineIso = resource?.expiry_time ?? resource?.pickup_window_end ?? null;
  const deadline = validDate(deadlineIso);

  return {
    id: code ?? operationCode(op.id),
    resource: resource?.title ?? 'Resource details unavailable',
    resourceType: lower(resource?.resource_type),
    quantity: round2(allocated > 0 ? allocated : Number(resource?.quantity ?? 0)),
    unit: resource?.unit ?? '',
    provider: resource?.provider?.full_name ?? 'Unknown provider',
    recipient: recipientLabel(op),
    partner: partnerLabel(op.partner),
    status: operationStatusToUi(op),
    eta: finished || durations.length === 0 ? '—' : formatDuration(Math.max(...durations)),
    deadline: formatDeadline(deadlineIso, now),
    location: resource?.location_address ?? '—',
    atRisk: !finished && deadline !== null && deadline.getTime() - now.getTime() < AT_RISK_WINDOW_MS,
  };
}

/* ------------------------------------------------------------------ */
/* Details                                                             */
/* ------------------------------------------------------------------ */

function itemsLabel(row) {
  const name = row.resource.toLowerCase();
  return row.unit ? `${row.quantity} ${row.unit} of ${name}` : `${row.quantity} × ${name}`;
}

function buildSummary(op, row) {
  const items = itemsLabel(row);
  const to = row.recipient ?? 'a recipient';
  const by = row.partner ?? 'A rescue partner';

  switch (op.status) {
    case 'PLANNED':
      return op.partner
        ? `${by} is assigned to move ${items} from ${row.provider} to ${to}. Pickup hasn't started yet.`
        : `${items} from ${row.provider} are matched to ${to}. A rescue partner hasn't been assigned yet.`;
    case 'IN_TRANSIT':
      return `${by} is moving ${items} from ${row.provider} to ${to}.`;
    case 'DELIVERED':
    case 'COMPLETED':
      return `${items} from ${row.provider} were delivered to ${to}.`;
    case 'FAILED':
      return `${op.failure_reason ?? 'This operation failed.'} ${items} from ${row.provider} were not delivered.`;
    default:
      return undefined;
  }
}

function buildEtaNote(op, hasEstimate) {
  if (FINISHED.has(op.status)) return 'No ETA — this operation has finished.';
  if (hasEstimate) {
    return 'Estimated travel time from pickup to delivery: straight-line distance at an assumed average speed — not live traffic or GPS.';
  }
  return 'No estimate — the pickup or delivery coordinates are not known yet.';
}

/* ---------- Stages ---------- */

/** Index of the furthest stage an operation has reached, by stage key. */
function reachedStageKey(op) {
  switch (op.status) {
    case 'PLANNED':
      return op.partner ? 'assigned' : 'matched';
    case 'IN_TRANSIT':
      return 'in_transit';
    case 'DELIVERED':
    case 'COMPLETED':
      return 'delivered';
    case 'FAILED':
      if (op.pickup_started_at) return 'pickup';
      return op.partner ? 'assigned' : 'matched';
    default:
      return 'created';
  }
}

function eventTime(op, predicate) {
  const match = (op.events ?? [])
    .filter(predicate)
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))[0];
  return match ? formatWhen(match.created_at) : null;
}

function stageDescription(key, state, row) {
  const to = row.recipient ?? 'a compatible recipient';
  const by = row.partner ?? 'a rescue partner';
  const items = itemsLabel(row);
  const done = state !== 'upcoming';

  switch (key) {
    case 'created':
      return `Rescue operation created for ${items} from ${row.provider}.`;
    case 'analyzed':
      return 'Batch analysed for allocation priority.';
    case 'matched':
      return done ? `Matched to ${to}.` : 'Waiting for a compatible recipient.';
    case 'assigned':
      return done ? `${by} assigned for pickup.` : 'Waiting for a rescue partner to be assigned.';
    case 'pickup':
      if (!done) return `Pickup at ${row.provider} hasn't started.`;
      return state === 'current'
        ? `${by} is collecting the items from ${row.provider}.`
        : `${by} collected the items from ${row.provider}.`;
    case 'in_transit':
      if (!done) return 'Starts once pickup is complete.';
      return state === 'current' ? `En route to ${to}.` : `${by} carried the items to ${to}.`;
    case 'delivered':
      return done ? `Drop-off confirmed at ${to}.` : `Awaiting drop-off confirmation at ${to}.`;
    default:
      return undefined;
  }
}

function buildStages(op, row, resource) {
  const defs = [
    { key: 'created', label: 'Created' },
    // Only shown when this resource actually went through the AI analysis.
    ...(resource?.ai_analysis ? [{ key: 'analyzed', label: 'AI Analyzed' }] : []),
    { key: 'matched', label: 'Matched' },
    { key: 'assigned', label: 'Partner Assigned' },
    { key: 'pickup', label: 'Pickup Started' },
    { key: 'in_transit', label: 'In Transit' },
    { key: 'delivered', label: 'Delivered' },
  ];

  const failed = op.status === 'FAILED';
  const delivered = op.status === 'DELIVERED' || op.status === 'COMPLETED';
  const reachedKey = reachedStageKey(op);
  const reached = Math.max(
    defs.findIndex((def) => def.key === reachedKey),
    0,
  );

  const timestamps = {
    created: formatWhen(op.created_at),
    pickup: formatWhen(op.pickup_started_at),
    in_transit: eventTime(op, (event) => event.event_metadata?.to === 'IN_TRANSIT'),
    delivered: formatWhen(op.delivered_at ?? op.completed_at),
    // The creation event records whether a partner was assigned from the start.
    assigned: eventTime(op, (event) => event.event_type === 'CREATED' && event.event_metadata?.partner_id),
  };

  const stateOf = (index) => {
    if (failed) return index <= reached ? 'completed' : null;
    if (index < reached || (delivered && index === reached)) return 'completed';
    return index === reached ? 'current' : 'upcoming';
  };

  const stages = defs
    .map((def, index) => {
      const state = stateOf(index);
      if (state === null) return null;
      return {
        key: def.key,
        label: def.label,
        state,
        timestamp: state === 'upcoming' ? null : (timestamps[def.key] ?? null),
        description: stageDescription(def.key, state, row),
      };
    })
    .filter(Boolean);

  if (failed) {
    stages.push({
      key: 'failed',
      label: 'Failed',
      state: 'ended',
      timestamp: formatWhen(op.updated_at),
      description: op.failure_reason ?? 'The operation could not be completed.',
    });
  }
  return stages;
}

/* ---------- Events ---------- */

const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const STATUS_WORDS = {
  PLANNED: 'planned',
  IN_TRANSIT: 'in transit',
  DELIVERED: 'delivered',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

/** The backend writes ids and enum names into event text; make it readable. */
function cleanEventText(text, op) {
  if (!text) return undefined;
  return text
    .replace(new RegExp(`partner (${UUID_PATTERN.source})`, 'gi'), (_match, id) =>
      id.toLowerCase() === String(op.partner?.id).toLowerCase() && op.partner?.organization_name
        ? `partner ${op.partner.organization_name}`
        : 'a rescue partner',
    )
    .replace(/\b(PLANNED|IN_TRANSIT|DELIVERED|COMPLETED|FAILED)\b/g, (word) => STATUS_WORDS[word]);
}

/** Icon key (see ACTIVITY_STAGE_ICONS) + badge status + title for one backend event. */
function describeEvent(event) {
  const meta = event.event_metadata ?? {};

  switch (event.event_type) {
    case 'CREATED':
      return { stage: 'created', status: STATUS.CREATED, title: 'Operation created' };
    case 'REALLOCATED':
      return { stage: 'reallocating', status: STATUS.REALLOCATING, title: 'Recipient reallocated' };
    case 'STATUS_CHANGED': {
      const to = meta.to;
      const word = STATUS_WORDS[to] ?? 'updated';
      const title = `Status changed to ${word}`;
      if (to === 'IN_TRANSIT') return { stage: 'in_transit', status: STATUS.IN_TRANSIT, title };
      if (to === 'DELIVERED') return { stage: 'delivered', status: STATUS.DELIVERED, title };
      if (to === 'COMPLETED') return { stage: 'completed', status: STATUS.DELIVERED, title };
      if (to === 'FAILED') return { stage: 'completed', status: STATUS.FAILED, title };
      return { stage: 'assigned', status: undefined, title };
    }
    case 'NOTE':
      return { stage: 'created', status: undefined, title: 'Note added' };
    default:
      return { stage: 'created', status: undefined, title: 'Update' };
  }
}

function buildEvents(op) {
  return [...(op.events ?? [])]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .map((event) => ({
      id: event.id,
      ...describeEvent(event),
      description: cleanEventText(event.description, op),
      time: formatWhen(event.created_at) ?? '',
    }));
}

/* ---------- Map ---------- */

/** Zoom that keeps every marker in frame, from the widest span (same idea as the mock map). */
function zoomFor(points) {
  if (points.length < 2) return 14;
  const lats = points.map((point) => point.lat);
  const lngs = points.map((point) => point.lng);
  const span = Math.max(Math.max(...lats) - Math.min(...lats), Math.max(...lngs) - Math.min(...lngs));
  if (span <= 0.012) return 14;
  if (span <= 0.025) return 13;
  if (span <= 0.05) return 12;
  if (span <= 0.2) return 11;
  return 9;
}

function buildMap(op, row, resource) {
  const legs = activeLegs(op);
  const firstLeg = legs[0];
  const pickup =
    coords(resource?.latitude, resource?.longitude) ??
    coords(firstLeg?.pickup_latitude, firstLeg?.pickup_longitude);

  const locations = [];
  if (pickup) {
    locations.push({
      id: `${row.id}-provider`,
      role: NETWORK_ROLE.PROVIDER,
      name: row.provider,
      ...pickup,
    });
  }

  legs.forEach((leg, index) => {
    const delivery = coords(leg.delivery_latitude, leg.delivery_longitude);
    if (!delivery) return;
    locations.push({
      id: `${row.id}-delivery-${index}`,
      role: leg.target_type === 'RESCUE_HUB' ? NETWORK_ROLE.HUB : NETWORK_ROLE.RECIPIENT,
      name: leg.target_name ?? 'Delivery point',
      ...delivery,
    });
  });

  const current = coords(op.current_latitude, op.current_longitude);
  if (current && !FINISHED.has(op.status)) {
    locations.push({
      id: `${row.id}-partner`,
      role: NETWORK_ROLE.PARTNER,
      name: `${row.partner ?? 'Rescue partner'} (last reported position)`,
      ...current,
    });
  }

  const firstDelivery = coords(firstLeg?.delivery_latitude, firstLeg?.delivery_longitude);
  const route = pickup && firstDelivery ? [pickup, firstDelivery] : null;

  return { locations, route, zoom: zoomFor(locations) };
}

/* ---------- Putting the details together ---------- */

/** One OperationOut (+ its resource) -> the payload of the Operations details view. */
export function toOperationDetail(op, resource, options = {}) {
  const row = toOperationRow(op, resource, options);
  const { locations, route, zoom } = buildMap(op, row, resource);
  const hasEstimate = row.eta !== '—';

  const routeSubtitle = route
    ? `Straight-line route from ${row.provider} to ${row.recipient ?? 'the recipient'}, ${row.location}.`
    : 'No route to show — the pickup or delivery coordinates are not known yet.';
  const mapFootnote = route
    ? 'The dashed line is the straight-line path between the pickup and delivery points, not a road route. A partner marker, when shown, is the last position reported for this operation.'
    : 'Markers show the positions known for this operation; some coordinates have not been recorded yet.';

  return {
    operation: {
      id: row.id,
      resource: row.resource,
      resourceType: row.resourceType,
      quantity: row.quantity,
      unit: row.unit,
      headline: row.unit ? `${row.quantity} ${row.unit} of ${row.resource}` : `${row.quantity} × ${row.resource}`,
      provider: row.provider,
      recipient: row.recipient,
      location: row.location,
      partner: row.partner,
      status: row.status,
      eta: row.eta,
      etaNote: buildEtaNote(op, hasEstimate),
      deadline: row.deadline,
      summary: buildSummary(op, row),
    },
    stages: buildStages(op, row, resource),
    events: buildEvents(op),
    locations,
    route,
    zoom,
    routeSubtitle,
    mapFootnote,
  };
}
