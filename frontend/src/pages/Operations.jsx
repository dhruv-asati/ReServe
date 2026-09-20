import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FilterX, FlaskConical, Map, Radio, SearchX } from 'lucide-react';

import { Card, Badge, Button, EmptyState, LoadingState } from '@/components/ui';
import OperationListCard from '@/components/OperationListCard';
import OperationsTable from '@/components/OperationsTable';
import OperationsFilters from '@/components/OperationsFilters';
import OperationSummaryCard from '@/components/OperationSummaryCard';
import OperationStageTracker from '@/components/OperationStageTracker';
import OperationEventsCard from '@/components/OperationEventsCard';
import ReallocationDemoCard from '@/components/ReallocationDemoCard';
import MapPreview from '@/components/MapPreview';
import MapLegend from '@/components/MapLegend';
import useReallocationDemo from '@/hooks/useReallocationDemo';
import {
  getRescueOperations,
  getRescueOperationDetail,
} from '@/services/rescueOperationsService';
import {
  DEMO_OPERATION_ID,
  applyDemoToOperationDetail,
  applyDemoToOperations,
} from '@/services/reallocationDemoService';
import {
  DEFAULT_FILTERS,
  countQuickFilters,
  filterOperations,
  hasActiveFilters,
} from '@/utils/operationFilters';

/** The operation whose details show until the user picks another (RS-1024). */
const DEFAULT_OPERATION_ID = 'RS-1024';

/** Longest search text echoed back in the empty state, so it can never overflow. */
const MAX_ECHOED_QUERY = 40;

/** Empty-state copy: says what found nothing, and what to try next. */
function noMatchDescription({ query }) {
  const text = query.trim().replace(/\s+/g, ' ');
  if (!text) {
    return 'No operation fits the selected filters. Try a different combination, or clear the filters to see every operation.';
  }
  const shown = text.length > MAX_ECHOED_QUERY ? `${text.slice(0, MAX_ECHOED_QUERY)}…` : text;
  return `Nothing matched “${shown}” with the current filters. Check the spelling, try a shorter search, or clear the filters.`;
}

/**
 * Operations — the Operations Control Center (`/app/operations`).
 *
 * Two parts, top to bottom:
 *
 *   1. A list of rescue operations — a table from `xl` up, cards below — with
 *      ID, resource, quantity, provider, recipient, rescue partner, status,
 *      ETA and deadline. Every operation is selectable. Above it, a filter
 *      bar (OperationsFilters) narrows the list by quick filter, status,
 *      resource type and search text; the rules live in
 *      utils/operationFilters.js. Filtering is instant and client-side, and
 *      only changes which rows are listed — the selected operation and its
 *      details below are left as they are.
 *   2. The details view for the selected operation: a status summary with
 *      its allocation breakdown, a progress tracker over the operation's
 *      lifecycle, a map area with an illustrative route, and the event feed
 *      of what has already happened. RS-1024 is selected by default, so the
 *      page still opens on the same details it always showed.
 *
 * While RS-1024 is selected, the details also show the recipient-unavailable
 * demo (ReallocationDemoCard). Triggering it moves RS-1024 to Reallocating in
 * the list, the summary and the map, adds a Reallocating stage to the
 * progress tracker, and records the cause in the event feed. When the mock
 * reallocation finishes the operation becomes Matched again to the updated
 * recipients: the tracker's current stage becomes "Matched (updated
 * allocation)", the allocation summary shows the updated split, the event
 * feed explains that the allocation changed because the original recipient
 * became unavailable, and the demo card compares the previous and updated
 * allocations side by side. It is the same scenario state that Smart Matching
 * and the Dashboard read.
 *
 * The selection lives in the URL (`?operation=RS-1025`), so it survives a
 * refresh and can be linked to. An unknown id falls back to RS-1024.
 *
 * Everything on this page is frontend-only mock data (see
 * data/rescueOperations.js and data/operationDetail.js) fetched through
 * rescueOperationsService, the same mock-request pattern used by the rest of
 * the app. There is no backend, no live GPS tracking, and no real-world
 * rescue-partner dispatch behind it — every illustrative figure (stage
 * timestamps, ETA, route, map position) is called out as demo information.
 */
export default function Operations() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('operation') ?? DEFAULT_OPERATION_ID;

  // What the mock service returned. The RS-1024 recipient-unavailable demo is
  // layered on top below, so the list, the summary, the tracker and the map
  // all read the same scenario state (see services/reallocationDemoService.js).
  const [baseOperations, setBaseOperations] = useState(null);
  const [baseDetail, setBaseDetail] = useState(null);
  const demo = useReallocationDemo();
  const operations = useMemo(
    () => applyDemoToOperations(baseOperations, demo),
    [baseOperations, demo],
  );
  const detail = useMemo(() => applyDemoToOperationDetail(baseDetail, demo), [baseDetail, demo]);

  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const detailsRef = useRef(null);
  const detailsHeadingRef = useRef(null);
  const listHeadingRef = useRef(null);

  useEffect(() => {
    let active = true;
    getRescueOperations().then((data) => active && setBaseOperations(data));
    return () => {
      active = false;
    };
  }, []);

  // Load the selected operation's details. `detail` resets to null first so
  // the cards below show their loading state instead of the previous
  // operation's data.
  useEffect(() => {
    let active = true;
    setBaseDetail(null);
    getRescueOperationDetail(selectedId).then((data) => active && setBaseDetail(data));
    return () => {
      active = false;
    };
  }, [selectedId]);

  // A hand-edited ?operation= that matches nothing falls back to the default.
  useEffect(() => {
    if (operations && !operations.some((operation) => operation.id === selectedId)) {
      setSearchParams({}, { replace: true });
    }
  }, [operations, selectedId, setSearchParams]);

  // Select an operation, then bring its details into view — on mobile the
  // details sit well below the list, so selecting would otherwise look like
  // nothing happened.
  const handleSelect = useCallback(
    (operation) => {
      setSearchParams({ operation: operation.id }, { replace: true });

      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      detailsRef.current?.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start',
      });
      detailsHeadingRef.current?.focus({ preventScroll: true });
    },
    [setSearchParams],
  );

  const updateFilter = useCallback(
    (key, value) => setFilters((current) => ({ ...current, [key]: value })),
    [],
  );
  const clearFilters = useCallback(() => setFilters(DEFAULT_FILTERS), []);

  // Clearing from the empty state removes the button that was just pressed, so
  // hand focus to the list heading instead of letting it fall back to <body>.
  const clearFromEmptyState = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    listHeadingRef.current?.focus();
  }, []);

  const filtersActive = hasActiveFilters(filters);
  const quickCounts = useMemo(
    () => (operations ? countQuickFilters(operations) : null),
    [operations],
  );
  const visibleOperations = useMemo(
    () => (operations ? filterOperations(operations, filters) : null),
    [operations, filters],
  );

  const operation = detail?.operation ?? null;
  const hasRoute = Boolean(detail?.route);

  let routeSubtitle = 'Illustrative route between the provider and the recipient.';
  if (detail?.routeSubtitle) {
    routeSubtitle = detail.routeSubtitle; // e.g. the route was withdrawn (recipient unavailable demo)
  } else if (operation && hasRoute) {
    routeSubtitle = `Illustrative route from ${operation.provider} to ${operation.recipient}, ${operation.location}.`;
  } else if (operation) {
    routeSubtitle = 'Provider location only — no route to show for this operation.';
  }

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      {/* ---------- Page header ---------- */}
      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
            Operations Control Center
          </h1>
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO / MOCK DATA
          </Badge>
        </div>
        <p className="mt-1.5 text-sm text-muted">
          Every rescue operation in one list. Select one to see its status, progress, and location.
        </p>
      </div>

      {/* ---------- Operations list ---------- */}
      <section aria-labelledby="operations-list-heading">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2
            id="operations-list-heading"
            ref={listHeadingRef}
            tabIndex={-1}
            className="text-base font-semibold tracking-tight text-content"
          >
            Operations
          </h2>
          {/* A status region, so screen readers hear the new count as the list changes. */}
          {operations && (
            <p role="status" className="text-xs text-muted">
              {filtersActive
                ? `Showing ${visibleOperations.length} of ${operations.length} operation${operations.length === 1 ? '' : 's'}`
                : `${operations.length} operation${operations.length === 1 ? '' : 's'}`}
            </p>
          )}
        </div>

        {/* Hidden only when loading has finished and there is nothing to filter. */}
        {(operations === null || operations.length > 0) && (
          <OperationsFilters
            filters={filters}
            counts={quickCounts}
            onChange={updateFilter}
            onClear={clearFilters}
          />
        )}

        {operations === null ? (
          <LoadingState variant="skeleton" rows={5} label="Loading operations…" />
        ) : operations.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={Radio}
              title="No rescue operations yet"
              description="Operations show up here once a rescue has been created."
            />
          </div>
        ) : visibleOperations.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={SearchX}
              title="No operations match your filters"
              description={noMatchDescription(filters)}
              action={
                <Button variant="secondary" icon={FilterX} onClick={clearFromEmptyState}>
                  Clear Filters
                </Button>
              }
            />
          </div>
        ) : (
          <>
            {/* Desktop: table */}
            <div className="hidden xl:block">
              <OperationsTable
                operations={visibleOperations}
                selectedId={selectedId}
                onSelect={handleSelect}
              />
            </div>

            {/* Mobile + tablet: cards */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:hidden">
              {visibleOperations.map((item) => (
                <OperationListCard
                  key={item.id}
                  operation={item}
                  selected={item.id === selectedId}
                  onSelect={handleSelect}
                />
              ))}
            </div>
          </>
        )}

        <p className="mt-3 text-[11px] text-faint">
          Mock data — operations, providers, recipients, rescue partners, ETAs and deadlines are
          illustrative, not a live feed.
        </p>
      </section>

      {/* ---------- Selected operation details ---------- */}
      <section
        ref={detailsRef}
        aria-labelledby="operation-details-heading"
        className="scroll-mt-20 space-y-6 lg:space-y-8"
      >
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2
            id="operation-details-heading"
            ref={detailsHeadingRef}
            tabIndex={-1}
            className="text-base font-semibold tracking-tight text-content"
          >
            Operation details
          </h2>
          <span className="font-mono text-xs text-muted">{selectedId}</span>
        </div>

        {/* ---------- Operation summary ---------- */}
        {operation === null ? (
          <Card>
            <Card.Body>
              <LoadingState label="Loading operation…" />
            </Card.Body>
          </Card>
        ) : (
          <OperationSummaryCard operation={operation} />
        )}

        {/* The recipient-unavailable demo belongs to the demo operation only. */}
        {operation?.id === DEMO_OPERATION_ID && <ReallocationDemoCard />}

        <div className="grid grid-cols-1 gap-6 lg:gap-8 xl:grid-cols-2">
          {/* ---------- Operation progress ---------- */}
          <Card>
            <Card.Header
              icon={Radio}
              title="Operation Progress"
              subtitle="Every stage of this operation, from Created through to Delivered — including any added while it is re-planned."
            />
            <Card.Body>
              {detail === null ? (
                <LoadingState label="Loading progress…" />
              ) : (
                <>
                  <OperationStageTracker stages={detail.stages} />
                  <p className="mt-4 border-t border-line pt-3 text-[11px] text-faint">
                    Timestamps are hardcoded, illustrative values for this demo — not a live or
                    auto-refreshing feed.
                  </p>
                </>
              )}
            </Card.Body>
          </Card>

          {/* ---------- Route / map area ---------- */}
          <Card>
            <Card.Header icon={Map} title="Route (Demo)" subtitle={routeSubtitle} />
            <Card.Body className="space-y-4">
              {detail === null ? (
                <LoadingState label="Loading map…" />
              ) : (
                <>
                  {/* Keyed by operation so the map re-centres on each selection —
                      the map's centre is only read when it first mounts. */}
                  <MapPreview
                    key={detail.operation.id}
                    locations={detail.locations}
                    route={detail.route}
                    zoom={detail.zoom}
                  />
                  <MapLegend />
                  <p className="text-[11px] text-faint">
                    {detail.mapFootnote ??
                      (hasRoute
                        ? 'Dashed line is a mock, hand-placed route for this demo — not generated by a routing engine. Positions, the ETA, and the rescue partner marker are illustrative only and are not a live GPS feed or vehicle location.'
                        : 'Marker positions are illustrative only for this demo — not a live GPS feed or vehicle location.')}
                  </p>
                </>
              )}
            </Card.Body>
          </Card>
        </div>

        {/* ---------- Operation events ---------- */}
        {detail === null ? (
          <Card>
            <Card.Body>
              <LoadingState label="Loading events…" />
            </Card.Body>
          </Card>
        ) : (
          <OperationEventsCard events={detail.events ?? []} />
        )}
      </section>
    </div>
  );
}
