import { STATUS, RESOURCE_TYPE, NETWORK_ROLE } from '@/utils/theme';

/**
 * Demo data for the Operations Control Center (`/app/operations`).
 *
 * Everything here describes a single, hardcoded illustrative rescue
 * (RS-1024) used to showcase the control-center layout. It is frontend-only
 * mock data — there is no backend, no live GPS feed, and the rescue partner
 * shown is an illustrative label, not a real-world partner assignment.
 * `eta` and the partner's map position are fixed illustrative values, not
 * calculated from traffic, routing, or a live location.
 */
export const DEMO_OPERATION = {
  id: 'RS-1024',
  resource: 'Vegetarian Meals',
  resourceType: RESOURCE_TYPE.FOOD,
  quantity: 80,
  unit: 'meals',
  provider: 'Hotel XYZ',
  recipient: 'NGO A',
  location: 'Indiranagar, Bengaluru',
  partner: 'Rescue Partner #12',
  status: STATUS.IN_TRANSIT,
  eta: '35 min',
  etaNote: 'Illustrative estimate for this demo — not calculated from live traffic or GPS data.',
  deadline: '11:30 PM',
  summary:
    "Rescue Partner #12 is in transit with 80 vegetarian meals from Hotel XYZ to NGO A in Indiranagar, Bengaluru — targeting arrival before the 11:30 PM rescue deadline.",
};

/**
 * Full 7-stage lifecycle for the demo operation, in order: Created →
 * AI Analyzed → Matched → Partner Assigned → Pickup Started → In Transit →
 * Delivered. Unlike a chronological event feed, this always lists every
 * stage — `state` marks each as 'completed', 'current' (exactly one), or
 * 'upcoming' — so the Operations Control Center can render a clear
 * completed/current/upcoming stepper (see OperationStageTracker).
 *
 * Every `timestamp` is a hardcoded, illustrative value (never a live
 * clock); upcoming stages intentionally carry no timestamp yet.
 */
export const DEMO_OPERATION_STAGES = [
  {
    key: 'created',
    label: 'Created',
    state: 'completed',
    timestamp: '2 hr 10 min ago (illustrative)',
    description: 'Hotel XYZ logged 80 vegetarian meals as surplus.',
  },
  {
    key: 'analyzed',
    label: 'AI Analyzed',
    state: 'completed',
    timestamp: '1 hr 52 min ago (illustrative)',
    description: 'Batch scored for allocation priority — demo analysis, not a live AI call.',
  },
  {
    key: 'matched',
    label: 'Matched',
    state: 'completed',
    timestamp: '1 hr 40 min ago (illustrative)',
    description: 'Vegetarian meals matched to NGO A.',
  },
  {
    key: 'assigned',
    label: 'Partner Assigned',
    state: 'completed',
    timestamp: '1 hr 15 min ago (illustrative)',
    description: 'Rescue Partner #12 assigned for pickup — illustrative assignment only.',
  },
  {
    key: 'pickup',
    label: 'Pickup Started',
    state: 'completed',
    timestamp: '22 min ago (illustrative)',
    description: 'Rescue Partner #12 collected the meals from Hotel XYZ.',
  },
  {
    key: 'in_transit',
    label: 'In Transit',
    state: 'current',
    timestamp: 'Last updated moments ago (illustrative)',
    description: 'En route to NGO A, Indiranagar, Bengaluru — demo position, not live tracking.',
  },
  {
    key: 'delivered',
    label: 'Delivered',
    state: 'upcoming',
    timestamp: null,
    description: 'Awaiting drop-off confirmation at NGO A.',
  },
];

/**
 * Event feed for the demo operation — what has already happened, newest
 * first. Where DEMO_OPERATION_STAGES always lists every stage of the
 * lifecycle (including the ones still to come), this is a chronological
 * record of events only, so a change part-way through an operation can be
 * recorded here without rewriting the lifecycle.
 *
 * The RS-1024 recipient-unavailable demo prepends its own events to this
 * list (see services/reallocationDemoService.js); nothing here is a live
 * feed and every `time` is a hardcoded, illustrative label.
 */
export const DEMO_OPERATION_EVENTS = [
  {
    id: 'rs-1024-in-transit',
    stage: 'in_transit',
    status: STATUS.IN_TRANSIT,
    title: 'In transit',
    description: 'Rescue Partner #12 left Hotel XYZ en route to NGO A.',
    time: '22 min ago (illustrative)',
  },
  {
    id: 'rs-1024-pickup',
    stage: 'pickup',
    status: STATUS.PICKUP_IN_PROGRESS,
    title: 'Pickup started',
    description: 'Rescue Partner #12 collected 80 vegetarian meals from Hotel XYZ.',
    time: '30 min ago (illustrative)',
  },
  {
    id: 'rs-1024-assigned',
    stage: 'assigned',
    status: STATUS.PARTNER_ASSIGNED,
    title: 'Rescue partner assigned',
    description: 'Rescue Partner #12 assigned for pickup — illustrative assignment only.',
    time: '1 hr 15 min ago (illustrative)',
  },
  {
    id: 'rs-1024-matched',
    stage: 'matched',
    status: STATUS.MATCHED,
    title: 'Matched',
    description: 'Vegetarian meals allocated across NGO A, Shelter B and Night Rescue Hub.',
    time: '1 hr 40 min ago (illustrative)',
  },
  {
    id: 'rs-1024-analyzed',
    stage: 'analyzed',
    status: STATUS.ANALYZING,
    title: 'AI analyzed',
    description: 'Batch scored for allocation priority — demo analysis, not a live AI call.',
    time: '1 hr 52 min ago (illustrative)',
  },
  {
    id: 'rs-1024-created',
    stage: 'created',
    status: STATUS.CREATED,
    title: 'Rescue created',
    description: 'Hotel XYZ logged 80 vegetarian meals as surplus.',
    time: '2 hr 10 min ago (illustrative)',
  },
];

/**
 * Mock map points for the demo operation, centred on Indiranagar, Bengaluru.
 * Coordinates are fictional but geographically coherent — a static
 * illustrative snapshot for this demo, not a live GPS position or route.
 */
export const DEMO_OPERATION_LOCATIONS = [
  {
    id: 'rs-1024-provider',
    role: NETWORK_ROLE.PROVIDER,
    name: 'Hotel XYZ (provider · demo)',
    lat: 12.9784,
    lng: 77.6408,
  },
  {
    id: 'rs-1024-recipient',
    role: NETWORK_ROLE.RECIPIENT,
    name: 'NGO A (recipient · demo)',
    lat: 12.9698,
    lng: 77.6482,
  },
  {
    id: 'rs-1024-partner',
    role: NETWORK_ROLE.PARTNER,
    name: 'Rescue Partner #12 (illustrative position · demo)',
    lat: 12.9741,
    lng: 77.6445,
  },
];

/**
 * Mock route waypoints from Hotel XYZ to NGO A, drawn as a dashed polyline
 * on the map. These are hand-placed illustrative points, not the output of
 * a routing engine (no real road geometry, turn-by-turn directions, or
 * distance/time calculation) and not a live vehicle track. The middle
 * waypoint lines up with Rescue Partner #12's illustrative position above,
 * so the marker reads as "somewhere along this mock route," not a GPS fix.
 */
export const DEMO_OPERATION_ROUTE = [
  { lat: 12.9784, lng: 77.6408 }, // Hotel XYZ (start)
  { lat: 12.9762, lng: 77.6421 },
  { lat: 12.9741, lng: 77.6445 }, // Rescue Partner #12 — illustrative position
  { lat: 12.9719, lng: 77.6463 },
  { lat: 12.9698, lng: 77.6482 }, // NGO A (end)
];
