import { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { setAuthFailureHandler } from '@/services/api';
import {
  getStoredSession,
  loginUser,
  logoutUser,
  refreshSessionUser,
  registerUser,
} from '@/services/auth';

/**
 * Auth state, backed by the ReServe backend (JWT) via services/auth.
 *
 * The session user is read synchronously from storage on first render so
 * there is no flash of "unauthenticated" — a page refresh keeps the user
 * signed in without a loading gate. The profile is then re-fetched in the
 * background, and if the backend says the session is over (expired access
 * token that cannot be refreshed) the user is signed out.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredSession());

  // The API client calls this when a request fails with 401 and the refresh
  // token doesn't work either.
  useEffect(
    () =>
      setAuthFailureHandler(() => {
        logoutUser();
        setUser(null);
      }),
    [],
  );

  // Keep tabs in sync: signing out (or in) in another tab changes the stored
  // tokens/session, and this tab should follow instead of showing stale pages.
  useEffect(() => {
    function handleStorage(event) {
      if (event.key === null || event.key === 'reserve.token' || event.key === 'reserve.session') {
        setUser(getStoredSession());
      }
    }
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  // Refresh the stored session from the backend once, on load.
  useEffect(() => {
    if (!getStoredSession()) return undefined;

    let cancelled = false;
    refreshSessionUser()
      .then((freshUser) => {
        if (!cancelled) setUser(freshUser);
      })
      .catch(() => {
        /* offline or a server error: keep the stored session; a real 401 signs out above */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (credentials) => {
    const sessionUser = await loginUser(credentials);
    setUser(sessionUser);
    return sessionUser;
  }, []);

  const register = useCallback(async (details) => {
    const sessionUser = await registerUser(details);
    setUser(sessionUser);
    return sessionUser;
  }, []);

  const logout = useCallback(() => {
    logoutUser();
    setUser(null);
  }, []);

  /** Re-pull the profile from the backend and refresh the stored session (e.g. after editing it elsewhere). */
  const refreshUser = useCallback(async () => {
    const freshUser = await refreshSessionUser();
    setUser(freshUser);
    return freshUser;
  }, []);

  const value = {
    user,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
