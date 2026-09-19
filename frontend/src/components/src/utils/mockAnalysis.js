import { RESOURCE_TYPE, URGENCY, RESOURCE_META } from '@/utils/theme';
import { CATEGORY_OPTIONS, UNIT_OPTIONS, PREPARATION_TIME_OPTIONS } from '@/data/rescueForm';

/** Ordered checklist the mock analysis "runs" through, top to bottom. */
export const ANALYSIS_STEPS = [
  { key: 'detected', label: 'Resource detected' },
  { key: 'category', label: 'Category identified' },
  { key: 'quantity', label: 'Quantity identified' },
  { key: 'urgency', label: 'Urgency calculated' },
  { key: 'window', label: 'Rescue window identified' },
];

/** How long each step "takes" before the next one starts, in ms. */
export const STEP_DURATION_MS = 650;

/** Minutes granted before pickup, by computed urgency tier. */
const RESCUE_WINDOW_MINUTES = {
  [URGENCY.CRITICAL]: 30,
  [URGENCY.HIGH]: 90,
  [URGENCY.MEDIUM]: 180,
  [URGENCY.LOW]: 360,
};

function labelFor(options, value) {
  return options.find((opt) => opt.value === value)?.label ?? value;
}

function formatWindow(minutes) {
  if (minutes < 60) return `${minutes}-minute rescue window`;
  const hours = Math.round(minutes / 60);
  return `${hours}-hour rescue window`;
}

/**
 * Deterministic, frontend-only "analysis" of a mock resource — no AI or
 * backend call involved. Urgency is derived from how soon the resource's
 * own deadline (pickup deadline for food, expiry for medical) arrives; the
 * rescue window then follows from that urgency tier. Clearly a stand-in:
 * the real analysis pipeline is a separate, later step.
 */
export function computeMockAnalysis(resource) {
  const isFood = resource.resourceType === RESOURCE_TYPE.FOOD;
  const deadlineRaw = isFood ? resource.pickupDeadline : resource.expiry;
  const deadlineTime = deadlineRaw ? new Date(deadlineRaw).getTime() : NaN;
  const hoursUntil = Number.isNaN(deadlineTime) ? null : (deadlineTime - Date.now()) / 3_600_000;

  let urgency = URGENCY.MEDIUM;
  if (hoursUntil !== null) {
    if (hoursUntil <= 2) urgency = URGENCY.CRITICAL;
    else if (hoursUntil <= 6) urgency = URGENCY.HIGH;
    else if (hoursUntil <= 24) urgency = URGENCY.MEDIUM;
    else urgency = URGENCY.LOW;
  }

  const rescueWindowMinutes = RESCUE_WINDOW_MINUTES[urgency];
  const categoryOptions = CATEGORY_OPTIONS[resource.resourceType] ?? [];
  const unitOptions = UNIT_OPTIONS[resource.resourceType] ?? [];

  const title = isFood ? labelFor(categoryOptions, resource.category) : resource.resourceName;
  const quantityLabel = `${resource.quantity} ${labelFor(unitOptions, resource.unit)}`;

  // ---- Everything below is read straight from what was entered on the
  // form — presented as "AI-understood information", since the mock
  // "analysis" steps above are just naming/echoing it back, not deciding
  // anything. Urgency + rescue window above are the only two values this
  // mock actually *derives*, so those are the "system allocation decisions".
  const resourceTypeLabel = RESOURCE_META[resource.resourceType]?.label ?? resource.resourceType;
  const categoryLabel = isFood ? labelFor(categoryOptions, resource.category) : resource.resourceName;

  const attributes = [
    { label: 'Pickup location', value: resource.location },
    isFood && {
      label: 'Preparation time',
      value: labelFor(PREPARATION_TIME_OPTIONS, resource.preparationTime),
    },
    isFood &&
      resource.pickupDeadline && {
        label: 'Pickup deadline',
        value: new Date(resource.pickupDeadline).toLocaleString(),
      },
    !isFood &&
      resource.expiry && {
        label: 'Expiry',
        value: new Date(resource.expiry).toLocaleDateString(),
      },
    !isFood && resource.batchReference && { label: 'Batch / reference', value: resource.batchReference },
    resource.description && { label: 'Description', value: resource.description },
    resource.images?.length > 0 && {
      label: 'Photos attached',
      value: `${resource.images.length} image${resource.images.length > 1 ? 's' : ''}`,
    },
    resource.documents?.length > 0 && {
      label: 'Documents attached',
      value: `${resource.documents.length} file${resource.documents.length > 1 ? 's' : ''}`,
    },
  ].filter((attr) => attr && attr.value);

  return {
    title: title || 'Untitled resource',
    resourceTypeLabel,
    categoryLabel: categoryLabel || 'Uncategorized',
    quantityLabel,
    attributes,
    urgency,
    rescueWindowMinutes,
    rescueWindowLabel: formatWindow(rescueWindowMinutes),
  };
}
