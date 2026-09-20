import { Link } from 'react-router-dom';

import { Button } from '@/components/ui';
import { Logo } from '@/components/Sidebar';
import StrokeText from '@/components/StrokeText';
import { useAuth } from '@/context/AuthContext';
import { PATHS } from '@/routes/paths';

/**
 * Landing header — brand on the left (logo mark + the animated ReServe
 * wordmark), section links in the middle on wide screens, and the sign-in /
 * get-started actions on the right. Sticks to the top with a blurred,
 * semi-transparent bar so the hero background shows through.
 */

const SECTION_LINKS = [
  { label: 'Rescue flow', href: '#rescue-flow' },
  { label: 'Resources', href: '#resources' },
  { label: 'Features', href: '#features' },
  { label: 'How it works', href: '#how-it-works' },
];

function scrollToSection(event, href) {
  const target = document.querySelector(href);
  if (!target) return;
  event.preventDefault();
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
}

export default function LandingHeader() {
  const { isAuthenticated } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-surface-0/50 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to={PATHS.LANDING}
          aria-label="ReServe home"
          className="flex shrink-0 items-center gap-2.5"
        >
          <Logo size={30} />
          <StrokeText
            text="ReServe"
            strokeColor="#A78BFA"
            fillColor="#F8FAFC"
            strokeWidth={1}
            drawDuration={1.6}
            fillDelay={0.1}
            stagger={0.05}
            ease="sine.inOut"
            trigger="mount"
            fillMode="wipe"
            fontSize={36}
            fontWeight={900}
            letterSpacing={-1}
            reverse={false}
            className="stroke-text--responsive"
          />
        </Link>

        <nav aria-label="Sections" className="hidden items-center gap-1 lg:flex">
          {SECTION_LINKS.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              onClick={(event) => scrollToSection(event, href)}
              className="rounded-control px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-content"
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          {isAuthenticated ? (
            <Button as={Link} to={PATHS.DASHBOARD} size="md">
              Open dashboard
            </Button>
          ) : (
            <>
              <Button as={Link} to={PATHS.LOGIN} variant="ghost" size="md" className="max-sm:hidden">
                Log in
              </Button>
              <Button as={Link} to={PATHS.REGISTER} size="md">
                Get started
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
