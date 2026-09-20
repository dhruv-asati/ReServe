import { mockRequest } from './api';
import {
  ANALYTICS_SUMMARY,
  RESOURCES_RESCUED_OVER_TIME,
  FOOD_VS_MEDICAL,
  SUCCESSFUL_ALLOCATIONS,
  AVG_MATCHING_TIME,
  SUPPLY_VS_DEMAND,
  DEADLINE_PERFORMANCE,
  OPERATION_COMPLETION,
  AT_RISK_VS_COMPLETED,
  SURPLUS_PREDICTION_HISTORY,
  SURPLUS_PREDICTION,
} from '@/data/analytics';

/**
 * Analytics data access.
 *
 * All data here is mock/illustrative (see src/data/analytics.js) and resolves
 * through the same simulated-latency path as every other service, so the
 * Analytics page exercises its loading states now and needs no changes when
 * a real reporting endpoint replaces these calls.
 */
export function getAnalyticsSummary() {
  return mockRequest(ANALYTICS_SUMMARY, { delay: 450 });
}

export function getResourcesRescuedOverTime() {
  return mockRequest(RESOURCES_RESCUED_OVER_TIME, { delay: 550 });
}

export function getFoodVsMedical() {
  return mockRequest(FOOD_VS_MEDICAL, { delay: 500 });
}

export function getSuccessfulAllocations() {
  return mockRequest(SUCCESSFUL_ALLOCATIONS, { delay: 500 });
}

export function getAvgMatchingTime() {
  return mockRequest(AVG_MATCHING_TIME, { delay: 500 });
}

export function getSupplyVsDemand() {
  return mockRequest(SUPPLY_VS_DEMAND, { delay: 500 });
}

export function getDeadlinePerformance() {
  return mockRequest(DEADLINE_PERFORMANCE, { delay: 500 });
}

export function getOperationCompletion() {
  return mockRequest(OPERATION_COMPLETION, { delay: 500 });
}

export function getAtRiskVsCompleted() {
  return mockRequest(AT_RISK_VS_COMPLETED, { delay: 500 });
}

export function getSurplusPredictionHistory() {
  return mockRequest(SURPLUS_PREDICTION_HISTORY, { delay: 500 });
}

export function getSurplusPrediction() {
  return mockRequest(SURPLUS_PREDICTION, { delay: 500 });
}

/**
 * Simulate notifying nearby rescue partners about the predicted surplus
 * window. This is a frontend-only demo action for the Predictive Surplus
 * section: it never calls the network or sends a real message to anyone —
 * it just resolves, after a short delay, with a mock confirmation payload
 * for the UI to show.
 */
export function notifyNearbyRescuePartners() {
  return mockRequest(
    {
      demo: true,
      partnersNotified: 6,
      message: 'Demo notification sent to nearby rescue partners.',
    },
    { delay: 900 },
  );
}
