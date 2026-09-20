import { Building2, Handshake, Truck, Warehouse } from 'lucide-react';

import { RESOURCE_TYPE } from '@/utils/theme';

/**
 * Shared vocabulary and helpers for the Network Directory (`/app/network`):
 * the category / availability / verification enums, their presentation, and
 * the pure filter + grouping functions used by the page, the filter bar, the
 * organization cards and the demo map.
 *
 * DEMO DATA ONLY. Everything these helpers describe is invented for the demo
 * (see data/networkDirectory.js). The availability and verification values
 * are illustrative labels in mock data — not statements about any real
 * organization, and not live status.
 *
 * NOTE: this file must not import from data/networkDirectory.js — the data
 * file imports the enums from here.
 */

/** The "no filter" value shared by every filter dropdown / chip group. */
export const ALL = 'all';

/* ---------- Organization categories ---------- */

export const ORG_TYPE = {
  NGO: 'ngo',
  SHELTER: 'shelter',
  PARTNER: 'partner',
  HUB: 'hub',
};

/** Directory order: sections, chips and the map legend all follow it. */
export const ORG_TYPES = [ORG_TYPE.NGO, ORG_TYPE.SHELTER, ORG_TYPE.PARTNER, ORG_TYPE.HUB];

/**
 * `label` is the plural (chips, section headings), `singular` names one
 * organization. `color` paints the map marker; the values mirror the design
 * tokens in styles/index.css (brand / active / predicted / urgent) because
 * Leaflet markers cannot read Tailwind classes.
 */
export const ORG_TYPE_META = {
  [ORG_TYPE.NGO]: {
    label: 'NGOs',
    singular: 'NGO',
    description: 'Community organizations that receive surplus resources and serve people directly.',
    icon: Handshake,
    color: '#14b98f',
  },
  [ORG_TYPE.SHELTER]: {
    label: 'Shelters',
    singular: 'Shelter',
    description: 'Shelters that can take in prepared meals and supplies for the people they house.',
    icon: Building2,
    color: '#38bdf8',
  },
  [ORG_TYPE.PARTNER]: {
    label: 'Rescue Partners',
    singular: 'Rescue Partner',
    description: 'Volunteers and couriers who move resources from providers to recipients.',
    icon: Truck,
    color: '#a78bfa',
  },
  [ORG_TYPE.HUB]: {
    label: 'Rescue Hubs',
    singular: 'Rescue Hub',
    description: 'Hubs that sort and hold resources between pickup and onward allocation.',
    icon: Warehouse,
    color: '#f59e0b',
  },
};

/* ---------- Availability (demo status) ---------- */

export const AVAILABILITY = {
  AVAILABLE: 'available',
  LIMITED: 'limited',
  UNAVAILABLE: 'unavailable',
};

export const AVAILABILITY_ORDER = [
  AVAILABILITY.AVAILABLE,
  AVAILABILITY.LIMITED,
  AVAILABILITY.UNAVAILABLE,
];

/** `tone` is a Badge tone; `color` paints the availability dot on map markers. */
export const AVAILABILITY_META = {
  [AVAILABILITY.AVAILABLE]: { label: 'Available', tone: 'success', color: '#22c55e' },
  [AVAILABILITY.LIMITED]: { label: 'Limited', tone: 'urgent', color: '#f59e0b' },
  [AVAILABILITY.UNAVAILABLE]: { label: 'Unavailable', tone: 'neutral', color: '#64748b' },
};

/* ---------- Verification (demo label) ---------- */

export const VERIFICATION = {
  VERIFIED: 'verified',
  PENDING: 'pending',
  UNLISTED: 'unlisted',
};

export const VERIFICATION_META = {
  [VERIFICATION.VERIFIED]: {
    label: 'Verified (demo label)',
    tone: 'success',
    note: 'Illustrative label in mock data — no real organization was verified.',
  },
  [VERIFICATION.PENDING]: {
    label: 'Pending review (demo label)',
    tone: 'urgent',
    note: 'Illustrative label in mock data — no real review is under way.',
  },
  [VERIFICATION.UNLISTED]: {
    label: 'Not listed (demo label)',
    tone: 'neutral',
    note: 'Illustrative label in mock data — not a statement about any real organization.',
  },
};

/* ---------- Filters ---------- */

/**
 * `category` is the organization type. `name` and `location` are free-text
 * searches; `resourceType` and `availability` are dropdown values. Every
 * field's "off" value is '' (text) or ALL (choice).
 */
export const DEFAULT_FILTERS = {
  name: '',
  location: '',
  category: ALL,
  resourceType: ALL,
  availability: ALL,
};

/** True when any filter differs from its default. */
export function hasActiveFilters(filters) {
  return (
    filters.category !== ALL ||
    filters.resourceType !== ALL ||
    filters.availability !== ALL ||
    filters.name.trim() !== '' ||
    filters.location.trim() !== ''
  );
}

/** "Indiranagar, Bengaluru" — the area and city joined for display. */
export function locationLabel({ area, city }) {
  return [area, city].filter(Boolean).join(', ');
}

/** Case-insensitive, whitespace-tolerant "contains". */
function includesText(haystack, needle) {
  const query = needle.trim().toLowerCase().replace(/\s+/g, ' ');
  if (!query) return true;
  return haystack.toLowerCase().replace(/\s+/g, ' ').includes(query);
}

/**
 * Narrow the directory. All conditions must hold (AND):
 *   category      the organization's type
 *   name          text inside the organization name
 *   location      text inside "area, city"
 *   resourceType  the organization handles that resource (food / medical)
 *   availability  the organization's demo availability value
 *
 * The directory cards and the map both render this one result, which is what
 * keeps them in step.
 */
export function filterOrganizations(organizations, filters) {
  const { name, location, category, resourceType, availability } = filters;

  return organizations.filter((organization) => {
    if (category !== ALL && organization.type !== category) return false;
    if (resourceType !== ALL && !organization.resourceTypes?.includes(resourceType)) return false;
    if (availability !== ALL && organization.availability !== availability) return false;
    if (!includesText(organization.name, name)) return false;
    if (!includesText(locationLabel(organization), location)) return false;
    return true;
  });
}

/** Totals per category, plus the overall total under ALL — for the chips. */
export function countByCategory(organizations) {
  const counts = { [ALL]: organizations.length };
  for (const type of ORG_TYPES) counts[type] = 0;
  for (const organization of organizations) {
    if (organization.type in counts) counts[organization.type] += 1;
  }
  return counts;
}

/** Split into directory sections, in ORG_TYPES order; empty sections are dropped. */
export function groupByCategory(organizations) {
  return ORG_TYPES.map((type) => ({
    type,
    ...ORG_TYPE_META[type],
    organizations: organizations.filter((organization) => organization.type === type),
  })).filter((section) => section.organizations.length > 0);
}

/* ---------- Workload ---------- */

/** Fill percentage (0–100) of a `{ active, max }` workload, or null if not measurable. */
export function workloadPercent(workload) {
  if (!workload || !workload.max) return null;
  const percent = Math.round((workload.active / workload.max) * 100);
  return Math.min(100, Math.max(0, percent));
}

/** Bar colour: critical from 90 %, urgent from 70 %, otherwise the default brand fill. */
export function workloadTone(percent) {
  if (percent === null) return 'default';
  if (percent >= 90) return 'critical';
  if (percent >= 70) return 'urgent';
  return 'default';
}

/* ---------- Resource filter options ---------- */

/** Resource types offered by the "supported resource type" filter. */
export const RESOURCE_FILTER_TYPES = [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL];
