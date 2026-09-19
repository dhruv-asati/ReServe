import { Building2, MapPin, PackageCheck, Truck } from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import StatusCheckBadge from '@/components/StatusCheckBadge';
import { cn } from '@/utils/cn';

/**
 * MatchCandidateCard — a single candidate recipient considered for the
 * selected resource. DEMO DATA only: hardcoded fields, no scoring, no
 * ranking, no live organization lookup.
 *
 * `selectable` (derived from availability + pickup feasibility) drives a
 * dimmed, clearly-marked "cannot be selected" treatment so unavailable
 * candidates read distinctly from eligible ones at a glance — no
 * allocation decision is made here either way.
 */
export default function MatchCandidateCard({ candidate }) {
  const {
    name,
    need,
    needLabel = 'Resource need',
    unit,
    distanceKm,
    capacity,
    capacityUnit,
    availability,
    eligibility,
    pickupFeasibility,
    selectable,
    unselectableReason,
  } = candidate;

  return (
    <Card
      className={cn(
        selectable
          ? 'border-l-2 border-l-success'
          : 'border-l-2 border-l-critical opacity-80',
      )}
    >
      <Card.Header
        icon={Building2}
        title={name}
        subtitle={`${needLabel}: ${need} ${unit}`}
        action={
          <Badge tone={selectable ? 'success' : 'critical'} size="sm">
            {selectable ? 'Can be selected' : 'Cannot be selected'}
          </Badge>
        }
      />
      <Card.Body className="space-y-3.5">
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-muted">
            <MapPin size={13} strokeWidth={1.75} />
            <span className="font-medium text-content">{distanceKm} km away</span>
          </div>
          <div className="flex items-center gap-1.5 text-muted">
            <PackageCheck size={13} strokeWidth={1.75} />
            <span className="font-medium text-content">
              {capacity === null || capacity === undefined
                ? 'Capacity unknown'
                : `${capacity} ${capacityUnit} capacity`}
            </span>
          </div>
        </div>

        <div className="space-y-2 border-t border-line pt-3">
          <StatusCheckBadge label="Availability" value={availability} />
          <StatusCheckBadge label="Eligibility" value={eligibility} />
          <StatusCheckBadge label="Pickup feasibility" value={pickupFeasibility} />
        </div>

        {!selectable && unselectableReason && (
          <p className="flex items-start gap-1.5 rounded-control bg-critical/5 px-2.5 py-2 text-[11px] text-critical">
            <Truck size={13} strokeWidth={1.75} className="mt-0.5 shrink-0" />
            {unselectableReason}
          </p>
        )}
      </Card.Body>
    </Card>
  );
}
