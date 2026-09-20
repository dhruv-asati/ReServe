/**
 * ReServe design system — JS side.
 *
 * CSS tokens live in src/styles/index.css. This file mirrors the parts that
 * components need programmatically: status semantics, resource types, and
 * chart colours for Recharts / Leaflet, which cannot read Tailwind classes.
 *
 * Rule: never write a raw hex in a component. Import from here.
 */

/** Operational statuses used by rescues, allocations and partners. */
export const STATUS = {
  DRAFT: 'draft',
  PENDING: 'pending',
  CREATED: 'created',
  ANALYZING: 'analyzing',
  MATCHING: 'matching',
  MATCHED: 'matched',
  PARTNER_ASSIGNED: 'partner_assigned',
  PICKUP_ASSIGNED: 'pickup_assigned',
  PICKUP_IN_PROGRESS: 'pickup_in_progress',
  DISPATCHED: 'dispatched',
  IN_TRANSIT: 'in_transit',
  DELIVERED: 'delivered',
  REALLOCATING: 'reallocating',
  CANCELLED: 'cancelled',
  FAILED: 'failed',
  EXPIRED: 'expired',
  PREDICTED: 'predicted',
};

/**
 * Presentation for each status: a label, a Tailwind class trio for badges,
 * and a raw colour for canvas-based surfaces (charts, map markers).
 */
export const STATUS_META = {
  [STATUS.DRAFT]: {
    label: 'Draft',
    className: 'bg-idle/10 text-idle ring-idle/25',
    color: '#64748b',
  },
  [STATUS.PENDING]: {
    label: 'Pending',
    className: 'bg-idle/10 text-idle ring-idle/25',
    color: '#64748b',
  },
  [STATUS.CREATED]: {
    label: 'Created',
    className: 'bg-idle/10 text-idle ring-idle/25',
    color: '#64748b',
  },
  [STATUS.ANALYZING]: {
    label: 'Analyzing',
    className: 'bg-active/10 text-active ring-active/25',
    color: '#38bdf8',
  },
  [STATUS.MATCHING]: {
    label: 'Matching',
    className: 'bg-active/10 text-active ring-active/25',
    color: '#38bdf8',
  },
  [STATUS.MATCHED]: {
    label: 'Matched',
    className: 'bg-brand-500/10 text-brand-400 ring-brand-500/25',
    color: '#14b98f',
  },
  [STATUS.PARTNER_ASSIGNED]: {
    label: 'Partner Assigned',
    className: 'bg-predicted/10 text-predicted ring-predicted/25',
    color: '#a78bfa',
  },
  [STATUS.PICKUP_ASSIGNED]: {
    label: 'Pickup Assigned',
    className: 'bg-predicted/10 text-predicted ring-predicted/25',
    color: '#a78bfa',
  },
  [STATUS.PICKUP_IN_PROGRESS]: {
    label: 'Pickup in Progress',
    className: 'bg-active/10 text-active ring-active/25',
    color: '#38bdf8',
  },
  [STATUS.DISPATCHED]: {
    label: 'Dispatched',
    className: 'bg-active/10 text-active ring-active/25',
    color: '#38bdf8',
  },
  [STATUS.IN_TRANSIT]: {
    label: 'In Transit',
    className: 'bg-active/10 text-active ring-active/25',
    color: '#38bdf8',
  },
  [STATUS.DELIVERED]: {
    label: 'Delivered',
    className: 'bg-success/10 text-success ring-success/25',
    color: '#22c55e',
  },
  [STATUS.REALLOCATING]: {
    label: 'Reallocating',
    className: 'bg-urgent/10 text-urgent ring-urgent/25',
    color: '#f59e0b',
  },
  [STATUS.CANCELLED]: {
    label: 'Cancelled',
    className: 'bg-critical/10 text-critical ring-critical/25',
    color: '#f4506a',
  },
  [STATUS.FAILED]: {
    label: 'Failed',
    className: 'bg-critical/10 text-critical ring-critical/25',
    color: '#f4506a',
  },
  [STATUS.EXPIRED]: {
    label: 'Expired',
    className: 'bg-critical/10 text-critical ring-critical/25',
    color: '#f4506a',
  },
  [STATUS.PREDICTED]: {
    label: 'Predicted',
    className: 'bg-predicted/10 text-predicted ring-predicted/25',
    color: '#a78bfa',
  },
};

/** Urgency drives sort order and colour weight across the app. */
export const URGENCY = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

export const URGENCY_META = {
  [URGENCY.CRITICAL]: { label: 'Critical', rank: 0, color: '#f4506a' },
  [URGENCY.HIGH]: { label: 'High', rank: 1, color: '#f59e0b' },
  [URGENCY.MEDIUM]: { label: 'Medium', rank: 2, color: '#38bdf8' },
  [URGENCY.LOW]: { label: 'Low', rank: 3, color: '#64748b' },
};

/** Resource domains. Medical is coordination/inventory only. */
export const RESOURCE_TYPE = {
  FOOD: 'food',
  MEDICAL: 'medical',
};

export const RESOURCE_META = {
  [RESOURCE_TYPE.FOOD]: { label: 'Food', icon: 'UtensilsCrossed', color: '#f59e0b' },
  [RESOURCE_TYPE.MEDICAL]: { label: 'Medical', icon: 'Pill', color: '#38bdf8' },
};

/** Network roles shown on the rescue map and its legend. */
export const NETWORK_ROLE = {
  PROVIDER: 'provider',
  RECIPIENT: 'recipient',
  PARTNER: 'partner',
  HUB: 'hub',
};

export const NETWORK_ROLE_META = {
  [NETWORK_ROLE.PROVIDER]: { label: 'Providers', color: '#14b98f' },
  [NETWORK_ROLE.RECIPIENT]: { label: 'Recipients', color: '#38bdf8' },
  [NETWORK_ROLE.PARTNER]: { label: 'Rescue Partners', color: '#a78bfa' },
  [NETWORK_ROLE.HUB]: { label: 'Rescue Hubs', color: '#f59e0b' },
};

/** The constraints the planner evaluates — reused by the reallocation UI. */
export const CONSTRAINTS = [
  { key: 'capacity', label: 'Capacity' },
  { key: 'distance', label: 'Distance' },
  { key: 'deadline', label: 'Deadline' },
  { key: 'availability', label: 'Availability' },
  { key: 'eligibility', label: 'Eligibility' },
  { key: 'pickup', label: 'Pickup feasibility' },
];

/** Recharts palette, ordered for multi-series charts. */
export const CHART_COLORS = ['#14b98f', '#38bdf8', '#f59e0b', '#a78bfa', '#f4506a', '#22c55e'];

export const CHART_AXIS = {
  stroke: '#64748b',
  grid: '#232d3b',
  fontSize: 12,
};

/**
 * Recharts hover styling. Recharts' defaults are a light grey band behind a
 * hovered bar and a white ring on the hovered point, which look harsh on dark
 * panels — these swap them for a dark violet tint that matches the app accent.
 *   bar  — the band behind a hovered bar group
 *   line — the vertical guide on line / area charts
 */
export const CHART_CURSOR = {
  bar: { fill: 'rgba(95, 77, 214, 0.14)', stroke: 'none' },
  line: { stroke: '#5f4dd6', strokeWidth: 1 },
};

/** The hovered point on line / area charts: series colour with a soft violet halo. */
export const CHART_ACTIVE_DOT = {
  r: 5,
  stroke: 'rgba(155, 140, 245, 0.35)',
  strokeWidth: 6,
};
