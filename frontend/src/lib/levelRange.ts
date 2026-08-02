export type LevelRange = { min: number; max: number };

export const DEFAULT_LEVEL_RANGE: LevelRange = { min: 20, max: 85 };
export const LEVEL_ABSOLUTE_MIN = 1;
export const LEVEL_ABSOLUTE_MAX = 99;

export function intersectLevelBounds(a: LevelRange, b: LevelRange): LevelRange {
  const min = Math.max(a.min, b.min);
  const max = Math.min(a.max, b.max);
  if (min > max) {
    return { min: b.min, max: b.max };
  }
  return { min, max };
}

export function resolveDataBounds(dataBounds?: LevelRange): LevelRange {
  const absolute = { min: LEVEL_ABSOLUTE_MIN, max: LEVEL_ABSOLUTE_MAX };
  if (!dataBounds) return absolute;
  return intersectLevelBounds(absolute, dataBounds);
}

/** Slider limits: full data range for unrestricted users, otherwise global restriction. */
export function resolveSliderBounds(
  dataBounds: LevelRange,
  options: { unrestricted: boolean; restriction?: LevelRange | null },
): LevelRange {
  if (options.unrestricted) return dataBounds;
  if (!options.restriction) return dataBounds;
  return intersectLevelBounds(dataBounds, options.restriction);
}

/** Initial filter values from preset, optionally clamped to restriction (not vice versa). */
export function resolveInitialLevelRange(
  preset: LevelRange,
  dataBounds: LevelRange,
  options: { unrestricted: boolean; restriction?: LevelRange | null },
): LevelRange {
  const allowed = options.unrestricted
    ? dataBounds
    : options.restriction
      ? intersectLevelBounds(dataBounds, options.restriction)
      : dataBounds;
  return clampLevelRange(preset, allowed);
}

export function clampLevelRange(
  range: LevelRange,
  bounds?: { min: number; max: number },
): LevelRange {
  const absMin = bounds?.min ?? LEVEL_ABSOLUTE_MIN;
  const absMax = bounds?.max ?? LEVEL_ABSOLUTE_MAX;
  let min = Math.max(absMin, Math.min(range.min, absMax));
  let max = Math.max(absMin, Math.min(range.max, absMax));
  if (min > max) {
    [min, max] = [max, min];
  }
  return { min, max };
}

export function normalizeLevelRange(raw: unknown): LevelRange | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.min !== "number" || typeof obj.max !== "number") return null;
  if (!Number.isFinite(obj.min) || !Number.isFinite(obj.max)) return null;
  return clampLevelRange({ min: Math.round(obj.min), max: Math.round(obj.max) });
}
