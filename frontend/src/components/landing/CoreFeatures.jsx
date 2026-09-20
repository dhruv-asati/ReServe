import {
  BrainCircuit,
  SlidersHorizontal,
  RefreshCw,
  Moon,
  TrendingUp,
} from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';

/**
 * CoreFeatures — the five capabilities that differentiate ReServe's
 * coordination layer. Each card is short by design: one line of context,
 * an optional compact tag list for anything with multiple factors.
 */
const FEATURES = [
  {
    key: 'ai-understanding',
    tone: 'brand',
    icon: BrainCircuit,
    title: 'AI Resource Understanding',
    desc: 'Gemini helps structure resource information — type, category, quantity, urgency, and rescue window.',
  },
  {
    key: 'smart-matching',
    tone: 'active',
    icon: SlidersHorizontal,
    title: 'Smart Matching',
    desc: 'Matching weighs every factor that decides whether a rescue actually succeeds.',
    tags: [
      'Demand',
      'Capacity',
      'Distance',
      'Urgency',
      'Deadline',
      'Availability',
      'Pickup feasibility',
      'Eligibility',
    ],
  },
  {
    key: 'dynamic-reallocation',
    tone: 'urgent',
    icon: RefreshCw,
    title: 'Dynamic Reallocation',
    desc: 'If a recipient or rescue partner becomes unavailable, the system recalculates the rescue plan.',
  },
  {
    key: 'late-night-rescue',
    tone: 'idle',
    icon: Moon,
    title: 'Late-Night Rescue',
    desc: 'Resources can be routed through rescue partners and rescue hubs when normal recipients are unavailable.',
  },
  {
    key: 'predictive-rescue',
    tone: 'predicted',
    icon: TrendingUp,
    title: 'Predictive Rescue',
    desc: 'Historical patterns can identify recurring surplus windows and help prepare rescue capacity.',
  },
];

const TONE_CLASSES = {
  brand: 'border-brand-500/25 bg-brand-500/10 text-brand-400',
  active: 'border-active/25 bg-active/10 text-active',
  urgent: 'border-urgent/25 bg-urgent/10 text-urgent',
  idle: 'border-idle/25 bg-idle/10 text-idle',
  predicted: 'border-predicted/25 bg-predicted/10 text-predicted',
};

export default function CoreFeatures() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="animate-fade-up mx-auto max-w-2xl text-center">
        <Badge tone="brand" size="sm">
          Core Features
        </Badge>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-content sm:text-3xl">
          What powers every rescue.
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
          A coordination layer that understands, matches, and adapts — not just a listing board.
        </p>
      </div>

      <div className="animate-fade-up mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ key, ...feature }) => (
          <FeatureCard key={key} {...feature} />
        ))}
      </div>
    </section>
  );
}

function FeatureCard({ tone, icon: Icon, title, desc, tags }) {
  return (
    <Card className="group p-6 transition-all duration-200 hover:-translate-y-1 hover:border-line-strong hover:shadow-lg hover:shadow-black/20 sm:p-7">
      <div
        className={cn(
          'flex h-12 w-12 items-center justify-center rounded-control border',
          TONE_CLASSES[tone],
        )}
      >
        <Icon size={22} strokeWidth={1.75} />
      </div>

      <h3 className="mt-5 text-base font-semibold tracking-tight text-content">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">{desc}</p>

      {tags && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-faint"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}
