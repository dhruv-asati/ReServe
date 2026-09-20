import { api, mockRequest, USE_MOCKS } from './api';

const STORAGE_KEY = 'reserve.mockResources';

/** Read the locally-saved mock resources. Defensive: never throws. */
function readStore() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** Write the locally-saved mock resources. Defensive: never throws. */
function writeStore(records) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  } catch {
    /* storage unavailable — the record still lives in the resolved response */
  }
}

/**
 * Submission for the create-rescue form.
 *
 * Mock by default (`USE_MOCKS`, see services/api.js): resolves with a fake
 * rescue id after a simulated network delay (same `mockRequest` pattern as
 * every other service), no backend and no AI call, then saves the record to
 * localStorage so it's available to the next (mock) stage. `payload` must
 * already be plain, serializable data — CreateRescue.jsx strips uploaded
 * File objects down to {name, size, type} metadata before calling this.
 *
 * The real branch posts the same payload to the backend and returns
 * whatever record it responds with; it does not touch localStorage, since
 * that cache exists only to make the later mock stages work offline.
 */
export function createRescue(payload) {
  if (USE_MOCKS) {
    const id = `RES-${Math.floor(1000 + Math.random() * 9000)}`;
    const record = { id, createdAt: new Date().toISOString(), status: 'draft', ...payload };

    return mockRequest(record, { delay: 900 }).then((result) => {
      writeStore([result, ...readStore()]);
      return result;
    });
  }
  return api.post('/rescues', payload).then((response) => response.data);
}

/** Read back one locally-saved mock resource by id, for later mock stages. */
export function getMockResource(id) {
  return readStore().find((record) => record.id === id) ?? null;
}
