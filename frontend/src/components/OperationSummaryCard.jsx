import { Store, Users, Truck, MapPin, Clock, CalendarClock } from 'lucide-react';

import { Card, StatusBadge, Badge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';

/**
 * OperationSummaryCard — the headline panel of the Operations Control
 * Center: what's moving, who's involved, and where it stands right now.
 *
 * Frontend only: everything passed in via `operation` is demo/mock data
 * (see data/operationDetail.js) — the ETA is an illustrative estimate, not
 * a live GPS-calculated arrival time, and the rescue partner is a demo
 * label, not a real-world dispatch assignment.
 */
export default function OperationSummaryCard({ operation }) {
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
  } = operation;

  const Icon = RESOURCE_ICONS[resourceType];

  return (
    <Card>
      <Card.Header
        icon={Icon}
        title={`${quantity} ${resource}`}
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
          <DetailRow icon={Users} label="Recipient" value={recipient} />
          <DetailRow icon={MapPin} label="Location" value={location} />
          <DetailRow icon={Truck} label="Rescue Partner" value={`${partner} (demo)`} />
        </div>

        <div className="grid grid-cols-1 gap-3 border-t border-line pt-4 sm:grid-cols-2">
          <div className="rounded-control border border-line bg-surface-2 px-3.5 py-3">
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
              <Clock size={12} strokeWidth={1.75} />
              ETA (illustrative)
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
            <p className="mt-1 text-[11px] text-faint">Demo deadline for this illustrative rescue.</p>
          </div>
        </div>
      </Card.Body>
      <Card.Footer>
        <Badge tone="neutral" size="sm">
          Demo information — not a live operation
        </Badge>
      </Card.Footer>
    </Card>
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
