/**
 * Cumulative EXP at the start of each level (Lu4 wiki: Gaining Experience and Penalties).
 * Index = level. Level 0 unused; levels 1..75.
 */
export const EXP_TOTAL: readonly number[] = [
  0, // unused
  0,
  68,
  363,
  1168,
  2884,
  6038,
  11287,
  19423,
  31378,
  48229,
  71202,
  103652,
  148742,
  210382,
  293262,
  402862,
  545462,
  728062,
  957962,
  1242662,
  1589703,
  2005503,
  2499103,
  3079403,
  3755003,
  4534103,
  5423803,
  6430038,
  7557101,
  8830547,
  10265878,
  11880025,
  13691468,
  15720358,
  17988657,
  20520261,
  23341163,
  26479602,
  29966217,
  33834236,
  38119631,
  42861328,
  48101384,
  53885204,
  60261749,
  67283757,
  75007986,
  83495438,
  92811624,
  103026820,
  115286820,
  130006820,
  147646820,
  168786820,
  194096820,
  224376820,
  260586820,
  303846820,
  355496820,
  417126820,
  490606570,
  578146570,
  681546570,
  802746570,
  943546570,
  1105746570,
  1291146570,
  1501146570,
  1737146570,
  2000000000,
  2290500000,
  2619100000,
  2999800000,
  3451400000,
  4000000000,
];

export const MIN_LEVEL = 1;
export const MAX_LEVEL = EXP_TOTAL.length - 1;

export type FatigueState = "green" | "orange" | "red";

/**
 * XP multiplier for mob/RB kills by Fatigue status:
 * green  — Battle Ready lv.1 (100%)
 * orange — Fatigue lv.2 (×0.5)
 * red    — Battle Worn (×0.025)
 */
export const FATIGUE_MULTIPLIER: Record<FatigueState, number> = {
  green: 1,
  orange: 0.5,
  red: 0.025,
};

export const FATIGUE_LABELS: Record<FatigueState, string> = {
  green: "Готов к бою (Lv.1)",
  orange: "Утомление (Lv.2)",
  red: "Усталость",
};

export function expToNextLevel(level: number): number | null {
  if (level < MIN_LEVEL || level >= MAX_LEVEL) return null;
  return EXP_TOTAL[level + 1]! - EXP_TOTAL[level]!;
}

/** Absolute EXP from level + percent progress within the level. */
export function absoluteExp(level: number, percent: number): number {
  const lv = clampLevel(level);
  const pct = clampPercent(percent);
  const span = expToNextLevel(lv);
  if (span == null) return EXP_TOTAL[MAX_LEVEL]!;
  return EXP_TOTAL[lv]! + (span * pct) / 100;
}

export function levelFromAbsoluteExp(total: number): { level: number; percent: number } {
  const xp = Math.max(0, total);
  if (xp >= EXP_TOTAL[MAX_LEVEL]!) {
    return { level: MAX_LEVEL, percent: 100 };
  }
  let level = MIN_LEVEL;
  for (let lv = MAX_LEVEL; lv >= MIN_LEVEL; lv--) {
    if (xp >= EXP_TOTAL[lv]!) {
      level = lv;
      break;
    }
  }
  const span = expToNextLevel(level);
  if (span == null || span <= 0) {
    return { level, percent: 100 };
  }
  const into = xp - EXP_TOTAL[level]!;
  const percent = Math.min(100, Math.max(0, (into / span) * 100));
  return { level, percent };
}

export function applyFatigue(baseExp: number, fatigue: FatigueState): number {
  return baseExp * FATIGUE_MULTIPLIER[fatigue];
}

export function projectLevel(
  level: number,
  percent: number,
  gainedExp: number,
  fatigue: FatigueState,
): { level: number; percent: number; appliedExp: number } {
  const appliedExp = applyFatigue(Math.max(0, gainedExp), fatigue);
  const result = levelFromAbsoluteExp(absoluteExp(level, percent) + appliedExp);
  return { ...result, appliedExp };
}

/** Character EXP needed to go from (level, %) to target level at toPercent (default 0%). */
export function expNeededToReach(
  fromLevel: number,
  fromPercent: number,
  toLevel: number,
  toPercent = 0,
): number {
  return Math.max(0, absoluteExp(toLevel, toPercent) - absoluteExp(fromLevel, fromPercent));
}

/** Base kill EXP that must be farmed to gain `needed` character EXP under fatigue. */
export function baseExpForNeeded(needed: number, fatigue: FatigueState): number {
  const mult = FATIGUE_MULTIPLIER[fatigue];
  if (mult <= 0) return Infinity;
  return needed / mult;
}

export type FatiguePools = {
  greenRemaining: number;
  yellowRemaining: number;
};

/** Remaining points from each daily pool by its own leftover percent. */
export function remainingFatiguePools(
  dailyGreen: number,
  dailyYellow: number,
  greenPercent: number,
  yellowPercent: number,
): FatiguePools {
  return {
    greenRemaining: (Math.max(0, dailyGreen) * clampPercent(greenPercent)) / 100,
    yellowRemaining: (Math.max(0, dailyYellow) * clampPercent(yellowPercent)) / 100,
  };
}

/**
 * Apply base kill EXP through green (×1) → yellow (×0.5) → red (×0.025).
 * Green/yellow consume fatigue equal to applied XP; red does not consume.
 */
export function applyBaseExpWithPools(
  baseExp: number,
  pools: FatiguePools,
): { appliedExp: number; greenUsed: number; yellowUsed: number; redBase: number } {
  let left = Math.max(0, baseExp);
  let applied = 0;
  let greenRem = Math.max(0, pools.greenRemaining);
  let yellowRem = Math.max(0, pools.yellowRemaining);

  const greenBase = Math.min(left, greenRem);
  applied += greenBase;
  left -= greenBase;
  greenRem -= greenBase;
  const greenUsed = greenBase;

  const yellowAppliedMax = yellowRem;
  const yellowBaseMax = yellowAppliedMax / FATIGUE_MULTIPLIER.orange;
  const yellowBase = Math.min(left, yellowBaseMax);
  const yellowApplied = yellowBase * FATIGUE_MULTIPLIER.orange;
  applied += yellowApplied;
  left -= yellowBase;
  const yellowUsed = yellowApplied;

  const redBase = left;
  applied += redBase * FATIGUE_MULTIPLIER.red;

  return { appliedExp: applied, greenUsed, yellowUsed, redBase };
}

export type FatigueBaseBreakdown = {
  /** Total base kill EXP to farm. */
  total: number;
  /** Base EXP while green (×1). */
  green: number;
  /** Base EXP while orange (×0.5). */
  orange: number;
  /** Base EXP while red (×0.025). */
  red: number;
  /** Character EXP gained in each tier. */
  appliedGreen: number;
  appliedOrange: number;
  appliedRed: number;
};

/** Minutes in one fatigue reset cycle. */
export const FATIGUE_DAY_MINUTES = 24 * 60;

/** Base kill EXP needed to earn `needed` character EXP with current pools (single pass, no daily reset). */
export function baseExpForNeededWithPools(
  needed: number,
  pools: FatiguePools,
): FatigueBaseBreakdown {
  let need = Math.max(0, needed);
  let greenRem = Math.max(0, pools.greenRemaining);
  let yellowRem = Math.max(0, pools.yellowRemaining);

  const appliedGreen = Math.min(need, greenRem);
  const green = appliedGreen;
  need -= appliedGreen;

  const appliedOrange = Math.min(need, yellowRem);
  const orange = appliedOrange / FATIGUE_MULTIPLIER.orange;
  need -= appliedOrange;

  const appliedRed = need;
  const red = need > 0 ? need / FATIGUE_MULTIPLIER.red : 0;

  return {
    total: green + orange + red,
    green,
    orange,
    red,
    appliedGreen,
    appliedOrange,
    appliedRed,
  };
}

export type FatigueDayBreakdown = {
  /** 1-based day index. */
  day: number;
  green: number;
  orange: number;
  red: number;
  minutes: number | null;
};

export type FatiguePlanResult = {
  plan: FatigueBaseBreakdown;
  totalMinutes: number | null;
  days: number;
  dayBreakdown: FatigueDayBreakdown[];
};

function emptyDay(day: number): FatigueDayBreakdown {
  return { day, green: 0, orange: 0, red: 0, minutes: null };
}

/**
 * Plan farming `needed` character EXP with green/orange reset every 24h.
 * Day 0 uses `todayPools`; later days use full `dailyGreen` / `dailyYellow`.
 * Within a day: green → orange → red for the remaining time of the 24h cycle.
 */
export function planFatigueForNeeded(
  needed: number,
  todayPools: FatiguePools,
  dailyGreen: number,
  dailyYellow: number,
  xpPerMin: number | null,
): FatiguePlanResult {
  let need = Math.max(0, needed);
  let green = 0;
  let orange = 0;
  let red = 0;
  let appliedGreen = 0;
  let appliedOrange = 0;
  let appliedRed = 0;
  let totalMinutes = 0;
  let days = 0;
  const dayBreakdown: FatigueDayBreakdown[] = [];

  const dayGreenFull = Math.max(0, dailyGreen);
  const dayYellowFull = Math.max(0, dailyYellow);
  const hasRate = xpPerMin != null && xpPerMin > 0;

  const MAX_DAYS = 10_000;
  while (need > 0 && days < MAX_DAYS) {
    const greenRem = days === 0 ? Math.max(0, todayPools.greenRemaining) : dayGreenFull;
    const yellowRem = days === 0 ? Math.max(0, todayPools.yellowRemaining) : dayYellowFull;
    let dayMinutes = 0;
    const slice = emptyDay(days + 1);

    // Green ×1 — consume = character EXP = base
    const g = Math.min(need, greenRem);
    need -= g;
    appliedGreen += g;
    green += g;
    slice.green = g;
    if (hasRate && g > 0) {
      dayMinutes += g / (xpPerMin! * FATIGUE_MULTIPLIER.green);
    }

    // Orange ×0.5 — consume = character EXP; base = char / 0.5
    const oChar = Math.min(need, yellowRem);
    need -= oChar;
    appliedOrange += oChar;
    const oBase = oChar / FATIGUE_MULTIPLIER.orange;
    orange += oBase;
    slice.orange = oBase;
    if (hasRate && oChar > 0) {
      dayMinutes += oChar / (xpPerMin! * FATIGUE_MULTIPLIER.orange);
    }

    if (need > 0) {
      if (hasRate) {
        const timeLeft = Math.max(0, FATIGUE_DAY_MINUTES - dayMinutes);
        if (timeLeft > 0) {
          const redRate = xpPerMin! * FATIGUE_MULTIPLIER.red;
          const canGain = timeLeft * redRate;
          const gain = Math.min(need, canGain);
          need -= gain;
          appliedRed += gain;
          const rBase = gain / FATIGUE_MULTIPLIER.red;
          red += rBase;
          slice.red = rBase;
          dayMinutes += gain / redRate;
        }
      } else if (dayGreenFull <= 0 && dayYellowFull <= 0 && greenRem <= 0 && yellowRem <= 0) {
        appliedRed += need;
        const rBase = need / FATIGUE_MULTIPLIER.red;
        red += rBase;
        slice.red = rBase;
        need = 0;
      }
    }

    if (hasRate) {
      totalMinutes += dayMinutes;
      slice.minutes = dayMinutes;
    }
    dayBreakdown.push(slice);
    days += 1;

    if (
      need > 0 &&
      dayGreenFull <= 0 &&
      dayYellowFull <= 0 &&
      (!hasRate || FATIGUE_MULTIPLIER.red <= 0)
    ) {
      appliedRed += need;
      const rBase = need / FATIGUE_MULTIPLIER.red;
      red += rBase;
      const last = dayBreakdown[dayBreakdown.length - 1]!;
      last.red += rBase;
      need = 0;
    }
  }

  return {
    plan: {
      total: green + orange + red,
      green,
      orange,
      red,
      appliedGreen,
      appliedOrange,
      appliedRed,
    },
    totalMinutes: hasRate ? totalMinutes : null,
    days: Math.max(1, days),
    dayBreakdown,
  };
}

/**
 * Plan farming a given amount of base kill EXP with green/orange reset every 24h.
 * Used for "полученный опыт" time estimates across multiple days.
 */
export function planBaseFarmWithDailyReset(
  baseNeeded: number,
  todayPools: FatiguePools,
  dailyGreen: number,
  dailyYellow: number,
  xpPerMin: number | null,
): FatiguePlanResult {
  let left = Math.max(0, baseNeeded);
  let green = 0;
  let orange = 0;
  let red = 0;
  let totalMinutes = 0;
  let days = 0;
  const dayBreakdown: FatigueDayBreakdown[] = [];

  const dayGreenFull = Math.max(0, dailyGreen);
  const dayYellowFull = Math.max(0, dailyYellow);
  const hasRate = xpPerMin != null && xpPerMin > 0;

  const MAX_DAYS = 10_000;
  while (left > 0 && days < MAX_DAYS) {
    const greenRem = days === 0 ? Math.max(0, todayPools.greenRemaining) : dayGreenFull;
    const yellowRem = days === 0 ? Math.max(0, todayPools.yellowRemaining) : dayYellowFull;
    let dayMinutes = 0;
    const slice = emptyDay(days + 1);

    // Base kill rate ≈ xpPerMin measured on green (char/min ×1).
    const baseRate = hasRate ? xpPerMin! : 0;

    const g = Math.min(left, greenRem);
    left -= g;
    green += g;
    slice.green = g;
    if (hasRate && g > 0) {
      dayMinutes += g / baseRate;
    }

    const oBaseMax = yellowRem / FATIGUE_MULTIPLIER.orange;
    const o = Math.min(left, oBaseMax);
    left -= o;
    orange += o;
    slice.orange = o;
    if (hasRate && o > 0) {
      dayMinutes += o / baseRate;
    }

    if (left > 0) {
      if (hasRate) {
        const timeLeft = Math.max(0, FATIGUE_DAY_MINUTES - dayMinutes);
        if (timeLeft > 0) {
          const canBase = timeLeft * baseRate;
          const r = Math.min(left, canBase);
          left -= r;
          red += r;
          slice.red = r;
          dayMinutes += r / baseRate;
        }
      } else if (dayGreenFull <= 0 && dayYellowFull <= 0 && greenRem <= 0 && yellowRem <= 0) {
        red += left;
        slice.red = left;
        left = 0;
      }
    }

    if (hasRate) {
      totalMinutes += dayMinutes;
      slice.minutes = dayMinutes;
    }
    dayBreakdown.push(slice);
    days += 1;

    if (
      left > 0 &&
      dayGreenFull <= 0 &&
      dayYellowFull <= 0 &&
      (!hasRate || FATIGUE_MULTIPLIER.red <= 0)
    ) {
      red += left;
      const last = dayBreakdown[dayBreakdown.length - 1]!;
      last.red += left;
      left = 0;
    }
  }

  return {
    plan: {
      total: green + orange + red,
      green,
      orange,
      red,
      appliedGreen: green,
      appliedOrange: orange * FATIGUE_MULTIPLIER.orange,
      appliedRed: red * FATIGUE_MULTIPLIER.red,
    },
    totalMinutes: hasRate ? totalMinutes : null,
    days: Math.max(1, days),
    dayBreakdown,
  };
}

export function projectLevelWithPools(
  level: number,
  percent: number,
  baseExp: number,
  pools: FatiguePools,
): { level: number; percent: number; appliedExp: number } {
  const { appliedExp } = applyBaseExpWithPools(baseExp, pools);
  const result = levelFromAbsoluteExp(absoluteExp(level, percent) + appliedExp);
  return { ...result, appliedExp };
}

function clampLevel(level: number): number {
  if (!Number.isFinite(level)) return MIN_LEVEL;
  return Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, Math.floor(level)));
}

function clampPercent(percent: number): number {
  if (!Number.isFinite(percent)) return 0;
  return Math.min(100, Math.max(0, percent));
}
