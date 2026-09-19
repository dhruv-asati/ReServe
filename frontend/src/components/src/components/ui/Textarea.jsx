import { useId } from 'react';
import { cn } from '@/utils/cn';

/**
 * Multi-line text input, styled to match Input/Select so a form can mix all
 * three without any visual seams. Same label/required/error/hint contract
 * as Input, so it drops into the same form layouts.
 */
export default function Textarea({
  label,
  hint,
  error,
  required = false,
  rows = 3,
  className,
  containerClassName,
  id,
  ...props
}) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;

  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label
          htmlFor={textareaId}
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

      <textarea
        id={textareaId}
        rows={rows}
        required={required}
        aria-required={required || undefined}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error || hint ? `${textareaId}-desc` : undefined}
        className={cn(
          'w-full resize-none rounded-control border bg-surface-2 px-3 py-2.5 text-sm text-content',
          'placeholder:text-faint',
          'transition-colors duration-150',
          'focus:border-brand-500 focus:outline-none',
          'disabled:cursor-not-allowed disabled:opacity-60',
          error ? 'border-critical' : 'border-line hover:border-line-strong',
          className,
        )}
        {...props}
      />

      {(error || hint) && (
        <p
          id={`${textareaId}-desc`}
          className={cn('mt-1.5 text-xs', error ? 'text-critical' : 'text-faint')}
        >
          {error || hint}
        </p>
      )}
    </div>
  );
}
