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
  Navigation,
  PackageCheck,
  RefreshCw,
  Shuffle,
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
 * assigned → pickup → completed. `in_transit` and `delivered` extend this
 * set for the Operations Control Center's 7-stage tracker (OperationStageTracker),
 * without changing the meaning of the existing keys used elsewhere.
 *
 * `reallocating` and `rematched` are the two stages the RS-1024
 * recipient-unavailable demo inserts into that tracker (and into the
 * operation's event feed) once a recipient drops out: the operation is being
 * re-planned, then matched again to the updated recipients. They extend the
 * set the same way — no existing key changes meaning.
 */
export const ACTIVITY_STAGE_ICONS = {
  created: PackagePlus,
  analyzed: Sparkles,
  matched: GitBranch,
  assigned: Handshake,
  pickup: Truck,
  in_transit: Navigation,
  completed: CheckCircle2,
  delivered: PackageCheck,
  reallocating: RefreshCw,
  rematched: Shuffle,
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
