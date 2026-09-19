import { Construction } from 'lucide-react';

/**
 * Temporary stand-in so routing can be verified before any section is built.
 * Each real page replaces its own placeholder in a later step.
 */
export default function Placeholder({ title, description }) {
  return (
    <div className="animate-fade-up panel flex min-h-[60vh] flex-col items-center justify-center gap-3 p-10 text-center">
      <span className="rounded-full bg-surface-3 p-3 text-brand-400">
        <Construction size={22} strokeWidth={1.75} />
      </span>
      <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
      <p className="max-w-md text-sm text-muted">
        {description ?? 'This section is scaffolded and will be implemented in a later step.'}
      </p>
    </div>
  );
}
