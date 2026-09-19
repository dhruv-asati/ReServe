/**
 * Tiny class-name joiner. Falsy values are dropped, so conditional classes
 * can be written inline without a helper library.
 *
 *   cn('panel', isActive && 'ring-1 ring-brand-500')
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

export default cn;
