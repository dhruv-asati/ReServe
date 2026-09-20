import axios from 'axios';

/**
 * Centralized API client for the ReServe backend (FastAPI, every route lives
 * under `/api`). All service modules import from here — nothing else in the
 * app should create its own axios instance or call `fetch` directly.
 *
 * Configuration
 *   VITE_API_BASE_URL  Base URL INCLUDING the `/api` prefix, e.g.
 *                      http://localhost:8000/api  (see frontend/.env.example).
 *                      Service paths are therefore written WITHOUT `/api`:
 *                      `api.get('/resources')` -> GET {base}/resources.
 *   VITE_USE_MOCKS     Unless set to the string 'false', services keep
 *                      resolving mock data (see `USE_MOCKS` below).
 *
 * Backend response contract (app/schemas/common.py, app/main.py)
 *   success  { "success": true,  "data": <payload>, "message": "..." }
 *   error    { "success": false, "error": { "code", "message", "details"? } }
 *
 * What this module does with it
 *   - Success: the interceptor unwraps the envelope, so `response.data` is the
 *     payload itself (`response.message` / `response.envelope` keep the rest).
 *     Existing `api.get(...).then((r) => r.data)` code therefore receives the
 *     payload, not the envelope.
 *   - Failure: every rejection is a plain object
 *       { message, status, code, details, fieldErrors, isNetworkError }
 *     (`message`, `status` and `details` are the shape callers already used).
 *   - Auth: attaches `Authorization: Bearer <access token>` when a token is
 *     stored, and on a 401 transparently exchanges the refresh token
 *     (POST /auth/refresh) once and retries the request.
 */

// ---------------------------------------------------------------------------
// Base URL
// ---------------------------------------------------------------------------

const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim();

/** Normalised base URL (no trailing slash). Falls back to same-origin `/api`. */
export const API_BASE_URL = (configuredBaseUrl || '/api').replace(/\/+$/, '');

if (import.meta.env.DEV && !configuredBaseUrl) {
  console.warn(
    '[api] VITE_API_BASE_URL is not set, so requests go to the frontend dev ' +
      "server's own /api. Copy frontend/.env.example to frontend/.env and restart Vite.",
  );
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

// Same access-token key the previous client already read.
const ACCESS_TOKEN_KEY = 'reserve.token';
const REFRESH_TOKEN_KEY = 'reserve.refreshToken';

function readKey(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeKey(key, value) {
  try {
    if (value) window.localStorage.setItem(key, value);
    else window.localStorage.removeItem(key);
  } catch {
    /* storage unavailable — tokens live only for this request cycle */
  }
}

/**
 * JWT storage for the backend's login/refresh flow. services/auth.js writes
 * these on login; with no stored access token the 401 handling below stays
 * out of the way and a 401 is just an error for the caller.
 */
export const tokenStorage = {
  getAccessToken: () => readKey(ACCESS_TOKEN_KEY),
  getRefreshToken: () => readKey(REFRESH_TOKEN_KEY),
  setTokens({ accessToken, refreshToken }) {
    if (accessToken !== undefined) writeKey(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken !== undefined) writeKey(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear() {
    writeKey(ACCESS_TOKEN_KEY, null);
    writeKey(REFRESH_TOKEN_KEY, null);
  },
};

let authFailureHandler = null;

/**
 * Register a callback fired when the session can no longer be recovered (no
 * refresh token, or the refresh was rejected). AuthContext should use this to
 * sign the user out. Returns an unsubscribe function.
 */
export function setAuthFailureHandler(handler) {
  authFailureHandler = handler;
  return () => {
    if (authFailureHandler === handler) authFailureHandler = null;
  };
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

/** Default timeout. AI-backed calls (resource analysis) should pass AI_REQUEST_TIMEOUT_MS. */
export const DEFAULT_TIMEOUT_MS = 60000;

/**
 * The backend gives Gemini 20s (GEMINI_TIMEOUT_SECONDS) before answering 504,
 * which is longer than DEFAULT_TIMEOUT_MS — pass `{ timeout: AI_REQUEST_TIMEOUT_MS }`
 * on `POST /resources/{id}/analyze` so the client doesn't give up first.
 */
export const AI_REQUEST_TIMEOUT_MS = 60000;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Success: unwrap { success, data, message }
// ---------------------------------------------------------------------------

function isEnvelope(body) {
  return (
    body !== null &&
    typeof body === 'object' &&
    typeof body.success === 'boolean' &&
    ('data' in body || 'message' in body || 'error' in body)
  );
}

// ---------------------------------------------------------------------------
// Failure: normalise to { message, status, code, details, fieldErrors, isNetworkError }
// ---------------------------------------------------------------------------

/**
 * FastAPI/Pydantic validation details -> { fieldName: message }.
 * `loc` looks like ['body', 'email'] or ['query', 'limit']; the leading
 * location segment is dropped so keys match request field names.
 */
function toFieldErrors(details) {
  if (!Array.isArray(details)) return {};
  const fieldErrors = {};
  for (const item of details) {
    if (!item || !Array.isArray(item.loc)) continue;
    const key = item.loc.slice(1).join('.');
    if (key && !(key in fieldErrors)) fieldErrors[key] = item.msg;
  }
  return fieldErrors;
}

function normalizeError(error) {
  const status = error.response?.status ?? 0;
  const body = error.response?.data ?? null;
  const backendError = body && typeof body === 'object' ? body.error : null;

  let message;
  let code = null;
  let details = body;

  if (backendError && typeof backendError === 'object') {
    // { success: false, error: { code, message, details? } }
    message = backendError.message;
    code = backendError.code ?? null;
    details = backendError.details ?? body;
  } else if (body && typeof body === 'object') {
    // Anything not wrapped by the backend's handlers (e.g. a proxy or FastAPI default).
    if (typeof body.detail === 'string') message = body.detail;
    else if (typeof body.message === 'string') message = body.message;
    if (Array.isArray(body.detail)) details = body.detail;
  }

  const isNetworkError = !error.response;
  if (isNetworkError) {
    if (axios.isCancel(error)) {
      code = 'CANCELLED';
      message = 'The request was cancelled.';
    } else if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      code = 'TIMEOUT';
      message = 'The request timed out. Please try again.';
    } else {
      code = 'NETWORK_ERROR';
      message =
        `Could not reach the ReServe server at ${API_BASE_URL}. ` +
        'Check that the backend is running, that CORS allows this origin, and its logs for errors.';
    }
  }

  return {
    message: message ?? error.message ?? 'Something went wrong.',
    status,
    code,
    details,
    fieldErrors: toFieldErrors(details),
    isNetworkError,
  };
}

// ---------------------------------------------------------------------------
// 401 handling: one refresh attempt, shared by every request that fails at once
// ---------------------------------------------------------------------------

// Auth endpoints never trigger a refresh: a 401 from /auth/login means "wrong
// password", and /auth/refresh failing means the session is really over.
const NO_REFRESH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'];

let refreshPromise = null;

function refreshSession() {
  if (!refreshPromise) {
    const refreshToken = tokenStorage.getRefreshToken();
    // A bare axios call: this must not pass through the interceptors below.
    refreshPromise = axios
      .post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken }, {
        timeout: DEFAULT_TIMEOUT_MS,
      })
      .then((response) => {
        const tokens = response.data?.data;
        if (!tokens?.access_token) throw new Error('Refresh response had no access token.');
        tokenStorage.setTokens({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        });
        return tokens.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function endSession() {
  tokenStorage.clear();
  if (authFailureHandler) authFailureHandler();
}

api.interceptors.response.use(
  (response) => {
    if (isEnvelope(response.data)) {
      response.envelope = response.data;
      response.message = response.data.message ?? '';
      response.data = response.data.data ?? null;
    }
    return response;
  },
  async (error) => {
    const original = error.config;
    const isAuthEndpoint = NO_REFRESH_PATHS.some((path) => original?.url?.startsWith(path));

    // Only recover sessions that exist: with no stored access token (mock auth,
    // or logged out) a 401 is just a normal error for the caller to handle.
    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isAuthEndpoint &&
      tokenStorage.getAccessToken()
    ) {
      original._retried = true;

      // Another request already refreshed while this one was in flight: it was
      // sent with the old token, so just retry it with the current one.
      const currentToken = tokenStorage.getAccessToken();
      if (original.headers?.Authorization !== `Bearer ${currentToken}`) {
        original.headers.Authorization = `Bearer ${currentToken}`;
        return api(original);
      }

      if (!tokenStorage.getRefreshToken()) {
        endSession();
        return Promise.reject(normalizeError(error));
      }

      try {
        const accessToken = await refreshSession();
        original.headers.Authorization = `Bearer ${accessToken}`;
        return api(original);
      } catch {
        endSession();
        return Promise.reject(normalizeError(error));
      }
    }

    return Promise.reject(normalizeError(error));
  },
);

// ---------------------------------------------------------------------------
// Convenience helpers: resolve straight to the unwrapped payload
// ---------------------------------------------------------------------------

/**
 * Thin wrappers for service modules: `http.get('/resources', { params })`
 * resolves to the payload (e.g. `{ items, total, skip, limit }`), not the axios
 * response. Paths are relative to API_BASE_URL and omit `/api`.
 */
export const http = {
  get: (url, config) => api.get(url, config).then((response) => response.data),
  post: (url, body, config) => api.post(url, body, config).then((response) => response.data),
  put: (url, body, config) => api.put(url, body, config).then((response) => response.data),
  patch: (url, body, config) => api.patch(url, body, config).then((response) => response.data),
  delete: (url, config) => api.delete(url, config).then((response) => response.data),
};

/**
 * GET /api/health (public). Never throws: resolves `{ ok, ...payload }` or
 * `{ ok: false, error }`. `ok` requires the API to be up AND connected to its
 * database (`database_connected`).
 */
export async function checkApiConnection() {
  try {
    const health = await http.get('/health', { timeout: 5000 });
    return { ok: Boolean(health?.database_connected), ...health };
  } catch (error) {
    return { ok: false, error };
  }
}

// ---------------------------------------------------------------------------
// Mock switch (unchanged behaviour)
// ---------------------------------------------------------------------------

/**
 * Toggle for service modules: while true they resolve mock data instead of
 * calling the network. Flip via VITE_USE_MOCKS=false once the backend is live.
 */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';

/**
 * Resolve a value the way a real request would: asynchronously, after a short
 * delay. Using this everywhere means loading and error states are exercised
 * from day one, and swapping in a real call is a one-line change.
 */
export function mockRequest(data, { delay = 450, shouldFail = false } = {}) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (shouldFail) {
        reject({ message: 'Mock request failed.', status: 500, details: null });
        return;
      }
      resolve(structuredClone(data));
    }, delay);
  });
}

export default api;
