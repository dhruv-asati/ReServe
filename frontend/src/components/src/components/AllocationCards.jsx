import { Users, FlaskConical } from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import { CHART_COLORS } from '@/utils/theme';

function StatBlock({ label, value }) {
  return (
    <div className="rounded-control border border-line bg-surface-2 px-3.5 py-3">
      <p className="text-[11px] uppercase tracking-wide text-faint">{label}</p>
      <p className="mt-1 text-sm font-semibold text-content">{value}</p>
    </div>
  );
}

/**
 * AllocationCards — visual breakdown of how a resource's quantity is split
 * across recipients: a proportional stacked bar plus one small card per
 * recipient, followed by allocated / remaining / deadline stats.
 *
 * Frontend only: `allocations` is mock data (see data/resources.js). Kept
 * as a standalone component since the shape — a total quantity split across
 * named recipients — is reusable anywhere else an allocation needs showing.
 */
export default function AllocationCards({
  allocations = [],
  totalQuantity = 0,
  unitLabel = '',
  deadlineLabel,
}) {
  const allocatedQuantity = allocations.reduce((sum, item) => sum + item.quantity, 0);
  const remainingQuantity = Math.max(totalQuantity - allocatedQuantity, 0);
  const barTotal = Math.max(totalQuantity, allocatedQuantity, 1);

  return (
    <Card>
      <Card.Header
        icon={Users}
        title="Current Allocation"
        subtitle={`${totalQuantity} ${unitLabel} split across recipients.`}
        action={
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO / MOCK DATA
          </Badge>
        }
      />
      <Card.Body className="space-y-5">
        {/* ---------- Stacked allocation bar ---------- */}
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface-3">
          {allocations.map((item, index) => (
            <span
              key={item.recipient}
              className="h-full first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${(item.quantity / barTotal) * 100}%`,
                backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
              }}
              title={`${item.recipient}: ${item.quantity} ${unitLabel}`}
            />
          ))}
          {remainingQuantity > 0 && (
            <span
              className="h-full bg-surface-3 last:rounded-r-full"
              style={{ width: `${(remainingQuantity / barTotal) * 100}%` }}
              title={`Unallocated: ${remainingQuantity} ${unitLabel}`}
            />
          )}
        </div>

        {/* ---------- Recipient cards ---------- */}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {allocations.map((item, index) => {
            const percent = totalQuantity > 0 ? Math.round((item.quantity / totalQuantity) * 100) : 0;
            return (
              <div
                key={item.recipient}
                className="flex items-center justify-between gap-3 rounded-control border border-line bg-surface-2 px-3.5 py-2.5"
              >
                <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-content">
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                  />
                  <span className="truncate">{item.recipient}</span>
                </span>
                <span className="shrink-0 text-right text-xs text-faint">
                  <span className="font-semibold text-content">{item.quantity}</span> {unitLabel}
                  <span className="ml-1">({percent}%)</span>
                </span>
              </div>
            );
          })}
          {remainingQuantity > 0 && (
            <div className="flex items-center justify-between gap-3 rounded-control border border-dashed border-line px-3.5 py-2.5">
              <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-faint">
                <span className="h-2 w-2 shrink-0 rounded-full bg-surface-3" />
                Unallocated
              </span>
              <span className="shrink-0 text-right text-xs text-faint">
                <span className="font-semibold text-content">{remainingQuantity}</span> {unitLabel}
              </span>
            </div>
          )}
        </div>

        {/* ---------- Stats ---------- */}
        <div className="grid grid-cols-1 gap-3 border-t border-line pt-4 sm:grid-cols-3">
          <StatBlock label="Allocated quantity" value={`${allocatedQuantity} ${unitLabel}`} />
          <StatBlock label="Remaining quantity" value={`${remainingQuantity} ${unitLabel}`} />
          <StatBlock label="Rescue deadline" value={deadlineLabel || 'Not set'} />
        </div>
      </Card.Body>
    </Card>
  );
}
