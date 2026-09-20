import { http, tokenStorage } from './api';

/**
 * Authentication against the ReServe backend.
 *
 * Flow (backend routes, all under VITE_API_BASE_URL):
 *   register  POST /auth/register  -> creates the account, returns NO tokens
 *   login     POST /auth/login     -> { access_token, refresh_token, user }
 *   profile   GET/PUT /users/me    -> the only place `organization_name` lives
 *
 * So registering is: register -> login -> save the organization name. Tokens
 * are kept by `tokenStorage` (services/api.js), which also attaches them to
 * every request and refreshes them on a 401. This module only keeps the
 * *display* session (who is signed in) under `reserve.session`.
 *
 * The rest of the UI reads a small session user, never the raw API user:
 *   { id, name, organization?, email, role }
 * where `role` is 'provider' | 'recipient' | 'rescue-partner' | 'admin'.
 */

const SESSION_KEY = 'reserve.session';
// Written by the old localStorage mock, including plain-text passwords.
const LEGACY_MOCK_USERS_KEY = 'reserve.users';

/** Backend role -> frontend role. */
const ROLE_FROM_API = {
  PROVIDER: 'provider',
  RECIPIENT: 'recipient',
  RESCUE_PARTNER: 'rescue-partner',
  ADMIN: 'admin',
};

/** Frontend role -> backend role. ADMIN is deliberately absent: it cannot self-register. */
const ROLE_TO_API = {
  provider: 'PROVIDER',
  recipient: 'RECIPIENT',
  'rescue-partner': 'RESCUE_PARTNER',
};

const FIELD_LABELS = {
  email: 'Email',
  password: 'Password',
  full_name: 'Name',
  role: 'Role',
  organization_name: 'Organization',
};

function readSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeSession(session) {
  try {
    if (session) {
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      window.localStorage.removeItem(SESSION_KEY);
    }
  } catch {
    /* storage unavailable — session stays in memory for this tab */
  }
}

/** Backend user (UserPublic or UserProfileOut) -> the session user the UI reads. */
function toSessionUser(apiUser) {
  return {
    id: apiUser.id,
    name: apiUser.full_name,
    organization: apiUser.organization_name || undefined,
    email: apiUser.email,
    role: ROLE_FROM_API[apiUser.role] ?? String(apiUser.role).toLowerCase(),
  };
}

function persist(sessionUser) {
  writeSession(sessionUser);
  return sessionUser;
}

/**
 * The backend's generic 422 message ("One or more fields failed validation.")
 * doesn't say what to fix; swap in the first field's own message.
 */
function withFormMessage(error) {
  if (error?.code === 'VALIDATION_ERROR' && error.fieldErrors) {
    const [field, message] = Object.entries(error.fieldErrors)[0] ?? [];
    if (field) return { ...error, message: `${FIELD_LABELS[field] ?? field}: ${message}` };
  }
  return error;
}

/**
 * Read the persisted session, if any. Used to hydrate auth state on load.
 *
 * A stored session only counts while its access token is still stored: a
 * session left over from the old localStorage mock has no token, and treating
 * it as signed-in would just make every API call fail with a 401.
 */
export function getStoredSession() {
  try {
    window.localStorage.removeItem(LEGACY_MOCK_USERS_KEY);
  } catch {
    /* storage unavailable */
  }

  const session = readSession();
  if (session && !tokenStorage.getAccessToken()) {
    writeSession(null);
    return null;
  }
  return session;
}

/** Exchange credentials for tokens, then load the full profile for the session. */
async function signIn({ email, password }) {
  const data = await http.post('/auth/login', { email: email.trim(), password });
  tokenStorage.setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });

  // /auth/login's user has no organization_name; /users/me does.
  let apiUser = data.user;
  try {
    apiUser = await http.get('/users/me');
  } catch {
    /* fall back to the login payload's user — the session still works */
  }
  return persist(toSessionUser(apiUser));
}

/** Sign in with email + password. Rejects with `{ message, status, code, ... }`. */
export async function loginUser(credentials) {
  try {
    return await signIn(credentials);
  } catch (error) {
    throw withFormMessage(error);
  }
}

/**
 * Create an account, sign it in, and save the organization name.
 * `role` is the frontend value ('provider' | 'recipient' | 'rescue-partner').
 */
export async function registerUser({ name, organization, email, password, role }) {
  const apiRole = ROLE_TO_API[role];
  if (!apiRole) {
    throw { message: 'Select a valid role.', status: 422, code: 'VALIDATION_ERROR' };
  }

  try {
    await http.post('/auth/register', {
      email: email.trim(),
      password,
      full_name: name.trim(),
      role: apiRole,
    });
  } catch (error) {
    throw withFormMessage(error);
  }

  let session;
  try {
    session = await signIn({ email, password });
  } catch (error) {
    // The account exists now, so retrying "register" would only answer 409.
    throw {
      ...error,
      message: 'Your account was created, but signing in failed. Please sign in from the login page.',
    };
  }

  const organizationName = organization?.trim();
  if (organizationName) {
    try {
      const profile = await http.put('/users/me', { organization_name: organizationName });
      return persist(toSessionUser(profile));
    } catch (error) {
      // Not worth failing a registration that succeeded; it can be set on the profile later.
      console.warn('[auth] Account created, but saving the organization name failed:', error?.message);
    }
  }
  return session;
}

/** Re-read the signed-in user's profile from the backend and refresh the stored session. */
export async function refreshSessionUser() {
  const profile = await http.get('/users/me');
  return persist(toSessionUser(profile));
}

/** Clear tokens and the stored session. (The backend has no logout endpoint.) */
export function logoutUser() {
  tokenStorage.clear();
  writeSession(null);
}
