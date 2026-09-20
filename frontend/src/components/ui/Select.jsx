import { useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/utils/cn';

/**
 * Native select, styled to match Input.
 * Options: [{ value, label, disabled }] — or pass children for option groups.
 */
export default function Select({
  label,
  hint,
  error,
  required = false,
  options = [],
  placeholder,
  className,
  containerClassName,
  id,
  children,
  ...props
}) {
  const generatedId = useId();
  const selectId = id ?? generatedId;

  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label
          htmlFor={selectId}
          className="mb-1.5 block text-xs font-medium tracking-wide text-muted"
        >
          {label}
          {required && (
            <span className="ml-0.5 text-critical" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <div className="relative">
        <select
          id={selectId}
          required={required}
          aria-required={required || undefined}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error || hint ? `${selectId}-desc` : undefined}
          className={cn(
            'h-9.5 w-full appearance-none rounded-control border bg-surface-2 pl-3 pr-9 text-sm text-content',
            'transition-colors duration-150',
            'focus:border-veil-500 focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-60',
            error ? 'border-critical' : 'border-line hover:border-line-strong',
            className,
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children ??
            options.map((option) => (
              <option key={option.value} value={option.value} disabled={option.disabled}>
                {option.label}
              </option>
            ))}
        </select>

        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-faint">
          <ChevronDown size={15} strokeWidth={1.75} />
        </span>
      </div>

      {(error || hint) && (
        <p
          id={`${selectId}-desc`}
          className={cn('mt-1.5 text-xs', error ? 'text-critical' : 'text-faint')}
        >
          {error || hint}
        </p>
      )}
    </div>
  );
}
