import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { LoginPayload, RegisterPayload, User } from "../types";
import { api, ApiError } from "../services/api";
import {
  clearAuth,
  getStoredUser,
  getToken,
  setStoredUser,
  setToken,
} from "../services/authStorage";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => getStoredUser());
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setTokenState(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const currentToken = getToken();
    if (!currentToken) {
      setUser(null);
      setTokenState(null);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
      setStoredUser(me);
      setTokenState(currentToken);
    } catch (err) {
      // Token invalid/expired — clear session
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        logout();
      }
    }
  }, [logout]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (getToken()) {
        await refreshUser();
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  const login = useCallback(async (payload: LoginPayload) => {
    const res = await api.login(payload);
    setToken(res.access_token);
    setStoredUser(res.user);
    setTokenState(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const res = await api.register(payload);
    setToken(res.access_token);
    setStoredUser(res.user);
    setTokenState(res.access_token);
    setUser(res.user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, token, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
