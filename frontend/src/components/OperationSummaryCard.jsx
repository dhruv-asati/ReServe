import { Store, Users, Truck, MapPin, Clock, CalendarClock } from 'lucide-react';

import { Card, StatusBadge, Badge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { cn } from '@/utils/cn';

/**
 * OperationSummaryCard — the headline panel of the Operations Control
 * Center: what's moving, who's involved, and where it stands right now.
 *
 * Frontend only: everything passed in via `operation` is demo/mock data
 * (see data/operationDetail.js and data/rescueOperations.js) — the ETA is an
 * illustrative estimate, not a live GPS-calculated arrival time, and the
 * rescue partner is a demo label, not a real-world dispatch assignment.
 *
 * `recipient` and `partner` may be null while an operation is still being
 * matched. An optional `headline` replaces the default "{quantity}
 * {resource}" title (used where a unit reads better, e.g. "35 boxes of
 * Bakery Surplus"), and an optional `allocation` adds the per-recipient
 * allocation breakdown with its totals.
 *
 * `live` is true when `operation` comes from the backend rather than mock
 * data: the demo/illustrative wording is dropped and the ETA is described as
 * an estimated travel time.
 */
export default function OperationSummaryCard({ operation, live = false }) {
  const {
    id,
    resource,
    resourceType,
    quantity,
    provider,
    recipient,
    location,
    partner,
    status,
    eta,
    etaNote,
    deadline,
    summary,
    headline,
    allocation,
  } = operation;

  const Icon = RESOURCE_ICONS[resourceType];

  return (
    <Card>
      <Card.Header
        icon={Icon}
        title={headline ?? `${quantity} ${resource}`}
        subtitle={id}
        action={<StatusBadge status={status} />}
      />
      <Card.Body className="space-y-5">
        {summary && (
          <p className="rounded-control border border-line bg-surface-2 px-3.5 py-3 text-xs leading-relaxed text-muted">
            {summary}
          </p>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <DetailRow icon={Store} label="Provider" value={provider} />
          <DetailRow icon={Users} label="Recipient" value={recipient ?? 'Not matched yet'} />
          <DetailRow icon={MapPin} label="Location" value={location} />
          <DetailRow
            icon={Truck}
            label="Rescue Partner"
            value={partner ? (live ? partner : `${partner} (demo)`) : 'Not assigned yet'}
          />
        </div>

        {allocation && <AllocationSummary allocation={allocation} />}

        <div className="grid grid-cols-1 gap-3 border-t border-line pt-4 sm:grid-cols-2">
          <div className="rounded-control border border-line bg-surface-2 px-3.5 py-3">
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
              <Clock size={12} strokeWidth={1.75} />
              {live ? 'Estimated travel time' : 'ETA (illustrative)'}
            </p>
            <p className="mt-1 text-lg font-semibold tracking-tight text-content">{eta}</p>
            {etaNote && <p className="mt-1 text-[11px] text-faint">{etaNote}</p>}
          </div>

          <div className="rounded-control border border-line bg-surface-2 px-3.5 py-3">
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
              <CalendarClock size={12} strokeWidth={1.75} />
              Rescue deadline
            </p>
            <p className="mt-1 text-lg font-semibold tracking-tight text-content">{deadline}</p>
            <p className="mt-1 text-[11px] text-faint">
              {live
                ? "The resource's expiry or pickup deadline."
                : 'Demo deadline for this illustrative rescue.'}
            </p>
          </div>
        </div>
      </Card.Body>
      <Card.Footer>
        {live ? (
          <Badge tone="active" dot size="sm">
            Live operation
          </Badge>
        ) : (
          <Badge tone="neutral" size="sm">
            Demo information — not a live operation
          </Badge>
        )}
      </Card.Footer>
    </Card>
  );
}

/**
 * The operation's allocation: who holds how many portions, plus totals for
 * what has a recipient and what does not.
 *
 * Optional — only operations that carry an allocation breakdown show it. It
 * is the same summary before and after a change, so when the RS-1024 demo
 * recipient becomes unavailable and the allocation is recalculated, this
 * panel shows the updated split with what changed for each recipient (see
 * services/reallocationDemoService.js).
 */
function AllocationSummary({ allocation }) {
  const { title, badge, rows, total, placed, unplaced, unit, footnote } = allocation;

  return (
    <section
      aria-label={title}
      className="space-y-3 border-t border-line pt-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">{title}</h3>
        {badge && (
          <Badge tone={badge.tone} size="sm">
            {badge.label}
          </Badge>
        )}
      </div>

      <ul className="divide-y divide-line overflow-hidden rounded-control border border-line">
        {rows.map((row) => (
          <li
            key={row.id}
            className={cn(
              'flex items-center justify-between gap-3 px-3.5 py-2.5',
              row.tone === 'unavailable' && 'bg-critical/5',
            )}
          >
            <div className="min-w-0">
              <p
                className={cn(
                  'truncate text-xs font-medium',
                  row.tone === 'unavailable' ? 'text-muted' : 'text-content',
                )}
              >
                {row.name}
              </p>
              {row.note && (
                <p
                  className={cn(
                    'mt-0.5 text-[11px]',
                    row.tone === 'unavailable' ? 'text-critical' : 'text-faint',
                  )}
                >
                  {row.note}
                </p>
              )}
            </div>
            <span
              className={cn(
                'tabular shrink-0 text-xs font-semibold',
                row.tone === 'unavailable' ? 'text-faint line-through' : 'text-content',
              )}
            >
              {row.quantity} {row.unit ?? unit}
            </span>
          </li>
        ))}
      </ul>

      <dl className="grid grid-cols-3 gap-2 text-center">
        <TotalCell label="Total" value={total} unit={unit} />
        <TotalCell label="With a recipient" value={placed} unit={unit} />
        <TotalCell label="No recipient" value={unplaced} unit={unit} urgent={unplaced > 0} />
      </dl>

      {footnote && <p className="text-[11px] leading-relaxed text-faint">{footnote}</p>}
    </section>
  );
}

function TotalCell({ label, value, unit, urgent = false }) {
  return (
    <div
      className={cn(
        'min-w-0 rounded-control border px-2 py-2',
        urgent ? 'border-urgent/30 bg-urgent/5' : 'border-line bg-surface-2',
      )}
    >
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd
        className={cn(
          'tabular mt-0.5 text-sm font-semibold',
          urgent ? 'text-urgent' : 'text-content',
        )}
      >
        {value} <span className="text-[11px] font-medium text-muted">{unit}</span>
      </dd>
    </div>
  );
}

function DetailRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-2.5 rounded-control border border-line px-3 py-2.5">
      <span className="mt-0.5 shrink-0 text-brand-400">
        {Icon && <Icon size={15} strokeWidth={1.75} />}
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</p>
        <p className="truncate text-xs font-semibold text-content">{value}</p>
      </div>
    </div>
  );
}
