/**
 * Mock recent rescue activity for the dashboard timeline.
 *
 * `stage` names the step in the rescue lifecycle (created → analyzed →
 * matched → assigned → pickup → completed) and drives which icon
 * ActivityTimeline renders — keep new stages in sync with the map in
 * utils/icons.js. `status` maps to the shared STATUS vocabulary in
 * utils/theme.js and is shown as a StatusBadge, so it stays consistent
 * with every other status pill in the app (operations, resources, etc.).
 */
export const RECENT_ACTIVITY = [
  {
    id: 'evt-1',
    stage: 'completed',
    status: 'delivered',
    title: 'Resource delivered',
    description: 'Dairy products delivered to St. Mary\u2019s Food Pantry',
    time: '6 min ago',
  },
  {
    id: 'evt-2',
    stage: 'pickup',
    status: 'in_transit',
    title: 'Pickup started',
    description: 'Mobile Health Unit 3 en route to Northside Pharmacy',
    time: '15 min ago',
  },
  {
    id: 'evt-3',
    stage: 'assigned',
    status: 'dispatched',
    title: 'Partner assigned',
    description: 'Northside Pharmacy paired with Mobile Health Unit 3',
    time: '18 min ago',
  },
  {
    id: 'evt-4',
    stage: 'matched',
    status: 'matched',
    title: 'Match found',
    description: 'Bakery surplus matched to Downtown Shelter',
    time: '34 min ago',
  },
  {
    id: 'evt-5',
    stage: 'analyzed',
    status: 'analyzing',
    title: 'AI analysis completed',
    description: 'Canned goods batch scored for allocation priority',
    time: '51 min ago',
  },
  {
    id: 'evt-6',
    stage: 'created',
    status: 'draft',
    title: 'Resource created',
    description: 'Fresh produce surplus logged by Green Valley Farms',
    time: '1 hr 12 min ago',
  },
];
