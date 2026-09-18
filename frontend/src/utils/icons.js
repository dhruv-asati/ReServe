import {
  UtensilsCrossed,
  Pill,
  PackagePlus,
  Sparkles,
  GitBranch,
  Handshake,
  CheckCircle2,
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

/** Icon for each stage in the rescue lifecycle, used by ActivityTimeline. */
export const ACTIVITY_STAGE_ICONS = {
  created: PackagePlus,
  analyzed: Sparkles,
  matched: GitBranch,
  assigned: Handshake,
  completed: CheckCircle2,
};
