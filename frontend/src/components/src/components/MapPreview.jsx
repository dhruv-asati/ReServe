import { useMemo } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { divIcon } from 'leaflet';
import { Map as MapIcon } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

import { EmptyState } from '@/components/ui';
import { NETWORK_ROLE_META } from '@/utils/theme';
import { NETWORK_ROLE_ICONS } from '@/utils/icons';

const FALLBACK_CENTER = [37.7749, -122.4194];

/**
 * Builds a small leaflet divIcon from a Lucide icon component, coloured by
 * role — a pin-shaped badge instead of a generic default marker, so each
 * network role reads as a distinct shape at a glance, not just a colour.
 */
function buildRoleIcon(role) {
  const Icon = NETWORK_ROLE_ICONS[role];
  const color = NETWORK_ROLE_META[role]?.color ?? '#94a3b8';
  const markup = renderToStaticMarkup(
    <span
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 26,
        height: 26,
        borderRadius: '9999px',
        backgroundColor: color,
        border: '2px solid rgba(16, 21, 29, 0.85)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.35)',
      }}
    >
      {Icon ? <Icon size={14} strokeWidth={2.25} color="#0b0f16" /> : null}
    </span>,
  );

  return divIcon({
    html: markup,
    className: 'map-role-marker',
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -13],
  });
}

/**
 * MapPreview — read-only OpenStreetMap view of the rescue network.
 *
 * Frontend only: no live GPS and no backend — `locations` is mock data
 * passed down from Dashboard.jsx (services/networkService). Markers are
 * divIcon badges built from Lucide icons so each role (provider, recipient,
 * rescue partner, rescue hub) has its own shape, not just a colour. The
 * full interactive map (search, routing, filters) is a separate, later
 * page — this is a compact preview only.
 */
export default function MapPreview({ locations = [] }) {
  const center = useMemo(() => centerOf(locations), [locations]);
  const icons = useMemo(() => {
    const cache = {};
    for (const role of Object.keys(NETWORK_ROLE_META)) {
      cache[role] = buildRoleIcon(role);
    }
    return cache;
  }, []);

  if (locations.length === 0) {
    return (
      <EmptyState
        icon={MapIcon}
        title="No network locations yet"
        description="Providers, recipients, partners and hubs will appear here once they're added."
      />
    );
  }

  return (
    <div className="map-preview-dark relative h-56 w-full overflow-hidden rounded-control sm:h-72 lg:h-[420px]">
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {locations.map((location) => {
          const meta = NETWORK_ROLE_META[location.role];
          const icon = icons[location.role];
          if (!icon) return null;

          return (
            <Marker key={location.id} position={[location.lat, location.lng]} icon={icon}>
              <Popup>
                <div className="min-w-[9rem]">
                  <p className="text-xs font-semibold text-content">{location.name}</p>
                  <p className="mt-0.5 text-[11px] text-muted">{meta?.label ?? 'Location'}</p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

/** Average lat/lng across all locations — a simple, dependency-free center. */
function centerOf(locations) {
  if (locations.length === 0) return FALLBACK_CENTER;
  const totals = locations.reduce(
    (acc, loc) => [acc[0] + loc.lat, acc[1] + loc.lng],
    [0, 0],
  );
  return [totals[0] / locations.length, totals[1] / locations.length];
}
