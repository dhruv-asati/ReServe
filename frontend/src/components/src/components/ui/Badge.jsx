import { cn } from '@/utils/cn';

/**
 * Generic badge. Tones are semantic, not decorative — pick by meaning.
 * For rescue/allocation statuses use StatusBadge instead, which reads the
 * status vocabulary from the design system.
 */
const TONES = {
  neutral: 'bg-surface-3 text-muted ring-line-strong/40',
  brand: 'bg-brand-500/10 text-brand-400 ring-brand-500/25',
  critical: 'bg-critical/10 text-critical ring-critical/25',
  urgent: 'bg-urgent/10 text-urgent ring-urgent/25',
  active: 'bg-active/10 text-active ring-active/25',
  success: 'bg-success/10 text-success ring-success/25',
  predicted: 'bg-predicted/10 text-predicted ring-predicted/25',
  food: 'bg-food/10 text-food ring-food/25',
  medical: 'bg-medical/10 text-medical ring-medical/25',
};

const SIZES = {
  sm: 'h-5 px-1.5 text-[10px] gap-1',
  md: 'h-6 px-2 text-xs gap-1.5',
};

export default function Badge({
  tone = 'neutral',
  size = 'md',
  icon: Icon,
  dot = false,
  className,
  children,
  ...props
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium tracking-tight ring-1 ring-inset whitespace-nowrap',
        TONES[tone] ?? TONES.neutral,
        SIZES[size],
        className,
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {Icon && <Icon size={size === 'sm' ? 10 : 12} strokeWidth={2} />}
      {children}
    </span>
  );
}
