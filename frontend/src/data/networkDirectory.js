import { RESOURCE_TYPE } from '@/utils/theme';
import { AVAILABILITY, ORG_TYPE, VERIFICATION } from '@/utils/networkDirectory';

/**
 * Mock organizations for the Network Directory (`/app/network`).
 *
 * DEMO DATA ONLY. Every organization below is invented for this walkthrough.
 * None of them exists, none has been contacted, and none has been checked or
 * approved by anyone — the `verification` field is a made-up illustrative
 * label for the demo UI, not a statement about any real-world organization.
 * There is no backend behind this file and no directory lookup is performed.
 *
 * Shape of one entry:
 *
 *   id             stable key
 *   name           fictional organization name
 *   type           ORG_TYPE — which section of the directory it appears in
 *   area, city     split so search can match either; `location` joins them
 *   position       { lat, lng } — an approximate, deliberately imprecise DEMO
 *                  pin for the map, near the named area of Bengaluru. It is
 *                  not a real address and not a live location.
 *   description    one line on what the organization does
 *   resourceTypes  which resource domains it handles (food / medical)
 *   capacity       { value, unit, label } — how much it can take or hold,
 *                  or null where capacity is not a meaningful measure
 *   availability   AVAILABILITY — whether it can take work right now
 *   workload       { active, max, label } — how loaded it currently is, or
 *                  null where the organization does not carry assignments
 *   verification   VERIFICATION, or null where it does not apply (rescue
 *                  hubs are run by the network itself in this demo)
 *
 * Fields are deliberately null where they do not apply, so the cards show
 * only what each kind of organization actually has (see NetworkOrgCard).
 */
export const NETWORK_ORGANIZATIONS = [
  /* ---------- NGOs ---------- */
  {
    id: 'org-ngo-a',
    name: 'NGO A',
    type: ORG_TYPE.NGO,
    area: 'Indiranagar',
    city: 'Bengaluru',
    position: { lat: 12.9789, lng: 77.6402 },
    description: 'Community meal programme distributing cooked food on weekday evenings.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 60, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-ngo-d',
    name: 'NGO D',
    type: ORG_TYPE.NGO,
    area: 'Koramangala',
    city: 'Bengaluru',
    position: { lat: 12.9361, lng: 77.6262 },
    description: 'Same-night vegetarian meal service with its own volunteer distribution team.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 40, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-ngo-night-rescue-hub',
    name: 'Night Rescue Hub',
    type: ORG_TYPE.NGO,
    area: 'MG Road',
    city: 'Bengaluru',
    position: { lat: 12.9752, lng: 77.6081 },
    description:
      'Late-night outreach team distributing hot meals on the street. Despite the name, it is an outreach organization, not one of the network\u2019s own rescue hubs.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 15, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-ngo-sanjeevini',
    name: 'Sanjeevini Relief Trust',
    type: ORG_TYPE.NGO,
    area: 'Jayanagar',
    city: 'Bengaluru',
    position: { lat: 12.9296, lng: 77.5821 },
    description: 'Runs a medicine bank alongside a weekend community kitchen.',
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 120, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.LIMITED,
    workload: null,
    verification: VERIFICATION.PENDING,
  },
  {
    id: 'org-ngo-eastside',
    name: 'Eastside Community Pantry',
    type: ORG_TYPE.NGO,
    area: 'Whitefield',
    city: 'Bengaluru',
    position: { lat: 12.9712, lng: 77.749 },
    description: 'Dry-goods pantry serving families; closed to deliveries after 6 PM.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 35, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.UNAVAILABLE,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-ngo-harborview',
    name: 'Harborview Soup Kitchen',
    type: ORG_TYPE.NGO,
    area: 'Hebbal',
    city: 'Bengaluru',
    position: { lat: 13.0372, lng: 77.5951 },
    description: 'Hot meal service; no loading access, so pickup partners cannot always reach it.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 25, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.LIMITED,
    workload: null,
    verification: VERIFICATION.UNLISTED,
  },

  /* ---------- Shelters ---------- */
  {
    id: 'org-shelter-b',
    name: 'Shelter B',
    type: ORG_TYPE.SHELTER,
    area: 'BTM Layout',
    city: 'Bengaluru',
    position: { lat: 12.9179, lng: 77.6118 },
    description: 'Overnight shelter with cold storage for prepared meals.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 25, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-shelter-asha',
    name: 'Asha Night Shelter',
    type: ORG_TYPE.SHELTER,
    area: 'Malleshwaram',
    city: 'Bengaluru',
    position: { lat: 13.0047, lng: 77.5661 },
    description: 'Family shelter with an on-site nurse two evenings a week.',
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 90, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.LIMITED,
    workload: null,
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-shelter-parkside',
    name: 'Parkside Transit Shelter',
    type: ORG_TYPE.SHELTER,
    area: 'Basavanagudi',
    city: 'Bengaluru',
    position: { lat: 12.9435, lng: 77.5752 },
    description: 'Short-stay shelter for people in transit; intake closes at 10 PM.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 55, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: null,
    verification: VERIFICATION.PENDING,
  },
  {
    id: 'org-shelter-riverbend',
    name: 'Riverbend Womens Shelter',
    type: ORG_TYPE.SHELTER,
    area: 'HSR Layout',
    city: 'Bengaluru',
    position: { lat: 12.9098, lng: 77.6459 },
    description: 'Long-stay shelter; accepts prepared meals and basic medical supplies.',
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 70, unit: 'portions', label: 'Intake capacity' },
    availability: AVAILABILITY.UNAVAILABLE,
    workload: null,
    verification: VERIFICATION.UNLISTED,
  },

  /* ---------- Rescue Partners ---------- */
  {
    id: 'org-partner-12',
    name: 'Rescue Partner #12',
    type: ORG_TYPE.PARTNER,
    area: 'Indiranagar',
    city: 'Bengaluru',
    position: { lat: 12.9769, lng: 77.6437 },
    description: 'Two-wheeler courier covering short inner-city runs.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 80, unit: 'portions/run', label: 'Load per run' },
    availability: AVAILABILITY.LIMITED,
    workload: { active: 3, max: 4, label: 'Active rescue assignments' },
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-partner-coldchain',
    name: 'Coldchain Logistics Co-op',
    type: ORG_TYPE.PARTNER,
    area: 'Whitefield',
    city: 'Bengaluru',
    position: { lat: 12.9679, lng: 77.7521 },
    description: 'Refrigerated vans for longer runs and temperature-sensitive loads.',
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 400, unit: 'kg/run', label: 'Load per run' },
    availability: AVAILABILITY.AVAILABLE,
    workload: { active: 2, max: 8, label: 'Active rescue assignments' },
    verification: VERIFICATION.VERIFIED,
  },
  {
    id: 'org-partner-nightowl',
    name: 'Night Owl Riders',
    type: ORG_TYPE.PARTNER,
    area: 'MG Road',
    city: 'Bengaluru',
    position: { lat: 12.9771, lng: 77.6049 },
    description: 'Volunteer riders available only for late-evening pickups.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 40, unit: 'portions/run', label: 'Load per run' },
    availability: AVAILABILITY.UNAVAILABLE,
    workload: { active: 0, max: 3, label: 'Active rescue assignments' },
    verification: VERIFICATION.PENDING,
  },
  {
    id: 'org-partner-medirun',
    name: 'MediRun Volunteers',
    type: ORG_TYPE.PARTNER,
    area: 'Jayanagar',
    city: 'Bengaluru',
    position: { lat: 12.9321, lng: 77.5854 },
    description: 'Small team moving medical supplies between clinics and shelters.',
    resourceTypes: [RESOURCE_TYPE.MEDICAL],
    capacity: { value: 60, unit: 'kg/run', label: 'Load per run' },
    availability: AVAILABILITY.AVAILABLE,
    workload: { active: 1, max: 5, label: 'Active rescue assignments' },
    verification: VERIFICATION.UNLISTED,
  },

  /* ---------- Rescue Hubs ---------- */
  {
    id: 'org-hub-central',
    name: 'Central Rescue Hub',
    type: ORG_TYPE.HUB,
    area: 'MG Road',
    city: 'Bengaluru',
    position: { lat: 12.9738, lng: 77.6098 },
    description: 'Main sorting and holding point for city-centre rescues.',
    resourceTypes: [RESOURCE_TYPE.FOOD, RESOURCE_TYPE.MEDICAL],
    capacity: { value: 1200, unit: 'portions', label: 'Holding capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: { active: 540, max: 1200, label: 'Currently held' },
    verification: null,
  },
  {
    id: 'org-hub-north',
    name: 'North Bengaluru Distribution Hub',
    type: ORG_TYPE.HUB,
    area: 'Hebbal',
    city: 'Bengaluru',
    position: { lat: 13.0341, lng: 77.5987 },
    description: 'Overflow hub with cold storage, used when city-centre capacity runs out.',
    resourceTypes: [RESOURCE_TYPE.FOOD],
    capacity: { value: 800, unit: 'portions', label: 'Holding capacity' },
    availability: AVAILABILITY.LIMITED,
    workload: { active: 720, max: 800, label: 'Currently held' },
    verification: null,
  },
  {
    id: 'org-hub-south',
    name: 'South Ring Medical Hub',
    type: ORG_TYPE.HUB,
    area: 'BTM Layout',
    city: 'Bengaluru',
    position: { lat: 12.9152, lng: 77.6093 },
    description: 'Medical-only hub holding supplies awaiting onward allocation.',
    resourceTypes: [RESOURCE_TYPE.MEDICAL],
    capacity: { value: 300, unit: 'kg', label: 'Holding capacity' },
    availability: AVAILABILITY.AVAILABLE,
    workload: { active: 60, max: 300, label: 'Currently held' },
    verification: null,
  },
];