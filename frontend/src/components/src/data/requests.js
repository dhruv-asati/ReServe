import { STATUS, RESOURCE_TYPE } from '@/utils/theme';

/**
 * Mock rescue requests for the /app/rescues (Rescue Requests) page.
 *
 * Shape mirrors ACTIVE_OPERATIONS (data/operations.js) plus the fields this
 * page needs — location and deadline — so a real endpoint can slot in later
 * without changing any component.
 *
 *   Incoming  — requests other organizations have sent to us, awaiting a
 *               response or currently being fulfilled.
 *   Outgoing  — requests we have raised with providers or partners.
 *   Completed — requests that have reached a final state, delivered or
 *               cancelled, from either direction.
 */
export const INCOMING_REQUESTS = [
  {
    id: 'REQ-3104',
    resource: 'Vegetarian Meals',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '150 servings',
    provider: 'Green Valley Farms',
    recipient: 'Riverside Community Kitchen',
    location: 'Riverside District, Sector 4',
    deadline: 'Today, 6:00 PM',
    status: STATUS.PENDING,
  },
  {
    id: 'REQ-3101',
    resource: 'Bakery Surplus',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '95 kg',
    provider: 'Sunrise Bakery Co.',
    recipient: 'Downtown Shelter',
    location: 'Downtown, Block 12',
    deadline: 'Today, 8:30 PM',
    status: STATUS.MATCHED,
  },
  {
    id: 'REQ-3098',
    resource: 'Medical Supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '40 boxes',
    provider: 'Metro General Hospital',
    recipient: 'Eastside Free Clinic',
    location: 'Eastside, Clinic Row',
    deadline: 'Tomorrow, 9:00 AM',
    status: STATUS.PICKUP_ASSIGNED,
  },
  {
    id: 'REQ-3092',
    resource: 'Canned Goods',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '340 kg',
    provider: 'Harbor Wholesale',
    recipient: 'Regional Food Bank',
    location: 'Harbor Industrial Park',
    deadline: 'Tomorrow, 2:00 PM',
    status: STATUS.IN_TRANSIT,
  },
  {
    id: 'REQ-3087',
    resource: 'Dairy Products',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '220 kg',
    provider: 'Lakeside Dairy Co-op',
    recipient: "St. Mary's Food Pantry",
    location: 'Lakeside, Route 9',
    deadline: 'Today, 5:00 PM',
    status: STATUS.PENDING,
  },
];

export const OUTGOING_REQUESTS = [
  {
    id: 'REQ-3110',
    resource: 'Wound Care Supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '12 boxes',
    provider: 'Northside Pharmacy',
    recipient: 'Mobile Health Unit 3',
    location: 'Northside, Unit Bay 2',
    deadline: 'Today, 7:00 PM',
    status: STATUS.PENDING,
  },
  {
    id: 'REQ-3106',
    resource: 'Fresh Produce',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '180 kg',
    provider: 'Green Valley Farms',
    recipient: 'Riverside Community Kitchen',
    location: 'Riverside District, Sector 4',
    deadline: 'Today, 4:30 PM',
    status: STATUS.MATCHED,
  },
  {
    id: 'REQ-3099',
    resource: 'Vegetarian Meals',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '75 servings',
    provider: 'Community Kitchen Collective',
    recipient: 'Westside Youth Center',
    location: 'Westside, Main Ave',
    deadline: 'Tomorrow, 11:00 AM',
    status: STATUS.PICKUP_ASSIGNED,
  },
  {
    id: 'REQ-3090',
    resource: 'Insulin (Refrigerated)',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '60 units',
    provider: 'Metro General Hospital',
    recipient: 'Eastside Free Clinic',
    location: 'Eastside, Clinic Row',
    deadline: 'Today, 9:45 PM',
    status: STATUS.IN_TRANSIT,
  },
];

export const COMPLETED_REQUESTS = [
  {
    id: 'REQ-3071',
    resource: 'Bakery Surplus',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '110 kg',
    provider: 'Sunrise Bakery Co.',
    recipient: 'Downtown Shelter',
    location: 'Downtown, Block 12',
    deadline: 'Delivered yesterday, 7:15 PM',
    status: STATUS.DELIVERED,
  },
  {
    id: 'REQ-3065',
    resource: 'Medical Supplies',
    resourceType: RESOURCE_TYPE.MEDICAL,
    quantity: '25 boxes',
    provider: 'Northside Pharmacy',
    recipient: 'Mobile Health Unit 3',
    location: 'Northside, Unit Bay 2',
    deadline: 'Delivered 2 days ago',
    status: STATUS.DELIVERED,
  },
  {
    id: 'REQ-3058',
    resource: 'Canned Goods',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '300 kg',
    provider: 'Harbor Wholesale',
    recipient: 'Regional Food Bank',
    location: 'Harbor Industrial Park',
    deadline: 'Delivered 3 days ago',
    status: STATUS.DELIVERED,
  },
  {
    id: 'REQ-3052',
    resource: 'Dairy Products',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '150 kg',
    provider: 'Lakeside Dairy Co-op',
    recipient: "St. Mary's Food Pantry",
    location: 'Lakeside, Route 9',
    deadline: 'Cancelled 4 days ago',
    status: STATUS.CANCELLED,
  },
  {
    id: 'REQ-3047',
    resource: 'Vegetarian Meals',
    resourceType: RESOURCE_TYPE.FOOD,
    quantity: '60 servings',
    provider: 'Community Kitchen Collective',
    recipient: 'Westside Youth Center',
    location: 'Westside, Main Ave',
    deadline: 'Delivered 5 days ago',
    status: STATUS.DELIVERED,
  },
];
