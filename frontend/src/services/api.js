import axios from 'axios';

/**
 * Shared Axios instance for the ReServe backend.
 *
 * The backend is built separately; until it exists, service modules return
 * mock data and this client stays unused. The base URL always comes from the
 * environment — never hardcode it, and never put API keys in the frontend.
 */
const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/** Attach the session token, when auth lands in a later section. */
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('reserve.token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/** Normalise errors so callers always see { message, status, details }. */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = {
      message:
        error.response?.data?.detail ??
        error.response?.data?.message ??
        error.message ??
        'Something went wrong.',
      status: error.response?.status ?? 0,
      details: error.response?.data ?? null,
    };
    return Promise.reject(normalized);
  },
);

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
