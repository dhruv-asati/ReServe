import { Fragment } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Building2,
  Package,
  Cpu,
  GitBranch,
  HeartHandshake,
  Rocket,
  Compass,
} from 'lucide-react';

import { Button, Badge } from '@/components/ui';
import RescueFlow from '@/components/landing/RescueFlow';
import ResourceTypes from '@/components/landing/ResourceTypes';
import CoreFeatures from '@/components/landing/CoreFeatures';
import HowItWorks from '@/components/landing/HowItWorks';
import FinalCTA from '@/components/landing/FinalCTA';
import Footer from '@/components/landing/Footer';
import { PATHS } from '@/routes/paths';
import { cn } from '@/utils/cn';

/**
 * Landing — public marketing entry point.
 *
 * Hero (copy + hero visual), Rescue Flow, and Resource Types are untouched.
 * Core Features, How It Works, the final CTA, and the footer are added
 * below them to complete the page.
 */

const FLOW = [
  {
    icon: Building2,
    label: 'Provider',
    desc: 'Restaurants, hospitals, and pharmacies report surplus as it happens.',
  },
  {
    icon: Package,
    label: 'Resource',
    desc: 'Food or eligible medical resources are logged with quantity and deadline.',
  },
  {
    icon: Cpu,
    label: 'AI',
    desc: 'Capacity, urgency, and eligibility are evaluated in real time.',
    emphasize: true,
  },
  {
    icon: GitBranch,
    label: 'Matching',
    desc: 'The best recipient and rescue partner are identified and confirmed.',
  },
  {
    icon: HeartHandshake,
    label: 'Recipient',
    desc: 'Shelters and clinics receive resources before they go to waste.',
  },
];

export default function Landing() {
  return (
    <>
    <section className="relative overflow-hidden">
      {/* Faint operational backdrop — restrained, no heavy gradients */}
      <div className="grid-backdrop pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />

      <div className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-2 lg:gap-16 lg:px-8 lg:py-28">
        {/* ---------- Hero copy ---------- */}
        <div className="animate-fade-up">
          <div className="inline-flex max-w-full items-start gap-2 rounded-full border border-line bg-surface-2 px-3 py-1.5 ring-1 ring-inset ring-brand-500/20">
            <Sparkles size={13} strokeWidth={2} className="mt-0.5 shrink-0 text-brand-400" />
            <span className="text-xs font-medium leading-snug text-muted">
              <span className="font-semibold text-content">ReServe</span> — AI-Powered Resource
              Redistribution &amp; Rescue Network
            </span>
          </div>

          <h1 className="mt-5 text-3xl font-bold tracking-tight text-content sm:text-4xl lg:text-5xl">
            Don&rsquo;t Let Useful Resources Go to Waste.
          </h1>

          <p className="mt-3 text-sm font-medium italic text-brand-400 sm:text-base">
            &ldquo;Turning surplus into timely service.&rdquo;
          </p>

          <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted sm:text-base">
            ReServe connects surplus food and eligible medical resources with organizations that
            can put them to use — coordinating matching, rescue partners, and dynamic
            reallocation.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              as={Link}
              to={PATHS.CREATE_RESCUE}
              variant="primary"
              size="lg"
              icon={Rocket}
              className="w-full justify-center sm:w-auto"
            >
              Start a Rescue
            </Button>
            <Button
              as={Link}
              to={PATHS.RESCUE_NETWORK}
              variant="outline"
              size="lg"
              icon={Compass}
              className="w-full justify-center sm:w-auto"
            >
              Explore the Network
            </Button>
          </div>
        </div>

        {/* ---------- Hero visual ---------- */}
        <div className="animate-fade-up mx-auto w-full max-w-md lg:mx-0 lg:max-w-none">
          <div className="panel relative overflow-hidden p-6 sm:p-8">
            {/* Subtle accent glow behind the AI node — single, restrained */}
            <div className="pointer-events-none absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-500/10 blur-3xl" />

            <div className="relative">
              <div className="mb-5 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-faint">
                  How it works
                </span>
                <Badge tone="active" dot size="sm">
                  Live coordination
                </Badge>
              </div>

              {FLOW.map((node, index) => (
                <Fragment key={node.label}>
                  <FlowNode {...node} />
                  {index < FLOW.length - 1 && <Connector />}
                </Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>

    <RescueFlow />
    <ResourceTypes />
    <CoreFeatures />
    <HowItWorks />
    <FinalCTA />
    <Footer />
    </>
  );
}

function FlowNode({ icon: Icon, label, desc, emphasize }) {
  return (
    <div className="flex items-start gap-4">
      <div
        className={cn(
          'flex h-11 w-11 shrink-0 items-center justify-center rounded-control border',
          emphasize
            ? 'animate-pulse-soft border-brand-500/40 bg-brand-500/10 text-brand-400'
            : 'border-line bg-surface-2 text-muted',
        )}
      >
        <Icon size={20} strokeWidth={1.75} />
      </div>
      <div className="min-w-0 pt-1.5">
        <div className="text-sm font-semibold tracking-tight text-content">{label}</div>
        <p className="mt-0.5 text-xs leading-relaxed text-muted">{desc}</p>
      </div>
    </div>
  );
}

function Connector() {
  return (
    <div className="ml-[21px] h-5 w-px bg-gradient-to-b from-line-strong to-line" aria-hidden />
  );
}
