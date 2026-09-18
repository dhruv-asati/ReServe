import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Package,
  Tag,
  Hash,
  Scale,
  Store,
  MapPin,
  CalendarPlus,
  CalendarClock,
  AlertTriangle,
  FileText,
} from 'lucide-react';

import { Card, Badge, StatusBadge, EmptyState, ErrorState, LoadingState } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META, URGENCY_META } from '@/utils/theme';
import { CATEGORY_OPTIONS, UNIT_OPTIONS } from '@/data/rescueForm';
import { getResourceDetails } from '@/services/resourcesService';
import { PATHS } from '@/routes/paths';
import { cn } from '@/utils/cn';

/** Urgency → Badge tone. Matches the colour weight used across the app (AtRiskCard). */
const URGENCY_TONE = {
  critical: 'critical',
  high: 'urgent',
  medium: 'active',
  low: 'neutral',
};

/** Urgency → left accent border, so the page reads its severity at a glance. */
const URGENCY_BORDER = {
  critical: 'border-l-2 border-l-critical',
  high: 'border-l-2 border-l-urgent',
  medium: 'border-l-2 border-l-active',
  low: 'border-l-2 border-l-line-strong',
};

/** Urgency → how many of the 4 indicator bars are filled, most severe first. */
const URGENCY_BARS = { critical: 4, high: 3, medium: 2, low: 1 };

function labelFor(options, value) {
  return options.find((opt) => opt.value === value)?.label ?? value;
}

function formatDateTime(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/** Compact 4-bar severity meter — a scannable companion to the urgency badge. */
function UrgencyIndicator({ urgency }) {
  const meta = URGENCY_META[urgency];
  const filled = URGENCY_BARS[urgency] ?? 0;

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-end gap-1" role="img" aria-label={`${meta?.label ?? 'Unknown'} urgency`}>
        {[0, 1, 2, 3].map((index) => (
          <span
            key={index}
            className={cn(
              'w-1.5 rounded-sm transition-colors',
              index === 0 && 'h-2',
              index === 1 && 'h-3',
              index === 2 && 'h-4',
              index === 3 && 'h-5',
              index < filled ? 'bg-current' : 'bg-surface-3',
            )}
            style={index < filled ? { color: meta?.color } : undefined}
          />
        ))}
      </div>
      <Badge tone={URGENCY_TONE[urgency] ?? 'neutral'} dot>
        {(meta?.label ?? 'Unknown').toUpperCase()} URGENCY
      </Badge>
    </div>
  );
}

function DetailRow({ icon: Icon, label, value, placeholder = 'Not provided' }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line py-3 last:border-b-0 sm:border-b-0 sm:py-2.5">
      <span className="flex shrink-0 items-center gap-1.5 text-xs text-faint">
        {Icon && <Icon size={13} strokeWidth={1.75} className="shrink-0" />}
        {label}
      </span>
      <span
        className={cn(
          'text-right text-xs font-medium',
          value ? 'text-content' : 'italic text-faint',
        )}
      >
        {value || placeholder}
      </span>
    </div>
  );
}

/**
 * ResourceDetails — read-only detail view for a single resource, at
 * `/resources/:id`.
 *
 * Frontend only: no backend call. Data comes from services/resourcesService
 * (getResourceDetails), which resolves a mock record from data/resources.js
 * after a simulated delay — same mockRequest pattern used everywhere else,
 * so swapping in a real endpoint later only touches that one service
 * function.
 */
export default function ResourceDetails() {
  const { id } = useParams();

  const [resource, setResource] = useState(null);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ready' | 'error'

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setResource(null);

    getResourceDetails(id)
      .then((record) => {
        if (cancelled) return;
        setResource(record);
        setStatus('ready');
      })
      .catch(() => {
        if (cancelled) return;
        setStatus('error');
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="animate-fade-up mx-auto max-w-3xl space-y-6">
      <div>
        <Link
          to={PATHS.DASHBOARD}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-content"
        >
          <ArrowLeft size={13} strokeWidth={1.75} />
          Back to dashboard
        </Link>
      </div>

      {status === 'loading' && (
        <Card>
          <Card.Body>
            <LoadingState label="Loading resource…" />
          </Card.Body>
        </Card>
      )}

      {status === 'error' && (
        <Card>
          <ErrorState
            title="Couldn't load this resource"
            description="Something went wrong resolving the mock resource details. Try again in a moment."
          />
        </Card>
      )}

      {status === 'ready' && !resource && (
        <Card>
          <EmptyState
            icon={Package}
            title="Resource not found"
            description={`No resource matches "${id}". It may have been removed, or this link is stale.`}
            action={
              <Link
                to={PATHS.DASHBOARD}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-400 hover:text-brand-300"
              >
                <ArrowLeft size={13} strokeWidth={1.75} />
                Back to dashboard
              </Link>
            }
          />
        </Card>
      )}

      {status === 'ready' && resource && (
        <ResourceDetailsView resource={resource} />
      )}
    </div>
  );
}

function ResourceDetailsView({ resource }) {
  const TypeIcon = RESOURCE_ICONS[resource.resourceType] ?? Package;
  const resourceTypeLabel = RESOURCE_META[resource.resourceType]?.label ?? resource.resourceType;
  const categoryLabel = labelFor(CATEGORY_OPTIONS[resource.resourceType] ?? [], resource.category);
  const unitLabel = labelFor(UNIT_OPTIONS[resource.resourceType] ?? [], resource.unit);

  return (
    <div className="space-y-6">
      {/* ---------- Header ---------- */}
      <Card className={URGENCY_BORDER[resource.urgency]}>
        <Card.Body className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control border border-line bg-surface-2 text-brand-400">
                <TypeIcon size={18} strokeWidth={1.75} />
              </span>
              <div className="min-w-0">
                <h1 className="truncate text-lg font-bold tracking-tight text-content sm:text-xl">
                  {resource.resourceName}
                </h1>
                <p className="mt-0.5 text-xs text-faint">{resource.id}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:flex-col sm:items-end">
              <StatusBadge status={resource.status} />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-line bg-surface-2 px-3.5 py-3">
            <span className="flex items-center gap-1.5 text-xs text-faint">
              <AlertTriangle size={13} strokeWidth={1.75} />
              Urgency
            </span>
            <UrgencyIndicator urgency={resource.urgency} />
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Details ---------- */}
      <Card>
        <Card.Header title="Resource Details" subtitle="Everything logged for this resource." />
        <Card.Body>
          <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
            <DetailRow icon={TypeIcon} label="Resource type" value={resourceTypeLabel} />
            <DetailRow icon={Tag} label="Category" value={categoryLabel} />
            <DetailRow icon={Hash} label="Quantity" value={String(resource.quantity)} />
            <DetailRow icon={Scale} label="Unit" value={unitLabel} />
            <DetailRow icon={Store} label="Provider" value={resource.provider} />
            <DetailRow icon={MapPin} label="Location" value={resource.location} />
            <DetailRow icon={CalendarPlus} label="Created" value={formatDateTime(resource.createdAt)} />
            <DetailRow
              icon={CalendarClock}
              label="Pickup deadline"
              value={formatDateTime(resource.pickupDeadline)}
            />
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Description ---------- */}
      <Card>
        <Card.Header icon={FileText} title="Description" />
        <Card.Body>
          <p
            className={cn(
              'text-sm leading-relaxed',
              resource.description ? 'text-content' : 'italic text-faint',
            )}
          >
            {resource.description || 'No description provided.'}
          </p>
        </Card.Body>
      </Card>
    </div>
  );
}
