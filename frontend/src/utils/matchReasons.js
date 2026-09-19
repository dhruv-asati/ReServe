/**
 * Build the "Why This Match?" reasons for one allocated recipient.
 *
 * Every reason is derived from the mock candidate/resource fields and is
 * only returned when those fields actually support it — a missing or
 * failing field means the reason is left out, never assumed. There are no
 * scores, percentages or confidence values, and nothing here calls a model
 * or backend.
 *
 * Each reason: { key, label, detail } — `detail` quotes the real values.
 */
export function buildMatchReasons(candidate, resource) {
  if (!candidate) return [];

  const {
    allocatedQuantity,
    unit,
    capacity,
    capacityUnit,
    availability,
    pickupEtaMinutes,
    pickupFeasibility,
    distanceKm,
    eligibility,
    eligibilityBasis,
  } = candidate;
  const reasons = [];

  if (
    Number.isFinite(capacity) &&
    Number.isFinite(allocatedQuantity) &&
    capacity >= allocatedQuantity
  ) {
    reasons.push({
      key: 'capacity',
      label: 'Capacity compatible',
      detail: `Can hold the ${allocatedQuantity} ${unit} proposed — capacity is ${capacity} ${capacityUnit ?? unit}.`,
    });
  }

  if (availability === 'yes') {
    reasons.push({
      key: 'availability',
      label: 'Recipient available',
      detail: 'Marked as available to receive this delivery.',
    });
  }

  const windowMinutes = resource?.rescueWindowMinutes;
  if (
    Number.isFinite(pickupEtaMinutes) &&
    Number.isFinite(windowMinutes) &&
    pickupEtaMinutes <= windowMinutes
  ) {
    reasons.push({
      key: 'window',
      label: 'Within rescue window',
      detail: `Estimated pickup in ${pickupEtaMinutes} min, inside the ${windowMinutes}-minute rescue window.`,
    });
  }

  if (pickupFeasibility === 'yes') {
    reasons.push({
      key: 'pickup',
      label: 'Pickup feasible',
      detail: 'A pickup partner can reach this location.',
    });
  }

  const radiusKm = resource?.serviceRadiusKm;
  if (Number.isFinite(distanceKm) && Number.isFinite(radiusKm) && distanceKm <= radiusKm) {
    reasons.push({
      key: 'geography',
      label: 'Geographic feasibility',
      detail: `${distanceKm} km from the provider, inside the ${radiusKm} km service radius.`,
    });
  }

  if (eligibility === 'yes') {
    reasons.push({
      key: 'eligibility',
      label: 'Eligibility satisfied',
      detail: eligibilityBasis ?? 'Meets the eligibility requirements for this resource.',
    });
  }

  return reasons;
}
