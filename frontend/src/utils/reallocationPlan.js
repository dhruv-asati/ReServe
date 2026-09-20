/**
 * Demo reallocation rule for the RS-1024 "recipient becomes unavailable"
 * scenario.
 *
 * DEMO ONLY. This is a small, deterministic rule applied to the hardcoded
 * demo candidates in data/matching.js. It is not a production allocation
 * engine, it calls no model or backend, and it produces no confidence,
 * ranking or optimization score. Pure functions only — no React, no network —
 * so the same rule can be read, tested and swapped out for a real service
 * later without touching any page.
 *
 * Step 1 — who is still eligible (evaluateRecipient). A recipient can take
 * part only if every constraint holds:
 *
 *   availability   available, and not the recipient that just dropped out
 *   eligibility    eligible for this resource
 *   pickup         a pickup partner can reach it
 *   deadline       pickup ETA is inside the rescue window
 *   distance       inside the resource's service radius
 *   capacity       has capacity to give
 *
 * Step 2 — who gets what (recalculateAllocation):
 *
 *   1. Recipients that are still eligible keep the share they already had.
 *   2. The displaced portions (the dropped recipient's share) go to the
 *      eligible recipients with the most spare capacity first, never above a
 *      recipient's capacity. Filling the largest gaps first touches as few
 *      recipients as possible.
 *   3. The result must place every portion: the total has to equal the
 *      original total exactly. If it cannot, the status is 'shortfall' and
 *      nothing is claimed as a valid plan.
 */

const sum = (values) => [...values].reduce((total, value) => total + value, 0);

/**
 * Check one candidate against every constraint. The first failing constraint
 * (in the order listed above) is the one reported, using the demo data's own
 * wording where it has some (`unselectableReason`).
 *
 * Returns `{ id, name, eligible, reason }`; `reason` is null when eligible.
 */
export function evaluateRecipient(candidate, resource, unavailableIds = []) {
  const {
    id,
    name,
    availability,
    eligibility,
    pickupFeasibility,
    pickupEtaMinutes,
    distanceKm,
    capacity,
    unselectableReason,
  } = candidate;
  const windowMinutes = resource?.rescueWindowMinutes;
  const radiusKm = resource?.serviceRadiusKm;

  let reason = null;
  if (unavailableIds.includes(id)) {
    reason = 'Marked unavailable — cannot receive this delivery.';
  } else if (availability !== 'yes') {
    reason = unselectableReason ?? 'Not available to receive deliveries.';
  } else if (eligibility !== 'yes') {
    reason = 'Not eligible for this resource.';
  } else if (pickupFeasibility !== 'yes') {
    reason = unselectableReason ?? 'No pickup partner can reach this location.';
  } else if (!Number.isFinite(pickupEtaMinutes) || !Number.isFinite(windowMinutes)) {
    reason = 'No pickup estimate is available to check against the rescue window.';
  } else if (pickupEtaMinutes > windowMinutes) {
    reason = `Pickup would take ${pickupEtaMinutes} min, outside the ${windowMinutes}-minute rescue window.`;
  } else if (!Number.isFinite(distanceKm) || !Number.isFinite(radiusKm) || distanceKm > radiusKm) {
    reason = `Outside the ${radiusKm} km service radius.`;
  } else if (!Number.isFinite(capacity) || capacity <= 0) {
    reason = 'No capacity available.';
  }

  return { id, name, eligible: reason === null, reason };
}

/** How a recipient's share moved between the previous and the updated allocation. */
function changeOf(previous, updated) {
  if (updated === 0) return 'removed';
  if (previous === 0) return 'new';
  if (updated > previous) return 'increased';
  if (updated < previous) return 'decreased';
  return 'unchanged';
}

/**
 * Recalculate an allocation after `unavailableIds` dropped out.
 *
 *   candidates      every candidate recipient (data/matching.js shape)
 *   resource        { rescueWindowMinutes, serviceRadiusKm, … }
 *   previous        the allocation being replaced: [{ id, name, portions, unit }]
 *   unavailableIds  recipients that can no longer receive anything
 *
 * Returns
 *   status       'complete' | 'shortfall'
 *   problems     why the plan is not valid (empty when complete)
 *   total        portions in the previous allocation — the amount to place
 *   unit         unit label of the portions
 *   displaced    portions that lost their recipient
 *   unplaced     portions still without a recipient (0 when complete)
 *   rows         one per recipient in the previous or updated allocation, in
 *                candidate order: { id, name, previous, updated, delta,
 *                change: 'unchanged' | 'increased' | 'decreased' | 'new' | 'removed' }
 *   evaluations  every candidate's { id, name, eligible, reason }
 */
export function recalculateAllocation({ candidates, resource, previous, unavailableIds = [] }) {
  const unit = previous[0]?.unit ?? resource?.unit ?? '';
  const total = sum(previous.map((item) => item.portions));

  const evaluations = candidates.map((candidate) =>
    evaluateRecipient(candidate, resource, unavailableIds),
  );
  const eligible = new Map(
    candidates
      .filter((candidate) => evaluations.find((entry) => entry.id === candidate.id)?.eligible)
      .map((candidate) => [candidate.id, candidate]),
  );

  // 1. Recipients that are still eligible keep their existing share.
  const shares = new Map();
  previous.forEach((item) => {
    if (eligible.has(item.id)) shares.set(item.id, item.portions);
  });
  const displaced = total - sum(shares.values());

  // 2. Place the displaced portions: most spare capacity first, capped at capacity.
  let remaining = displaced;
  const byHeadroom = [...eligible.values()]
    .map((candidate) => ({
      candidate,
      headroom: candidate.capacity - (shares.get(candidate.id) ?? 0),
    }))
    .filter(({ headroom }) => headroom > 0)
    .sort((a, b) => b.headroom - a.headroom || a.candidate.distanceKm - b.candidate.distanceKm);

  for (const { candidate, headroom } of byHeadroom) {
    if (remaining <= 0) break;
    const take = Math.min(headroom, remaining);
    shares.set(candidate.id, (shares.get(candidate.id) ?? 0) + take);
    remaining -= take;
  }

  // 3. Validate: everything placed, nobody over capacity, total unchanged.
  const problems = [];
  if (remaining > 0) {
    problems.push(
      `${remaining} ${unit} could not be placed — the remaining eligible recipients have no spare capacity.`,
    );
  }
  shares.forEach((portions, id) => {
    const { name, capacity } = eligible.get(id);
    if (portions > capacity) {
      problems.push(`${name} would exceed its capacity of ${capacity} ${unit}.`);
    }
  });
  if (sum(shares.values()) + remaining !== total) {
    problems.push('The updated allocation does not add up to the original total.');
  }

  const previousById = new Map(previous.map((item) => [item.id, item.portions]));
  const rows = candidates
    .filter((candidate) => previousById.has(candidate.id) || shares.has(candidate.id))
    .map((candidate) => {
      const before = previousById.get(candidate.id) ?? 0;
      const after = shares.get(candidate.id) ?? 0;
      return {
        id: candidate.id,
        name: candidate.name,
        previous: before,
        updated: after,
        delta: after - before,
        change: changeOf(before, after),
      };
    });

  return {
    status: problems.length === 0 ? 'complete' : 'shortfall',
    problems,
    total,
    unit,
    displaced,
    unplaced: remaining,
    rows,
    evaluations,
  };
}
