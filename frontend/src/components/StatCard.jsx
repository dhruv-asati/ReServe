import { Card, Skeleton } from '@/components/ui';
import { cn } from '@/utils/cn';

/**
 * StatCard — a single overview metric: label, big number, optional unit and
 * delta line, with a tone-accented icon chip. Built on the shared Card
 * primitive so it inherits the app's panel styling everywhere it's used.
 *
 * Tones match Badge's semantic set (brand/active/urgent/success/etc.) —
 * pick by meaning, not by how it looks.
 */
const TONES = {
  neutral: 'bg-surface-3 text-muted',
  brand: 'bg-brand-500/10 text-brand-400',
  critical: 'bg-critical/10 text-critical',
  urgent: 'bg-urgent/10 text-urgent',
  active: 'bg-active/10 text-active',
  success: 'bg-success/10 text-success',
  predicted: 'bg-predicted/10 text-predicted',
};

export default function StatCard({
  label,
  value,
  unit,
  delta,
  icon: Icon,
  tone = 'brand',
  loading = false,
  className,
}) {
  return (
    <Card className={cn('p-4 sm:p-5', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium tracking-wide text-muted">{label}</p>

          {loading ? (
            <Skeleton className="mt-2 h-7 w-20" />
          ) : (
            <p className="mt-1.5 flex items-baseline gap-1 text-2xl font-bold tracking-tight text-content">
              {value}
              {unit && <span className="text-sm font-medium text-muted">{unit}</span>}
            </p>
          )}
        </div>

        {Icon && (
          <span
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-control',
              TONES[tone] ?? TONES.brand,
            )}
          >
            <Icon size={17} strokeWidth={1.75} />
          </span>
        )}
      </div>

      {loading ? (
        <Skeleton className="mt-3 h-3 w-28" />
      ) : (
        delta && <p className="mt-3 truncate text-xs text-faint">{delta}</p>
      )}
    </Card>
  );
}
