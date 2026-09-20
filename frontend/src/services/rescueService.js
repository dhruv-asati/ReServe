import { api, mockRequest, USE_MOCKS, AI_REQUEST_TIMEOUT_MS } from './api';
import { CATEGORY_OPTIONS } from '@/data/rescueForm';
import { RESOURCE_TYPE } from '@/utils/theme';

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
  return api
    .post('/resources', toResourceCreate(payload))
    .then((response) => response.data)
    .catch((error) => {
      throw friendlyCreateError(error);
    });
}

// ---------------------------------------------------------------------------
// Live mode: Create Rescue form -> POST /api/resources (ResourceCreate)
// ---------------------------------------------------------------------------

/** Form category value -> backend FoodCategory enum. */
const FOOD_CATEGORY = {
  produce: 'RAW_PRODUCE',
  bakery: 'BAKERY',
  dairy: 'DAIRY',
  prepared: 'COOKED_MEALS',
  canned: 'CANNED_GOODS',
  beverages: 'BEVERAGES',
  other: 'OTHER',
};

/** "How soon is it ready?" option -> minutes from now until it is available. */
const READY_IN_MINUTES = { ready_now: 0, within_30m: 30, within_1h: 60, within_2h: 120, within_4h: 240 };

/** Urgency from how soon the deadline is — the same tiers the old mock analysis used. */
function urgencyFor(deadline) {
  const hours = (deadline.getTime() - Date.now()) / 3_600_000;
  if (hours <= 2) return 'CRITICAL';
  if (hours <= 6) return 'HIGH';
  if (hours <= 24) return 'MEDIUM';
  return 'LOW';
}

function toResourceCreate(form) {
  const isFood = form.resourceType === RESOURCE_TYPE.FOOD;
  const categoryLabel =
    CATEGORY_OPTIONS[form.resourceType]?.find((option) => option.value === form.category)?.label ??
    form.category;

  // Food: the deadline is a datetime-local value. Medical: expiry is a date,
  // so the resource is usable through the end of that day.
  const deadline = isFood ? new Date(form.pickupDeadline) : new Date(`${form.expiry}T23:59:00`);

  const description =
    [
      form.description?.trim(),
      !isFood && form.batchReference?.trim() ? `Batch / reference: ${form.batchReference.trim()}` : '',
    ]
      .filter(Boolean)
      .join('\n\n') || undefined;

  const body = {
    title: isFood ? categoryLabel : form.resourceName.trim(),
    description,
    resource_type: isFood ? 'FOOD' : 'MEDICAL',
    category: categoryLabel,
    quantity: Number(form.quantity),
    unit: form.unit,
    urgency: urgencyFor(deadline),
    expiry_time: deadline.toISOString(),
    location_address: form.location.trim(),
    is_perishable: true,
  };

  if (isFood) {
    body.available_time = new Date(Date.now() + (READY_IN_MINUTES[form.preparationTime] ?? 0) * 60_000).toISOString();
    body.food_category = FOOD_CATEGORY[form.category] ?? 'OTHER';
  }
  return body;
}

/** Turn the backend's validation payload into one readable sentence. */
function friendlyCreateError(error) {
  if (error?.status === 422 && Array.isArray(error.details) && error.details.length > 0) {
    const message = error.details
      .map((item) => String(item?.msg ?? '').replace(/^Value error, /, ''))
      .filter(Boolean)
      .join(' ');
    if (message) return { ...error, message };
  }
  return error;
}

// ---------------------------------------------------------------------------
// Live mode: read + analyze a resource
// ---------------------------------------------------------------------------

/** GET /api/resources/{id}, resolved to the backend's ResourceOut. */
export function getRescue(id) {
  return api.get(`/resources/${encodeURIComponent(id)}`).then((response) => response.data);
}

/**
 * POST /api/resources/{id}/analyze — Gemini reads the resource and the result
 * is stored in `ai_analysis`. Slow (the backend allows Gemini 20s), so it
 * gets the longer AI timeout. Resolves to the updated ResourceOut.
 */
export function analyzeRescue(id) {
  return api
    .post(`/resources/${encodeURIComponent(id)}/analyze`, null, { timeout: AI_REQUEST_TIMEOUT_MS })
    .then((response) => response.data);
}

/** Read back one locally-saved mock resource by id, for later mock stages. */
export function getMockResource(id) {
  return readStore().find((record) => record.id === id) ?? null;
}
