import { Clock } from 'lucide-react';

import { Card, Badge, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { URGENCY_META } from '@/utils/theme';
import { cn } from '@/utils/cn';

/** Urgency → Badge tone. Matches the colour weight in URGENCY_META. */
const URGENCY_TONE = {
  critical: 'critical',
  high: 'urgent',
  medium: 'active',
  low: 'neutral',
};

/** Urgency → left accent border, so the most time-sensitive cards read first. */
const URGENCY_BORDER = {
  critical: 'border-l-2 border-l-critical',
  high: 'border-l-2 border-l-urgent',
  medium: 'border-l-2 border-l-active',
  low: 'border-l-2 border-l-line-strong',
};

/**
 * AtRiskCard — a single resource approaching its rescue deadline.
 * Built on Card/Badge/StatusBadge so it matches OperationCard and the rest
 * of the app; urgency drives the accent border and badge tone.
 */
export default function AtRiskCard({ resource }) {
  const { resource: name, resourceType, quantity, deadline, urgency, status } = resource;
  const Icon = RESOURCE_ICONS[resourceType];
  const urgencyMeta = URGENCY_META[urgency];

  return (
    <Card className={cn(URGENCY_BORDER[urgency])}>
      <Card.Header
        icon={Icon}
        title={name}
        subtitle={quantity}
        action={
          <Badge tone={URGENCY_TONE[urgency] ?? 'neutral'} dot size="sm">
            {urgencyMeta?.label ?? 'Unknown'}
          </Badge>
        }
      />
      <Card.Body className="space-y-2.5">
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <Clock size={13} strokeWidth={1.75} />
          <span className="font-medium text-content">{deadline}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-faint">Current status</span>
          <StatusBadge status={status} size="sm" />
        </div>
      </Card.Body>
    </Card>
  );
}
