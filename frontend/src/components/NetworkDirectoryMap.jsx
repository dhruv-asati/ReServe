import { useEffect, useMemo, useRef, useState } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';
import { divIcon, latLngBounds } from 'leaflet';
import { ArrowDownToLine, FlaskConical, Maximize2, X } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

import { Badge, Button } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';
import {
  AVAILABILITY_META,
  AVAILABILITY_ORDER,
  ORG_TYPES,
  ORG_TYPE_META,
  VERIFICATION_META,
  locationLabel,
  workloadPercent,
} from '@/utils/networkDirectory';

/** Where the demo map opens: Indiranagar, Bengaluru. */
const DEMO_CENTER = [12.9784, 77.6408];
const DEMO_ZOOM = 13;

/** Leaflet cannot read Tailwind classes, so the marker chrome uses these fixed values. */
const MARKER_BORDER = 'rgba(16, 21, 29, 0.85)';
const MARKER_ICON_INK = '#0b0f16';
const MARKER_DOT_BORDER = '#10151d';
const FALLBACK_COLOR = '#94a3b8';

/** Height of the sticky Topbar (h-16) plus a little air, and of the mobile bottom nav. */
const TOPBAR_CLEARANCE = 72;
const MOBILE_NAV_CLEARANCE = 88;

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/* ---------- Marker icons ---------- */

const iconCache = new Map();

/**
 * One round badge per organization: filled with the category colour and
 * carrying the category's icon, so categories differ by shape as well as
 * colour. A small corner dot shows the demo availability value. The selected
 * marker is larger, ringed in white and lifted above its neighbours.
 */
function buildIcon(type, availability, selected) {
  const key = `${type}|${availability}|${selected ? 1 : 0}`;
  const cached = iconCache.get(key);
  if (cached) return cached;

  const meta = ORG_TYPE_META[type];
  const Icon = meta?.icon;
  const color = meta?.color ?? FALLBACK_COLOR;
  const dotColor = AVAILABILITY_META[availability]?.color ?? FALLBACK_COLOR;
  const size = selected ? 40 : 30;

  const markup = renderToStaticMarkup(
    <span
      style={{
        position: 'relative',
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        borderRadius: '9999px',
        backgroundColor: color,
        border: selected ? '3px solid #ffffff' : `2px solid ${MARKER_BORDER}`,
        boxShadow: selected
          ? `0 0 0 4px ${color}99, 0 4px 12px rgba(0,0,0,0.55)`
          : '0 1px 4px rgba(0,0,0,0.35)',
      }}
    >
      {Icon ? (
        <Icon size={selected ? 19 : 15} strokeWidth={2.25} color={MARKER_ICON_INK} aria-hidden="true" />
      ) : null}
      <span
        style={{
          position: 'absolute',
          right: -3,
          bottom: -3,
          boxSizing: 'border-box',
          width: 12,
          height: 12,
          borderRadius: '9999px',
          backgroundColor: dotColor,
          border: `2px solid ${MARKER_DOT_BORDER}`,
        }}
      />
    </span>,
  );

  const icon = divIcon({
    html: markup,
    className: 'org-map-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2)],
  });
  iconCache.set(key, icon);
  return icon;
}

/** Fit the map to every marker currently shown (a single marker just centres on it). */
function fitToOrganizations(map, organizations, animate) {
  if (organizations.length === 0) return;
  const bounds = latLngBounds(
    organizations.map((organization) => [organization.position.lat, organization.position.lng]),
  );
  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14, animate });
}

/* ---------- Map panel ---------- */

/**
 * NetworkDirectoryMap — the demo map beside the Network Directory cards.
 *
 * Controlled by the page: `organizations` is the already-filtered list (the
 * same one the cards render, so markers and cards can never disagree),
 * `selectedId` is the single selected organization, and the map reports
 * interaction back through `onSelect(id)` / `onDeselect(id)`.
 *
 *   marker click        → onSelect(id): the page highlights the card.
 *   selectedId changes  → the marker is enlarged and ringed, the map pans to
 *                         it if it is out of view, and its popup opens.
 *   popup closed        → onDeselect(id): the highlight clears on both sides.
 *   revealRequest       → bumped by the page when a *card* is chosen; if the
 *                         map is scrolled out of view (mobile), it is brought
 *                         back into view so the highlight is actually seen.
 *
 * DEMO DATA. Every organization and every position is invented (see
 * data/networkDirectory.js). Pins are approximate demo positions near named
 * Bengaluru areas — not real addresses and not live locations — and the
 * availability shown is a demo value, not a real-world status. The panel says
 * so in its notice, on the map itself, and in every popup.
 *
 * Uses the same Leaflet + OpenStreetMap setup as the dashboard's MapPreview.
 */
export default function NetworkDirectoryMap({
  organizations,
  selectedId,
  onSelect,
  onDeselect,
  onJumpToCard,
  revealRequest = 0,
}) {
  const [map, setMap] = useState(null);
  const frameRef = useRef(null);
  const markerRefs = useRef(new Map());
  const hasFitted = useRef(false);

  const selected = useMemo(
    () => organizations.find((organization) => organization.id === selectedId) ?? null,
    [organizations, selectedId],
  );

  // Fit to the visible markers on first load and whenever the filters change.
  useEffect(() => {
    if (!map || organizations.length === 0) return;
    fitToOrganizations(map, organizations, hasFitted.current && !prefersReducedMotion());
    hasFitted.current = true;
  }, [map, organizations]);

  // Selection → bring the marker into view and open its popup.
  useEffect(() => {
    if (!map || !selectedId) return;
    const marker = markerRefs.current.get(selectedId);
    if (!marker) return;

    const position = marker.getLatLng();
    if (!map.getBounds().pad(-0.1).contains(position)) {
      map.panTo(position, { animate: !prefersReducedMotion() });
    }
    if (!marker.isPopupOpen()) marker.openPopup();
  }, [map, selectedId]);

  // A card was chosen: make sure the map is on screen so the highlight is seen.
  useEffect(() => {
    if (!revealRequest || !frameRef.current) return;
    const rect = frameRef.current.getBoundingClientRect();
    const bottomLimit =
      window.innerHeight - (window.innerWidth < 768 ? MOBILE_NAV_CLEARANCE : 16);
    if (rect.top >= TOPBAR_CLEARANCE && rect.bottom <= bottomLimit) return;
    frameRef.current.scrollIntoView({
      block: 'center',
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    });
  }, [revealRequest]);

  // Keep Leaflet's size in step with its container (rotation, drawer, layout shifts).
  useEffect(() => {
    if (!map || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);

  return (
    <section aria-labelledby="network-map-heading" className="space-y-3">
      <div className="flex flex-wrap items-center gap-2.5">
        <h3 id="network-map-heading" className="text-sm font-semibold tracking-tight text-content">
          Demo map
        </h3>
        <Badge tone="predicted" icon={FlaskConical} size="sm">
          DEMO DATA
        </Badge>
        <span className="text-xs text-muted">
          {organizations.length} pin{organizations.length === 1 ? '' : 's'} shown
        </span>
      </div>

      <p className="rounded-control border border-line bg-surface-2 px-3.5 py-3 text-xs leading-relaxed text-muted">
        Every pin is an invented organization at an approximate demo position near a named
        Bengaluru area, centred on Indiranagar. Pins are not live locations or real addresses, and
        the availability shown is a made-up demo value — it does not mean any organization is
        available in the real world.
      </p>

      <div
        ref={frameRef}
        className="map-preview-dark relative isolate h-72 w-full overflow-hidden rounded-control border border-line sm:h-80 lg:h-[26rem]"
      >
        <MapContainer
          ref={setMap}
          center={DEMO_CENTER}
          zoom={DEMO_ZOOM}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {organizations.map((organization) => {
            const isSelected = organization.id === selectedId;
            const typeLabel = ORG_TYPE_META[organization.type]?.singular ?? 'Organization';

            return (
              <Marker
                key={organization.id}
                ref={(marker) => {
                  if (marker) markerRefs.current.set(organization.id, marker);
                  else markerRefs.current.delete(organization.id);
                }}
                position={[organization.position.lat, organization.position.lng]}
                icon={buildIcon(organization.type, organization.availability, isSelected)}
                zIndexOffset={isSelected ? 1000 : 0}
                riseOnHover
                title={`${organization.name} — demo ${typeLabel}`}
                alt={`${organization.name}, demo ${typeLabel}`}
                eventHandlers={{
                  click: () => onSelect(organization.id),
                  popupclose: () => onDeselect(organization.id),
                }}
              >
                <Popup maxWidth={280} minWidth={220} autoPanPadding={[24, 24]}>
                  <OrganizationPopup organization={organization} />
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Always-visible demo label, on the map itself. */}
        <span className="pointer-events-none absolute bottom-2 left-2 z-[500] rounded-full border border-line bg-surface-1/90 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
          Demo data · approximate positions
        </span>

        <div className="absolute right-2 top-2 z-[500]">
          <Button
            variant="secondary"
            size="sm"
            icon={Maximize2}
            onClick={() => map && fitToOrganizations(map, organizations, !prefersReducedMotion())}
            disabled={!map || organizations.length === 0}
            aria-label="Fit the map to all pins shown"
          >
            <span className="hidden sm:inline">Fit all</span>
          </Button>
        </div>

        {organizations.length === 0 && (
          <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center bg-surface-0/60 p-6 text-center">
            <p className="max-w-xs rounded-control border border-line bg-surface-1 px-4 py-3 text-xs text-muted">
              No demo organizations match the current filters, so there are no pins to show.
            </p>
          </div>
        )}
      </div>

      {/* Selection summary — also the on-map way back to the matching card. */}
      <div
        role="status"
        aria-live="polite"
        className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-control border border-line bg-surface-2 px-3.5 py-2.5"
      >
        {selected ? (
          <>
            <p className="min-w-0 text-xs text-muted">
              <span className="font-semibold text-content">{selected.name}</span>
              {' — '}
              {ORG_TYPE_META[selected.type]?.singular} · {locationLabel(selected)} (demo)
            </p>
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                icon={ArrowDownToLine}
                onClick={() => onJumpToCard(selected.id)}
              >
                Show card
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={X}
                onClick={() => onDeselect(selected.id)}
                aria-label={`Clear selection: ${selected.name}`}
              >
                Clear
              </Button>
            </div>
          </>
        ) : (
          <p className="text-xs text-muted">
            Select a pin or a directory card to see its demo details.
          </p>
        )}
      </div>

      <MapLegend />
    </section>
  );
}

/* ---------- Legend ---------- */

/** Marker key: one entry per category (colour + shape) and per demo availability dot. */
function MapLegend() {
  return (
    <div className="flex flex-col gap-x-6 gap-y-2 sm:flex-row sm:flex-wrap sm:items-center">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {ORG_TYPES.map((type) => {
          const { label, icon: Icon, color } = ORG_TYPE_META[type];
          return (
            <span key={type} className="flex items-center gap-1.5 text-xs text-muted">
              <span
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full ring-1 ring-inset ring-black/10"
                style={{ backgroundColor: color }}
              >
                <Icon size={11} strokeWidth={2.25} color={MARKER_ICON_INK} aria-hidden="true" />
              </span>
              {label}
            </span>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-[11px] font-medium uppercase tracking-wide text-faint">
          Corner dot = demo availability
        </span>
        {AVAILABILITY_ORDER.map((availability) => {
          const { label, color } = AVAILABILITY_META[availability];
          return (
            <span key={availability} className="flex items-center gap-1.5 text-xs text-muted">
              <span
                aria-hidden="true"
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: color }}
              />
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- Popup ---------- */

/**
 * Popup body for one organization. Built from <div>/<span> only: Leaflet's
 * stylesheet gives `.leaflet-popup-content p` unlayered margins that would
 * override Tailwind's utilities on paragraphs.
 */
function OrganizationPopup({ organization }) {
  const {
    name,
    type,
    description,
    resourceTypes = [],
    capacity,
    availability,
    workload,
    verification,
  } = organization;

  const category = ORG_TYPE_META[type];
  const available = AVAILABILITY_META[availability];
  const verified = verification ? VERIFICATION_META[verification] : null;
  const percent = workloadPercent(workload);

  return (
    <div className="w-full space-y-2.5 text-content">
      <div>
        <div className="text-sm font-semibold leading-snug tracking-tight">{name}</div>
        <div className="mt-0.5 text-[11px] text-muted">
          {category?.singular} · {locationLabel(organization)}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Badge tone="predicted" icon={FlaskConical} size="sm">
          DEMO ORGANIZATION
        </Badge>
        {available && (
          <Badge tone={available.tone} dot size="sm">
            Demo availability: {available.label}
          </Badge>
        )}
      </div>

      {description && <div className="text-[11px] leading-relaxed text-muted">{description}</div>}

      {resourceTypes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {resourceTypes.map((resourceType) => {
            const Icon = RESOURCE_ICONS[resourceType];
            return (
              <Badge key={resourceType} tone={resourceType} icon={Icon} size="sm">
                {RESOURCE_META[resourceType]?.label ?? resourceType}
              </Badge>
            );
          })}
        </div>
      )}

      {(capacity || workload) && (
        <div className="space-y-0.5 text-[11px] text-muted">
          {capacity && (
            <div>
              {capacity.label}:{' '}
              <span className="font-semibold text-content">
                {capacity.value} {capacity.unit}
              </span>
            </div>
          )}
          {workload && (
            <div>
              {workload.label}:{' '}
              <span className="font-semibold text-content">
                {workload.active} of {workload.max}
                {percent !== null ? ` (${percent}%)` : ''}
              </span>
            </div>
          )}
        </div>
      )}

      {verified && (
        <div className="text-[11px] text-muted">
          <Badge tone={verified.tone} size="sm">
            {verified.label}
          </Badge>
        </div>
      )}

      <div className="border-t border-line pt-2 text-[10px] leading-relaxed text-faint">
        Invented for this demo. The pin is an approximate demo position — not a real address or a
        live location — and no availability, capacity or workload shown here reflects the real
        world.
      </div>
    </div>
  );
}
