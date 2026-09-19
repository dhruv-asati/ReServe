import { cn } from '@/utils/cn';

/**
 * ResourceTypeCard — one selectable option in a radiogroup of resource
 * types (Food / Medical Resources). A real <input type="radio"> backs each
 * card so the group is keyboard- and screen-reader-accessible; the card
 * itself is just the label's visual skin. Reused as-is for both options
 * rather than writing two bespoke buttons.
 */
export default function ResourceTypeCard({
  name,
  value,
  label,
  description,
  icon: Icon,
  tone = 'brand',
  checked,
  onChange,
}) {
  const TONE_RING = {
    food: 'has-[:checked]:border-food has-[:checked]:ring-food/30',
    medical: 'has-[:checked]:border-medical has-[:checked]:ring-medical/30',
    brand: 'has-[:checked]:border-brand-500 has-[:checked]:ring-brand-500/30',
  };
  const TONE_ICON = {
    food: 'text-food',
    medical: 'text-medical',
    brand: 'text-brand-400',
  };

  return (
    <label
      className={cn(
        'relative flex cursor-pointer items-start gap-3 rounded-control border border-line bg-surface-2 p-4',
        'transition-colors duration-150 hover:border-line-strong',
        'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500/40',
        'has-[:checked]:ring-1',
        TONE_RING[tone] ?? TONE_RING.brand,
      )}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onChange(value)}
        className="absolute right-4 top-4 h-4 w-4 accent-brand-500"
      />

      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-surface-3',
          TONE_ICON[tone] ?? TONE_ICON.brand,
        )}
      >
        {Icon && <Icon size={18} strokeWidth={1.75} />}
      </span>

      <span className="min-w-0 pr-6">
        <span className="block text-sm font-semibold text-content">{label}</span>
        {description && (
          <span className="mt-0.5 block text-xs leading-relaxed text-muted">{description}</span>
        )}
      </span>
    </label>
  );
}
