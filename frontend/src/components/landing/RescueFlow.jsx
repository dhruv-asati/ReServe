import { Fragment } from 'react';
import { Building2, BrainCircuit, Network, Truck, HeartHandshake, ArrowRight } from 'lucide-react';

import { Badge } from '@/components/ui';
import { cn } from '@/utils/cn';

/**
 * RescueFlow — the five-stage pipeline that turns surplus into service.
 *
 * Distinct from the compact "how it works" list inside the hero visual:
 * this is a full-width, standalone section with a step index, an icon,
 * a title, and a one-line description per stage, connected visually by
 * arrows (desktop) or a vertical line (mobile).
 */
const STEPS = [
  {
    step: '01',
    icon: Building2,
    title: 'Provider',
    desc: 'Restaurants, hospitals, and pharmacies report surplus as it happens.',
  },
  {
    step: '02',
    icon: BrainCircuit,
    title: 'AI Resource Understanding',
    desc: 'Quantity, condition, and urgency are parsed and classified automatically.',
    emphasize: true,
  },
  {
    step: '03',
    icon: Network,
    title: 'Smart Matching',
    desc: 'The best-fit recipient is identified from live capacity and need.',
    emphasize: true,
  },
  {
    step: '04',
    icon: Truck,
    title: 'Rescue Partner',
    desc: 'A verified partner is routed to pick up and transport the resource.',
  },
  {
    step: '05',
    icon: HeartHandshake,
    title: 'Recipient',
    desc: 'Shelters and clinics receive resources before they go to waste.',
  },
];

export default function RescueFlow() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="animate-fade-up mx-auto max-w-2xl text-center">
        <Badge tone="brand" size="sm">
          Rescue Flow
        </Badge>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-content sm:text-3xl">
          From surplus to service, in five steps.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
          Every rescue moves through the same coordinated pipeline — reported, understood,
          matched, moved, and delivered.
        </p>
      </div>

      {/* ---------- Desktop / tablet: horizontal pipeline ---------- */}
      <div className="animate-fade-up mt-12 hidden items-stretch gap-2 lg:flex">
        {STEPS.map((s, index) => (
          <Fragment key={s.step}>
            <FlowStep {...s} />
            {index < STEPS.length - 1 && <FlowArrow />}
          </Fragment>
        ))}
      </div>

      {/* ---------- Mobile / tablet: vertical pipeline ---------- */}
      <div className="animate-fade-up mx-auto mt-10 max-w-md lg:hidden">
        {STEPS.map((s, index) => (
          <Fragment key={s.step}>
            <FlowStep vertical {...s} />
            {index < STEPS.length - 1 && <FlowConnector />}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

function FlowIcon({ icon: Icon, emphasize }) {
  return (
    <div
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-control border transition-colors duration-200',
        emphasize
          ? 'animate-pulse-soft border-brand-500/40 bg-brand-500/10 text-brand-400'
          : 'border-line bg-surface-2 text-muted group-hover:border-brand-500/30 group-hover:text-brand-400',
      )}
    >
      <Icon size={20} strokeWidth={1.75} />
    </div>
  );
}

function FlowStep({ step, icon: Icon, title, desc, emphasize, vertical }) {
  if (vertical) {
    return (
      <div
        className={cn(
          'group panel flex items-start gap-4 p-4 transition-all duration-200',
          'hover:-translate-y-0.5 hover:border-line-strong hover:shadow-lg hover:shadow-black/20',
        )}
      >
        <FlowIcon icon={Icon} emphasize={emphasize} />
        <div className="min-w-0 pt-0.5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-semibold tracking-wide text-faint">
              {step}
            </span>
            <h3 className="text-sm font-semibold tracking-tight text-content">{title}</h3>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-muted">{desc}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group panel relative flex-1 p-5 transition-all duration-200',
        'hover:-translate-y-1 hover:border-line-strong hover:shadow-lg hover:shadow-black/20',
      )}
    >
      <span className="font-mono text-[11px] font-semibold tracking-wide text-faint">{step}</span>
      <div className="mt-3">
        <FlowIcon icon={Icon} emphasize={emphasize} />
      </div>
      <div className="mt-4">
        <h3 className="text-sm font-semibold tracking-tight text-content">{title}</h3>
        <p className="mt-1 text-xs leading-relaxed text-muted">{desc}</p>
      </div>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flex shrink-0 items-center px-1 text-faint" aria-hidden>
      <ArrowRight size={16} strokeWidth={1.75} />
    </div>
  );
}

function FlowConnector() {
  return (
    <div className="ml-[35px] h-6 w-px bg-gradient-to-b from-line-strong to-line" aria-hidden />
  );
}
