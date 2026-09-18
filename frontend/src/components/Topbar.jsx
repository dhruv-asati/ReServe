import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Search, Bell, Plus, ChevronDown, LogOut, UserCircle } from 'lucide-react';

import { Button, Badge } from '@/components/ui';
import { NAV_ITEMS } from '@/routes/navigation';
import { PATHS } from '@/routes/paths';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/utils/cn';

const ROLE_LABELS = {
  provider: 'Provider',
  recipient: 'Recipient',
  'rescue-partner': 'Rescue Partner',
};

/**
 * Topbar.
 *
 * Carries the current section title, a clock, the search entry point, and the
 * primary action. The clock is deliberate: every rescue in this system is
 * bounded by a deadline, so the operator should always see the current time
 * next to the window they are working against.
 */
export default function Topbar({ onOpenMenu, notificationCount = 0 }) {
  const { pathname } = useLocation();
  const title = resolveTitle(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b border-line bg-surface-1/95 px-4 backdrop-blur-sm sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Open navigation"
        className="-ml-1 rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content lg:hidden"
      >
        <Menu size={18} strokeWidth={1.75} />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-semibold tracking-tight text-content sm:text-base">
          {title}
        </h1>
        <Clock />
      </div>

      {/* Search — full control on desktop, icon on smaller screens */}
      <button
        type="button"
        className="hidden h-9 w-56 items-center gap-2 rounded-control border border-line bg-surface-2 px-3 text-xs text-faint transition-colors hover:border-line-strong hover:text-muted xl:flex"
      >
        <Search size={14} strokeWidth={1.75} />
        Search resources, partners…
      </button>
      <button
        type="button"
        aria-label="Search"
        className="rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content xl:hidden"
      >
        <Search size={17} strokeWidth={1.75} />
      </button>

      <button
        type="button"
        aria-label="Notifications"
        className="relative rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content"
      >
        <Bell size={17} strokeWidth={1.75} />
        {notificationCount > 0 && (
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-brand-400 ring-2 ring-surface-1" />
        )}
      </button>

      <Button
        as={Link}
        to={PATHS.CREATE_RESCUE}
        size="md"
        icon={Plus}
        className="hidden sm:inline-flex"
      >
        Create Rescue
      </Button>

      <OrgMenu />
    </header>
  );
}

function resolveTitle(pathname) {
  const match = NAV_ITEMS.filter((item) => pathname.startsWith(item.to)).sort(
    (a, b) => b.to.length - a.to.length,
  )[0];

  if (pathname === PATHS.DASHBOARD) return 'Overview';
  if (pathname.startsWith(PATHS.PROFILE)) return 'Organization';
  return match?.label ?? 'ReServe';
}

function Clock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const date = now.toLocaleDateString([], { day: 'numeric', month: 'short' });

  return (
    <p className="hidden text-[11px] text-faint tabular sm:block">
      {date} · {time} local
    </p>
  );
}

function initials(name) {
  if (!name) return 'RS';
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

function OrgMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    function handleEscape(event) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  function handleLogout() {
    setOpen(false);
    logout();
    navigate(PATHS.LOGIN, { replace: true });
  }

  const displayName = user?.organization ?? user?.name ?? 'Demo Org';
  const roleLabel = ROLE_LABELS[user?.role] ?? 'Provider';

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'flex items-center gap-2 rounded-control border border-line bg-surface-2 py-1 pl-1 pr-1.5 sm:pr-2.5',
          'transition-colors hover:border-line-strong',
        )}
      >
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-[6px] bg-brand-600/20 text-[11px] font-semibold text-brand-300">
          {initials(displayName)}
        </span>
        <span className="hidden min-w-0 leading-tight sm:block">
          <span className="block max-w-[9rem] truncate text-xs font-medium text-content">
            {displayName}
          </span>
          <Badge tone="brand" size="sm" className="mt-0.5">
            {roleLabel}
          </Badge>
        </span>
        <ChevronDown
          size={14}
          strokeWidth={1.75}
          className={cn(
            'hidden shrink-0 text-faint transition-transform sm:block',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="animate-fade-up absolute right-0 top-[calc(100%+0.5rem)] z-40 w-48 overflow-hidden rounded-control border border-line bg-surface-1 py-1 shadow-lg"
        >
          {user?.name && (
            <div className="border-b border-line px-3 py-2">
              <p className="truncate text-xs font-medium text-content">{user.name}</p>
              <p className="truncate text-[11px] text-faint">{user.email}</p>
            </div>
          )}
          <Link
            to={PATHS.PROFILE}
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-xs text-muted transition-colors hover:bg-surface-2 hover:text-content"
          >
            <UserCircle size={14} strokeWidth={1.75} />
            Organization profile
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-critical transition-colors hover:bg-critical/10"
          >
            <LogOut size={14} strokeWidth={1.75} />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
