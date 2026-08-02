import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { getLevelPreset, getLevelRestriction } from "../api/settings";
import { useAuth } from "./useAuth";
import {
  DEFAULT_LEVEL_RANGE,
  clampLevelRange,
  resolveDataBounds,
  resolveInitialLevelRange,
  resolveSliderBounds,
  type LevelRange,
} from "../lib/levelRange";

type LevelRangeContextType = {
  globalPreset: LevelRange;
  sessionRange: LevelRange | null;
  setSessionRange: (next: LevelRange | null, bounds?: { min: number; max: number }) => void;
  ready: boolean;
};

const LevelRangeContext = createContext<LevelRangeContextType | null>(null);

export function LevelRangeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  const { data: preset, isSuccess: presetReady } = useQuery({
    queryKey: ["level-preset"],
    queryFn: getLevelPreset,
    enabled: Boolean(user),
    staleTime: 1000 * 60 * 5,
  });

  const [sessionRange, setSessionRangeState] = useState<LevelRange | null>(null);

  useEffect(() => {
    setSessionRangeState(null);
  }, [preset?.min, preset?.max, user?.id]);

  const globalPreset = preset ?? DEFAULT_LEVEL_RANGE;

  const setSessionRange = useCallback(
    (next: LevelRange | null, bounds?: { min: number; max: number }) => {
      if (next == null) {
        setSessionRangeState(null);
        return;
      }
      setSessionRangeState(clampLevelRange(next, bounds));
    },
    [],
  );

  const value = useMemo(
    () => ({
      globalPreset,
      sessionRange,
      setSessionRange,
      ready: !user || presetReady,
    }),
    [globalPreset, sessionRange, setSessionRange, presetReady, user],
  );

  return <LevelRangeContext.Provider value={value}>{children}</LevelRangeContext.Provider>;
}

export function useLevelRange(dataBounds?: { min: number; max: number }) {
  const ctx = useContext(LevelRangeContext);
  const { hasPermission } = useAuth();
  if (!ctx) throw new Error("useLevelRange must be used within LevelRangeProvider");

  const unrestricted = hasPermission("feature.level_unrestricted");

  const { data: restriction, isSuccess: restrictionReady } = useQuery({
    queryKey: ["level-restriction"],
    queryFn: getLevelRestriction,
    staleTime: 1000 * 60 * 5,
  });

  const dataRange = useMemo(() => resolveDataBounds(dataBounds), [dataBounds]);

  const boundsReady = unrestricted || restrictionReady;

  const sliderBounds = useMemo(() => {
    if (!boundsReady) {
      return clampLevelRange(ctx.globalPreset, dataRange);
    }
    return resolveSliderBounds(dataRange, {
      unrestricted,
      restriction: unrestricted ? null : restriction,
    });
  }, [boundsReady, ctx.globalPreset, dataRange, restriction, unrestricted]);

  const baseRange = useMemo(() => {
    if (!boundsReady) {
      return clampLevelRange(ctx.globalPreset, dataRange);
    }
    return resolveInitialLevelRange(ctx.globalPreset, dataRange, {
      unrestricted,
      restriction: unrestricted ? null : restriction,
    });
  }, [boundsReady, ctx.globalPreset, dataRange, restriction, unrestricted]);

  const levelRange = useMemo(() => {
    if (!ctx.sessionRange) return baseRange;
    return clampLevelRange(ctx.sessionRange, sliderBounds);
  }, [baseRange, ctx.sessionRange, sliderBounds]);

  const setLevelRange = useCallback(
    (next: LevelRange) => ctx.setSessionRange(next, sliderBounds),
    [ctx, sliderBounds],
  );

  const resetLevelRange = useCallback(() => ctx.setSessionRange(null), [ctx]);

  useEffect(() => {
    if (!ctx.ready || !boundsReady || !ctx.sessionRange) return;
    const clamped = clampLevelRange(ctx.sessionRange, sliderBounds);
    if (clamped.min === ctx.sessionRange.min && clamped.max === ctx.sessionRange.max) return;
    ctx.setSessionRange(clamped, sliderBounds);
  }, [boundsReady, ctx, sliderBounds]);

  return {
    levelRange,
    globalPreset: ctx.globalPreset,
    effectivePreset: baseRange,
    minLevel: levelRange.min,
    maxLevel: levelRange.max,
    setLevelRange,
    resetLevelRange,
    sliderBounds,
    unrestricted,
    restriction: restriction ?? null,
    ready: ctx.ready && boundsReady,
  };
}

export function useLevelSettingsQuery() {
  const presetQuery = useQuery({
    queryKey: ["level-preset"],
    queryFn: getLevelPreset,
    staleTime: 1000 * 60 * 5,
  });
  const restrictionQuery = useQuery({
    queryKey: ["level-restriction"],
    queryFn: getLevelRestriction,
    staleTime: 1000 * 60 * 5,
  });
  return { presetQuery, restrictionQuery };
}
