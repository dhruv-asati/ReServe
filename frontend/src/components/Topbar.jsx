import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, Plus, ChevronDown, LogOut, UserCircle, X } from 'lucide-react';

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
export default function Topbar({ notificationCount = 0 }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const searchButtonRef = useRef(null);
  const title = resolveTitle(pathname);

  const closeSearch = useCallback(() => {
    setSearchOpen(false);
    searchButtonRef.current?.focus();
  }, []);

  // Search runs against the operations list (ID, resource, provider, recipient,
  // rescue partner) — the Live Operations page reads it from `?q=`.
  function handleSearch(event) {
    event.preventDefault();
    const text = query.trim();
    const search = text ? `?${new URLSearchParams({ q: text })}` : '';
    navigate(`${PATHS.LIVE_OPERATIONS}${search}`);
    setQuery('');
    closeSearch();
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-2 border-b border-line bg-surface-1/60 px-4 backdrop-blur-sm sm:gap-3 sm:px-6">
      {/* Room for the StaggeredMenu toggle + logo mark, which sit fixed over this bar
          (see StaggeredMenu.css). Phones: 2.25rem icon button + 1.25rem gap + 1.75rem
          logo = 5.25rem. From sm up: 5.5rem button with label + gap + logo = 8.5rem. */}
      <div aria-hidden="true" className="w-[5.25rem] shrink-0 sm:w-[8.5rem]" />

      <div className="ml-3 min-w-0 flex-1 sm:ml-6">
        <h1 className="truncate text-sm font-semibold tracking-tight text-content sm:text-base">
          {title}
        </h1>
        <Clock />
      </div>

      {/* Search — typeable field on desktop, pop-up search (dimmed page) on smaller screens */}
      <form role="search" onSubmit={handleSearch} className="relative hidden xl:block">
        <Search
          size={14}
          strokeWidth={1.75}
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
        />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search operations"
          placeholder="Search resources, partners…"
          className="h-9 w-56 rounded-control border border-line bg-surface-2 pl-9 pr-3 text-xs text-content outline-none transition-colors placeholder:text-faint hover:border-line-strong focus:border-veil-500"
        />
      </form>
      <button
        ref={searchButtonRef}
        type="button"
        aria-label="Search operations"
        aria-haspopup="dialog"
        onClick={() => setSearchOpen(true)}
        className="shrink-0 rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content xl:hidden"
      >
        <Search size={17} strokeWidth={1.75} />
      </button>
      {searchOpen && (
        <SearchOverlay
          query={query}
          onQueryChange={setQuery}
          onSubmit={handleSearch}
          onClose={closeSearch}
        />
      )}

      <button
        type="button"
        aria-label="Notifications"
        className="relative shrink-0 rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content"
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
        className="shrink-0 max-sm:hidden"
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
    <div ref={menuRef} className="relative shrink-0">
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

/**
 * Pop-up search for screens where the inline field doesn't fit: the page dims,
 * and only a search bar is shown. Rendered in a portal on <body> because the
 * Topbar's backdrop-filter would otherwise turn `fixed` into "fixed to the bar".
 */
function SearchOverlay({ query, onQueryChange, onSubmit, onClose }) {
  const inputRef = useRef(null);
  const closeRef = useRef(onClose);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(true));
    inputRef.current?.focus();

    // Lock page scroll behind the overlay.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeyDown(event) {
      if (event.key === 'Escape') closeRef.current();
    }
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return createPortal(
    <div role="dialog" aria-modal="true" aria-label="Search operations" className="fixed inset-0 z-[300]">
      {/* Dimmed page — tap anywhere outside the bar to dismiss */}
      <div
        aria-hidden="true"
        onMouseDown={onClose}
        className={cn(
          'absolute inset-0 bg-black/75 backdrop-blur-[2px] transition-opacity duration-200',
          shown ? 'opacity-100' : 'opacity-0',
        )}
      />

      <div className="pointer-events-none relative mx-auto w-[min(92vw,36rem)] pt-[14vh]">
        <form
          role="search"
          onSubmit={onSubmit}
          className={cn(
            'pointer-events-auto rounded-card border border-line-strong bg-surface-1 p-2 shadow-2xl',
            'transition duration-200 ease-out',
            shown ? 'translate-y-0 scale-100 opacity-100' : '-translate-y-2 scale-95 opacity-0',
          )}
        >
          <div className="relative">
            <Search
              size={18}
              strokeWidth={1.75}
              aria-hidden="true"
              className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-faint"
            />
            {/* text-base (16px) on purpose: smaller inputs make iOS Safari zoom the page on focus */}
            <input
              ref={inputRef}
              type="text"
              inputMode="search"
              enterKeyHint="search"
              autoComplete="off"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              aria-label="Search operations"
              placeholder="Search resources, partners…"
              className="h-12 w-full rounded-control border border-line bg-surface-2 pl-11 pr-11 text-base text-content outline-none transition-colors placeholder:text-faint focus:border-veil-500"
            />
            <button
              type="button"
              onClick={onClose}
              aria-label="Close search"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-control p-1.5 text-faint transition-colors hover:text-content"
            >
              <X size={16} strokeWidth={1.75} />
            </button>
          </div>
          <p className="px-1.5 pb-1 pt-2.5 text-[11px] leading-relaxed text-faint">
            Search by operation ID, resource, provider, recipient or rescue partner. Press Enter to search.
          </p>
        </form>
      </div>
    </div>,
    document.body,
  );
}
