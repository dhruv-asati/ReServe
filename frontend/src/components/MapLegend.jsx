import { NETWORK_ROLE_META } from '@/utils/theme';
import { NETWORK_ROLE_ICONS } from '@/utils/icons';
import { cn } from '@/utils/cn';

/**
 * MapLegend — marker key for the four network roles shown on MapPreview.
 * Reads straight from NETWORK_ROLE_META / NETWORK_ROLE_ICONS, so a new role
 * only needs adding there and the markers and legend both pick it up.
 */
export default function MapLegend({ className }) {
  return (
    <div className={cn('flex flex-wrap items-center gap-x-4 gap-y-2', className)}>
      {Object.entries(NETWORK_ROLE_META).map(([role, meta]) => {
        const Icon = NETWORK_ROLE_ICONS[role];
        return (
          <span key={role} className="flex items-center gap-1.5 text-xs text-muted">
            <span
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full ring-1 ring-inset ring-black/10"
              style={{ backgroundColor: meta.color }}
            >
              {Icon ? <Icon size={11} strokeWidth={2.25} color="#0b0f16" /> : null}
            </span>
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}
