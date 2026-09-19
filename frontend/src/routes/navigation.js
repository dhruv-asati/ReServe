import {
  LayoutDashboard,
  PlusCircle,
  ClipboardList,
  GitBranch,
  Radio,
  Map,
  BarChart3,
} from 'lucide-react';

import { PATHS } from './paths';

/**
 * Sidebar navigation, grouped by what an operator is doing.
 *
 * `end` marks routes that should only highlight on an exact match, so the
 * dashboard index does not stay active while a child route is open.
 * `badgeKey` names a live counter the shell can fill in later (open requests,
 * in-flight operations) without changing this file.
 */
export const NAV_GROUPS = [
  {
    label: 'Operations',
    items: [
      { label: 'Overview', to: PATHS.DASHBOARD, icon: LayoutDashboard, end: true },
      { label: 'Create Rescue', to: PATHS.CREATE_RESCUE, icon: PlusCircle },
      { label: 'Requests', to: PATHS.RESCUE_REQUESTS, icon: ClipboardList, badgeKey: 'requests', end: true },
      { label: 'Matching', to: PATHS.MATCHING, icon: GitBranch },
      { label: 'Live Operations', to: PATHS.LIVE_OPERATIONS, icon: Radio, badgeKey: 'live' },
    ],
  },
  {
    label: 'Network',
    items: [
      { label: 'Rescue Network', to: PATHS.RESCUE_NETWORK, icon: Map },
      { label: 'Analytics', to: PATHS.ANALYTICS, icon: BarChart3 },
    ],
  },
];

/** Flat list, handy for the mobile bar and for breadcrumb lookups. */
export const NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items);

/** The five destinations that fit a mobile bottom bar. */
export const MOBILE_NAV_ITEMS = [
  NAV_ITEMS[0], // Overview
  NAV_ITEMS[2], // Requests
  NAV_ITEMS[1], // Create Rescue — centre, emphasised
  NAV_ITEMS[4], // Live Operations
  NAV_ITEMS[5], // Rescue Network
];
