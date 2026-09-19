import { cn } from '@/utils/cn';

/**
 * Tabs — segmented control for switching between views of the same data
 * (e.g. Incoming / Outgoing / Completed requests).
 *
 * Controlled component: the parent owns the active tab.
 *
 *   <Tabs
 *     tabs={[{ key: 'incoming', label: 'Incoming', count: 4 }, …]}
 *     value={activeTab}
 *     onChange={setActiveTab}
 *   />
 */
export default function Tabs({ tabs, value, onChange, className }) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex items-center gap-1 rounded-control border border-line bg-surface-2 p-1',
        className,
      )}
    >
      {tabs.map(({ key, label, count }) => {
        const active = key === value;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(key)}
            className={cn(
              'inline-flex h-8 items-center gap-2 rounded-[calc(var(--radius-control)-2px)] px-3.5 text-sm font-medium tracking-tight',
              'transition-colors duration-150',
              active
                ? 'bg-brand-600 text-white'
                : 'text-muted hover:bg-surface-3 hover:text-content',
            )}
          >
            {label}
            {count !== undefined && (
              <span
                className={cn(
                  'inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-full px-1 text-[10px] font-semibold tabular',
                  active ? 'bg-white/20 text-white' : 'bg-surface-3 text-faint',
                )}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
