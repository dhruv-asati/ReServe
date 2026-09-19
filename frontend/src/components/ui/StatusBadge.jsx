import Badge from './Badge';
import { STATUS_META } from '@/utils/theme';
import { cn } from '@/utils/cn';

/**
 * Badge bound to the operational status vocabulary in src/utils/theme.js.
 * Live statuses (analyzing, matching, pickup in progress, reallocating,
 * in transit) get a pulsing dot so an operator can spot movement without
 * reading every row.
 */
const LIVE = new Set([
  'analyzing',
  'matching',
  'pickup_in_progress',
  'reallocating',
  'in_transit',
  'dispatched',
]);

export default function StatusBadge({ status, size = 'md', className, ...props }) {
  const meta = STATUS_META[status];

  if (!meta) {
    return (
      <Badge tone="neutral" size={size} className={className} {...props}>
        {status ?? 'Unknown'}
      </Badge>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium tracking-tight ring-1 ring-inset whitespace-nowrap',
        size === 'sm' ? 'h-5 gap-1 px-1.5 text-[10px]' : 'h-6 gap-1.5 px-2 text-xs',
        meta.className,
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full bg-current',
          LIVE.has(status) && 'animate-pulse-soft',
        )}
      />
      {meta.label}
    </span>
  );
}
