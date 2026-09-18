import { AlertTriangle, RotateCw } from 'lucide-react';
import Button from './Button';
import { cn } from '@/utils/cn';

/**
 * Shown when a request or an operation failed. `onRetry` renders the retry
 * control; omit it for failures that cannot be retried from the UI.
 */
export default function ErrorState({
  title = 'Something went wrong',
  description = 'The request could not be completed. Try again in a moment.',
  onRetry,
  retryLabel = 'Retry',
  className,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-14 text-center',
        className,
      )}
      role="alert"
    >
      <span className="rounded-full border border-critical/25 bg-critical/10 p-3 text-critical">
        <AlertTriangle size={20} strokeWidth={1.75} />
      </span>
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-content">{title}</h3>
        <p className="mx-auto mt-1 max-w-sm text-xs text-muted">{description}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" icon={RotateCw} onClick={onRetry} className="mt-1">
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
