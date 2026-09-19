import { useSyncExternalStore } from 'react';

import {
  getReallocationDemoState,
  subscribeReallocationDemo,
} from '@/services/reallocationDemoService';

/**
 * Subscribe a component to the RS-1024 "recipient unavailable" demo state
 * (see services/reallocationDemoService.js). Every page that shows RS-1024
 * reads it through this hook, so they all update together — including while
 * the mock reallocation progress is ticking.
 *
 * Returns `{ unavailable, progress }`. Frontend-only demo state.
 */
export default function useReallocationDemo() {
  return useSyncExternalStore(
    subscribeReallocationDemo,
    getReallocationDemoState,
    getReallocationDemoState,
  );
}
