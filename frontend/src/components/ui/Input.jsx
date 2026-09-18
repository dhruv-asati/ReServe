import { useId } from 'react';
import { cn } from '@/utils/cn';

/**
 * Text input with optional label, leading icon, suffix unit and error state.
 * Suffix is used heavily in this app for units ("meals", "km", "min").
 */
export default function Input({
  label,
  hint,
  error,
  icon: Icon,
  suffix,
  className,
  containerClassName,
  id,
  ...props
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1.5 block text-xs font-medium tracking-wide text-muted"
        >
          {label}
        </label>
      )}

      <div className="relative">
        {Icon && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">
            <Icon size={15} strokeWidth={1.75} />
          </span>
        )}

        <input
          id={inputId}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error || hint ? `${inputId}-desc` : undefined}
          className={cn(
            'h-9.5 w-full rounded-control border bg-surface-2 text-sm text-content',
            'placeholder:text-faint',
            'transition-colors duration-150',
            'focus:border-brand-500 focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-60',
            Icon ? 'pl-9' : 'pl-3',
            suffix ? 'pr-16' : 'pr-3',
            error ? 'border-critical' : 'border-line hover:border-line-strong',
            className,
          )}
          {...props}
        />

        {suffix && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-faint">
            {suffix}
          </span>
        )}
      </div>

      {(error || hint) && (
        <p
          id={`${inputId}-desc`}
          className={cn('mt-1.5 text-xs', error ? 'text-critical' : 'text-faint')}
        >
          {error || hint}
        </p>
      )}
    </div>
  );
}
