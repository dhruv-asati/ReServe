/**
 * Adapters between the backend's resource shape (snake_case, UPPERCASE enums —
 * see backend/app/schemas/resource.py) and the shapes the pages were built
 * around (camelCase, lowercase vocabulary from utils/theme.js).
 */

export const lower = (value) => (value == null ? '' : String(value).toLowerCase());

const RESOURCE_STATUS_TO_UI = {
  AVAILABLE: 'pending',
  MATCHING: 'matching',
  ALLOCATED: 'matched',
  IN_TRANSIT: 'in_transit',
  DELIVERED: 'delivered',
  EXPIRED: 'expired',
  CANCELLED: 'cancelled',
};

/** ResourceStatus -> the STATUS vocabulary StatusBadge understands. */
export function resourceStatusToUi(status) {
  return RESOURCE_STATUS_TO_UI[status] ?? lower(status);
}

/** Minutes granted before pickup, by urgency tier (same tiers the mock analysis used). */
const RESCUE_WINDOW_MINUTES = { critical: 30, high: 90, medium: 180, low: 360 };

export function rescueWindowMinutesFor(urgency) {
  return RESCUE_WINDOW_MINUTES[lower(urgency)] ?? RESCUE_WINDOW_MINUTES.medium;
}

export function formatMinutes(minutes) {
  if (minutes < 60) return `${minutes} minutes`;
  const hours = minutes / 60;
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)} hour${hours === 1 ? '' : 's'}`;
}

/** Plain, flat view of a backend resource for summary cards. */
export function toDisplayResource(out) {
  return {
    id: out.id,
    resource: out.title,
    resourceType: lower(out.resource_type),
    category: out.category ?? '',
    quantity: Number(out.quantity),
    unit: out.unit,
    provider: out.provider?.full_name ?? 'Unknown provider',
    location: out.location_address,
    urgency: lower(out.urgency),
    status: out.status,
    deadline: out.expiry_time ?? null,
    rescueWindowMinutes: rescueWindowMinutesFor(out.urgency),
  };
}

/** Backend resource -> the record shape the Resource Details page renders. */
export function toResourceDetails(out) {
  return {
    id: out.id,
    resourceName: out.title,
    resourceType: lower(out.resource_type),
    category: out.category ?? '',
    quantity: Number(out.quantity),
    unit: out.unit,
    provider: out.provider?.full_name ?? 'Unknown provider',
    location: out.location_address,
    createdAt: out.created_at,
    pickupDeadline: out.expiry_time ?? out.pickup_window_end ?? null,
    urgency: lower(out.urgency),
    status: resourceStatusToUi(out.status),
    description: out.description ?? '',
  };
}
