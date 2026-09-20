import { mockRequest } from './api';

/**
 * Mock organization-profile store.
 *
 * There is no backend for this yet, so each account's profile lives in
 * localStorage, keyed by email — same pattern as the mock session store in
 * services/auth.js. This lets the Organization Profile page fully work with
 * the backend OFF: edits saved here survive a refresh, but are not shared
 * across accounts or devices.
 */

const STORAGE_PREFIX = 'reserve.profile.';

function storageKey(email) {
  const normalized = (email ?? 'demo').trim().toLowerCase();
  return `${STORAGE_PREFIX}${normalized}`;
}

function readStoredProfile(email) {
  try {
    const raw = window.localStorage.getItem(storageKey(email));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeStoredProfile(email, profile) {
  try {
    window.localStorage.setItem(storageKey(email), JSON.stringify(profile));
  } catch {
    /* storage unavailable — edits stay in memory for this tab */
  }
}

/**
 * Fetch the organization profile for `email`. Falls back to `seed` (built by
 * data/profile.js's buildDefaultProfile from the signed-in account) the
 * first time this account is opened, before anything has been saved.
 *
 * Called from pages/Profile.jsx as:
 *   getOrganizationProfile(user?.email, buildDefaultProfile(user))
 *
 * Resolves (mockRequest, ~450ms) with the profile object — the same shape
 * buildDefaultProfile returns: organizationName, type, contactName, email,
 * phone, address, serviceArea, operatingHours, resourceTypes, capacity,
 * requirements, verification.
 */
export function getOrganizationProfile(email, seed) {
  const stored = readStoredProfile(email);
  return mockRequest(stored ?? seed, { delay: 450 });
}

/**
 * Persist an edited profile for `email` and resolve with what was saved.
 *
 * Called from pages/Profile.jsx on submit (after validateProfile(draft)
 * passes) as:
 *   updateOrganizationProfile(user?.email, draft)
 */
export function updateOrganizationProfile(email, profile) {
  return mockRequest(profile, { delay: 650 }).then((saved) => {
    writeStoredProfile(email, saved);
    return saved;
  });
}
