import { RESOURCE_TYPE } from '@/utils/theme';

/**
 * Mock option lists for the create-rescue form (src/pages/CreateRescue.jsx).
 * Frontend only — a real backend will likely drive these from an org's
 * configured categories/units later; kept here so the form component stays
 * free of hardcoded arrays.
 */

export const FOOD_CATEGORIES = [
  { value: 'produce', label: 'Fresh Produce' },
  { value: 'bakery', label: 'Bakery & Bread' },
  { value: 'dairy', label: 'Dairy & Eggs' },
  { value: 'prepared', label: 'Prepared Meals' },
  { value: 'canned', label: 'Canned & Packaged Goods' },
  { value: 'beverages', label: 'Beverages' },
  { value: 'other', label: 'Other' },
];

export const MEDICAL_CATEGORIES = [
  { value: 'medications', label: 'Medications' },
  { value: 'vaccines', label: 'Vaccines' },
  { value: 'ppe', label: 'PPE & Protective Equipment' },
  { value: 'supplies', label: 'Medical Supplies' },
  { value: 'equipment', label: 'Medical Equipment' },
  { value: 'other', label: 'Other' },
];

export const FOOD_UNITS = [
  { value: 'kg', label: 'Kilograms (kg)' },
  { value: 'lbs', label: 'Pounds (lbs)' },
  { value: 'liters', label: 'Liters (L)' },
  { value: 'trays', label: 'Trays' },
  { value: 'boxes', label: 'Boxes' },
  { value: 'servings', label: 'Servings' },
  { value: 'crates', label: 'Crates' },
];

export const MEDICAL_UNITS = [
  { value: 'units', label: 'Units' },
  { value: 'vials', label: 'Vials' },
  { value: 'boxes', label: 'Boxes' },
  { value: 'kits', label: 'Kits' },
  { value: 'doses', label: 'Doses' },
  { value: 'packs', label: 'Packs' },
];

export const PREPARATION_TIME_OPTIONS = [
  { value: 'ready_now', label: 'Ready now' },
  { value: 'within_30m', label: 'Within 30 minutes' },
  { value: 'within_1h', label: 'Within 1 hour' },
  { value: 'within_2h', label: 'Within 2 hours' },
  { value: 'within_4h', label: 'Within 4 hours' },
];

/** Per-resource-type option lookup, keyed by RESOURCE_TYPE. */
export const CATEGORY_OPTIONS = {
  [RESOURCE_TYPE.FOOD]: FOOD_CATEGORIES,
  [RESOURCE_TYPE.MEDICAL]: MEDICAL_CATEGORIES,
};

export const UNIT_OPTIONS = {
  [RESOURCE_TYPE.FOOD]: FOOD_UNITS,
  [RESOURCE_TYPE.MEDICAL]: MEDICAL_UNITS,
};
