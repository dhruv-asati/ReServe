import { api } from './api';
import { operationCode, toOperationDetail, toOperationRow } from './operationAdapter';

/**
 * Live data for the Operations page (`/app/operations`) when
 * `VITE_USE_MOCKS=false`.
 *
 * The backend has no single "operation with its resource" endpoint, so this
 * builds each row from two real calls:
 *
 *   GET /operations?limit=50   the operations (status, partner, allocations,
 *                              events, route legs, last reported position)
 *   GET /resources/{id}        the resource each operation carries (title,
 *                              quantity, unit, provider, location, deadline)
 *
 * There is no `GET /operations/{id}`, so the details view is derived from the
 * same snapshot the list was built from — selecting a row costs no request.
 * A resource that can't be loaded degrades to a placeholder row instead of
 * failing the whole list.
 */

const LIST_LIMIT = 50;

/** operationCode -> { code, op, resource } for the most recent list fetch. */
let snapshotPromise = null;

/** ResourceOut by id — resources rarely change mid-session, so each is fetched once. */
const resourceCache = new Map();

async function loadResources(ids) {
  const missing = ids.filter((id) => !resourceCache.has(id));
  const results = await Promise.allSettled(
    missing.map((id) => api.get(`/resources/${encodeURIComponent(id)}`).then((response) => response.data)),
  );
  results.forEach((result, index) => {
    if (result.status === 'fulfilled' && result.value) resourceCache.set(missing[index], result.value);
  });
}

async function fetchSnapshot() {
  const page = await api.get('/operations', { params: { limit: LIST_LIMIT } }).then((response) => response.data);
  const items = Array.isArray(page?.items) ? page.items : Array.isArray(page) ? page : [];

  await loadResources([...new Set(items.map((op) => op.resource_id))]);

  const snapshot = new Map();
  for (const op of items) {
    // Eight hex characters of a random UUID are effectively unique; lengthen the
    // code on the off chance two operations in the list share one.
    let length = 8;
    let code = operationCode(op.id, length);
    while (snapshot.has(code) && length < 32) {
      length += 1;
      code = operationCode(op.id, length);
    }
    snapshot.set(code, { code, op, resource: resourceCache.get(op.resource_id) ?? null });
  }
  return snapshot;
}

function loadSnapshot({ force = false } = {}) {
  if (force || !snapshotPromise) {
    snapshotPromise = fetchSnapshot().catch((error) => {
      snapshotPromise = null; // let the next call retry instead of caching the failure
      throw error;
    });
  }
  return snapshotPromise;
}

/** Every operation as a list row. Always fetches fresh; always resolves an array. */
export async function getLiveOperations() {
  const snapshot = await loadSnapshot({ force: true });
  return [...snapshot.values()].map(({ code, op, resource }) => toOperationRow(op, resource, { code }));
}

/** The details payload for one operation code, or null when it isn't in the list. */
export async function getLiveOperationDetail(code) {
  const snapshot = await loadSnapshot();
  const entry = snapshot.get(code);
  return entry ? toOperationDetail(entry.op, entry.resource, { code: entry.code }) : null;
}
