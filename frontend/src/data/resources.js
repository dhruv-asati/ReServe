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
