import {
  UtensilsCrossed,
  Pill,
  PackagePlus,
  Sparkles,
  GitBranch,
  Handshake,
  CheckCircle2,
  Store,
  Users,
  Truck,
  Warehouse,
} from 'lucide-react';

/**
 * Maps the string icon names in utils/theme.js (RESOURCE_META) to actual
 * Lucide components. theme.js keeps icons as strings so it stays framework
 * data (usable by canvas/map surfaces too); components resolve through here.
 */
export const RESOURCE_ICONS = {
  food: UtensilsCrossed,
  medical: Pill,
};

/**
 * Icon for each stage in the rescue lifecycle, used by ActivityTimeline.
 * Order mirrors the operational flow: created → analyzed → matched →
 * assigned → pickup → completed.
 */
export const ACTIVITY_STAGE_ICONS = {
  created: PackagePlus,
  analyzed: Sparkles,
  matched: GitBranch,
  assigned: Handshake,
  pickup: Truck,
  completed: CheckCircle2,
};

/**
 * Icon for each network role, used by MapPreview markers and MapLegend.
 * Keeps the "which shape means what" decision in one place, same pattern
 * as RESOURCE_ICONS above.
 */
export const NETWORK_ROLE_ICONS = {
  provider: Store,
  recipient: Users,
  partner: Truck,
  hub: Warehouse,
};
