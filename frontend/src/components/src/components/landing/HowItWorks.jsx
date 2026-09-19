import { Fragment } from 'react';
import { PackagePlus, BrainCircuit, Route, CheckCircle2 } from 'lucide-react';

import { Badge } from '@/components/ui';
import { cn } from '@/utils/cn';

/**
 * HowItWorks — the four-step mental model for ReServe, shown as a
 * connected timeline. Distinct from RescueFlow (which names the parties
 * involved); this names the actions a user actually takes and sees.
 */
const STEPS = [
  {
    step: '01',
    icon: PackagePlus,
    title: 'Create Resource',
    desc: 'Log a surplus resource with quantity, category, and deadline.',
  },
  {
    step: '02',
    icon: BrainCircuit,
    title: 'AI Understands',
    desc: 'Gemini structures the details and flags urgency automatically.',
    emphasize: true,
  },
  {
    step: '03',
    icon: Route,
    title: 'Rescue Plan',
    desc: 'A match is proposed across recipients and rescue partners.',
    emphasize: true,
  },
  {
    step: '04',
    icon: CheckCircle2,
    title: 'Rescue Happens',
    desc: 'The plan is confirmed and the resource reaches its destination.',
  },
];

export default function HowItWorks() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="animate-fade-up mx-auto max-w-2xl text-center">
        <Badge tone="brand" size="sm">
          How ReServe Works
        </Badge>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-content sm:text-3xl">
          Four steps from surplus to service.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
          Simple to start, coordinated underneath.
        </p>
      </div>

      {/* ---------- Desktop / tablet: horizontal timeline ---------- */}
      <div className="animate-fade-up relative mt-16 hidden lg:block">
        <div className="absolute left-0 right-0 top-7 h-px bg-line" aria-hidden />
        <div className="grid grid-cols-4 gap-6">
          {STEPS.map((s) => (
            <TimelineStep key={s.step} {...s} />
          ))}
        </div>
      </div>

      {/* ---------- Mobile / tablet: vertical timeline ---------- */}
      <div className="animate-fade-up mx-auto mt-12 max-w-md lg:hidden">
        {STEPS.map((s, index) => (
          <Fragment key={s.step}>
            <TimelineStep vertical {...s} />
            {index < STEPS.length - 1 && (
              <div
                className="ml-[27px] h-6 w-px bg-gradient-to-b from-line-strong to-line"
                aria-hidden
              />
            )}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

function TimelineStep({ step, icon: Icon, title, desc, emphasize, vertical }) {
  const node = (
    <div
      className={cn(
        'relative z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 bg-surface-1',
        emphasize ? 'border-brand-500/50 text-brand-400' : 'border-line-strong text-muted',
      )}
    >
      <Icon size={22} strokeWidth={1.75} />
    </div>
  );

  if (vertical) {
    return (
      <div className="flex items-start gap-4">
        {node}
        <div className="min-w-0 pt-2.5">
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
    <div className="flex flex-col items-center text-center">
      {node}
      <span className="mt-4 font-mono text-[11px] font-semibold tracking-wide text-faint">
        {step}
      </span>
      <h3 className="mt-1 text-sm font-semibold tracking-tight text-content">{title}</h3>
      <p className="mt-1.5 max-w-[15rem] text-xs leading-relaxed text-muted">{desc}</p>
    </div>
  );
}
