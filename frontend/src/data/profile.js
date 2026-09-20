import { DAYS, PROFILE_ORG_TYPE } from '@/utils/profile';
import { VERIFICATION } from '@/utils/networkDirectory';
import { RESOURCE_TYPE } from '@/utils/theme';

/**
 * Starter data for the Organization Profile page (`/app/profile`).
 *
 * DEMO DATA ONLY. There is no backend behind this. `buildDefaultProfile`
 * seeds a profile from the signed-in mock account (services/auth.js) the
 * first time that account opens the page; services/profileService.js then
 * keeps any saved edits in localStorage, keyed by the account's email, and
 * returns those instead. Address, hours, capacity and requirements below are
 * invented placeholders for the walkthrough, not real details.
 *
 * Shape of the profile (what pages/Profile.jsx reads and edits):
 *
 *   organizationName  string — from the account's organization
 *   type              PROFILE_ORG_TYPE — provider / ngo / shelter / partner
 *   contactName       string — from the account's name (optional)
 *   email             string — from the account
 *   phone             string — optional; left blank
 *   address           string
 *   serviceArea       string
 *   operatingHours    [{ day, closed, open: 'HH:MM', close: 'HH:MM' }] × 7,
 *                     in utils/profile.js DAYS order
 *   resourceTypes     RESOURCE_TYPE[] — food / medical
 *   capacity          { value, unit } — value may be '' when unspecified
 *   requirements      string — free-text notes for partners
 *   verification      VERIFICATION — a demo label, read-only on the page
 */

/** Register's role (services/auth.js) → the profile's organization type. */
const ROLE_TO_ORG_TYPE = {
  provider: PROFILE_ORG_TYPE.PROVIDER,
  recipient: PROFILE_ORG_TYPE.NGO,
  'rescue-partner': PROFILE_ORG_TYPE.PARTNER,
};

/** Type-specific starting points for capacity, resources and notes. */
const TYPE_DEFAULTS = {
  [PROFILE_ORG_TYPE.PROVIDER]: {
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 200, unit: 'meals / day' },
    requirements:
      'Surplus is packed in sealed, labelled containers. Please bring insulated bags for hot food and collect within the pickup window.',
  },
  [PROFILE_ORG_TYPE.NGO]: {
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 150, unit: 'meals / day' },
    requirements:
      'Limited cold storage on site. Deliveries are easiest to receive between 11:00 AM and 8:00 PM.',
  },
  [PROFILE_ORG_TYPE.SHELTER]: {
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 100, unit: 'meals / day' },
    requirements: 'Prepared meals only. Please call ahead for deliveries after 8:00 PM.',
  },
  [PROFILE_ORG_TYPE.PARTNER]: {
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 40, unit: 'pickups / day' },
    requirements: 'Own vehicle with insulated carriers. Medical items are handled as coordination only.',
  },
};

/** Mon–Fri 9 AM–6 PM, Sat 10 AM–4 PM, Sun closed. Closed rows keep times so un-ticking "Closed" has sane values. */
export function buildDefaultOperatingHours() {
  return DAYS.map(({ key }) => {
    if (key === 'sat') return { day: key, closed: false, open: '10:00', close: '16:00' };
    if (key === 'sun') return { day: key, closed: true, open: '09:00', close: '18:00' };
    return { day: key, closed: false, open: '09:00', close: '18:00' };
  });
}

/**
 * Build the default organization profile for the signed-in account.
 * `user` is the session object from useAuth(): { name, organization, email, role }.
 * Safe to call with `null`/`undefined` — falls back to a generic demo profile.
 */
export function buildDefaultProfile(user) {
  const type = ROLE_TO_ORG_TYPE[user?.role] ?? PROFILE_ORG_TYPE.PROVIDER;
  const defaults = TYPE_DEFAULTS[type];

  return {
    organizationName: user?.organization?.trim() || 'Demo Organization',
    type,
    contactName: user?.name?.trim() ?? '',
    email: user?.email ?? '',
    phone: '',
    address: '12 Sample Road, Indiranagar, Bengaluru, Karnataka',
    serviceArea: 'Indiranagar, Koramangala and nearby areas, Bengaluru',
    operatingHours: buildDefaultOperatingHours(),
    resourceTypes: [...defaults.resourceTypes],
    capacity: { ...defaults.capacity },
    requirements: defaults.requirements,
    verification: VERIFICATION.PENDING,
  };
}
