import { NETWORK_ROLE } from '@/utils/theme';

/**
 * Mock network locations for the dashboard map preview.
 *
 * Coordinates are fictional but geographically coherent (spread across one
 * metro area) so the preview reads like a real service area. `role` comes
 * from utils/theme so markers and the legend share one source of truth.
 */
export const NETWORK_LOCATIONS = [
  {
    id: 'prov-1',
    role: NETWORK_ROLE.PROVIDER,
    name: 'Green Valley Farms',
    lat: 37.7849,
    lng: -122.4294,
  },
  {
    id: 'prov-2',
    role: NETWORK_ROLE.PROVIDER,
    name: 'Sunrise Bakery Co.',
    lat: 37.7595,
    lng: -122.4367,
  },
  {
    id: 'prov-3',
    role: NETWORK_ROLE.PROVIDER,
    name: 'Harbor Wholesale',
    lat: 37.8083,
    lng: -122.4098,
  },
  {
    id: 'recip-1',
    role: NETWORK_ROLE.RECIPIENT,
    name: 'Riverside Community Kitchen',
    lat: 37.7694,
    lng: -122.4862,
  },
  {
    id: 'recip-2',
    role: NETWORK_ROLE.RECIPIENT,
    name: 'Downtown Shelter',
    lat: 37.7822,
    lng: -122.4097,
  },
  {
    id: 'recip-3',
    role: NETWORK_ROLE.RECIPIENT,
    name: "St. Mary's Food Pantry",
    lat: 37.728,
    lng: -122.4453,
  },
  {
    id: 'partner-1',
    role: NETWORK_ROLE.PARTNER,
    name: 'Mobile Health Unit 3',
    lat: 37.7955,
    lng: -122.3937,
  },
  {
    id: 'partner-2',
    role: NETWORK_ROLE.PARTNER,
    name: 'Eastside Free Clinic',
    lat: 37.7749,
    lng: -122.4194,
  },
  {
    id: 'hub-1',
    role: NETWORK_ROLE.HUB,
    name: 'Central Rescue Hub',
    lat: 37.7752,
    lng: -122.4184,
  },
  {
    id: 'hub-2',
    role: NETWORK_ROLE.HUB,
    name: 'North Bay Distribution Hub',
    lat: 37.8199,
    lng: -122.4783,
  },
];
