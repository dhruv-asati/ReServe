/**
 * Mock analytics data.
 *
 * ILLUSTRATIVE ONLY — every number here is a fabricated placeholder used to
 * exercise the Analytics page's layout and charts before a real reporting
 * endpoint exists. Nothing in this file should be read as a verified,
 * production, or real-world impact figure. Shape mirrors what the real
 * endpoint will return, so swapping the service call in analyticsService.js
 * for a live request later needs no change here or in Analytics.jsx.
 */

/** Summary cards shown at the top of the page. */
export const ANALYTICS_SUMMARY = {
  resourcesRescued: {
    value: 1284,
    unit: 'kg',
    delta: '+164 kg vs. last period',
    tone: 'brand',
  },
  successfulAllocations: {
    value: 342,
    delta: '96% success rate',
    tone: 'success',
  },
  avgMatchingTime: {
    value: 4.2,
    unit: 'min',
    delta: '-0.6 min vs. last period',
    tone: 'active',
  },
  activeOperations: {
    value: 12,
    delta: '4 awaiting match',
    tone: 'urgent',
  },
};

/** Resources rescued over time (kg), daily for the last two weeks. */
export const RESOURCES_RESCUED_OVER_TIME = [
  { label: 'Sep 6', kg: 62 },
  { label: 'Sep 7', kg: 78 },
  { label: 'Sep 8', kg: 55 },
  { label: 'Sep 9', kg: 91 },
  { label: 'Sep 10', kg: 84 },
  { label: 'Sep 11', kg: 103 },
  { label: 'Sep 12', kg: 97 },
  { label: 'Sep 13', kg: 112 },
  { label: 'Sep 14', kg: 88 },
  { label: 'Sep 15', kg: 121 },
  { label: 'Sep 16', kg: 109 },
  { label: 'Sep 17', kg: 134 },
  { label: 'Sep 18', kg: 118 },
  { label: 'Sep 19', kg: 142 },
];

/** Food vs. medical split of rescued resources (kg). */
export const FOOD_VS_MEDICAL = [
  { name: 'Food', value: 946, key: 'food' },
  { name: 'Medical', value: 338, key: 'medical' },
];

/** Successful vs. failed/expired allocation attempts, by week. */
export const SUCCESSFUL_ALLOCATIONS = [
  { label: 'Wk 1', successful: 71, unsuccessful: 4 },
  { label: 'Wk 2', successful: 84, unsuccessful: 3 },
  { label: 'Wk 3', successful: 79, unsuccessful: 6 },
  { label: 'Wk 4', successful: 108, unsuccessful: 2 },
];

/** Average matching time (minutes) by week. */
export const AVG_MATCHING_TIME = [
  { label: 'Wk 1', minutes: 5.8 },
  { label: 'Wk 2', minutes: 5.1 },
  { label: 'Wk 3', minutes: 4.6 },
  { label: 'Wk 4', minutes: 4.2 },
];

/**
 * Supply vs. demand (kg), by week — kg of resources logged as available
 * ("supply") against kg requested by recipients ("demand"). Same unit and
 * weekly cadence as the successful-allocations and matching-time charts
 * above, so the two sections read as one consistent time series.
 */
export const SUPPLY_VS_DEMAND = [
  { label: 'Wk 1', supply: 420, demand: 381 },
  { label: 'Wk 2', supply: 460, demand: 414 },
  { label: 'Wk 3', supply: 505, demand: 472 },
  { label: 'Wk 4', supply: 540, demand: 512 },
];

/**
 * Rescues completed before vs. after their stated deadline. Counts, not a
 * pre-computed percentage — the page derives the on-time rate from these so
 * the number shown always matches the chart.
 */
export const DEADLINE_PERFORMANCE = [
  { name: 'Before deadline', value: 267, key: 'onTime' },
  { name: 'After deadline', value: 75, key: 'late' },
];

/** Operations by completion status, as counts. */
export const OPERATION_COMPLETION = [
  { name: 'Completed', value: 298, key: 'completed' },
  { name: 'In Progress', value: 34, key: 'inProgress' },
  { name: 'Cancelled / Failed', value: 10, key: 'cancelled' },
];

/**
 * At-risk operations vs. completed operations, by week — same weekly
 * cadence and "count of operations" unit as the other weekly charts, so it
 * can be read side by side with successful allocations and matching time.
 */
export const AT_RISK_VS_COMPLETED = [
  { label: 'Wk 1', atRisk: 9, completed: 71 },
  { label: 'Wk 2', atRisk: 7, completed: 84 },
  { label: 'Wk 3', atRisk: 11, completed: 79 },
  { label: 'Wk 4', atRisk: 5, completed: 108 },
];

/**
 * Predictive Surplus demo — a worked example of how a week's worth of
 * historical surplus counts could feed a short-term forecast for a single
 * upcoming window. Every value here (the daily history, the predicted
 * range, and the window itself) is illustrative and fixed for the demo; it
 * is not the output of a real forecasting model and is not a guarantee of
 * future surplus.
 */
export const SURPLUS_PREDICTION_HISTORY = [
  { label: 'Mon', meals: 65 },
  { label: 'Tue', meals: 72 },
  { label: 'Wed', meals: 78 },
  { label: 'Thu', meals: 74 },
  { label: 'Fri', meals: 96 },
];

export const SURPLUS_PREDICTION = {
  windowLabel: '10:30 PM – 11:30 PM',
  low: 80,
  high: 100,
  unit: 'meals',
};
