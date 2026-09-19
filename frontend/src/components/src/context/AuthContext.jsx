import { createContext, useCallback, useContext, useState } from 'react';

import { getStoredSession, loginMockUser, logoutMockUser, registerMockUser } from '@/services/auth';

/**
 * Frontend-only auth state, backed by localStorage via services/auth.
 *
 * Session is read synchronously on first render so there is no flash of
 * "unauthenticated" while storage is checked — a page refresh keeps the
 * user signed in without a loading gate.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredSession());

  const login = useCallback(async (credentials) => {
    const sessionUser = await loginMockUser(credentials);
    setUser(sessionUser);
    return sessionUser;
  }, []);

  const register = useCallback(async (details) => {
    const sessionUser = await registerMockUser(details);
    setUser(sessionUser);
    return sessionUser;
  }, []);

  const logout = useCallback(() => {
    logoutMockUser();
    setUser(null);
  }, []);

  const value = {
    user,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
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
