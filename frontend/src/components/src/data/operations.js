import { STATUS, RESOURCE_TYPE } from '@/utils/theme';

/**
 * Mock active rescue operations for the dashboard.
 *
 * Shape mirrors what the real endpoint will return — resourceType and status
 * are drawn from utils/theme so cards render with the same badges and icons
 * the rest of the app will use once matching/operations pages are built.
 */
export const ACTIVE_OPERATIONS = [
  {
    id: 'RSC-2043',
    resource: 'Fresh produce',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '180 kg',
    provider: 'Green Valley Farms',
    recipient: 'Riverside Community Kitchen',
    status: STATUS.IN_TRANSIT,
    eta: '32 min',
  },
  {
    id: 'RSC-2041',
    resource: 'Insulin (refrigerated)',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '60 units',
    provider: 'Metro General Hospital',
    recipient: 'Eastside Free Clinic',
    status: STATUS.DISPATCHED,
    eta: '18 min',
  },
  {
    id: 'RSC-2038',
    resource: 'Bakery surplus',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '95 kg',
    provider: 'Sunrise Bakery Co.',
    recipient: 'Downtown Shelter',
    status: STATUS.MATCHED,
    eta: '1 hr 05 min',
  },
  {
    id: 'RSC-2035',
    resource: 'Canned goods',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '340 kg',
    provider: 'Harbor Wholesale',
    recipient: 'Regional Food Bank',
    status: STATUS.ANALYZING,
    eta: 'Pending match',
  },
  {
    id: 'RSC-2031',
    resource: 'Wound care supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '12 boxes',
    provider: 'Northside Pharmacy',
    recipient: 'Mobile Health Unit 3',
    status: STATUS.REALLOCATING,
    eta: 'Recalculating',
  },
  {
    id: 'RSC-2027',
    resource: 'Dairy products',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '220 kg',
    provider: 'Lakeside Dairy Co-op',
    recipient: "St. Mary's Food Pantry",
    status: STATUS.DELIVERED,
    eta: 'Arrived',
  },
];
