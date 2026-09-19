import { MapPin, CalendarClock } from 'lucide-react';

import { Card, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';

/**
 * RequestCard — one rescue request row on the Rescue Requests page.
 * Same Card/StatusBadge primitives as OperationCard, extended with the
 * location and deadline fields this page needs.
 */
export default function RequestCard({ request }) {
  const { id, resource, resourceType, quantity, provider, recipient, location, deadline, status } =
    request;
  const Icon = RESOURCE_ICONS[resourceType];

  return (
    <Card>
      <Card.Header
        icon={Icon}
        title={resource}
        subtitle={id}
        action={<StatusBadge status={status} size="sm" />}
      />
      <Card.Body className="space-y-2.5">
        <Row label="Quantity" value={quantity} />
        <Row label="Provider" value={provider} />
        <Row label="Recipient" value={recipient} />
      </Card.Body>
      <Card.Footer>
        <div className="flex w-full items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted">
            <MapPin size={13} strokeWidth={1.75} className="shrink-0" />
            <span className="truncate">{location}</span>
          </span>
          <span className="flex shrink-0 items-center gap-1.5 text-xs font-medium text-content">
            <CalendarClock size={13} strokeWidth={1.75} />
            {deadline}
          </span>
        </div>
      </Card.Footer>
    </Card>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="shrink-0 text-faint">{label}</span>
      <span className="truncate font-medium text-content">{value}</span>
    </div>
  );
}
