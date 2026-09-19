import { CheckCircle2, XCircle, MinusCircle } from 'lucide-react';

import { Badge } from '@/components/ui';

/**
 * One yes/no/unknown check row (availability, eligibility, pickup
 * feasibility, capacity compatibility). `null` means "not evaluated" —
 * used where a later check wouldn't run (e.g. an unavailable candidate).
 *
 * Shared by MatchCandidateCard and AllocationResultCard so both mock
 * candidate views read the same status vocabulary.
 */
export default function StatusCheckBadge({ label, value }) {
  const tone = value === 'yes' ? 'success' : value === 'no' ? 'critical' : 'neutral';
  const Icon = value === 'yes' ? CheckCircle2 : value === 'no' ? XCircle : MinusCircle;
  const text = value === 'yes' ? 'Yes' : value === 'no' ? 'No' : 'Not evaluated';

  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</span>
      <Badge tone={tone} icon={Icon} size="sm">
        {text}
      </Badge>
    </div>
  );
}
