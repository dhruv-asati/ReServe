import { Link } from 'react-router-dom';
import { Rocket, Compass } from 'lucide-react';

import { Button } from '@/components/ui';
import { PATHS } from '@/routes/paths';

/**
 * FinalCTA — last conversion point on the landing page before the footer.
 * Mirrors the hero's action pair so the two entry points a visitor sees
 * (top and bottom) always agree.
 */
export default function FinalCTA() {
  return (
    <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
      <div className="animate-fade-up panel relative overflow-hidden px-6 py-14 text-center sm:px-12 sm:py-16">
        <div className="grid-backdrop pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-500/10 blur-3xl" />

        <div className="relative">
          <h2 className="mx-auto max-w-2xl text-2xl font-bold tracking-tight text-content sm:text-3xl lg:text-4xl">
            Every usable resource deserves a chance to be used.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-muted sm:text-base">
            Create a rescue, connect with the network, and turn surplus into timely service.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
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
      </div>
    </section>
  );
}
