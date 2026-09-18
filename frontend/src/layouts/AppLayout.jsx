import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import Sidebar, { SidebarDrawer } from '@/components/Sidebar';
import Topbar from '@/components/Topbar';
import MobileNav from '@/components/MobileNav';

/**
 * Operational shell: sidebar (desktop) / drawer (tablet) / bottom bar (mobile),
 * a sticky topbar, and the scrolling content area.
 *
 * `counts` will be fed by live data in a later step; the shape is fixed now so
 * nav badges do not need a refactor when real numbers arrive.
 */
export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return window.localStorage.getItem('reserve.sidebarCollapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { pathname } = useLocation();

  // Placeholder counters until live data lands.
  const counts = { requests: 6, live: 3 };

  useEffect(() => {
    try {
      window.localStorage.setItem('reserve.sidebarCollapsed', String(collapsed));
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  // Close the drawer and return to the top of the page on navigation.
  useEffect(() => {
    setDrawerOpen(false);
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="flex min-h-screen bg-surface-0">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((value) => !value)}
        counts={counts}
      />

      <SidebarDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} counts={counts} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMenu={() => setDrawerOpen(true)} notificationCount={4} />

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
