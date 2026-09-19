import { STATUS, RESOURCE_TYPE } from '@/utils/theme';
import { DEMO_OPERATION } from '@/data/operationDetail';

/**
 * MOCK DATA — the rescue operations list on the Operations page
 * (`/app/operations`).
 *
 * Everything here is invented for this demo: the operations, providers,
 * recipients, rescue partners, ETAs and deadlines are illustrative, and
 * `createdMinutesAgo` / `geo` only feed the illustrative details view.
 * Nothing is live, there is no backend, and no real dispatch or GPS data
 * sits behind any of it. The data covers every operation status so each
 * badge, ETA and details-view state can be seen.
 *
 * Fields
 *   recipient / partner  null until one has been matched / assigned
 *   eta / deadline       display strings, not timestamps
 *   note                 reason shown in the details view for reallocating,
 *                        cancelled and expired operations
 *   atRisk               optional. true when an in-flight operation is in
 *                        danger of missing its rescue deadline. The Operations
 *                        page's "At Risk" filter also counts every
 *                        reallocating operation, so that status needs no flag
 *                        (see utils/operationFilters.js)
 *   createdMinutesAgo    illustrative age, used to derive stage timestamps
 *   geo                  fictional Bengaluru coordinates for the details map;
 *                        `recipient` is null while none is matched
 *
 * RS-1024 is built from DEMO_OPERATION, so its row can never drift from the
 * demo operation whose full details already existed on this page.
 */

const RS_1024 = {
  id: DEMO_OPERATION.id,
  resource: DEMO_OPERATION.resource,
  resourceType: DEMO_OPERATION.resourceType,
  quantity: DEMO_OPERATION.quantity,
  unit: DEMO_OPERATION.unit,
  provider: DEMO_OPERATION.provider,
  recipient: DEMO_OPERATION.recipient,
  partner: DEMO_OPERATION.partner,
  status: DEMO_OPERATION.status,
  eta: DEMO_OPERATION.eta,
  deadline: DEMO_OPERATION.deadline,
  location: DEMO_OPERATION.location,
};

export const RESCUE_OPERATIONS = [
  RS_1024,
  {
    id: 'RS-1025',
    resource: 'Bakery Surplus',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 35,
    unit: 'boxes',
    provider: 'Bakery ABC',
    recipient: 'Shelter B',
    partner: 'Rescue Partner #07',
    status: STATUS.PICKUP_IN_PROGRESS,
    eta: '48 min',
    deadline: '10:45 PM',
    location: 'Koramangala, Bengaluru',
    createdMinutesAgo: 95,
    geo: {
      provider: { lat: 12.9352, lng: 77.6245 },
      recipient: { lat: 12.9309, lng: 77.6316 },
    },
  },
  {
    id: 'RS-1026',
    resource: 'Medical Supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: 20,
    unit: 'units',
    provider: 'City Hospital',
    recipient: 'Authorized NGO',
    partner: 'Rescue Partner #03',
    status: STATUS.PARTNER_ASSIGNED,
    eta: '1 hr 10 min',
    deadline: 'Tomorrow, 9:00 AM',
    location: 'Jayanagar, Bengaluru',
    createdMinutesAgo: 140,
    geo: {
      provider: { lat: 12.9756, lng: 77.6068 },
      recipient: { lat: 12.925, lng: 77.5938 },
    },
  },
  {
    id: 'RS-1027',
    resource: 'Fresh Produce',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 180,
    unit: 'kg',
    provider: 'Green Valley Farms',
    recipient: 'Riverside Community Kitchen',
    partner: null,
    status: STATUS.MATCHED,
    eta: 'Awaiting partner',
    deadline: '9:00 PM',
    location: 'Hebbal, Bengaluru',
    atRisk: true,
    createdMinutesAgo: 70,
    geo: {
      provider: { lat: 13.1007, lng: 77.5963 },
      recipient: { lat: 13.0358, lng: 77.597 },
    },
  },
  {
    id: 'RS-1028',
    resource: 'Canned Goods',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 340,
    unit: 'kg',
    provider: 'Harbor Wholesale',
    recipient: null,
    partner: null,
    status: STATUS.MATCHING,
    eta: 'Pending match',
    deadline: 'Tomorrow, 12:00 PM',
    location: 'Whitefield, Bengaluru',
    createdMinutesAgo: 25,
    geo: {
      provider: { lat: 12.9698, lng: 77.75 },
      recipient: null,
    },
  },
  {
    id: 'RS-1029',
    resource: 'Cooked Rice',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 150,
    unit: 'meals',
    provider: 'Spice Route Kitchen',
    recipient: null,
    partner: null,
    status: STATUS.CREATED,
    eta: 'Pending match',
    deadline: '11:00 PM',
    location: 'Malleshwaram, Bengaluru',
    atRisk: true,
    createdMinutesAgo: 6,
    geo: {
      provider: { lat: 13.0035, lng: 77.5647 },
      recipient: null,
    },
  },
  {
    id: 'RS-1030',
    resource: 'Wound Care Supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: 12,
    unit: 'boxes',
    provider: 'Northside Pharmacy',
    recipient: null,
    partner: 'Rescue Partner #09',
    status: STATUS.REALLOCATING,
    eta: 'Recalculating',
    deadline: '8:15 PM',
    location: 'BTM Layout, Bengaluru',
    note: 'The earlier match fell through because the recipient could no longer take the delivery — a demo scenario.',
    createdMinutesAgo: 175,
    geo: {
      provider: { lat: 12.9166, lng: 77.6101 },
      recipient: null,
    },
  },
  {
    id: 'RS-1031',
    resource: 'Dairy Products',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 220,
    unit: 'kg',
    provider: 'Lakeside Dairy Co-op',
    recipient: "St. Mary's Food Pantry",
    partner: 'Rescue Partner #05',
    status: STATUS.DELIVERED,
    eta: 'Arrived',
    deadline: '6:30 PM',
    location: 'HSR Layout, Bengaluru',
    createdMinutesAgo: 260,
    geo: {
      provider: { lat: 12.8452, lng: 77.6602 },
      recipient: { lat: 12.9116, lng: 77.6474 },
    },
  },
  {
    id: 'RS-1032',
    resource: 'Sandwiches',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 45,
    unit: 'trays',
    provider: 'Cafe Meridian',
    recipient: null,
    partner: null,
    status: STATUS.CANCELLED,
    eta: '—',
    deadline: '10:00 PM',
    location: 'MG Road, Bengaluru',
    note: 'The provider withdrew the surplus before a match was confirmed — a demo scenario.',
    createdMinutesAgo: 150,
    geo: {
      provider: { lat: 12.9756, lng: 77.6068 },
      recipient: null,
    },
  },
  {
    id: 'RS-1033',
    resource: 'Bread & Rolls',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: 60,
    unit: 'kg',
    provider: 'Sunrise Bakery Co.',
    recipient: null,
    partner: null,
    status: STATUS.EXPIRED,
    eta: '—',
    deadline: 'Yesterday, 9:00 PM',
    location: 'Basavanagudi, Bengaluru',
    note: 'The deadline passed before a compatible recipient could be matched — a demo scenario.',
    createdMinutesAgo: 1560,
    geo: {
      provider: { lat: 12.9422, lng: 77.575 },
      recipient: null,
    },
  },
  {
    id: 'RS-1034',
    resource: 'Insulin (refrigerated)',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: 60,
    unit: 'units',
    provider: 'Metro General Hospital',
    recipient: 'Eastside Free Clinic',
    partner: 'Rescue Partner #02',
    status: STATUS.IN_TRANSIT,
    eta: '18 min',
    deadline: '9:30 PM',
    location: 'Whitefield, Bengaluru',
    createdMinutesAgo: 120,
    geo: {
      provider: { lat: 12.9569, lng: 77.7011 },
      recipient: { lat: 12.9698, lng: 77.75 },
    },
  },
];
