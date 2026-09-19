import { Inbox } from 'lucide-react';
import { cn } from '@/utils/cn';

/**
 * Shown when a query succeeded but returned nothing. Always offers the next
 * action where one exists — an empty operations board should still let the
 * operator create a rescue.
 */
export default function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  description,
  action,
  className,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-14 text-center',
        className,
      )}
    >
      <span className="rounded-full border border-line bg-surface-2 p-3 text-faint">
        <Icon size={20} strokeWidth={1.5} />
      </span>
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-content">{title}</h3>
        {description && <p className="mx-auto mt-1 max-w-sm text-xs text-muted">{description}</p>}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
