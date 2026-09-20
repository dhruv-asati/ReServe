import { RESOURCE_TYPE, URGENCY } from '@/utils/theme';

/**
 * Mock matching data for the Smart Matching page (DEMO ONLY).
 *
 * Everything here is hardcoded for the walkthrough — it is not the output of
 * a matching engine, scoring model or backend, and carries no confidence or
 * ranking values. Recipient names are fictional demo names.
 *
 * The "Why This Match?" explanations on the allocation cards are derived
 * from the fields below (see utils/matchReasons.js). A reason only appears
 * when the field behind it supports it, so anything not modelled here is
 * simply never claimed.
 *
 * Yes/no/unknown check fields use 'yes' | 'no' | null (null = not evaluated).
 * `allocatedQuantity` marks the demo allocation: candidates with a number get
 * a proposed share; `null` means not allocated. The proposed shares sum to
 * the resource quantity so the confirm step passes.
 *
 * The same candidate fields (capacity, availability, distance, pickup ETA,
 * pickup feasibility, eligibility) feed the RS-1024 "recipient unavailable"
 * demo, which re-checks them to produce an updated allocation — see
 * utils/reallocationPlan.js and services/reallocationDemoService.js. NGO D is
 * a feasible candidate that the original split simply does not use; it only
 * receives portions once NGO A drops out.
 */

/**
 * The resource being matched in the demo: 80 portions of Vegetarian Meals.
 * `serviceRadiusKm` is the demo's geographic limit for a recipient.
 * `rescueWindowMinutes` is derived from `urgency` in matchingService.js.
 */
export const MATCH_RESOURCE = {
  id: 'RES-DEMO-80',
  resource: 'Vegetarian Meals',
  resourceType: RESOURCE_TYPE.FOOD,
  quantity: 80,
  unit: 'portions',
  provider: 'Riverside Community Kitchen',
  location: '480 Riverside Ave, Warehouse B',
  urgency: URGENCY.HIGH,
  serviceRadiusKm: 15,
};

/**
 * Candidate recipients. Extra fields beyond the card basics:
 *   pickupEtaMinutes  — mock estimate for a pickup partner to arrive
 *   eligibilityBasis  — short, human-readable reason eligibility passed
 */
export const MATCH_CANDIDATES = [
  {
    id: 'cand-ngo-a',
    name: 'NGO A',
    need: 60,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 4.2,
    capacity: 60,
    capacityUnit: 'portions',
    availability: 'yes',
    eligibility: 'yes',
    eligibilityBasis: 'Registered NGO that accepts vegetarian meals',
    pickupFeasibility: 'yes',
    pickupEtaMinutes: 35,
    selectable: true,
    unselectableReason: null,
    allocatedQuantity: 50,
  },
  {
    id: 'cand-shelter-b',
    name: 'Shelter B',
    need: 25,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 8.6,
    capacity: 25,
    capacityUnit: 'portions',
    availability: 'yes',
    eligibility: 'yes',
    eligibilityBasis: 'Overnight shelter with cold storage for prepared meals',
    pickupFeasibility: 'yes',
    pickupEtaMinutes: 50,
    selectable: true,
    unselectableReason: null,
    allocatedQuantity: 20,
  },
  {
    id: 'cand-ngo-d',
    name: 'NGO D',
    need: 40,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 13.4,
    capacity: 40,
    capacityUnit: 'portions',
    availability: 'yes',
    eligibility: 'yes',
    eligibilityBasis: 'Registered NGO that accepts vegetarian meals',
    pickupFeasibility: 'yes',
    pickupEtaMinutes: 80,
    selectable: true,
    unselectableReason: null,
    allocatedQuantity: null,
  },
  {
    id: 'cand-night-rescue-hub',
    name: 'Night Rescue Hub',
    need: 20,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 12.3,
    capacity: 20,
    capacityUnit: 'portions',
    availability: 'yes',
    eligibility: 'yes',
    eligibilityBasis: 'Late-night outreach hub that distributes hot meals',
    pickupFeasibility: 'yes',
    pickupEtaMinutes: 70,
    selectable: true,
    unselectableReason: null,
    allocatedQuantity: 10,
  },
  {
    id: 'cand-harborview',
    name: 'Harborview Soup Kitchen',
    need: 25,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 9.6,
    capacity: 25,
    capacityUnit: 'portions',
    availability: 'yes',
    eligibility: 'yes',
    pickupFeasibility: 'no',
    selectable: false,
    unselectableReason:
      'No pickup partner can reach this location inside the rescue window.',
    allocatedQuantity: null,
  },
  {
    id: 'cand-eastside',
    name: 'Eastside Community Pantry',
    need: 35,
    needLabel: 'Meals needed tonight',
    unit: 'portions',
    distanceKm: 11.2,
    capacity: null,
    capacityUnit: 'portions',
    availability: 'no',
    eligibility: null,
    pickupFeasibility: null,
    selectable: false,
    unselectableReason: 'Closed for the day — not accepting deliveries.',
    allocatedQuantity: null,
  },
];
