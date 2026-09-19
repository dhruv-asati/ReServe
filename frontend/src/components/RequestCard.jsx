import { Eye } from 'lucide-react';

import { Button, Card, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';

/**
 * RequestCard — mobile / tablet view of one rescue request.
 *
 * Used on the Rescue Requests page below the `xl` breakpoint, where the
 * desktop RequestsTable would not fit without scrolling sideways.
 *
 * Shows: Request ID · Status (header) · Resource · Quantity ·
 * Provider / Recipient · Location · Deadline (body) · View Details (footer).
 * Values wrap instead of truncating so nothing is cut off on narrow screens.
 */
export default function RequestCard({ request, onViewDetails }) {
  const { id, resource, resourceType, quantity, provider, recipient, location, deadline, status } =
    request;
  const Icon = RESOURCE_ICONS[resourceType];
  const typeMeta = RESOURCE_META[resourceType];

  return (
    <Card className="flex h-full flex-col">
      <Card.Header
        icon={Icon}
        title={id}
        subtitle={typeMeta?.label ?? resourceType}
        action={<StatusBadge status={status} size="sm" />}
      />

      <Card.Body className="flex-1">
        <dl className="space-y-3 text-sm">
          <Field label="Resource">
            <span className="font-medium text-content">{resource}</span>
          </Field>
          <Field label="Quantity">
            <span className="tabular text-content">{quantity}</span>
          </Field>
          <Field label="Provider">{provider}</Field>
          <Field label="Recipient">{recipient}</Field>
          <Field label="Location">{location}</Field>
          <Field label="Deadline">
            <span className="text-content">{deadline}</span>
          </Field>
        </dl>
      </Card.Body>

      <Card.Footer>
        <Button
          variant="outline"
          size="sm"
          icon={Eye}
          className="w-full justify-center"
          onClick={() => onViewDetails?.(request)}
          aria-label={`View details for ${id}`}
        >
          View Details
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
