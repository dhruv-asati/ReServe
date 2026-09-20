import { useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { Logo } from '@/components/Sidebar';
import StaggeredMenu from '@/components/StaggeredMenu';
import Topbar from '@/components/Topbar';
import MobileNav from '@/components/MobileNav';
import { NAV_ITEMS, isExactMatchOnly } from '@/routes/navigation';
import { PATHS } from '@/routes/paths';

/**
 * Operational shell: a left-hand staggered menu (all screen sizes), a sticky
 * topbar, the scrolling content area, and a bottom bar on mobile.
 *
 * The menu's toggle + logo are fixed over the topbar's left edge; the Topbar
 * reserves matching space for them.
 *
 * `counts` will be fed by live data in a later step; the shape is fixed now so
 * nav badges do not need a refactor when real numbers arrive.
 */
export default function AppLayout() {
  const { pathname } = useLocation();

  // Placeholder counters until live data lands.
  const counts = { requests: 6, live: 3 };

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
        <Topbar notificationCount={4} />

        {/* Bottom padding clears MobileNav, which is hidden from md up */}
        <main className="min-w-0 flex-1 px-4 pb-24 pt-5 sm:px-6 md:pb-8">
          <div className="mx-auto w-full max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>

      <MobileNav counts={counts} />
    </div>
  );
}
