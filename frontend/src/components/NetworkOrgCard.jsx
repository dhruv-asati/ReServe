import { MapPin, ShieldCheck } from 'lucide-react';

import { Badge, Button, Card } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';
import {
  AVAILABILITY_META,
  ORG_TYPE_META,
  VERIFICATION_META,
  locationLabel,
  workloadPercent,
  workloadTone,
} from '@/utils/networkDirectory';
import { cn } from '@/utils/cn';

/**
 * NetworkOrgCard — one organization in the Network Directory.
 *
 * Shows, top to bottom: name, category and location (header, with the
 * availability badge) · what it does · the resource types it handles ·
 * capacity · workload with a fill bar · verification status (footer).
 *
 * Fields that do not apply to a kind of organization are simply left out
 * rather than shown empty: a shelter carries no rescue assignments, so it has
 * no workload bar, and a rescue hub is run by the network itself, so it has
 * no verification status. Values wrap instead of truncating, so a long
 * organization name stays readable on a narrow screen.
 *
 * Selection: when `onSelect` is given the whole card is clickable, and the
 * footer carries a real "Show on map" button (aria-pressed) for keyboard and
 * screen-reader users. The page keeps one `selected` organization shared with
 * the demo map, so choosing a card highlights its marker and vice versa; the
 * selected card gets a ring and `aria-current`. The button has no handler of
 * its own — its click bubbles to the card, so `onSelect` fires exactly once.
 *
 * DEMO DATA: every organization is invented for this walkthrough (see
 * data/networkDirectory.js). The availability and verification labels are
 * illustrative demo values — they do not mean any real organization is
 * available, was checked or was contacted, and the card says so.
 */
export default function NetworkOrgCard({ organization, selected = false, onSelect }) {
  const {
    id,
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
  const tone = workloadTone(percent);

  return (
    <Card
      id={`org-card-${id}`}
      interactive={Boolean(onSelect)}
      aria-current={selected ? 'true' : undefined}
      onClick={onSelect ? () => onSelect(id) : undefined}
      className={cn(
        'flex h-full scroll-mt-24 flex-col',
        selected && 'border-brand-500 bg-surface-2 ring-2 ring-brand-400/60',
      )}
    >
      <Card.Header icon={category?.icon} title={name} subtitle={category?.singular} />

      <Card.Body className="flex-1 space-y-4">
        <p className="flex items-start gap-1.5 text-xs text-muted">
          <MapPin size={13} strokeWidth={1.75} className="mt-0.5 shrink-0 text-brand-400" />
          <span className="break-words">{locationLabel(organization)}</span>
        </p>

        {description && <p className="text-xs leading-relaxed text-muted">{description}</p>}

        {available && (
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
              Availability (demo)
            </p>
            <div className="mt-1.5">
              <Badge tone={available.tone} dot size="sm">
                {available.label}
              </Badge>
            </div>
          </div>
        )}

        {resourceTypes.length > 0 && (
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
              Resource types
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {resourceTypes.map((resourceType) => {
                const meta = RESOURCE_META[resourceType];
                const Icon = RESOURCE_ICONS[resourceType];
                return (
                  <Badge key={resourceType} tone={resourceType} icon={Icon} size="sm">
                    {meta?.label ?? resourceType}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {capacity && (
          <div className="rounded-control border border-line bg-surface-2 px-3 py-2.5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
              {capacity.label}
            </p>
            <p className="mt-0.5 text-sm font-semibold text-content">
              <span className="tabular">{capacity.value}</span>{' '}
              <span className="text-[11px] font-medium text-muted">{capacity.unit}</span>
            </p>
          </div>
        )}

        {workload && (
          <div>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
                {workload.label}
              </p>
              <p className="tabular text-xs font-semibold text-content">
                {workload.active} of {workload.max}
              </p>
            </div>
            {percent !== null && (
              <div
                className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-3"
                role="progressbar"
                aria-label={`${workload.label}: ${workload.active} of ${workload.max}`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
              >
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-300 ease-soft',
                    tone === 'critical' && 'bg-critical',
                    tone === 'urgent' && 'bg-urgent',
                    tone === 'default' && 'bg-brand-500',
                  )}
                  style={{ width: `${percent}%` }}
                />
              </div>
            )}
          </div>
        )}
      </Card.Body>

      <Card.Footer>
        <div className="w-full space-y-3">
          {verified ? (
            <div className="flex min-w-0 items-start gap-2">
              <ShieldCheck size={14} strokeWidth={1.75} className="mt-0.5 shrink-0 text-faint" />
              <div className="min-w-0">
                <Badge tone={verified.tone} size="sm">
                  {verified.label}
                </Badge>
                <p className="mt-1 break-words text-[11px] text-faint">{verified.note}</p>
              </div>
            </div>
          ) : (
            <p className="text-[11px] text-faint">
              Operated by the rescue network in this demo — no verification status applies.
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
            <p className="min-w-0 text-[11px] text-faint">
              Demo organization · approximate demo pin
            </p>
            {onSelect && (
              <Button
                variant={selected ? 'primary' : 'outline'}
                size="sm"
                icon={MapPin}
                aria-pressed={selected}
                aria-label={`Show ${name} on the map`}
              >
                {selected ? 'Shown on map' : 'Show on map'}
              </Button>
            )}
          </div>
        </div>
      </Card.Footer>
    </Card>
  );
}
