import { api, USE_MOCKS } from './api';

/**
 * Analytics data access — real data only.
 *
 * Every figure on the Analytics page comes from the backend (`/dashboard/overview`,
 * `/analytics/trends`, `/analytics/resource-types`, `/analytics/insights`,
 * `/analytics/surplus-forecast`, `/analytics/surplus-alert`). Nothing here
 * invents numbers: when there is no data the services resolve empty values
 * (zeros, `null`, `[]`) and the page draws an empty state instead of a chart.
 *
 * With `VITE_USE_MOCKS` not set to 'false' the app is not talking to the
 * backend at all, so every getter resolves those same empty values (the page
 * tells the user how to connect). There is deliberately no mock dataset.
 *
 * Quantities are stored in mixed units (meals, kg, vials...), so aggregate
 * figures are plain "units", never kg.
 */

/** True when the page is reading from the API. */
export const ANALYTICS_LIVE = !USE_MOCKS;

/** Days covered by the "rescued over time" chart. */
export const TREND_DAYS = 14;

/** Weeks covered by the weekly charts (backend allows 1-12). */
export const INSIGHT_WEEKS = 4;

/** "2026-09-06" -> "Sep 6" (parsed by hand so the UTC day never shifts with the browser timezone). */
function dayLabel(isoDay) {
  const [year, month, day] = isoDay.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** 0 -> "12 AM", 22 -> "10 PM". */
function hourLabel(hour) {
  const h = ((hour % 24) + 24) % 24;
  return `${h % 12 || 12} ${h < 12 ? 'AM' : 'PM'}`;
}

/** The browser's UTC offset in minutes (India = 330), so the backend can work in the viewer's local time. */
function utcOffsetMinutes() {
  return -new Date().getTimezoneOffset() || 0;
}

// ---------------------------------------------------------------------------
// Summary cards / trend / food-vs-medical
// ---------------------------------------------------------------------------

const EMPTY_SUMMARY = {
  resourcesRescued: { value: 0, unit: 'units', delta: 'Nothing delivered yet' },
  successfulAllocations: { value: 0, delta: 'No completed allocations yet' },
  activeOperations: { value: 0, delta: 'No active rescues' },
};

export function getAnalyticsSummary() {
  if (USE_MOCKS) return Promise.resolve(EMPTY_SUMMARY);
  return api.get('/dashboard/overview').then((response) => {
    const overview = response.data;
    return {
      resourcesRescued: overview.resourcesRescued,
      successfulAllocations: overview.successfulAllocations,
      activeOperations: overview.activeRescues,
    };
  });
}

export function getResourcesRescuedOverTime() {
  if (USE_MOCKS) return Promise.resolve([]);
  return api
    .get('/analytics/trends', { params: { days: TREND_DAYS } })
    .then((response) =>
      response.data.daily.map((point) => ({
        label: dayLabel(point.day),
        quantity: point.quantity_delivered,
      })),
    );
}

export function getFoodVsMedical() {
  if (USE_MOCKS) return Promise.resolve([]);
  return api.get('/analytics/resource-types').then((response) =>
    response.data.by_resource_type.map((stats) => ({
      name: stats.resource_type === 'FOOD' ? 'Food' : 'Medical',
      value: stats.quantity_rescued,
      key: stats.resource_type.toLowerCase(),
    })),
  );
}

// ---------------------------------------------------------------------------
// Weekly / outcome charts — one request feeds all of them
// ---------------------------------------------------------------------------

const EMPTY_INSIGHTS = {
  windowWeeks: INSIGHT_WEEKS,
  supplyVsDemand: [],
  allocations: [],
  matchingTime: [],
  avgMatchingMinutes: null,
  matchingSamples: 0,
  deadlinePerformance: [],
  noDeadline: 0,
  operationCompletion: [],
  atRiskVsCompleted: [],
};

function adaptInsights(data) {
  return {
    windowWeeks: data.window_weeks,
    supplyVsDemand: data.supply_vs_demand.map((week) => ({
      label: dayLabel(week.week_start),
      supply: week.supply,
      demand: week.demand,
    })),
    allocations: data.allocations.map((week) => ({
      label: dayLabel(week.week_start),
      successful: week.successful,
      unsuccessful: week.unsuccessful,
    })),
    // `minutes` stays null for weeks with no matches so the line shows a gap, not a fake zero.
    matchingTime: data.matching_time.map((week) => ({
      label: dayLabel(week.week_start),
      minutes: week.avg_minutes,
      samples: week.samples,
    })),
    avgMatchingMinutes: data.avg_matching_minutes,
    matchingSamples: data.matching_samples,
    deadlinePerformance: [
      { name: 'Before deadline', value: data.deadline_performance.on_time, key: 'onTime' },
      { name: 'After deadline', value: data.deadline_performance.late, key: 'late' },
    ],
    noDeadline: data.deadline_performance.no_deadline,
    operationCompletion: [
      { name: 'Completed', value: data.operation_completion.completed, key: 'completed' },
      { name: 'In Progress', value: data.operation_completion.in_progress, key: 'inProgress' },
      { name: 'Failed', value: data.operation_completion.failed, key: 'failed' },
    ],
    atRiskVsCompleted: data.operation_outcomes.map((week) => ({
      label: dayLabel(week.week_start),
      completed: week.completed,
      atRisk: week.at_risk,
    })),
  };
}

export function getAnalyticsInsights() {
  if (USE_MOCKS) return Promise.resolve(EMPTY_INSIGHTS);
  return api
    .get('/analytics/insights', { params: { weeks: INSIGHT_WEEKS } })
    .then((response) => adaptInsights(response.data));
}

// ---------------------------------------------------------------------------
// Predictive surplus
// ---------------------------------------------------------------------------

const EMPTY_FORECAST = {
  unit: 'units',
  history: [],
  prediction: null,
  minDaysRequired: 3,
  windowDays: 28,
};

/**
 * Recent daily food surplus plus — only when the recorded history supports
 * one — the hour of day surplus usually appears in. `prediction` is `null`
 * otherwise; the card says "not enough history" rather than showing a guess.
 */
export function getSurplusForecast() {
  if (USE_MOCKS) return Promise.resolve(EMPTY_FORECAST);
  return api
    .get('/analytics/surplus-forecast', { params: { tz_offset_minutes: utcOffsetMinutes() } })
    .then((response) => {
      const data = response.data;
      const p = data.prediction;
      return {
        unit: data.unit,
        history: data.history.map((day) => ({ label: day.label, quantity: day.quantity })),
        prediction: p
          ? {
              low: p.low,
              high: p.high,
              unit: p.unit,
              windowLabel: `${hourLabel(p.start_hour)} – ${hourLabel(p.end_hour)}`,
              daysWithSurplus: p.days_with_surplus,
              windowDays: p.window_days,
            }
          : null,
        minDaysRequired: data.min_days_required,
        windowDays: data.window_days,
      };
    });
}

/**
 * Really notify the rescue partners about the predicted window
 * (POST /analytics/surplus-alert). Resolves with the true counts — which can
 * be 0 when there are no eligible partners — and rejects (with `message`)
 * when the alert cannot be sent.
 */
export function notifyNearbyRescuePartners() {
  if (USE_MOCKS) {
    return Promise.reject({
      message: 'Not connected to the backend, so no one can be notified. Set VITE_USE_MOCKS=false.',
    });
  }
  return api
    .post('/analytics/surplus-alert', { tz_offset_minutes: utcOffsetMinutes() })
    .then((response) => {
      const data = response.data;
      return {
        partnersNotified: data.partners_notified,
        alreadyNotified: data.already_notified,
        eligiblePartners: data.eligible_partners,
        scope: data.scope,
        windowLabel: data.window_label,
      };
    });
}
