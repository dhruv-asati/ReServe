import { useCallback, useState } from 'react';

/**
 * State backed by localStorage. Reads are lazy and guarded, so a blocked or
 * full storage never breaks rendering — the initial value is used instead.
 */
export default function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored !== null ? JSON.parse(stored) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const set = useCallback(
    (next) => {
      setValue((current) => {
        const resolved = typeof next === 'function' ? next(current) : next;
        try {
          window.localStorage.setItem(key, JSON.stringify(resolved));
        } catch {
          /* storage unavailable — keep in-memory state */
        }
        return resolved;
      });
    },
    [key],
  );

  return [value, set];
}
