/**
 * Mock recent rescue activity for the dashboard timeline.
 *
 * `stage` names the step in the rescue lifecycle (created → analyzed →
 * matched → assigned → completed) and drives which icon ActivityTimeline
 * renders — keep new stages in sync with the map in that component.
 */
export const RECENT_ACTIVITY = [
  {
    id: 'evt-1',
    stage: 'completed',
    title: 'Rescue completed',
    description: 'Dairy products delivered to St. Mary\u2019s Food Pantry',
    time: '6 min ago',
  },
  {
    id: 'evt-2',
    stage: 'assigned',
    title: 'Partner assigned',
    description: 'Northside Pharmacy paired with Mobile Health Unit 3',
    time: '18 min ago',
  },
  {
    id: 'evt-3',
    stage: 'matched',
    title: 'Match found',
    description: 'Bakery surplus matched to Downtown Shelter',
    time: '34 min ago',
  },
  {
    id: 'evt-4',
    stage: 'analyzed',
    title: 'AI analyzed',
    description: 'Canned goods batch scored for allocation priority',
    time: '51 min ago',
  },
  {
    id: 'evt-5',
    stage: 'created',
    title: 'Resource created',
    description: 'Fresh produce surplus logged by Green Valley Farms',
    time: '1 hr 12 min ago',
  },
];
