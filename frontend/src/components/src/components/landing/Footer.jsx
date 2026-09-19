import { Link } from 'react-router-dom';

import { Logo } from '@/components/Sidebar';
import { PATHS } from '@/routes/paths';

/**
 * Footer — closes out the public landing page. Kept to what the page
 * actually offers: navigation, resource types, and the two network-facing
 * app sections (Rescue Network, Analytics). No newsletter, social, or
 * payment content.
 */
const NAV_LINKS = [
  { label: 'Home', to: PATHS.LANDING },
  { label: 'Log In', to: PATHS.LOGIN },
  { label: 'Register', to: PATHS.REGISTER },
  { label: 'Start a Rescue', to: PATHS.CREATE_RESCUE },
];

const RESOURCE_LINKS = [
  { label: 'Food', to: PATHS.CREATE_RESCUE },
  { label: 'Medical Resources', to: PATHS.CREATE_RESCUE },
];

const PLATFORM_LINKS = [
  { label: 'Rescue Network', to: PATHS.RESCUE_NETWORK },
  { label: 'Analytics', to: PATHS.ANALYTICS },
];

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          {/* ---------- Brand ---------- */}
          <div className="max-w-sm">
            <Link to={PATHS.LANDING} className="flex items-center gap-2.5">
              <Logo size={28} />
              <span className="text-sm font-semibold tracking-tight text-content">ReServe</span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              AI-powered resource redistribution and rescue network — turning surplus into timely
              service.
            </p>
          </div>

          <FooterColumn title="Navigation" links={NAV_LINKS} />
          <FooterColumn title="Resource Types" links={RESOURCE_LINKS} />
          <FooterColumn title="Network" links={PLATFORM_LINKS} />
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-line pt-6 text-xs text-faint sm:flex-row sm:items-center sm:justify-between">
          <p>&copy; {new Date().getFullYear()} ReServe. All rights reserved.</p>
          <p className="italic">&ldquo;Turning surplus into timely service.&rdquo;</p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-faint">{title}</p>
      <ul className="mt-4 space-y-2.5">
        {links.map((link) => (
          <li key={link.label}>
            <Link
              to={link.to}
              className="text-sm text-muted transition-colors hover:text-content"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
