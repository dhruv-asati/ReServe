import { ORG_TYPE, ORG_TYPE_META } from '@/utils/networkDirectory';

/**
 * Shared vocabulary and pure helpers for the Organization Profile page
 * (`/app/profile`, pages/Profile.jsx): the organization-type and weekday
 * lists, form validation, and the read-only operating-hours summary.
 *
 * Nothing here touches storage or the network — data/profile.js seeds the
 * default profile and services/profileService.js persists it.
 */

/* ---------- Organization type ---------- */

/**
 * The Network Directory's categories (utils/networkDirectory.js) describe
 * organizations that receive or move resources. A profile also needs
 * "Provider" (hotels, bakeries, hospitals that supply surplus), which the
 * directory does not list, so it is added here. Rescue hubs are run by the
 * network itself in the demo, so they are not an option an operator can pick.
 *
 * Values for NGO / Shelter / Rescue Partner are the same strings the
 * directory uses, so the two features stay interchangeable.
 */
export const PROFILE_ORG_TYPE = {
  PROVIDER: 'provider',
  NGO: ORG_TYPE.NGO,
  SHELTER: ORG_TYPE.SHELTER,
  PARTNER: ORG_TYPE.PARTNER,
};

/** Singular label for each type — shown in the header badge and read-only view. */
export const ORG_TYPE_LABELS = {
  [PROFILE_ORG_TYPE.PROVIDER]: 'Provider',
  [PROFILE_ORG_TYPE.NGO]: ORG_TYPE_META[ORG_TYPE.NGO].singular,
  [PROFILE_ORG_TYPE.SHELTER]: ORG_TYPE_META[ORG_TYPE.SHELTER].singular,
  [PROFILE_ORG_TYPE.PARTNER]: ORG_TYPE_META[ORG_TYPE.PARTNER].singular,
};

/** `[{ value, label }]` for the Select in edit mode. */
export const ORG_TYPE_OPTIONS = Object.entries(ORG_TYPE_LABELS).map(([value, label]) => ({
  value,
  label,
}));

/* ---------- Weekdays ---------- */

/**
 * Week order used by the operating-hours editor. Each profile row is
 * `{ day: <key>, closed, open: 'HH:MM', close: 'HH:MM' }` (24-hour times, as
 * produced by <input type="time">).
 */
export const DAYS = [
  { key: 'mon', short: 'Mon', label: 'Monday' },
  { key: 'tue', short: 'Tue', label: 'Tuesday' },
  { key: 'wed', short: 'Wed', label: 'Wednesday' },
  { key: 'thu', short: 'Thu', label: 'Thursday' },
  { key: 'fri', short: 'Fri', label: 'Friday' },
  { key: 'sat', short: 'Sat', label: 'Saturday' },
  { key: 'sun', short: 'Sun', label: 'Sunday' },
];

/* ---------- Display helpers ---------- */

/** Up to two initials for the avatar tile: "Hotel XYZ" → "HX", "Bakery" → "BA". */
export function initialsFromName(name) {
  const words = String(name ?? '')
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ''))
    .filter(Boolean);

  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

/** '18:30' → '6:30 PM'. Returns '' for anything that is not a valid HH:MM time. */
function formatTime(value) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(String(value ?? ''));
  if (!match) return '';
  const hours = Number(match[1]);
  if (hours > 23 || Number(match[2]) > 59) return '';
  return `${hours % 12 || 12}:${match[2]} ${hours >= 12 ? 'PM' : 'AM'}`;
}

function describeHours(row) {
  if (row.closed) return 'Closed';
  const open = formatTime(row.open);
  const close = formatTime(row.close);
  return open && close ? `${open} – ${close}` : 'Hours not set';
}

/**
 * Collapse the seven editable rows into the read-only summary lines the page
 * renders: consecutive days with identical hours are merged into one line.
 *
 *   Mon–Fri 9–6, Sat 10–4, Sun closed  →
 *   [{ label: 'Mon – Fri', hours: '9:00 AM – 6:00 PM' },
 *    { label: 'Sat',       hours: '10:00 AM – 4:00 PM' },
 *    { label: 'Sun',       hours: 'Closed' }]
 *
 * Closed days always have `hours === 'Closed'` — the page styles on that.
 */
export function summarizeOperatingHours(operatingHours) {
  if (!Array.isArray(operatingHours)) return [];

  const groups = [];
  for (const row of operatingHours) {
    const short = DAYS.find((day) => day.key === row.day)?.short ?? row.day;
    const hours = describeHours(row);
    const last = groups[groups.length - 1];

    if (last && last.hours === hours) {
      last.end = short;
    } else {
      groups.push({ start: short, end: short, hours });
    }
  }

  return groups.map(({ start, end, hours }) => ({
    label: start === end ? start : `${start} – ${end}`,
    hours,
  }));
}

/* ---------- Validation ---------- */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_CHARS_RE = /^[+()\d\s.-]+$/;

/**
 * Validate an edited profile draft. Returns an object keyed by the field the
 * page renders each message under — `organizationName`, `type`, `email`,
 * `phone`, `address`, `serviceArea`, `operatingHours`, `capacity`,
 * `resourceTypes` — and an empty object when everything is valid.
 */
export function validateProfile(profile) {
  const errors = {};
  if (!profile) return errors;

  if (!String(profile.organizationName ?? '').trim()) {
    errors.organizationName = 'Organization name is required.';
  }

  if (!profile.type) {
    errors.type = 'Select an organization type.';
  } else if (!ORG_TYPE_LABELS[profile.type]) {
    errors.type = 'Select a valid organization type.';
  }

  const email = String(profile.email ?? '').trim();
  if (!email) {
    errors.email = 'Email is required.';
  } else if (!EMAIL_RE.test(email)) {
    errors.email = 'Enter a valid email address.';
  }

  // Phone is optional, but if given it must look like one.
  const phone = String(profile.phone ?? '').trim();
  if (phone) {
    const digits = phone.replace(/\D/g, '');
    if (!PHONE_CHARS_RE.test(phone) || digits.length < 7 || digits.length > 15) {
      errors.phone = 'Enter a valid phone number.';
    }
  }

  if (!String(profile.address ?? '').trim()) {
    errors.address = 'Address is required.';
  }

  if (!String(profile.serviceArea ?? '').trim()) {
    errors.serviceArea = 'Service area is required.';
  }

  // Report the first problem only — the editor shows one message above the rows.
  for (const row of profile.operatingHours ?? []) {
    if (row.closed) continue;
    const dayLabel = DAYS.find((day) => day.key === row.day)?.label ?? row.day;

    if (!row.open || !row.close) {
      errors.operatingHours = `${dayLabel}: enter opening and closing times, or mark the day as closed.`;
      break;
    }
    // 'HH:MM' strings compare correctly as text.
    if (row.close <= row.open) {
      errors.operatingHours = `${dayLabel}: closing time must be after opening time.`;
      break;
    }
  }

  // Capacity is optional; when given it must be a whole number >= 0.
  const rawCapacity = profile.capacity?.value;
  if (rawCapacity != null && String(rawCapacity).trim() !== '') {
    const capacity = Number(rawCapacity);
    if (!Number.isInteger(capacity) || capacity < 0) {
      errors.capacity = 'Capacity must be a whole number, 0 or more.';
    }
  }

  if (!Array.isArray(profile.resourceTypes) || profile.resourceTypes.length === 0) {
    errors.resourceTypes = 'Select at least one resource type.';
  }

  return errors;
}

/** True when `validateProfile` found anything to fix. */
export function hasErrors(errors) {
  return Object.keys(errors ?? {}).length > 0;
}
