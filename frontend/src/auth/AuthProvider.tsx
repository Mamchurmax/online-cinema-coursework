import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "../api/auth";
import { tokenStore } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  /** True while a stored token is being checked on page load. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Query keys whose data depends on who is signed in. */
const USER_QUERY_KEYS = new Set(["playback", "history"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(tokenStore.get);
  useEffect(() => tokenStore.subscribe(setToken), []);

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: ({ signal }) => authApi.me(signal),
    enabled: Boolean(token),
    staleTime: Infinity,
  });

  // Per-user data cached for the previous account must not leak into the next one.
  useEffect(() => {
    queryClient.removeQueries({ predicate: (query) => USER_QUERY_KEYS.has(String(query.queryKey[0])) });
  }, [token, queryClient]);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    tokenStore.set(access_token);
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      await authApi.register(email, password, displayName);
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => tokenStore.set(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: token ? (me.data ?? null) : null,
      isLoading: Boolean(token) && me.isPending,
      login,
      register,
      logout,
    }),
    [token, me.data, me.isPending, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
