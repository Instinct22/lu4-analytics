import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { clearTokens, setTokens } from "../api/client";
import { fetchMe, login as apiLogin, type User } from "../api/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    setUser(await fetchMe());
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const tokens = await apiLogin(username, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(await fetchMe());
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  const hasPermission = (permission: string) =>
    Boolean(user?.permissions?.includes(permission));

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasPermission, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** First allowed app route for the current user (fallback /craft). */
export function defaultHomePath(permissions: string[] | undefined): string {
  const order = [
    ["nav.dashboard", "/"],
    ["nav.craft", "/craft"],
    ["nav.items", "/items"],
    ["nav.character", "/character"],
    ["nav.charts", "/charts"],
    ["nav.statistics", "/statistics"],
    ["nav.resources", "/resources"],
    ["nav.search", "/search"],
    ["nav.raid_bosses", "/raid-bosses"],
    ["nav.admin", "/admin"],
  ] as const;
  for (const [perm, path] of order) {
    if (permissions?.includes(perm)) return path;
  }
  return "/craft";
}
