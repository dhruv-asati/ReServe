import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { Logo } from '@/components/Sidebar';
import StaggeredMenu from '@/components/StaggeredMenu';
import Topbar from '@/components/Topbar';
import ErrorBoundary from '@/components/ErrorBoundary';
import MobileNav from '@/components/MobileNav';
import { NAV_ITEMS, isExactMatchOnly } from '@/routes/navigation';
import { PATHS } from '@/routes/paths';
import { getIncomingRequests, getOutgoingRequests } from '@/services/requestsService';
import { getActiveOperations } from '@/services/operationsService';
import { listNotifications } from '@/services/notificationsService';

/**
 * Operational shell: a left-hand staggered menu (all screen sizes), a sticky
 * topbar, the scrolling content area, and a bottom bar on mobile.
 *
 * The menu's toggle + logo are fixed over the topbar's left edge; the Topbar
 * reserves matching space for them.
 *
 * `counts` (menu badges) and the topbar's notification dot come from the same
 * services the pages use — open requests (incoming + outgoing), active
 * operations, and the unread notification count — and refresh on navigation.
 * A count that fails to load simply shows nothing.
 */
export default function AppLayout() {
  const { pathname } = useLocation();

  const [counts, setCounts] = useState({ requests: 0, live: 0 });
  const [notificationCount, setNotificationCount] = useState(0);

  // Refresh the badges whenever the route changes.
  useEffect(() => {
    let active = true;
    const size = (result) =>
      result.status === 'fulfilled' && Array.isArray(result.value) ? result.value.length : 0;

    Promise.allSettled([
      getIncomingRequests(),
      getOutgoingRequests(),
      getActiveOperations(),
      listNotifications({ limit: 1 }),
    ]).then(([incoming, outgoing, live, notifications]) => {
      if (!active) return;
      setCounts({ requests: size(incoming) + size(outgoing), live: size(live) });
      setNotificationCount(
        notifications.status === 'fulfilled' ? notifications.value?.unread_count ?? 0 : 0,
      );
    });

    return () => {
      active = false;
    };
  }, [pathname]);

  // Return to the top of the page on navigation.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);

  const menuItems = NAV_ITEMS.map((item) => ({
    label: item.label,
    ariaLabel: `Go to ${item.label}`,
    link: item.to,
    end: isExactMatchOnly(item, pathname),
    count: counts[item.badgeKey],
  }));

  return (
    <div className="flex min-h-screen w-full max-w-full overflow-x-clip bg-transparent">
      <StaggeredMenu
        isFixed
        position="left"
        items={menuItems}
        displaySocials={false}
        displayItemNumbering
        logo={
          <Link to={PATHS.DASHBOARD} aria-label="ReServe home">
            <Logo size={28} />
          </Link>
        }
        menuButtonColor="#e6edf5"
        changeMenuColorOnOpen={false}
        colors={['#4a3bb0', '#5f4dd6']}
        accentColor="#9b8cf5"
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          notificationCount={notificationCount}
          onNotificationCountChange={setNotificationCount}
        />

        {/* Bottom padding clears MobileNav, which is hidden from md up */}
        <main className="min-w-0 flex-1 px-4 pb-24 pt-5 sm:px-6 md:pb-8">
          <div className="mx-auto w-full max-w-[1600px]">
            {/* Keyed by route so a page that crashed recovers when you navigate away. */}
            <ErrorBoundary key={pathname}>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>

      <MobileNav counts={counts} />
    </div>
  );
}
