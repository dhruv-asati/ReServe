import { Clock } from 'lucide-react';

import { Card, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';

/**
 * OperationCard — one active rescue operation.
 * Built on the shared Card/StatusBadge primitives so it matches every other
 * panel in the app; resourceType picks the icon, status picks the badge.
 */
export default function OperationCard({ operation }) {
  const { id, resource, resourceType, quantity, provider, recipient, status, eta } = operation;
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
        <div className="flex w-full items-center justify-between">
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <Clock size={13} strokeWidth={1.75} />
            ETA
          </span>
          <span className="text-xs font-medium text-content">{eta}</span>
        </div>
      </Card.Footer>
    </Card>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 text-xs">
      <span className="shrink-0 text-faint">{label}</span>
      {/* Wraps rather than truncates: a re-allocated operation can list several recipients. */}
      <span className="min-w-0 break-words text-right font-medium text-content">{value}</span>
    </div>
  );
}
