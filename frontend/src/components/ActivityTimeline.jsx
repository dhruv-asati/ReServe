import { ACTIVITY_STAGE_ICONS } from '@/utils/icons';
import { StatusBadge } from '@/components/ui';

/**
 * ActivityTimeline — compact vertical timeline of rescue lifecycle events:
 * created → analyzed → matched → assigned → pickup → completed. Generic
 * over `items`, so it can back any activity feed later, not just the
 * dashboard's recent-activity section.
 */
export default function ActivityTimeline({ items = [] }) {
  return (
    <ol className="space-y-0">
      {items.map((item, index) => {
        const Icon = ACTIVITY_STAGE_ICONS[item.stage];
        const isLast = index === items.length - 1;

        return (
          <li key={item.id} className="relative flex gap-3 pb-5 last:pb-0">
            {!isLast && (
              <span className="absolute left-[15px] top-8 h-[calc(100%-1.75rem)] w-px bg-line" />
            )}

            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-3 text-brand-400 ring-1 ring-inset ring-line">
              {Icon && <Icon size={14} strokeWidth={1.75} />}
            </span>

            <div className="min-w-0 flex-1 pt-1">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                  <p className="truncate text-xs font-semibold text-content">{item.title}</p>
                  {item.status && <StatusBadge status={item.status} size="sm" />}
                </div>
                <span className="shrink-0 text-[11px] text-faint">{item.time}</span>
              </div>
              <p className="mt-0.5 truncate text-xs text-muted">{item.description}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
