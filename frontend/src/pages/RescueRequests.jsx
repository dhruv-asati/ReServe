import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FilterX, Inbox, Search, SearchX, X } from 'lucide-react';

import { Badge, Button, EmptyState, LoadingState, Modal, Select, StatusBadge } from '@/components/ui';
import Tabs from '@/components/ui/Tabs';
import RequestCard from '@/components/RequestCard';
import RequestsTable from '@/components/RequestsTable';
import {
  getIncomingRequests,
  getOutgoingRequests,
  getCompletedRequests,
} from '@/services/requestsService';
import { RESOURCE_META, RESOURCE_TYPE, STATUS } from '@/utils/theme';

const TAB_KEYS = {
  INCOMING: 'incoming',
  OUTGOING: 'outgoing',
  COMPLETED: 'completed',
};

const EMPTY_COPY = {
  [TAB_KEYS.INCOMING]: {
    title: 'No incoming requests',
    description: 'Requests other organizations send you will show up here.',
  },
  [TAB_KEYS.OUTGOING]: {
    title: 'No outgoing requests',
    description: 'Requests you raise with providers or partners will show up here.',
  },
  [TAB_KEYS.COMPLETED]: {
    title: 'No completed requests yet',
    description: 'Delivered and cancelled requests will show up here.',
  },
};

const ALL = 'all';

const STATUS_OPTIONS = [
  { value: ALL, label: 'All' },
  { value: STATUS.PENDING, label: 'Pending' },
  { value: STATUS.MATCHED, label: 'Matched' },
  { value: STATUS.PICKUP_ASSIGNED, label: 'Pickup Assigned' },
  { value: STATUS.IN_TRANSIT, label: 'In Transit' },
  { value: STATUS.DELIVERED, label: 'Delivered' },
  { value: STATUS.CANCELLED, label: 'Cancelled' },
];

const RESOURCE_TYPE_OPTIONS = [
  { value: ALL, label: 'All' },
  { value: RESOURCE_TYPE.FOOD, label: 'Food' },
  { value: RESOURCE_TYPE.MEDICAL, label: 'Medical' },
];

/** Fields the search box looks through. */
const SEARCH_FIELDS = ['id', 'resource', 'provider', 'recipient', 'location'];

/**
 * A request is shown only if it passes every active condition:
 * search text (case-insensitive "contains" across SEARCH_FIELDS), status, and
 * resource type. "All" / empty search means that condition is not applied.
 * The tab is applied before this, by choosing which list is filtered.
 */
function matchesFilters(request, { query, status, resourceType }) {
  if (status !== ALL && request.status !== status) return false;
  if (resourceType !== ALL && request.resourceType !== resourceType) return false;
  if (!query) return true;
  return SEARCH_FIELDS.some((field) => String(request[field] ?? '').toLowerCase().includes(query));
}

/**
 * View Details dialog for one request, built on the shared Modal (Escape,
 * backdrop click and the X all close it; on mobile it opens as a bottom
 * sheet). `request` is the selected request, or null when closed.
 */
function RequestDetailsModal({ request, onClose }) {
  const typeMeta = request ? RESOURCE_META[request.resourceType] : null;

  return (
    <Modal
      open={Boolean(request)}
      onClose={onClose}
      title="Request Details"
      size="lg"
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {request && (
        <dl className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
          <DetailField label="Request ID">
            <span className="font-mono text-xs">{request.id}</span>
          </DetailField>
          <DetailField label="Resource">{request.resource}</DetailField>
          <DetailField label="Resource Type">
            <Badge tone={typeMeta ? request.resourceType : 'neutral'} size="sm">
              {typeMeta?.label ?? request.resourceType}
            </Badge>
          </DetailField>
          <DetailField label="Quantity">{request.quantity}</DetailField>
          <DetailField label="Provider">{request.provider}</DetailField>
          <DetailField label="Recipient">{request.recipient}</DetailField>
          <DetailField label="Location">{request.location}</DetailField>
          <DetailField label="Deadline">{request.deadline}</DetailField>
          <DetailField label="Status">
            <StatusBadge status={request.status} size="sm" />
          </DetailField>
          <DetailField label="Created">{request.created}</DetailField>
          <DetailField label="Description" className="sm:col-span-2">
            <span className="text-muted">{request.description}</span>
          </DetailField>
        </dl>
      )}
    </Modal>
  );
}

function DetailField({ label, className = '', children }) {
  return (
    <div className={`min-w-0 ${className}`}>
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-content">{children}</dd>
    </div>
  );
}

/**
 * Rescue Requests — queue of incoming, outgoing, and completed resource
 * rescue requests.
 *
 * Each tab loads through its own mock service (requestsService), same shape
 * a real endpoint will return later.
 *
 * Search and the Status / Resource Type filters all narrow the active tab
 * together (AND). Search updates as the user types (Request ID, resource,
 * provider, recipient, location). Tab counts always show the full size of
 * each tab, regardless of search or filters. Search and filter values are
 * kept when switching tabs.
 *
 * Layout:
 *   xl and up  — RequestsTable
 *   below xl   — RequestCards (1 column on mobile, 2 on tablet)
 *
 * "View Details" (table and cards, every tab) opens RequestDetailsModal.
 */
export default function RescueRequests() {
  const [activeTab, setActiveTab] = useState(TAB_KEYS.INCOMING);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState(ALL);
  const [resourceTypeFilter, setResourceTypeFilter] = useState(ALL);
  const searchRef = useRef(null);
  const [requestsByTab, setRequestsByTab] = useState({
    [TAB_KEYS.INCOMING]: null,
    [TAB_KEYS.OUTGOING]: null,
    [TAB_KEYS.COMPLETED]: null,
  });

  useEffect(() => {
    let active = true;

    getIncomingRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.INCOMING]: data })),
    );
    getOutgoingRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.OUTGOING]: data })),
    );
    getCompletedRequests().then(
      (data) => active && setRequestsByTab((prev) => ({ ...prev, [TAB_KEYS.COMPLETED]: data })),
    );

    return () => {
      active = false;
    };
  }, []);

  // The request whose details dialog is open (null = closed). Stable
  // callbacks keep Modal's escape/focus effect from re-running on each render.
  const [selectedRequest, setSelectedRequest] = useState(null);
  const handleViewDetails = useCallback((request) => setSelectedRequest(request), []);
  const handleCloseDetails = useCallback(() => setSelectedRequest(null), []);

  const clearSearch = () => {
    setSearchText('');
    searchRef.current?.focus();
  };

  const hasActiveFilters = statusFilter !== ALL || resourceTypeFilter !== ALL;

  const clearFilters = () => {
    setStatusFilter(ALL);
    setResourceTypeFilter(ALL);
  };

  // "Incoming (5)" — counts are the full tab size, not the search result size.
  // While a tab is still loading its count is unknown, so only the label shows.
  const tabLabel = (label, requests) => (requests ? `${label} (${requests.length})` : label);

  const tabs = [
    {
      key: TAB_KEYS.INCOMING,
      label: tabLabel('Incoming', requestsByTab[TAB_KEYS.INCOMING]),
    },
    {
      key: TAB_KEYS.OUTGOING,
      label: tabLabel('Outgoing', requestsByTab[TAB_KEYS.OUTGOING]),
    },
    {
      key: TAB_KEYS.COMPLETED,
      label: tabLabel('Completed', requestsByTab[TAB_KEYS.COMPLETED]),
    },
  ];

  const activeRequests = requestsByTab[activeTab];
  const emptyCopy = EMPTY_COPY[activeTab];
  const query = searchText.trim().toLowerCase();

  const visibleRequests = useMemo(
    () =>
      activeRequests
        ? activeRequests.filter((request) =>
            matchesFilters(request, {
              query,
              status: statusFilter,
              resourceType: resourceTypeFilter,
            }),
          )
        : null,
    [activeRequests, query, statusFilter, resourceTypeFilter],
  );

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
          Rescue Requests
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Manage incoming, outgoing, and completed resource rescue requests.
        </p>
      </div>

      {/* Search sits above the tabs on mobile, and to the right of them from md up */}
      <div className="flex flex-col-reverse gap-3 md:flex-row md:items-center md:justify-between">
        <Tabs
          tabs={tabs}
          value={activeTab}
          onChange={setActiveTab}
          className="max-w-full self-start overflow-x-auto"
        />

        <div role="search" className="relative w-full md:max-w-sm">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">
            <Search size={15} strokeWidth={1.75} />
          </span>
          <input
            ref={searchRef}
            type="text"
            inputMode="search"
            autoComplete="off"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape' && searchText) {
                event.preventDefault();
                clearSearch();
              }
            }}
            placeholder="Search rescue requests..."
            aria-label="Search rescue requests"
            className="h-9.5 w-full rounded-control border border-line bg-surface-2 pl-9 pr-9 text-sm text-content transition-colors duration-150 placeholder:text-faint hover:border-line-strong focus:border-brand-500 focus:outline-none"
          />
          {searchText && (
            <button
              type="button"
              onClick={clearSearch}
              aria-label="Clear search"
              className="absolute right-1.5 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-faint transition-colors duration-150 hover:bg-surface-3 hover:text-content"
            >
              <X size={14} strokeWidth={2} />
            </button>
          )}
        </div>
      </div>

      {/* Filters: two columns on mobile, a single row from sm up */}
      <div className="grid grid-cols-2 items-end gap-3 sm:flex sm:flex-wrap">
        <Select
          label="Status"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          options={STATUS_OPTIONS}
          containerClassName="sm:w-48"
        />
        <Select
          label="Resource Type"
          value={resourceTypeFilter}
          onChange={(event) => setResourceTypeFilter(event.target.value)}
          options={RESOURCE_TYPE_OPTIONS}
          containerClassName="sm:w-48"
        />
        {hasActiveFilters && (
          <Button
            variant="outline"
            icon={FilterX}
            onClick={clearFilters}
            className="col-span-2 justify-center sm:col-span-1"
          >
            Clear Filters
          </Button>
        )}
      </div>

      <section>
        {visibleRequests === null ? (
          <LoadingState label="Loading requests…" />
        ) : activeRequests.length === 0 ? (
          <div className="panel">
            <EmptyState icon={Inbox} title={emptyCopy.title} description={emptyCopy.description} />
          </div>
        ) : visibleRequests.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={SearchX}
              title="No rescue requests found."
              description={
                hasActiveFilters
                  ? 'Try changing your search or filters, or clear the filters.'
                  : 'Try changing your search or clearing the search field.'
              }
            />
          </div>
        ) : (
          <>
            {/* Desktop: table */}
            <div className="hidden xl:block">
              <RequestsTable requests={visibleRequests} onViewDetails={handleViewDetails} />
            </div>

            {/* Mobile + tablet: cards */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:hidden">
              {visibleRequests.map((request) => (
                <RequestCard
                  key={request.id}
                  request={request}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <RequestDetailsModal request={selectedRequest} onClose={handleCloseDetails} />

      {/* Announces the result count to screen readers while typing */}
      <p className="sr-only" aria-live="polite">
        {(query || hasActiveFilters) && visibleRequests
          ? `${visibleRequests.length} rescue request${visibleRequests.length === 1 ? '' : 's'} found`
          : ''}
      </p>
    </div>
  );
}
