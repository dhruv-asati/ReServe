import { Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';

/**
 * Button primitive.
 *
 * Variants map to operational intent, not decoration:
 *   primary   — the one committing action on a screen
 *   secondary — supporting actions
 *   ghost     — toolbar / icon actions
 *   danger    — destructive or abort (cancel a rescue)
 *   outline   — filters and toggles
 */
const VARIANTS = {
  primary:
    'bg-veil-600/50 text-white hover:bg-veil-500 active:bg-veil-700 disabled:bg-veil-700/50',
  secondary:
    'bg-surface-3 text-content hover:bg-line-strong active:bg-surface-2 border border-line',
  ghost: 'text-muted hover:text-content hover:bg-surface-2',
  danger: 'bg-critical/90 text-white hover:bg-critical active:bg-critical/80',
  outline:
    'border border-line text-muted hover:text-content hover:border-line-strong bg-transparent',
};

const SIZES = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-9.5 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-sm gap-2',
  icon: 'h-9 w-9 justify-center',
};

export default function Button({
  as: Component = 'button',
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  iconRight: IconRight,
  className,
  children,
  ...props
}) {
  const isDisabled = disabled || loading;

  return (
    <Component
      className={cn(
        'inline-flex items-center rounded-control font-medium tracking-tight',
        'transition-colors duration-150',
        'disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      disabled={Component === 'button' ? isDisabled : undefined}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <Loader2 size={15} strokeWidth={2} className="animate-spin" />
      ) : (
        Icon && <Icon size={15} strokeWidth={2} />
      )}
      {size !== 'icon' && children}
      {!loading && IconRight && <IconRight size={15} strokeWidth={2} />}
    </Component>
  );
}
