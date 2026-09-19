import { RESOURCE_META, RESOURCE_TYPE, STATUS, STATUS_META } from '@/utils/theme';

/**
 * Filtering rules for the Operations list (`/app/operations`).
 *
 * Pure functions and constants only — no React, no network — so the page and
 * the filter bar share one definition of what each filter means, and the same
 * rules keep working when the operations come from a real endpoint later.
 *
 * A row is shown only if it passes every active condition (AND):
 *
 *   quick filter   All · Active · Completed · At Risk · Reallocating
 *   status         one exact operation status
 *   resource type  Food · Medical
 *   search text    every word must appear in the ID, resource, provider,
 *                  recipient or rescue partner
 *
 * "All" / empty search means the condition is not applied.
 */

export const ALL = 'all';

export const DEFAULT_FILTERS = Object.freeze({
  query: '',
  quick: ALL,
  status: ALL,
  resourceType: ALL,
});

/* ------------------------------------------------------------------ */
/* Quick filters                                                       */
/* ------------------------------------------------------------------ */

/** Statuses of an operation that is still in flight (not yet finished). */
const IN_FLIGHT = new Set([
  STATUS.CREATED,
  STATUS.MATCHING,
  STATUS.MATCHED,
  STATUS.PARTNER_ASSIGNED,
  STATUS.PICKUP_IN_PROGRESS,
  STATUS.IN_TRANSIT,
  STATUS.REALLOCATING,
]);

/** Still moving through the rescue lifecycle: everything except delivered, cancelled and expired. */
export function isActive(operation) {
  return IN_FLIGHT.has(operation.status);
}

/** Delivered. Cancelled and expired operations ended without a delivery, so they are not "completed". */
export function isCompleted(operation) {
  return operation.status === STATUS.DELIVERED;
}

/** Reallocating: the earlier match fell through and a new recipient is being found. */
export function isReallocating(operation) {
  return operation.status === STATUS.REALLOCATING;
}

/**
 * At risk of missing its rescue deadline: an in-flight operation that the
 * data flags with `atRisk`, or any operation that is reallocating (it has lost
 * its recipient, so its deadline is under pressure by definition). Finished
 * operations are never at risk.
 */
export function isAtRisk(operation) {
  return isActive(operation) && (operation.atRisk === true || isReallocating(operation));
}

/** In display order. `test` decides whether an operation belongs to the group. */
export const QUICK_FILTERS = [
  { key: ALL, label: 'All', test: () => true },
  { key: 'active', label: 'Active', test: isActive },
  { key: 'completed', label: 'Completed', test: isCompleted },
  { key: 'at_risk', label: 'At Risk', test: isAtRisk },
  { key: 'reallocating', label: 'Reallocating', test: isReallocating },
];

const QUICK_TESTS = Object.fromEntries(QUICK_FILTERS.map(({ key, test }) => [key, test]));

/** How many operations each quick filter would show, e.g. `{ all: 10, active: 7, … }`. */
export function countQuickFilters(operations) {
  return Object.fromEntries(
    QUICK_FILTERS.map(({ key, test }) => [key, operations.filter(test).length]),
  );
}

/* ------------------------------------------------------------------ */
/* Dropdown options                                                    */
/* ------------------------------------------------------------------ */

/** Every status an operation can have, in lifecycle order. */
const OPERATION_STATUSES = [
  STATUS.CREATED,
  STATUS.MATCHING,
  STATUS.MATCHED,
  STATUS.PARTNER_ASSIGNED,
  STATUS.PICKUP_IN_PROGRESS,
  STATUS.IN_TRANSIT,
  STATUS.DELIVERED,
  STATUS.REALLOCATING,
  STATUS.CANCELLED,
  STATUS.EXPIRED,
];

export const STATUS_OPTIONS = [
  { value: ALL, label: 'All' },
  ...OPERATION_STATUSES.map((status) => ({ value: status, label: STATUS_META[status].label })),
];

export const RESOURCE_TYPE_OPTIONS = [
  { value: ALL, label: 'All' },
  { value: RESOURCE_TYPE.FOOD, label: RESOURCE_META[RESOURCE_TYPE.FOOD].label },
  { value: RESOURCE_TYPE.MEDICAL, label: RESOURCE_META[RESOURCE_TYPE.MEDICAL].label },
];

/* ------------------------------------------------------------------ */
/* Search                                                              */
/* ------------------------------------------------------------------ */

/** Fields the search box looks through. */
const SEARCH_FIELDS = ['id', 'resource', 'provider', 'recipient', 'partner'];

/** Lower-case, drop apostrophes ("St. Mary's" ~ "st marys"), collapse whitespace. */
function normalize(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** The search text as a list of lower-case words (empty when there is nothing to search for). */
function searchTerms(query) {
  const text = normalize(query);
  return text ? text.split(' ') : [];
}

function matchesSearch(operation, terms) {
  if (terms.length === 0) return true;
  const haystack = SEARCH_FIELDS.map((field) => normalize(operation[field])).join(' ');
  return terms.every((term) => haystack.includes(term));
}

/* ------------------------------------------------------------------ */
/* Putting it together                                                 */
/* ------------------------------------------------------------------ */

/** True when any filter or search text is set, i.e. "Clear Filters" would change something. */
export function hasActiveFilters({ query, quick, status, resourceType }) {
  return Boolean(query.trim()) || quick !== ALL || status !== ALL || resourceType !== ALL;
}

/** The operations that pass every active condition, in their original order. */
export function filterOperations(operations, { query, quick, status, resourceType }) {
  const terms = searchTerms(query);
  const inQuickFilter = QUICK_TESTS[quick] ?? QUICK_TESTS[ALL];

  return operations.filter(
    (operation) =>
      inQuickFilter(operation) &&
      (status === ALL || operation.status === status) &&
      (resourceType === ALL || operation.resourceType === resourceType) &&
      matchesSearch(operation, terms),
  );
}
