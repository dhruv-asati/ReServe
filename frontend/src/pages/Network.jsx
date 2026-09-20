import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FilterX, FlaskConical, Network as NetworkIcon, SearchX } from 'lucide-react';

import { Badge, Button, EmptyState, LoadingState } from '@/components/ui';
import NetworkOrgCard from '@/components/NetworkOrgCard';
import NetworkDirectoryFilters from '@/components/NetworkDirectoryFilters';
import NetworkDirectoryMap from '@/components/NetworkDirectoryMap';
import { getNetworkOrganizations } from '@/services/networkService';
import {
  ALL,
  AVAILABILITY_META,
  DEFAULT_FILTERS,
  countByCategory,
  filterOrganizations,
  groupByCategory,
  hasActiveFilters,
} from '@/utils/networkDirectory';
import { RESOURCE_META } from '@/utils/theme';

/** Longest search text echoed back in the empty state, so it can never overflow. */
const MAX_ECHOED_QUERY = 40;

/** Trim and collapse a query for display, with an ellipsis when it is long. */
function echo(text) {
  const clean = text.trim().replace(/\s+/g, ' ');
  return clean.length > MAX_ECHOED_QUERY ? `${clean.slice(0, MAX_ECHOED_QUERY)}…` : clean;
}

/** Empty-state copy: says what found nothing, and what to try next. */
function noMatchDescription({ name, location, resourceType, availability }) {
  const parts = [];
  if (name.trim()) parts.push(`the name “${echo(name)}”`);
  if (location.trim()) parts.push(`the location “${echo(location)}”`);
  if (resourceType !== ALL) {
    parts.push(`the ${RESOURCE_META[resourceType]?.label.toLowerCase() ?? resourceType} resource type`);
  }
  if (availability !== ALL) {
    parts.push(`${AVAILABILITY_META[availability]?.label.toLowerCase() ?? availability} demo availability`);
  }

  if (parts.length === 0) {
    return 'No organization is listed in this category. Try another category, or clear the filters to see the whole directory.';
  }
  return `Nothing matched ${parts.join(' and ')} in this category. Check the spelling, loosen a filter, or clear the filters.`;
}

/**
 * Network Directory — every organization in the rescue network (`/app/network`).
 *
 * The directory is split into four sections, in order: NGOs, Shelters,
 * Rescue Partners and Rescue Hubs. Each organization is a card showing its
 * name, category, location, the resource types it handles, its capacity,
 * availability, workload and verification status — with whatever does not
 * apply to that kind of organization left out rather than shown empty (a
 * shelter carries no rescue assignments; a hub is run by the network itself,
 * so it has no verification status).
 *
 * Above the sections, a filter bar (NetworkDirectoryFilters) narrows the list
 * by organization type, supported resource type, demo availability, and two
 * searches: organization name, and location. Filtering is instant and
 * client-side; the rules live in utils/networkDirectory.js. Sections with no
 * remaining matches disappear, so the page never shows an empty heading.
 *
 * Between the filters and the cards sits an interactive demo map
 * (NetworkDirectoryMap: Leaflet + OpenStreetMap, centred on Indiranagar,
 * Bengaluru). The map and the cards render the SAME filtered list, and the
 * page owns one `selectedId` they share:
 *   - choosing a card highlights its marker, opens its popup, and brings the
 *     map back into view if it has scrolled away (matters on mobile, where
 *     the map is above the list);
 *   - choosing a marker opens its popup and highlights its card;
 *   - closing the popup (or "Clear") clears the highlight on both sides;
 *   - a filter that removes the selected organization clears the selection.
 *
 * DEMO DATA. Every organization here is invented for this walkthrough (see
 * data/networkDirectory.js) and fetched through networkService, the same
 * mock-request pattern the rest of the app uses. There is no backend and no
 * directory lookup. Marker positions are approximate demo pins, not real
 * addresses or live locations; availability and verification labels are
 * illustrative demo values — no real organization is available, verified,
 * reviewed, listed or contacted. The page says so at the top, on the map, in
 * every popup and on every card.
 */
export default function Network() {
  const [organizations, setOrganizations] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState(null);
  const [revealRequest, setRevealRequest] = useState(0);
  const headingRef = useRef(null);

  useEffect(() => {
    let active = true;
    getNetworkOrganizations().then((data) => active && setOrganizations(data));
    return () => {
      active = false;
    };
  }, []);

  const updateFilter = useCallback(
    (key, value) => setFilters((current) => ({ ...current, [key]: value })),
    [],
  );
  const clearFilters = useCallback(() => setFilters(DEFAULT_FILTERS), []);

  // Clearing from the empty state removes the button that was just pressed, so
  // hand focus to the directory heading instead of letting it fall to <body>.
  const clearFromEmptyState = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    headingRef.current?.focus();
  }, []);

  const counts = useMemo(
    () => (organizations ? countByCategory(organizations) : null),
    [organizations],
  );
  const visible = useMemo(
    () => (organizations ? filterOrganizations(organizations, filters) : null),
    [organizations, filters],
  );
  const sections = useMemo(() => (visible ? groupByCategory(visible) : null), [visible]);

  const filtersActive = hasActiveFilters(filters);

  // A filter that removes the selected organization also clears the selection,
  // so no highlight or popup is left pointing at something that is not shown.
  useEffect(() => {
    if (selectedId && visible && !visible.some((organization) => organization.id === selectedId)) {
      setSelectedId(null);
    }
  }, [visible, selectedId]);

  // Marker click (or card click, below) → the one shared selection.
  const selectFromMap = useCallback((id) => setSelectedId(id), []);

  // Card click → select, and ask the map to scroll itself into view if needed.
  const selectFromCard = useCallback((id) => {
    setSelectedId(id);
    setRevealRequest((count) => count + 1);
  }, []);

  // A popup closing reports its own id; only clear when it is still the selected
  // one — opening another marker closes the previous popup *after* selecting it.
  const deselect = useCallback(
    (id) => setSelectedId((current) => (current === id ? null : current)),
    [],
  );

  // "Show card" on the map: scroll to the selected card and move focus to it.
  const jumpToCard = useCallback((id) => {
    const card = document.getElementById(`org-card-${id}`);
    if (!card) return;
    const reduce =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    card.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
    card.querySelector('button')?.focus({ preventScroll: true });
  }, []);

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      {/* ---------- Page header ---------- */}
      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
            Network Directory
          </h1>
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO / MOCK DATA
          </Badge>
        </div>
        <p className="mt-1.5 text-sm text-muted">
          Every organization in the rescue network, on a demo map and grouped by what it does.
        </p>
        <p className="mt-3 rounded-control border border-line bg-surface-2 px-3.5 py-3 text-xs leading-relaxed text-muted">
          Every organization listed here is invented for this demo. None of them exists, none has
          been contacted, and none has been verified or approved by anyone. The map pins are
          approximate demo positions, not live locations, and the availability and verification
          labels are illustrative values in mock data — not a statement about any real-world
          organization.
        </p>
      </div>

      {/* ---------- Directory ---------- */}
      <section aria-labelledby="network-directory-heading">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2
            id="network-directory-heading"
            ref={headingRef}
            tabIndex={-1}
            className="text-base font-semibold tracking-tight text-content"
          >
            Organizations
          </h2>
          {/* A status region, so screen readers hear the new count as the list changes. */}
          {organizations && (
            <p role="status" className="text-xs text-muted">
              {filtersActive
                ? `Showing ${visible.length} of ${organizations.length} organizations`
                : `${organizations.length} organization${organizations.length === 1 ? '' : 's'}`}
            </p>
          )}
        </div>

        {/* Hidden only when loading has finished and there is nothing to filter. */}
        {(organizations === null || organizations.length > 0) && (
          <NetworkDirectoryFilters
            filters={filters}
            counts={counts}
            onChange={updateFilter}
            onClear={clearFilters}
          />
        )}

        {organizations === null ? (
          <LoadingState variant="skeleton" rows={5} label="Loading the network directory…" />
        ) : organizations.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={NetworkIcon}
              title="No organizations yet"
              description="Organizations show up here once they join the rescue network."
            />
          </div>
        ) : (
          <div className="space-y-8">
            {/* The map stays mounted even with zero matches, so filtering never resets it. */}
            <NetworkDirectoryMap
              organizations={visible}
              selectedId={selectedId}
              onSelect={selectFromMap}
              onDeselect={deselect}
              onJumpToCard={jumpToCard}
              revealRequest={revealRequest}
            />

            {sections.length === 0 ? (
              <div className="panel">
                <EmptyState
                  icon={SearchX}
                  title="No organizations match your search"
                  description={noMatchDescription(filters)}
                  action={
                    <Button variant="secondary" icon={FilterX} onClick={clearFromEmptyState}>
                      Clear Filters
                    </Button>
                  }
                />
              </div>
            ) : (
              sections.map((section) => (
                <CategorySection
                  key={section.type}
                  section={section}
                  selectedId={selectedId}
                  onSelect={selectFromCard}
                />
              ))
            )}
          </div>
        )}

        <p className="mt-6 text-[11px] text-faint">
          Mock data — organization names, locations, map positions, capacities, availability,
          workload and verification labels are illustrative, not a live directory.
        </p>
      </section>
    </div>
  );
}

/**
 * One category of the directory: its heading, how many organizations it holds
 * right now, and the cards themselves. One column on mobile, two from `md`,
 * three from `xl` — the same grid rhythm the rest of the app uses.
 */
function CategorySection({ section, selectedId, onSelect }) {
  const { type, label, singular, description, icon: Icon, organizations } = section;
  const headingId = `network-section-${type}`;
  const count = organizations.length;

  return (
    <section aria-labelledby={headingId}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="flex min-w-0 items-center gap-2">
          {Icon && (
            <span className="shrink-0 text-brand-400">
              <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
            </span>
          )}
          <h3
            id={headingId}
            className="text-sm font-semibold tracking-tight text-content"
          >
            {label}
          </h3>
          <Badge tone="neutral" size="sm">
            {count} {count === 1 ? singular : label}
          </Badge>
        </div>
      </div>

      {description && <p className="mb-3 text-xs text-muted">{description}</p>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {organizations.map((organization) => (
          <NetworkOrgCard
            key={organization.id}
            organization={organization}
            selected={organization.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
