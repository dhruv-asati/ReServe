import { NavLink, Link, useLocation } from 'react-router-dom';
import { PanelLeftClose, PanelLeftOpen, ChevronRight } from 'lucide-react';

import { NAV_GROUPS, isExactMatchOnly } from '@/routes/navigation';
import { PATHS } from '@/routes/paths';
import { cn } from '@/utils/cn';

/**
 * Desktop sidebar.
 *
 * Collapses to an icon rail so the map and operations board can take the full
 * width — an operator watching a live rescue needs the pixels more than the
 * labels. Collapsed state is owned by AppLayout and persisted there.
 */
export default function Sidebar({ collapsed, onToggleCollapse, counts = {} }) {
  return (
    <aside
      className={cn(
        'sticky top-0 hidden h-screen shrink-0 flex-col border-r border-line bg-surface-1 lg:flex',
        'transition-[width] duration-200 ease-out',
        collapsed ? 'w-[68px]' : 'w-60',
      )}
    >
      <Brand collapsed={collapsed} />

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-5 last:mb-0">
            {!collapsed && (
              <p className="mb-2 px-2.5 text-[10px] font-semibold tracking-[0.12em] text-faint uppercase">
                {group.label}
              </p>
            )}
            {collapsed && <div className="mx-2.5 mb-2 h-px bg-line" />}

            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavItem item={item} collapsed={collapsed} count={counts[item.badgeKey]} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <SidebarFooter collapsed={collapsed} onToggleCollapse={onToggleCollapse} />
    </aside>
  );
}

function Brand({ collapsed }) {
  return (
    <Link
      to={PATHS.DASHBOARD}
      className={cn(
        'flex h-16 shrink-0 items-center gap-2.5 border-b border-line',
        collapsed ? 'justify-center px-0' : 'px-5',
      )}
    >
      <Logo />
      {!collapsed && (
        <div className="min-w-0 leading-tight">
          <p className="text-sm font-semibold tracking-tight text-content">ReServe</p>
          <p className="truncate text-[10px] text-faint">Rescue Network</p>
        </div>
      )}
    </Link>
  );
}

/** Mark glyph: a node routing surplus onward. Drawn, not an image asset. */
export function Logo({ size = 28 }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-control bg-brand-600/15 ring-1 ring-brand-500/30"
      style={{ width: size, height: size }}
    >
      <svg
        width={size * 0.6}
        height={size * 0.6}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M4 6h9a5 5 0 0 1 0 10H8"
          stroke="var(--color-brand-400)"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <path
          d="m11 13-3 3 3 3"
          stroke="var(--color-brand-400)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="19" cy="6" r="2" fill="var(--color-brand-400)" />
      </svg>
    </span>
  );
}

function NavItem({ item, collapsed, count }) {
  const Icon = item.icon;
  const { pathname } = useLocation();

  return (
    <NavLink
      to={item.to}
      end={isExactMatchOnly(item, pathname)}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center rounded-control text-sm transition-colors duration-150',
          collapsed ? 'h-10 justify-center' : 'h-9.5 gap-2.5 px-2.5',
          isActive
            ? 'bg-veil-500/20 font-medium text-white'
            : 'text-muted hover:bg-surface-2 hover:text-content',
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* Active rail marker */}
          <span
            className={cn(
              'absolute left-0 h-5 w-0.5 rounded-r-full bg-veil-400 transition-opacity',
              isActive ? 'opacity-100' : 'opacity-0',
            )}
          />
          <Icon size={17} strokeWidth={1.75} className="shrink-0" />
          {!collapsed && <span className="truncate">{item.label}</span>}

          {count > 0 &&
            (collapsed ? (
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-brand-400" />
            ) : (
              <span className="ml-auto rounded-full bg-surface-3 px-1.5 text-[10px] font-medium text-muted tabular">
                {count}
              </span>
            ))}
        </>
      )}
    </NavLink>
  );
}

function SidebarFooter({ collapsed, onToggleCollapse }) {
  return (
    <div className="shrink-0 border-t border-line p-3">
      <button
        type="button"
        onClick={onToggleCollapse}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className={cn(
          'flex h-9 w-full items-center rounded-control text-muted transition-colors hover:bg-surface-2 hover:text-content',
          collapsed ? 'justify-center' : 'gap-2.5 px-2.5 text-xs',
        )}
      >
        {collapsed ? (
          <PanelLeftOpen size={16} strokeWidth={1.75} />
        ) : (
          <>
            <PanelLeftClose size={16} strokeWidth={1.75} />
            Collapse
          </>
        )}
      </button>
    </div>
  );
}

/** Slide-over version of the same navigation, used on tablet widths. */
export function SidebarDrawer({ open, onClose, counts = {} }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <div className="absolute inset-0 bg-surface-0/80" onClick={onClose} />

      <div className="animate-fade-up absolute inset-y-0 left-0 flex w-64 flex-col border-r border-line bg-surface-1">
        <Brand collapsed={false} />

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4" onClick={onClose}>
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-5 last:mb-0">
              <p className="mb-2 px-2.5 text-[10px] font-semibold tracking-[0.12em] text-faint uppercase">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavItem item={item} collapsed={false} count={counts[item.badgeKey]} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <Link
          to={PATHS.PROFILE}
          onClick={onClose}
          className="flex h-14 shrink-0 items-center justify-between border-t border-line px-4 text-sm text-muted hover:text-content"
        >
          Organization profile
          <ChevronRight size={15} strokeWidth={1.75} />
        </Link>
      </div>
    </div>
  );
}
