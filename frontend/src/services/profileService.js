import { http } from './api';

/**
 * Organization Profile (`/app/profile`) service.
 *
 * The backend's User model (see backend `app/models/user.py`,
 * `app/schemas/user.py`, `GET/PUT /api/users/me`) only stores:
 *   full_name, phone, organization_name, organization_description,
 *   profile_image_url, address, latitude, longitude
 *
 * It has no columns for organization `type`, `serviceArea`,
 * `operatingHours`, `resourceTypes`, `capacity` or `verification` — those
 * fields exist only in this frontend's profile UI. Rather than invent
 * backend fields for them (or silently drop them), the fields the backend
 * *does* support round-trip through the real API; the rest continue to be
 * kept in localStorage, per account, exactly as before.
 */

const EXT_STORAGE_PREFIX = 'reserve.profile.ext.';

function extStorageKey(email) {
  const normalized = (email ?? 'demo').trim().toLowerCase();
  return `${EXT_STORAGE_PREFIX}${normalized}`;
}

function readExt(email) {
  try {
    const raw = window.localStorage.getItem(extStorageKey(email));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeExt(email, ext) {
  try {
    window.localStorage.setItem(extStorageKey(email), JSON.stringify(ext));
  } catch {
    /* storage unavailable — these fields stay in memory for this tab */
  }
}

/** Fields with no backend column — held in localStorage only. */
const EXT_FIELDS = ['type', 'serviceArea', 'operatingHours', 'resourceTypes', 'capacity', 'verification'];

function pickExt(profile) {
  const ext = {};
  for (const key of EXT_FIELDS) ext[key] = profile[key];
  return ext;
}

/** Backend UserProfileOut -> the profile shape pages/Profile.jsx reads, merged with local extension fields. */
function toProfile(apiUser, ext, seed) {
  return {
    organizationName: apiUser.organization_name?.trim() || seed.organizationName,
    contactName: apiUser.full_name ?? seed.contactName,
    email: apiUser.email ?? seed.email,
    phone: apiUser.phone ?? seed.phone,
    address: apiUser.address ?? seed.address,
    requirements: apiUser.organization_description ?? seed.requirements,
    // No backend column for these yet — fall back to what was last saved locally, then the seed.
    type: ext?.type ?? seed.type,
    serviceArea: ext?.serviceArea ?? seed.serviceArea,
    operatingHours: ext?.operatingHours ?? seed.operatingHours,
    resourceTypes: ext?.resourceTypes ?? seed.resourceTypes,
    capacity: ext?.capacity ?? seed.capacity,
    verification: ext?.verification ?? seed.verification,
  };
}

/**
 * Fetch the organization profile for the signed-in account: real fields
 * from `GET /api/users/me`, merged with locally-held extension fields.
 * `seed` (from `data/profile.js`'s `buildDefaultProfile`) fills in anything
 * neither source has yet.
 */
export async function getOrganizationProfile(email, seed) {
  const apiUser = await http.get('/users/me');
  const ext = readExt(email);
  return toProfile(apiUser, ext, seed);
}

/**
 * Persist an edited profile: the backend-supported fields are saved via
 * `PUT /api/users/me`; the rest are saved to localStorage as before.
 * Resolves with the merged profile that was saved.
 */
export async function updateOrganizationProfile(email, profile) {
  const apiUser = await http.put('/users/me', {
    full_name: profile.contactName?.trim() || undefined,
    organization_name: profile.organizationName?.trim() || undefined,
    organization_description: profile.requirements ?? undefined,
    phone: profile.phone?.trim() || undefined,
    address: profile.address?.trim() || undefined,
  });

  const ext = pickExt(profile);
  writeExt(email, ext);

  return toProfile(apiUser, ext, profile);
}
