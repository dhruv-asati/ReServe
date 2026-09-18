import { cn } from '@/utils/cn';

/**
 * Loading placeholders.
 *
 *   <LoadingState />                     → centred spinner block
 *   <LoadingState variant="skeleton" />  → shimmering rows matching list layout
 *   <Skeleton className="h-4 w-24" />    → inline skeleton for one element
 */
export function Skeleton({ className }) {
  return <div className={cn('animate-pulse-soft rounded bg-surface-3', className)} />;
}

export default function LoadingState({
  variant = 'spinner',
  rows = 3,
  label = 'Loading…',
  className,
}) {
  if (variant === 'skeleton') {
    return (
      <div className={cn('space-y-3', className)} role="status" aria-label={label}>
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="panel flex items-center gap-4 p-4">
            <Skeleton className="h-9 w-9 shrink-0 rounded-control" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-3.5 w-2/5" />
              <Skeleton className="h-3 w-3/5" />
            </div>
            <Skeleton className="h-5 w-16 shrink-0 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn('flex flex-col items-center justify-center gap-3 py-14', className)}
      role="status"
      aria-label={label}
    >
      <span className="relative flex h-8 w-8 items-center justify-center">
        <span className="absolute inset-0 rounded-full border-2 border-line" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-brand-400" />
      </span>
      <p className="text-xs text-muted">{label}</p>
    </div>
  );
}
