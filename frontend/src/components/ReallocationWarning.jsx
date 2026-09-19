import { AlertTriangle } from 'lucide-react';

import { cn } from '@/utils/cn';

/**
 * ReallocationWarning — the "original allocation is no longer feasible"
 * notice for the RS-1024 recipient-unavailable demo.
 *
 * `variant="full"` carries the title and the complete explanation (used in
 * the Operations allocation card). `variant="compact"` is a one-line notice
 * for the other pages that show RS-1024 (Matching, Dashboard); its wording
 * comes from getReallocationView so every page says the same thing.
 *
 * `role` is "alert" only where the warning appears as the direct result of a
 * click (so it is announced once); on pages that merely load with the
 * scenario already active it stays a polite "status". `children` is an
 * optional action row (e.g. a link to the operation). Demo-only content.
 */
export default function ReallocationWarning({
  warning,
  variant = 'full',
  role = 'status',
  className,
  children,
  ref,
}) {
  const compact = variant === 'compact';

  return (
    <div
      ref={ref}
      tabIndex={ref ? -1 : undefined}
      role={role}
      className={cn(
        'rounded-control border border-urgent/25 bg-urgent/10 outline-none focus-visible:ring-2 focus-visible:ring-urgent/50',
        compact ? 'px-3.5 py-2.5' : 'px-4 py-3.5',
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        <AlertTriangle size={compact ? 16 : 18} strokeWidth={2} className="mt-0.5 shrink-0 text-urgent" />
        <div className="min-w-0 flex-1 space-y-1">
          {compact ? (
            <p className="text-sm font-medium text-urgent">{warning.short}</p>
          ) : (
            <>
              <p className="text-sm font-semibold text-urgent">{warning.title}</p>
              <p className="text-xs leading-relaxed text-muted">{warning.message}</p>
            </>
          )}
          {children && <div className="pt-1.5">{children}</div>}
        </div>
      </div>
    </div>
  );
}
