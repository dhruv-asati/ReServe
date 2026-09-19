import { Soup, Syringe, Check, Info } from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';

/**
 * ResourceTypes — the two categories ReServe coordinates. Kept as two
 * reusable Card instances so a third category can be added later without
 * restructuring the section.
 */
const CATEGORIES = [
  {
    key: 'food',
    tone: 'food',
    icon: Soup,
    title: 'Food',
    subtitle: 'Surplus meals and eligible food resources',
    examples: [
      'Surplus meals',
      'Prepared food',
      'Restaurant / hotel surplus',
      'Bakery & other eligible food',
    ],
  },
  {
    key: 'medical',
    tone: 'medical',
    icon: Syringe,
    title: 'Medical Resources',
    subtitle: 'Eligible supplies routed through verified partners',
    examples: ['Eligible medical supplies', 'Other authorized resources'],
  },
];

export default function ResourceTypes() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="animate-fade-up mx-auto max-w-2xl text-center">
        <Badge tone="brand" size="sm">
          Resource Types
        </Badge>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-content sm:text-3xl">
          What ReServe redistributes.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
          Two categories today, each routed through the same verified rescue pipeline.
        </p>
      </div>

      <div className="animate-fade-up mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2">
        {CATEGORIES.map((cat) => (
          <ResourceCard key={cat.key} {...cat} />
        ))}
      </div>

      <div className="animate-fade-up mt-6 flex items-start gap-2.5 rounded-control border border-line bg-surface-2 px-4 py-3">
        <Info size={15} strokeWidth={1.75} className="mt-0.5 shrink-0 text-faint" />
        <p className="text-xs leading-relaxed text-muted">
          ReServe coordinates resource redistribution. It does not prescribe medicines or make
          clinical decisions.
        </p>
      </div>
    </section>
  );
}

function ResourceCard({ tone, icon: Icon, title, subtitle, examples }) {
  const toneClasses = {
    food: 'border-food/25 bg-food/10 text-food',
    medical: 'border-medical/25 bg-medical/10 text-medical',
  };

  return (
    <Card className="group p-6 transition-all duration-200 hover:-translate-y-1 hover:border-line-strong hover:shadow-lg hover:shadow-black/20 sm:p-7">
      <div
        className={cn(
          'flex h-12 w-12 items-center justify-center rounded-control border',
          toneClasses[tone],
        )}
      >
        <Icon size={22} strokeWidth={1.75} />
      </div>

      <h3 className="mt-5 text-base font-semibold tracking-tight text-content">{title}</h3>
      <p className="mt-1 text-xs text-muted">{subtitle}</p>

      <ul className="mt-5 space-y-2.5">
        {examples.map((ex) => (
          <li key={ex} className="flex items-start gap-2.5 text-sm text-muted">
            <Check size={14} strokeWidth={2} className="mt-0.5 shrink-0 text-brand-400" />
            <span>{ex}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
