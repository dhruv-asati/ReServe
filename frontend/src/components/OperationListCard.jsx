import { Eye } from 'lucide-react';

import { Button, Card, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';
import { formatQuantity, partnerCell, recipientCell } from '@/utils/operationFormat';
import { cn } from '@/utils/cn';

/**
 * OperationListCard — mobile / tablet view of one rescue operation in the
 * Operations list.
 *
 * Used below the `xl` breakpoint, where the desktop OperationsTable would not
 * fit without scrolling sideways. Shows: Operation ID and status (header) ·
 * Resource · Quantity · Provider · Recipient · Rescue Partner · ETA · Deadline
 * (body) · a View details button (footer). Values wrap instead of truncating.
 *
 * The whole card is selectable: a tap anywhere on it calls
 * `onSelect(operation)`. The footer button is the keyboard and screen-reader
 * entry point — its click bubbles up to the card. The card matching the
 * selected operation is highlighted. Frontend only — mock data.
 */
export default function OperationListCard({ operation, selected = false, onSelect }) {
  const { id, resource, resourceType, provider, status, eta, deadline } = operation;
  const Icon = RESOURCE_ICONS[resourceType];
  const typeLabel = RESOURCE_META[resourceType]?.label ?? resourceType;
  const recipient = recipientCell(operation);
  const partner = partnerCell(operation);

  return (
    <Card
      interactive
      onClick={() => onSelect(operation)}
      className={cn(
        'flex h-full flex-col',
        selected && 'border-brand-500/60 bg-surface-2 hover:border-brand-500/60',
      )}
    >
      <Card.Header
        icon={Icon}
        title={id}
        subtitle={typeLabel}
        action={<StatusBadge status={status} size="sm" />}
      />

      <Card.Body className="flex-1">
        <dl className="space-y-3 text-sm">
          <Field label="Resource">
            <span className="font-medium text-content">{resource}</span>
          </Field>
          <Field label="Quantity">
            <span className="tabular text-content">{formatQuantity(operation)}</span>
          </Field>
          <Field label="Provider">{provider}</Field>
          <Field label="Recipient">
            <span className={recipient.empty ? 'text-faint' : undefined}>{recipient.text}</span>
          </Field>
          <Field label="Rescue Partner">
            <span className={partner.empty ? 'text-faint' : undefined}>{partner.text}</span>
          </Field>
          <Field label="ETA">
            <span className="text-content">{eta}</span>
          </Field>
          <Field label="Deadline">
            <span className="text-content">{deadline}</span>
          </Field>
        </dl>
      </Card.Body>

      <Card.Footer>
        <Button
          variant={selected ? 'secondary' : 'outline'}
          size="sm"
          icon={Eye}
          className="w-full justify-center"
          aria-label={`View details for ${id}`}
          aria-current={selected ? 'true' : undefined}
        >
          {selected ? 'Viewing details' : 'View details'}
        </Button>
      </Card.Footer>
    </Card>
  );
}

function Field({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="shrink-0 text-xs text-faint">{label}</dt>
      <dd className="min-w-0 break-words text-right text-muted">{children}</dd>
    </div>
  );
}
