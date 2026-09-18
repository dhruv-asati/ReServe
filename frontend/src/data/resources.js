import { STATUS, URGENCY, RESOURCE_TYPE } from '@/utils/theme';

/**
 * Mock resources approaching their rescue deadline.
 *
 * `deadline` is a short, already-formatted countdown (mock data has no live
 * clock behind it) — urgency and status still come from utils/theme so the
 * cards share the same vocabulary as the rest of the app.
 */
export const AT_RISK_RESOURCES = [
  {
    id: 'RES-8841',
    resource: 'Prepared meals',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '75 trays',
    deadline: '42 min remaining',
    urgency: URGENCY.CRITICAL,
    status: STATUS.ANALYZING,
  },
  {
    id: 'RES-8839',
    resource: 'Vaccines (cold chain)',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '30 vials',
    deadline: '1 hr 10 min remaining',
    urgency: URGENCY.HIGH,
    status: STATUS.MATCHED,
  },
  {
    id: 'RES-8835',
    resource: 'Leafy greens',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '110 kg',
    deadline: '2 hr 30 min remaining',
    urgency: URGENCY.MEDIUM,
    status: STATUS.DRAFT,
  },
  {
    id: 'RES-8829',
    resource: 'Bread & pastries',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '64 kg',
    deadline: '5 hr remaining',
    urgency: URGENCY.LOW,
    status: STATUS.DRAFT,
  },
];

/**
 * Full mock records for the Resource Details page (`/resources/:id`).
 *
 * Category and unit are kept as raw codes (see data/rescueForm.js's
 * CATEGORY_OPTIONS / UNIT_OPTIONS) rather than pre-labelled strings, same as
 * every other resource-shaped mock in the app — the page resolves display
 * labels itself, so swapping this for a real endpoint later is a one-line
 * change and not a relabel.
 */
export const RESOURCE_DETAILS = [
  {
    id: 'RES-8841',
    resourceName: 'Prepared meals',
    resourceType: RESOURCE_TYPE.FOOD,
    category: 'prepared',
    quantity: 75,
    unit: 'trays',
    provider: 'Riverside Community Kitchen',
    location: '480 Riverside Ave, Warehouse B',
    createdAt: '2026-09-18T07:05:00',
    pickupDeadline: '2026-09-18T13:15:00',
    urgency: URGENCY.CRITICAL,
    status: STATUS.ANALYZING,
    description:
      'Surplus lunch service trays from a cancelled corporate catering order. Kept warm in insulated carriers; best picked up within the hour for food safety.',
  },
  {
    id: 'RES-8839',
    resourceName: 'Vaccines (cold chain)',
    resourceType: RESOURCE_TYPE.MEDICAL,
    category: 'vaccines',
    quantity: 30,
    unit: 'vials',
    provider: 'Metro General Hospital',
    location: '900 Metro Pkwy, Pharmacy Loading Dock',
    createdAt: '2026-09-18T06:20:00',
    pickupDeadline: '2026-09-18T14:00:00',
    urgency: URGENCY.HIGH,
    status: STATUS.MATCHED,
    description:
      'Overstock flu vaccine vials nearing end of cold-chain window. Requires refrigerated transport (2–8°C) end to end; cold pack included at pickup.',
  },
  {
    id: 'RES-8835',
    resourceName: 'Leafy greens',
    resourceType: RESOURCE_TYPE.FOOD,
    category: 'produce',
    quantity: 110,
    unit: 'kg',
    provider: 'Green Valley Farms',
    location: '12 Orchard Rd, Loading Bay 2',
    createdAt: '2026-09-18T05:40:00',
    pickupDeadline: '2026-09-18T15:30:00',
    urgency: URGENCY.MEDIUM,
    status: STATUS.DRAFT,
    description:
      'Mixed spinach and kale, slightly over-ordered for a farmers-market run. Crated and refrigerated; still well within safe shelf life.',
  },
  {
    id: 'RES-8829',
    resourceName: 'Bread & pastries',
    resourceType: RESOURCE_TYPE.FOOD,
    category: 'bakery',
    quantity: 64,
    unit: 'kg',
    provider: 'Sunrise Bakery Co.',
    location: '221 Baker St, Front Counter',
    createdAt: '2026-09-18T04:10:00',
    pickupDeadline: '2026-09-18T18:00:00',
    urgency: URGENCY.LOW,
    status: STATUS.DRAFT,
    description:
      "End-of-day bread and pastries unsold from the morning bake. Boxed and shelf-stable at room temperature for the rest of the day.",
  },
  {
    id: 'RES-8822',
    resourceName: 'Wound care supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    category: 'supplies',
    quantity: 12,
    unit: 'boxes',
    provider: 'Northside Pharmacy',
    location: '55 Northside Blvd, Storeroom',
    createdAt: '2026-09-17T22:15:00',
    pickupDeadline: '2026-09-19T09:00:00',
    urgency: URGENCY.LOW,
    status: STATUS.REALLOCATING,
    description:
      'Gauze, dressings, and antiseptic wipes from a discontinued supplier line. Sealed, unopened boxes with no cold-chain requirement.',
  },
];
