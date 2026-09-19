import { NavLink, useLocation } from 'react-router-dom';
import { Plus } from 'lucide-react';

import { MOBILE_NAV_ITEMS, isExactMatchOnly } from '@/routes/navigation';
import { PATHS } from '@/routes/paths';
import { cn } from '@/utils/cn';

/**
 * Mobile bottom bar.
 *
 * Five destinations with Create Rescue raised in the centre — logging surplus
 * is the one thing a provider does from a phone, usually in a hurry at the end
 * of service. Everything else stays reachable through the drawer.
 */
export default function MobileNav({ counts = {} }) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface-1/95 backdrop-blur-sm md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <ul className="flex items-stretch">
        {MOBILE_NAV_ITEMS.map((item) => {
          const isCreate = item.to === PATHS.CREATE_RESCUE;
          return (
            <li key={item.to} className="flex-1">
              {isCreate ? <CreateTab /> : <Tab item={item} count={counts[item.badgeKey]} />}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function Tab({ item, count }) {
  const Icon = item.icon;
  const { pathname } = useLocation();

  return (
    <NavLink
      to={item.to}
      end={isExactMatchOnly(item, pathname)}
      className={({ isActive }) =>
        cn(
          'flex h-14 flex-col items-center justify-center gap-1 text-[10px] transition-colors',
          isActive ? 'text-white' : 'text-faint',
        )
      }
    >
      <span className="relative">
        <Icon size={19} strokeWidth={1.75} />
        {count > 0 && (
          <span className="absolute -right-1.5 -top-1 h-1.5 w-1.5 rounded-full bg-brand-400" />
        )}
      </span>
      <span className="max-w-full truncate px-1">{shortLabel(item.label)}</span>
    </NavLink>
  );
}

function CreateTab() {
  return (
    <NavLink
      to={PATHS.CREATE_RESCUE}
      aria-label="Create rescue"
      className="flex h-14 flex-col items-center justify-center"
    >
      {({ isActive }) => (
        <span
          className={cn(
            'grid h-11 w-11 -translate-y-3 place-items-center rounded-full ring-4 ring-surface-1 transition-colors',
            isActive ? 'bg-veil-500 text-white' : 'bg-veil-600 text-white',
          )}
        >
          <Plus size={20} strokeWidth={2.25} />
        </span>
      )}
    </NavLink>
  );
}

/** Bottom-bar labels have roughly 9 characters before they truncate. */
function shortLabel(label) {
  const map = {
    'Live Operations': 'Live Ops',
    'Rescue Network': 'Network',
    'Create Rescue': 'Create',
  };
  return map[label] ?? label;
}
