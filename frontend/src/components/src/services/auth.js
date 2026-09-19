import { mockRequest } from './api';

/**
 * Mock authentication store.
 *
 * There is no backend yet, so "accounts" live in localStorage under
 * `reserve.users` (never read directly by UI code) and the active session
 * lives under `reserve.session`. Passwords are kept only to compare against
 * on a later mock login — this is a frontend stand-in, not real auth, and
 * must be replaced before anything here touches production data.
 */

const USERS_KEY = 'reserve.users';
const SESSION_KEY = 'reserve.session';

function readUsers() {
  try {
    const raw = window.localStorage.getItem(USERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeUsers(users) {
  try {
    window.localStorage.setItem(USERS_KEY, JSON.stringify(users));
  } catch {
    /* storage unavailable — registration still resolves for this session */
  }
}

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

/** Strip the mock password before anything touches state or storage-facing UI. */
function toSessionUser(user) {
  const { password: _password, ...sessionUser } = user;
  return sessionUser;
}

/** Read the persisted session, if any. Used to hydrate auth state on load. */
export function getStoredSession() {
  return readSession();
}

/** Register a mock account, sign it in, and persist both. */
export async function registerMockUser({ name, organization, email, password, role }) {
  const normalizedEmail = email.trim().toLowerCase();
  const users = readUsers();

  if (users.some((existing) => existing.email === normalizedEmail)) {
    await mockRequest(null, { delay: 400 });
    throw { message: 'An account with this email already exists.', status: 409 };
  }

  await mockRequest(null, { delay: 700 });

  const user = {
    name: name.trim(),
    organization: organization.trim(),
    email: normalizedEmail,
    password,
    role,
  };

  writeUsers([...users, user]);

  const sessionUser = toSessionUser(user);
  writeSession(sessionUser);
  return sessionUser;
}

/** Validate mock credentials against registered accounts and start a session. */
export async function loginMockUser({ email, password }) {
  const normalizedEmail = email.trim().toLowerCase();

  await mockRequest(null, { delay: 600 });

  const users = readUsers();
  const user = users.find((existing) => existing.email === normalizedEmail);

  if (!user || user.password !== password) {
    throw { message: 'Incorrect email or password.', status: 401 };
  }

  const sessionUser = toSessionUser(user);
  writeSession(sessionUser);
  return sessionUser;
}

/** Clear the active session. Accounts themselves stay in storage. */
export function logoutMockUser() {
  writeSession(null);
}
