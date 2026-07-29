import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  getPreferences,
  putPreference,
  type CraftCartPayload,
  type PreferenceScope,
  type ScopePayload,
} from "../api/preferences";
import { useAuth } from "./useAuth";

/** localStorage keys kept as an offline cache and as the migration source. */
const LOCAL_KEYS: Record<PreferenceScope, string> = {
  craft_owned: "lu4_craft_owned",
  craft_prices: "lu4_craft_prices",
  craft_variants: "lu4_craft_variants",
  craft_cart: "lu4_craft_cart",
};

const SCOPES = Object.keys(LOCAL_KEYS) as PreferenceScope[];

const SAVE_DEBOUNCE_MS = 700;

type ScopeState = ScopePayload;

function readLocal(scope: PreferenceScope): ScopePayload[typeof scope] {
  try {
    const raw = localStorage.getItem(LOCAL_KEYS[scope]);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {} as ScopePayload[typeof scope];
  }
}

function writeLocal(scope: PreferenceScope, value: ScopePayload[typeof scope]) {
  try {
    localStorage.setItem(LOCAL_KEYS[scope], JSON.stringify(value));
  } catch {
    // Quota or private mode: the server copy is authoritative anyway.
  }
}

function initialState(): ScopeState {
  return SCOPES.reduce((acc, scope) => {
    acc[scope] = readLocal(scope);
    return acc;
  }, {} as ScopeState);
}

interface PreferencesContextType {
  scopes: ScopeState;
  setScope: <S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => void;
  synced: boolean;
}

const PreferencesContext = createContext<PreferencesContextType | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [scopes, setScopes] = useState<ScopeState>(initialState);
  const [synced, setSynced] = useState(false);
  const timers = useRef<Partial<Record<PreferenceScope, number>>>({});

  useEffect(() => {
    if (!user) {
      setSynced(false);
      return;
    }
    let cancelled = false;

    getPreferences()
      .then((remote) => {
        if (cancelled) return;
        setScopes((prev) => {
          const next = { ...prev };
          for (const scope of SCOPES) {
            const server = remote[scope];
            if (server && Object.keys(server).length > 0) {
              next[scope] = server;
              writeLocal(scope, server);
            } else if (Object.keys(prev[scope]).length > 0) {
              // First login after the move: push what the browser still holds.
              void putPreference(scope, prev[scope]).catch(() => undefined);
            }
          }
          return next;
        });
        setSynced(true);
      })
      .catch(() => setSynced(false));

    return () => {
      cancelled = true;
    };
  }, [user]);

  const setScope = useCallback(<S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => {
    setScopes((prev) => ({ ...prev, [scope]: value }));
    writeLocal(scope, value);

    window.clearTimeout(timers.current[scope]);
    timers.current[scope] = window.setTimeout(() => {
      void putPreference(scope, value).catch(() => undefined);
    }, SAVE_DEBOUNCE_MS);
  }, []);

  useEffect(() => () => {
    Object.values(timers.current).forEach((id) => window.clearTimeout(id));
  }, []);

  const value = useMemo(() => ({ scopes, setScope, synced }), [scopes, setScope, synced]);
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

/** Current value of one scope plus a setter that syncs to the server. */
export function usePreference<S extends PreferenceScope>(
  scope: S,
): [ScopePayload[S], (next: ScopePayload[S]) => void] {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreference must be used within PreferencesProvider");
  const setValue = useCallback(
    (next: ScopePayload[S]) => ctx.setScope(scope, next),
    [ctx, scope],
  );
  return [ctx.scopes[scope], setValue];
}

/** Typed shortcut for the mass-craft cart scope. */
export function useCraftCartPreference(): [CraftCartPayload, (next: CraftCartPayload) => void] {
  return usePreference("craft_cart");
}
