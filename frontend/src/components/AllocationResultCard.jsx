import { useId, useState } from 'react';
import { Building2, CheckCircle2, ChevronDown, CircleHelp, MapPin } from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import StatusCheckBadge from '@/components/StatusCheckBadge';
import { buildMatchReasons } from '@/utils/matchReasons';
import { cn } from '@/utils/cn';

/**
 * AllocationResultCard — one recipient's proposed share of the selected
 * resource. DEMO / PROPOSED DATA only: `allocatedQuantity` is a hardcoded
 * illustrative split (see src/data/matching.js), not the output of an
 * optimization routine, and carries no confidence or scoring value. No
 * confirmation action is attached here — this is a preview, not a commit.
 * Once the plan is confirmed on the Matching page (`confirmed`), the card
 * only relabels itself as a confirmed *demo* allocation.
 *
 * Each card also carries a collapsible "Why This Match?" section. Its
 * reasons come straight from the mock candidate/resource fields (see
 * utils/matchReasons.js) and only appear when the data supports them — no
 * scores, percentages or confidence values.
 */
export default function AllocationResultCard({ allocation, resource, confirmed = false }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const reasons = buildMatchReasons(allocation, resource);

  const {
    name,
    allocatedQuantity,
    unit,
    distanceKm,
    capacity,
    capacityUnit,
    availability,
    eligibility,
    pickupFeasibility,
  } = allocation;

  const capacityCompatible =
    capacity === null || capacity === undefined ? null : capacity >= allocatedQuantity ? 'yes' : 'no';

  return (
    <Card className={cn('border-l-2', confirmed ? 'border-l-success' : 'border-l-brand-500')}>
      <Card.Header
        icon={Building2}
        title={name}
        subtitle={confirmed ? 'Confirmed allocation (demo)' : 'Proposed allocation'}
        action={
          <Badge tone={confirmed ? 'success' : 'brand'} size="sm">
            {confirmed ? 'Confirmed (Demo)' : 'Proposed'}
          </Badge>
        }
      />
      <Card.Body className="space-y-3.5">
        <div className="rounded-control border border-line bg-surface-2 px-3.5 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
            Allocated quantity
          </p>
          <p className="mt-1 text-lg font-semibold tracking-tight text-content">
            {allocatedQuantity} {unit}
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-muted">
          <MapPin size={13} strokeWidth={1.75} />
          <span className="font-medium text-content">{distanceKm} km away</span>
        </div>

        <div className="space-y-2 border-t border-line pt-3">
          <StatusCheckBadge label="Capacity compatibility" value={capacityCompatible} />
          <StatusCheckBadge label="Availability" value={availability} />
          <StatusCheckBadge label="Eligibility" value={eligibility} />
          <StatusCheckBadge label="Pickup feasibility" value={pickupFeasibility} />
        </div>

        {/* ---------- Why This Match? ---------- */}
        <div className="border-t border-line pt-3">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls={panelId}
            className="flex w-full items-center justify-between gap-2 rounded-control text-left text-xs font-medium text-brand-400 transition-colors duration-150 hover:text-brand-300"
          >
            <span className="flex items-center gap-1.5">
              <CircleHelp size={14} strokeWidth={1.75} />
              Why This Match?
            </span>
            <ChevronDown
              size={15}
              strokeWidth={1.75}
              className={cn('shrink-0 transition-transform duration-200', open && 'rotate-180')}
            />
          </button>

          {open && (
            <div id={panelId} className="mt-3 space-y-3">
              {reasons.length > 0 ? (
                <ul className="space-y-2.5">
                  {reasons.map((reason) => (
                    <li key={reason.key} className="flex items-start gap-2">
                      <CheckCircle2
                        size={14}
                        strokeWidth={2}
                        className="mt-0.5 shrink-0 text-success"
                      />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-content">{reason.label}</p>
                        <p className="mt-0.5 break-words text-[11px] text-muted">{reason.detail}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[11px] text-muted">
                  No supporting checks are available in the demo data for this recipient.
                </p>
              )}
              <p className="text-[11px] text-faint">
                Read directly from the demo data — no AI score or confidence value is used.
              </p>
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
}
