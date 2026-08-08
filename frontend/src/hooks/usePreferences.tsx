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
  patchPreference,
  putPreference,
  type CraftCartLine,
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
const REFETCH_INTERVAL_MS = 20_000;

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

function cartLineEqual(a: CraftCartLine | undefined, b: CraftCartLine | undefined): boolean {
  if (!a || !b) return false;
  return a.qty === b.qty && (a.variant ?? null) === (b.variant ?? null);
}

function diffPreference<S extends PreferenceScope>(
  scope: S,
  oldValue: ScopePayload[S],
  nextValue: ScopePayload[S],
): Partial<ScopePayload[S]> {
  const patch: Record<string, unknown> = {};
  const oldRecord = oldValue as Record<string, unknown>;
  const nextRecord = nextValue as Record<string, unknown>;
  const keys = new Set([...Object.keys(oldRecord), ...Object.keys(nextRecord)]);

  if (scope === "craft_cart") {
    for (const key of keys) {
      const oldLine = oldRecord[key] as CraftCartLine | undefined;
      const nextLine = nextRecord[key] as CraftCartLine | undefined;
      if (!cartLineEqual(oldLine, nextLine)) {
        patch[key] = nextLine ?? { qty: 0 };
      }
    }
    return patch as Partial<ScopePayload[S]>;
  }

  for (const key of keys) {
    if (oldRecord[key] !== nextRecord[key]) {
      patch[key] = nextRecord[key] ?? 0;
    }
  }
  return patch as Partial<ScopePayload[S]>;
}

function mergePendingPatch<S extends PreferenceScope>(
  scope: S,
  existing: Partial<ScopePayload[S]> | undefined,
  incoming: Partial<ScopePayload[S]>,
): Partial<ScopePayload[S]> {
  if (!existing) return incoming;
  if (scope === "craft_cart") {
    return { ...existing, ...incoming } as Partial<ScopePayload[S]>;
  }
  return { ...existing, ...incoming } as Partial<ScopePayload[S]>;
}

function isScopePayload(value: unknown): value is ScopePayload[PreferenceScope] {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function scopeFromLocalKey(key: string): PreferenceScope | null {
  const entry = Object.entries(LOCAL_KEYS).find(([, localKey]) => localKey === key);
  return entry ? (entry[0] as PreferenceScope) : null;
}

function isRemoteNewer(remoteAt: string | undefined, localAt: string | undefined): boolean {
  if (!remoteAt) return false;
  if (!localAt) return true;
  return remoteAt > localAt;
}

interface PreferencesContextType {
  scopes: ScopeState;
  setScope: <S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => void;
  replaceScope: <S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => Promise<void>;
  synced: boolean;
  saveError: string | null;
}

const PreferencesContext = createContext<PreferencesContextType | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { user, hasPermission } = useAuth();
  const [scopes, setScopes] = useState<ScopeState>(initialState);
  const [synced, setSynced] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const timers = useRef<Partial<Record<PreferenceScope, number>>>({});
  const pendingPatchRef = useRef<Partial<Record<PreferenceScope, Partial<ScopePayload[PreferenceScope]>>>>({});
  const serverUpdatedAtRef = useRef<Partial<Record<PreferenceScope, string>>>({});

  const applyRemote = useCallback(
    (
      remoteScopes: Partial<ScopePayload>,
      remoteUpdatedAt: Partial<Record<PreferenceScope, string>>,
      options?: { allowWhilePending?: boolean },
    ) => {
      setScopes((prev) => {
        let changed = false;
        const next = { ...prev };

        for (const scope of SCOPES) {
          if (!(scope in remoteScopes)) continue;
          if (!options?.allowWhilePending && timers.current[scope]) continue;

          const remoteAt = remoteUpdatedAt[scope];
          const localAt = serverUpdatedAtRef.current[scope];
          if (!isRemoteNewer(remoteAt, localAt)) continue;

          const remoteValue = remoteScopes[scope];
          if (!isScopePayload(remoteValue)) continue;

          next[scope] = remoteValue as ScopePayload[typeof scope];
          writeLocal(scope, remoteValue as ScopePayload[typeof scope]);
          if (remoteAt) serverUpdatedAtRef.current[scope] = remoteAt;
          changed = true;
        }

        return changed ? next : prev;
      });
    },
    [],
  );

  const canSyncScope = useCallback(
    (scope: PreferenceScope) => {
      if (scope === "craft_owned") return hasPermission("feature.craft_warehouse");
      if (scope === "craft_cart") return hasPermission("feature.craft_bulk");
      return true;
    },
    [hasPermission],
  );

  const flushPatch = useCallback(async (scope: PreferenceScope) => {
    if (!canSyncScope(scope)) return;
    const patch = pendingPatchRef.current[scope];
    if (!patch || Object.keys(patch).length === 0) return;

    pendingPatchRef.current[scope] = undefined;
    try {
      const response = await patchPreference(scope, patch);
      if (response.updated_at) {
        serverUpdatedAtRef.current[scope] = response.updated_at;
      }
      setSaveError(null);
    } catch {
      pendingPatchRef.current[scope] = mergePendingPatch(
        scope,
        pendingPatchRef.current[scope],
        patch,
      );
      setSaveError("Не удалось сохранить настройки. Проверьте соединение.");
    }
  }, [canSyncScope]);

  const refetchPreferences = useCallback(async () => {
    if (!user) return;
    try {
      const remote = await getPreferences();
      applyRemote(remote.scopes, remote.updated_at);
      setSynced(true);
      setSaveError(null);
    } catch {
      setSynced(false);
    }
  }, [applyRemote, user]);

  useEffect(() => {
    if (!user) {
      setSynced(false);
      serverUpdatedAtRef.current = {};
      pendingPatchRef.current = {};
      return;
    }
    let cancelled = false;

    getPreferences()
      .then((remote) => {
        if (cancelled) return;
        setScopes((prev) => {
          const next = { ...prev };
          for (const scope of SCOPES) {
            if (scope in remote.scopes) {
              const serverValue = remote.scopes[scope];
              if (isScopePayload(serverValue)) {
                next[scope] = serverValue as ScopePayload[typeof scope];
                writeLocal(scope, serverValue as ScopePayload[typeof scope]);
              }
              if (remote.updated_at[scope]) {
                serverUpdatedAtRef.current[scope] = remote.updated_at[scope];
              }
            } else if (Object.keys(prev[scope]).length > 0 && canSyncScope(scope)) {
              void patchPreference(scope, prev[scope] as Partial<ScopePayload[typeof scope]>)
                .then((response) => {
                  if (response.updated_at) {
                    serverUpdatedAtRef.current[scope] = response.updated_at;
                  }
                })
                .catch(() => {
                  setSaveError("Не удалось синхронизировать локальные настройки с сервером.");
                });
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
  }, [user, canSyncScope]);

  useEffect(() => {
    if (!user) return;

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refetchPreferences();
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refetchPreferences();
      }
    }, REFETCH_INTERVAL_MS);

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.clearInterval(intervalId);
    };
  }, [refetchPreferences, user]);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (!event.key) return;
      const scope = scopeFromLocalKey(event.key);
      if (!scope || event.newValue == null) return;
      if (timers.current[scope]) return;

      try {
        const parsed = JSON.parse(event.newValue);
        if (!isScopePayload(parsed)) return;
        setScopes((prev) => ({ ...prev, [scope]: parsed as ScopePayload[typeof scope] }));
      } catch {
        // Ignore malformed cache entries from other tabs.
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setScope = useCallback(
    <S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => {
      setScopes((prev) => {
        const patch = diffPreference(scope, prev[scope], value);
        if (Object.keys(patch).length > 0) {
          pendingPatchRef.current[scope] = mergePendingPatch(
            scope,
            pendingPatchRef.current[scope],
            patch,
          ) as Partial<ScopePayload[typeof scope]>;
        }
        return { ...prev, [scope]: value };
      });
      writeLocal(scope, value);

      window.clearTimeout(timers.current[scope]);
      timers.current[scope] = window.setTimeout(() => {
        timers.current[scope] = undefined;
        void flushPatch(scope);
      }, SAVE_DEBOUNCE_MS);
    },
    [flushPatch],
  );

  const replaceScope = useCallback(
    async <S extends PreferenceScope>(scope: S, value: ScopePayload[S]) => {
      window.clearTimeout(timers.current[scope]);
      timers.current[scope] = undefined;
      pendingPatchRef.current[scope] = undefined;
      setScopes((prev) => ({ ...prev, [scope]: value }));
      writeLocal(scope, value);
      if (!canSyncScope(scope)) return;
      try {
        const response = await putPreference(scope, value);
        if (response.updated_at) {
          serverUpdatedAtRef.current[scope] = response.updated_at;
        }
        setSaveError(null);
      } catch {
        setSaveError("Не удалось сохранить настройки. Проверьте соединение.");
      }
    },
    [canSyncScope],
  );

  useEffect(
    () => () => {
      Object.values(timers.current).forEach((id) => {
        if (id) window.clearTimeout(id);
      });
    },
    [],
  );

  const value = useMemo(
    () => ({ scopes, setScope, replaceScope, synced, saveError }),
    [scopes, setScope, replaceScope, synced, saveError],
  );
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

/** Current value of one scope plus a setter that syncs to the server. */
export function usePreference<S extends PreferenceScope>(
  scope: S,
): [ScopePayload[S], (next: ScopePayload[S]) => void, (next: ScopePayload[S]) => Promise<void>] {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreference must be used within PreferencesProvider");
  const setValue = useCallback(
    (next: ScopePayload[S]) => ctx.setScope(scope, next),
    [ctx, scope],
  );
  const replaceValue = useCallback(
    (next: ScopePayload[S]) => ctx.replaceScope(scope, next),
    [ctx, scope],
  );
  return [ctx.scopes[scope], setValue, replaceValue];
}

/** Typed shortcut for the mass-craft cart scope. */
export function useCraftCartPreference(): [CraftCartPayload, (next: CraftCartPayload) => void] {
  return usePreference("craft_cart");
}

export function usePreferencesSyncState(): { synced: boolean; saveError: string | null } {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferencesSyncState must be used within PreferencesProvider");
  return { synced: ctx.synced, saveError: ctx.saveError };
}
