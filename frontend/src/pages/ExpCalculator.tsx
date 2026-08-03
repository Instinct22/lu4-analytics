import { useEffect, useMemo, useState } from "react";
import PercentInput, { parsePercentInput } from "../components/character/PercentInput";
import StepperInput from "../components/character/StepperInput";
import { PageHeader } from "../components/ui";
import {
  loadDailyGreen,
  loadDailyYellow,
  loadGreenFatiguePercent,
  loadUseFatigue,
  loadUseXpPerMin,
  loadXpPerMin,
  loadYellowFatiguePercent,
  saveDailyGreen,
  saveDailyYellow,
  saveGreenFatiguePercent,
  saveUseFatigue,
  saveUseXpPerMin,
  saveXpPerMin,
  saveYellowFatiguePercent,
} from "../lib/expFatigueStorage";
import {
  absoluteExp,
  expNeededToReach,
  levelFromAbsoluteExp,
  MAX_LEVEL,
  MIN_LEVEL,
  planBaseFarmWithDailyReset,
  planFatigueForNeeded,
  remainingFatiguePools,
  type FatigueBaseBreakdown,
  type FatigueDayBreakdown,
} from "../lib/expTable";
import { formatDurationMinutes, formatFullNumber } from "../lib/formatNumber";

type CalcMode = "gained" | "target";
type XpRatePhase = "idle" | "running" | "done";

type CalcResult =
  | {
      mode: "gained";
      level: number;
      percent: number;
      appliedExp: number;
      breakdown?: FatigueBaseBreakdown;
      planMinutes?: number | null;
      planDays?: number;
      dayBreakdown?: FatigueDayBreakdown[];
    }
  | {
      mode: "target";
      neededExp: number;
      baseFarmExp: number;
      targetLevel: number;
      breakdown?: FatigueBaseBreakdown;
      /** Total minutes with 24h fatigue reset (when XP/min is set). */
      planMinutes?: number | null;
      planDays?: number;
      dayBreakdown?: FatigueDayBreakdown[];
    };

const XP_RATE_SECONDS = 60;

/** Time for character EXP at the measured XP/min rate. */
function minutesForExp(exp: number, xpPerMin: number | null): number | null {
  if (xpPerMin == null || xpPerMin <= 0 || exp <= 0) return null;
  return exp / xpPerMin;
}

/**
 * Time to farm `baseExp` kill XP.
 * `xpPerMin` is character XP/min on green (= base kill rate).
 */
function minutesForFatigueBase(baseExp: number, xpPerMin: number | null): number | null {
  if (xpPerMin == null || xpPerMin <= 0 || baseExp <= 0) return null;
  return baseExp / xpPerMin;
}

function fatigueBreakdownMinutes(
  green: number,
  orange: number,
  red: number,
  xpPerMin: number | null,
): number | null {
  return minutesForFatigueBase(green + orange + red, xpPerMin);
}

function FatigueTierRows({
  green,
  orange,
  red,
  xpPerMin,
  minutesOverride,
}: {
  green: number;
  orange: number;
  red: number;
  xpPerMin?: number | null;
  minutesOverride?: number | null;
}) {
  const rows = [
    { key: "green", label: "Зелёная ×1", value: green, color: "text-emerald-400" },
    { key: "orange", label: "Оранжевая ×0.5", value: orange, color: "text-orange-400" },
    { key: "red", label: "Красная ×0.025", value: red, color: "text-red-400" },
  ].filter((r) => r.value > 0);

  const dayTotal = green + orange + red;
  const dayMins =
    minutesOverride ?? fatigueBreakdownMinutes(green, orange, red, xpPerMin ?? null);

  return (
    <ul className="space-y-1 text-sm">
      {rows.map((r) => {
        const mins = minutesForFatigueBase(r.value, xpPerMin ?? null);
        return (
          <li key={r.key} className="flex items-start justify-between gap-3">
            <span className={r.color}>{r.label}</span>
            <span className="text-right tabular-nums text-zinc-300">
              {formatFullNumber(r.value)}
              {mins != null && (
                <span className="mt-0.5 block text-xs text-zinc-500">
                  {formatDurationMinutes(mins)}
                </span>
              )}
            </span>
          </li>
        );
      })}
      <li className="flex items-start justify-between gap-3 border-t border-zinc-800/60 pt-1 text-zinc-400">
        <span>Итого</span>
        <span className="text-right tabular-nums text-zinc-200">
          {formatFullNumber(dayTotal)}
          {dayMins != null && (
            <span className="mt-0.5 block text-xs text-zinc-500">
              {formatDurationMinutes(dayMins)}
            </span>
          )}
        </span>
      </li>
    </ul>
  );
}

function FatigueBreakdownList({
  green,
  orange,
  red,
  totalLabel,
  total,
  xpPerMin,
  totalMinutesOverride,
  dayBreakdown,
}: {
  green: number;
  orange: number;
  red: number;
  totalLabel: string;
  total: number;
  xpPerMin?: number | null;
  totalMinutesOverride?: number | null;
  dayBreakdown?: FatigueDayBreakdown[];
}) {
  if (green + orange + red <= 0) return null;

  const totalMins =
    totalMinutesOverride ?? fatigueBreakdownMinutes(green, orange, red, xpPerMin ?? null);
  const showDays = (dayBreakdown?.length ?? 0) > 1;

  return (
    <div className="space-y-3 border-t border-zinc-800/80 pt-3">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{totalLabel}</p>

      {showDays ? (
        <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
          {dayBreakdown!.map((d) => (
            <div
              key={d.day}
              className="rounded-lg border border-zinc-800/80 bg-zinc-900/40 px-3 py-2"
            >
              <p className="mb-1.5 text-xs font-medium text-zinc-400">
                День {d.day}
                {d.minutes != null && (
                  <span className="ml-2 tabular-nums text-zinc-500">
                    {formatDurationMinutes(d.minutes)}
                  </span>
                )}
              </p>
              <FatigueTierRows
                green={d.green}
                orange={d.orange}
                red={d.red}
                xpPerMin={xpPerMin}
                minutesOverride={d.minutes}
              />
            </div>
          ))}
        </div>
      ) : (
        <FatigueTierRows green={green} orange={orange} red={red} xpPerMin={xpPerMin} />
      )}

      <div className="flex items-start justify-between gap-3 border-t border-zinc-800/60 pt-2 text-sm text-zinc-400">
        <span>{showDays ? `Всего · ${dayBreakdown!.length} дн.` : "Всего"}</span>
        <span className="text-right tabular-nums text-zinc-200">
          {formatFullNumber(total)}
          {totalMins != null && (
            <span className="mt-0.5 block text-xs text-zinc-500">
              {formatDurationMinutes(totalMins)}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}

function formatCountdown(secondsLeft: number): string {
  const m = Math.floor(secondsLeft / 60);
  const s = secondsLeft % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function parseNum(raw: string): number | null {
  const cleaned = raw.replace(/\s/g, "").replace(",", ".");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function formatInt(n: number): string {
  return String(Math.trunc(n));
}

function stepLevel(raw: string, dir: 1 | -1): string {
  const current = parseNum(raw);
  const base = current == null ? MIN_LEVEL : Math.trunc(current);
  return formatInt(Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, base + dir)));
}

function stepGained(raw: string, dir: 1 | -1): string {
  const current = parseNum(raw) ?? 0;
  const step = Math.abs(current) >= 1_000_000 ? 100_000 : Math.abs(current) >= 10_000 ? 1_000 : 100;
  const next = Math.max(0, Math.round(current + dir * step));
  return formatInt(next);
}

function stepDaily(raw: string, dir: 1 | -1): string {
  const current = parseNum(raw) ?? 0;
  const step = Math.abs(current) >= 1_000_000 ? 100_000 : Math.abs(current) >= 10_000 ? 1_000 : 1000;
  return formatInt(Math.max(0, Math.round(current + dir * step)));
}

function formatResultPercent(percent: number): string {
  if (Number.isInteger(percent)) return String(percent);
  return percent.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function emptyPools() {
  return { greenRemaining: 0, yellowRemaining: 0 };
}

export default function ExpCalculatorPage() {
  const [levelRaw, setLevelRaw] = useState("40");
  const [percentRaw, setPercentRaw] = useState("0");
  const [mode, setMode] = useState<CalcMode>("gained");
  const [gainedRaw, setGainedRaw] = useState("");
  const [targetLevelRaw, setTargetLevelRaw] = useState("50");
  const [useFatigue, setUseFatigue] = useState(loadUseFatigue);
  const [dailyGreenRaw, setDailyGreenRaw] = useState(loadDailyGreen);
  const [dailyYellowRaw, setDailyYellowRaw] = useState(loadDailyYellow);
  const [greenPercentRaw, setGreenPercentRaw] = useState(loadGreenFatiguePercent);
  const [yellowPercentRaw, setYellowPercentRaw] = useState(loadYellowFatiguePercent);
  const [useXpPerMin, setUseXpPerMin] = useState(loadUseXpPerMin);
  const [xpPerMin, setXpPerMin] = useState<number | null>(loadXpPerMin);
  const [xpRatePhase, setXpRatePhase] = useState<XpRatePhase>("idle");
  const [xpRateSecondsLeft, setXpRateSecondsLeft] = useState(XP_RATE_SECONDS);
  const [xpRateStartLevel, setXpRateStartLevel] = useState<number | null>(null);
  const [xpRateStartPercent, setXpRateStartPercent] = useState<number | null>(null);
  const [xpRateEndPercentRaw, setXpRateEndPercentRaw] = useState("");
  const [xpRateError, setXpRateError] = useState<string | null>(null);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (xpRatePhase !== "running") return;
    if (xpRateSecondsLeft <= 0) {
      setXpRatePhase("done");
      return;
    }
    const id = window.setTimeout(() => setXpRateSecondsLeft((s) => s - 1), 1000);
    return () => window.clearTimeout(id);
  }, [xpRatePhase, xpRateSecondsLeft]);

  const levelNum = parseNum(levelRaw);
  const gainedNum = parseNum(gainedRaw);
  const targetLevelNum = parseNum(targetLevelRaw);
  const dailyGreenNum = parseNum(dailyGreenRaw) ?? 0;
  const dailyYellowNum = parseNum(dailyYellowRaw) ?? 0;
  const activeXpPerMin = useXpPerMin ? xpPerMin : null;

  const pools = useMemo(() => {
    if (!useFatigue) return emptyPools();
    const greenPct = parsePercentInput(greenPercentRaw);
    const yellowPct = parsePercentInput(yellowPercentRaw);
    if (greenPct == null || yellowPct == null) return emptyPools();
    return remainingFatiguePools(dailyGreenNum, dailyYellowNum, greenPct, yellowPct);
  }, [useFatigue, dailyGreenNum, dailyYellowNum, greenPercentRaw, yellowPercentRaw]);

  const previewApplied = useMemo(() => {
    if (mode !== "gained" || gainedNum == null || gainedNum < 0) return null;
    if (!useFatigue) return gainedNum;
    const planned = planBaseFarmWithDailyReset(
      gainedNum,
      pools,
      dailyGreenNum,
      dailyYellowNum,
      activeXpPerMin,
    );
    return planned.plan.appliedGreen + planned.plan.appliedOrange + planned.plan.appliedRed;
  }, [
    mode,
    gainedNum,
    useFatigue,
    pools,
    dailyGreenNum,
    dailyYellowNum,
    activeXpPerMin,
  ]);

  const previewNeeded = useMemo(() => {
    if (mode !== "target") return null;
    const level = parseNum(levelRaw);
    const percent = parsePercentInput(percentRaw);
    const target = parseNum(targetLevelRaw);
    if (level == null || percent == null || target == null) return null;
    if (target < MIN_LEVEL || target > MAX_LEVEL) return null;
    const neededExp = expNeededToReach(level, percent, target, 0);
    if (!useFatigue) {
      return {
        neededExp,
        baseFarmExp: neededExp,
        breakdown: null as FatigueBaseBreakdown | null,
        planMinutes: null as number | null,
        planDays: 1,
        alreadyReached: neededExp <= 0,
      };
    }
    const planned = planFatigueForNeeded(
      neededExp,
      pools,
      dailyGreenNum,
      dailyYellowNum,
      activeXpPerMin,
    );
    return {
      neededExp,
      baseFarmExp: planned.plan.total,
      breakdown: planned.plan,
      planMinutes: planned.totalMinutes,
      planDays: planned.days,
      alreadyReached: neededExp <= 0,
    };
  }, [
    mode,
    levelRaw,
    percentRaw,
    targetLevelRaw,
    useFatigue,
    pools,
    dailyGreenNum,
    dailyYellowNum,
    activeXpPerMin,
  ]);

  const setCalcMode = (next: CalcMode) => {
    setMode(next);
    setResult(null);
    setError(null);
  };

  const toggleUseFatigue = (next: boolean) => {
    setUseFatigue(next);
    saveUseFatigue(next);
    setResult(null);
  };

  const toggleUseXpPerMin = (next: boolean) => {
    setUseXpPerMin(next);
    saveUseXpPerMin(next);
    if (!next) {
      setXpRatePhase("idle");
      setXpRateSecondsLeft(XP_RATE_SECONDS);
      setXpRateError(null);
    }
    setResult(null);
  };

  const snapshotXpRateStart = (): boolean => {
    const level = parseNum(levelRaw);
    const percent = parsePercentInput(percentRaw);
    if (level == null || level < MIN_LEVEL || level > MAX_LEVEL) {
      setXpRateError(`Уровень должен быть от ${MIN_LEVEL} до ${MAX_LEVEL}`);
      return false;
    }
    if (percent == null) {
      setXpRateError("Укажите процент на уровне перед стартом");
      return false;
    }
    setXpRateError(null);
    setXpRateStartLevel(Math.trunc(level));
    setXpRateStartPercent(percent);
    setXpRateEndPercentRaw(percentRaw);
    return true;
  };

  const startXpRateMeasure = () => {
    if (!snapshotXpRateStart()) return;
    setXpRateEndPercentRaw("");
    setXpRateSecondsLeft(XP_RATE_SECONDS);
    setXpRatePhase("running");
  };

  /** Skip the 1-minute wait and enter end % immediately. */
  const startXpRateManual = () => {
    if (!snapshotXpRateStart()) return;
    setXpRatePhase("done");
  };

  const finishXpRateMeasure = () => {
    if (xpRateStartLevel == null || xpRateStartPercent == null) return;
    const endPercent = parsePercentInput(xpRateEndPercentRaw);
    if (endPercent == null) {
      setXpRateError("Укажите процент после минуты");
      return;
    }
    let endLevel = xpRateStartLevel;
    // If % dropped, assume at least one level-up during the minute.
    if (endPercent < xpRateStartPercent) {
      endLevel = Math.min(MAX_LEVEL, xpRateStartLevel + 1);
    }
    const gained =
      absoluteExp(endLevel, endPercent) - absoluteExp(xpRateStartLevel, xpRateStartPercent);
    if (gained <= 0) {
      setXpRateError("Опыт не вырос — проверьте процент после минуты");
      return;
    }
    setXpRateError(null);
    setXpPerMin(gained);
    saveXpPerMin(gained);
    setXpRatePhase("idle");
    setResult(null);
  };

  const resetXpRateMeasure = () => {
    setXpRatePhase("idle");
    setXpRateSecondsLeft(XP_RATE_SECONDS);
    setXpRateStartLevel(null);
    setXpRateStartPercent(null);
    setXpRateEndPercentRaw("");
    setXpRateError(null);
  };

  const clearXpPerMin = () => {
    setXpPerMin(null);
    saveXpPerMin(null);
    resetXpRateMeasure();
    setResult(null);
  };

  const commitGreenPercent = (raw: string) => {
    setGreenPercentRaw(raw);
    const parsed = parsePercentInput(raw);
    if (parsed != null) saveGreenFatiguePercent(String(parsed));
  };

  const commitYellowPercent = (raw: string) => {
    setYellowPercentRaw(raw);
    const parsed = parsePercentInput(raw);
    if (parsed != null) saveYellowFatiguePercent(String(parsed));
  };

  const calculate = () => {
    const level = parseNum(levelRaw);
    const percent = parsePercentInput(percentRaw);

    if (level == null || level < MIN_LEVEL || level > MAX_LEVEL) {
      setError(`Уровень должен быть от ${MIN_LEVEL} до ${MAX_LEVEL}`);
      setResult(null);
      return;
    }
    if (percent == null) {
      setError("Процент: формат 0–100, до 4 знаков после точки (например 99.99 или 99.9999)");
      setResult(null);
      return;
    }

    if (useFatigue) {
      if ((parseNum(dailyGreenRaw) ?? -1) < 0 || (parseNum(dailyYellowRaw) ?? -1) < 0) {
        setError("Укажите дневную зелёную и оранжевую fatigue");
        setResult(null);
        return;
      }
      if (parsePercentInput(greenPercentRaw) == null || parsePercentInput(yellowPercentRaw) == null) {
        setError("Укажите проценты зелёной и оранжевой fatigue");
        setResult(null);
        return;
      }
    }

    if (mode === "gained") {
      const gained = parseNum(gainedRaw);
      if (gained == null || gained < 0) {
        setError("Укажите количество полученного опыта");
        setResult(null);
        return;
      }
      setError(null);
      if (useFatigue) {
        const planned = planBaseFarmWithDailyReset(
          gained,
          pools,
          dailyGreenNum,
          dailyYellowNum,
          activeXpPerMin,
        );
        const appliedExp =
          planned.plan.appliedGreen + planned.plan.appliedOrange + planned.plan.appliedRed;
        const projected = levelFromAbsoluteExp(absoluteExp(level, percent) + appliedExp);
        setResult({
          mode: "gained",
          ...projected,
          appliedExp,
          breakdown: planned.plan,
          planMinutes: planned.totalMinutes,
          planDays: planned.days,
          dayBreakdown: planned.dayBreakdown,
        });
      } else {
        const appliedExp = gained;
        setResult({
          mode: "gained",
          ...levelFromAbsoluteExp(absoluteExp(level, percent) + appliedExp),
          appliedExp,
        });
      }
      return;
    }

    const target = parseNum(targetLevelRaw);
    if (target == null || target < MIN_LEVEL || target > MAX_LEVEL) {
      setError(`Целевой уровень: от ${MIN_LEVEL} до ${MAX_LEVEL}`);
      setResult(null);
      return;
    }
    if (target < level || (target === level && percent >= 100)) {
      setError("Целевой уровень должен быть выше текущего прогресса");
      setResult(null);
      return;
    }

    const neededExp = expNeededToReach(level, percent, target, 0);
    setError(null);
    if (useFatigue) {
      const planned = planFatigueForNeeded(
        neededExp,
        pools,
        dailyGreenNum,
        dailyYellowNum,
        activeXpPerMin,
      );
      setResult({
        mode: "target",
        neededExp,
        baseFarmExp: planned.plan.total,
        targetLevel: Math.trunc(target),
        breakdown: planned.plan,
        planMinutes: planned.totalMinutes,
        planDays: planned.days,
        dayBreakdown: planned.dayBreakdown,
      });
    } else {
      setResult({
        mode: "target",
        neededExp,
        baseFarmExp: neededExp,
        targetLevel: Math.trunc(target),
      });
    }
  };

  return (
    <div className="min-h-full">
      <PageHeader title="Exp">
        <p className="text-sm text-zinc-500">
          Калькулятор опыта с учётом Fatigue (таблица уровней Lu4)
        </p>
      </PageHeader>

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <section className="panel min-w-0 flex-1 space-y-5 p-5 sm:p-6 xl:max-w-4xl">
          <div className="space-y-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4">
            <label className="flex cursor-pointer items-center gap-2.5">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-amber-500 focus:ring-amber-500/40"
                checked={useFatigue}
                onChange={(e) => toggleUseFatigue(e.target.checked)}
              />
              <span className="text-sm font-medium text-zinc-200">Использовать фатигу</span>
            </label>

            {useFatigue && (
              <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-2">
                <div className="flex min-w-0 flex-col gap-3">
                  <label className="flex min-w-0 flex-col gap-1.5">
                    <span className="flex h-7 items-center gap-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      Дневная зелёная
                    </span>
                    <StepperInput
                      value={dailyGreenRaw}
                      onChange={(raw) => {
                        if (raw === "" || /^\d*$/.test(raw)) setDailyGreenRaw(raw);
                      }}
                      onStep={(dir) => {
                        const next = stepDaily(dailyGreenRaw, dir);
                        setDailyGreenRaw(next);
                        saveDailyGreen(next);
                      }}
                      minReached={(parseNum(dailyGreenRaw) ?? 0) <= 0}
                      placeholder="2500000"
                      inputMode="numeric"
                      groupThousands
                      ariaLabel="Дневная зелёная fatigue"
                      onBlur={() => {
                        const n = parseNum(dailyGreenRaw);
                        const next = n == null ? "" : formatInt(Math.max(0, n));
                        setDailyGreenRaw(next);
                        saveDailyGreen(next);
                      }}
                    />
                  </label>
                  <label className="flex min-w-0 flex-col gap-1.5">
                    <span className="flex h-7 items-center gap-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      Процент зелёной
                    </span>
                    <PercentInput value={greenPercentRaw} onChange={commitGreenPercent} />
                    <p className="min-h-4 text-xs text-zinc-500">
                      Осталось:{" "}
                      <span className="tabular-nums text-emerald-400/90">
                        {formatFullNumber(pools.greenRemaining)}
                      </span>
                    </p>
                  </label>
                </div>

                <div className="flex min-w-0 flex-col gap-3">
                  <label className="flex min-w-0 flex-col gap-1.5">
                    <span className="flex h-7 items-center gap-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      <span className="h-2 w-2 rounded-full bg-orange-400" />
                      Дневная оранжевая
                    </span>
                    <StepperInput
                      value={dailyYellowRaw}
                      onChange={(raw) => {
                        if (raw === "" || /^\d*$/.test(raw)) setDailyYellowRaw(raw);
                      }}
                      onStep={(dir) => {
                        const next = stepDaily(dailyYellowRaw, dir);
                        setDailyYellowRaw(next);
                        saveDailyYellow(next);
                      }}
                      minReached={(parseNum(dailyYellowRaw) ?? 0) <= 0}
                      placeholder="2500000"
                      inputMode="numeric"
                      groupThousands
                      ariaLabel="Дневная оранжевая fatigue"
                      onBlur={() => {
                        const n = parseNum(dailyYellowRaw);
                        const next = n == null ? "" : formatInt(Math.max(0, n));
                        setDailyYellowRaw(next);
                        saveDailyYellow(next);
                      }}
                    />
                  </label>
                  <label className="flex min-w-0 flex-col gap-1.5">
                    <span className="flex h-7 items-center gap-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                      <span className="h-2 w-2 rounded-full bg-orange-400" />
                      Процент оранжевой
                    </span>
                    <PercentInput value={yellowPercentRaw} onChange={commitYellowPercent} />
                    <p className="min-h-4 text-xs text-zinc-500">
                      Осталось:{" "}
                      <span className="tabular-nums text-orange-400/90">
                        {formatFullNumber(pools.yellowRemaining)}
                      </span>
                    </p>
                  </label>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4">
            <label className="flex cursor-pointer items-center gap-2.5">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-amber-500 focus:ring-amber-500/40"
                checked={useXpPerMin}
                onChange={(e) => toggleUseXpPerMin(e.target.checked)}
              />
              <span className="text-sm font-medium text-zinc-200">Опыт в минуту</span>
            </label>

            {useXpPerMin && (
              <div className="space-y-3">
                <p className="text-xs text-zinc-500">
                  Укажите текущий уровень и % выше. «Старт» — замер минуты, либо «Ввести сразу» —
                  без ожидания. Затем укажите новый % и посчитайте опыт/мин.
                </p>

                {xpRatePhase === "idle" && (
                  <div className="flex flex-wrap items-center gap-3">
                    <button type="button" className="btn-primary" onClick={startXpRateMeasure}>
                      Старт (1 мин)
                    </button>
                    <button type="button" className="btn-ghost" onClick={startXpRateManual}>
                      Ввести сразу
                    </button>
                    {xpPerMin != null && (
                      <p className="text-sm text-zinc-400">
                        Сохранено:{" "}
                        <span className="tabular-nums text-amber-400">
                          {formatFullNumber(xpPerMin)}
                        </span>{" "}
                        опыта/мин
                        <button
                          type="button"
                          className="ml-2 text-xs text-zinc-500 underline hover:text-zinc-300"
                          onClick={clearXpPerMin}
                        >
                          сбросить
                        </button>
                      </p>
                    )}
                  </div>
                )}

                {xpRatePhase === "running" && (
                  <div className="flex flex-wrap items-center gap-4">
                    <p className="text-3xl font-semibold tabular-nums text-amber-400">
                      {formatCountdown(xpRateSecondsLeft)}
                    </p>
                    <p className="text-sm text-zinc-500">
                      Замер с {xpRateStartLevel} ур. / {formatResultPercent(xpRateStartPercent ?? 0)}%
                    </p>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => {
                        setXpRatePhase("done");
                      }}
                    >
                      Ввести сразу
                    </button>
                    <button type="button" className="btn-ghost" onClick={resetXpRateMeasure}>
                      Отмена
                    </button>
                  </div>
                )}

                {xpRatePhase === "done" && (
                  <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[1fr_auto_auto]">
                    <label className="flex min-w-0 flex-col gap-1.5">
                      <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                        % после фарма
                      </span>
                      <PercentInput
                        value={xpRateEndPercentRaw}
                        onChange={setXpRateEndPercentRaw}
                      />
                      <p className="text-xs text-zinc-600">
                        Старт: {xpRateStartLevel} / {formatResultPercent(xpRateStartPercent ?? 0)}%
                        {parsePercentInput(xpRateEndPercentRaw) != null &&
                          xpRateStartPercent != null &&
                          parsePercentInput(xpRateEndPercentRaw)! < xpRateStartPercent && (
                            <span> · учтён +1 уровень</span>
                          )}
                      </p>
                    </label>
                    <button type="button" className="btn-primary" onClick={finishXpRateMeasure}>
                      Посчитать опыт/мин
                    </button>
                    <button type="button" className="btn-ghost" onClick={resetXpRateMeasure}>
                      Заново
                    </button>
                  </div>
                )}

                {xpRatePhase !== "idle" && xpPerMin != null && (
                  <p className="text-sm text-zinc-400">
                    Текущий опыт/мин:{" "}
                    <span className="tabular-nums text-amber-400">
                      {formatFullNumber(xpPerMin)}
                    </span>
                  </p>
                )}

                {xpRateError && <p className="text-sm text-red-400">{xpRateError}</p>}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-3">
            <label className="flex min-w-0 flex-col gap-1.5">
              <span className="flex h-7 items-center text-xs font-medium uppercase tracking-wider text-zinc-500">
                Текущий уровень
              </span>
              <StepperInput
                value={levelRaw}
                onChange={(raw) => {
                  if (raw === "" || /^\d{0,3}$/.test(raw)) setLevelRaw(raw);
                }}
                onStep={(dir) => setLevelRaw(stepLevel(levelRaw === "" ? String(MIN_LEVEL) : levelRaw, dir))}
                minReached={levelNum != null && levelNum <= MIN_LEVEL}
                maxReached={levelNum != null && levelNum >= MAX_LEVEL}
                placeholder={String(MIN_LEVEL)}
                inputMode="numeric"
                ariaLabel="Текущий уровень"
                onBlur={() => {
                  const n = parseNum(levelRaw);
                  if (n == null) {
                    setLevelRaw(String(MIN_LEVEL));
                    return;
                  }
                  setLevelRaw(formatInt(Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, n))));
                }}
              />
              <p className="min-h-4 text-xs text-transparent select-none" aria-hidden>
                —
              </p>
            </label>

            <label className="flex min-w-0 flex-col gap-1.5">
              <span className="flex h-7 items-center text-xs font-medium uppercase tracking-wider text-zinc-500">
                Процент на уровне
              </span>
              <PercentInput value={percentRaw} onChange={setPercentRaw} />
              <p className="min-h-4 text-xs text-transparent select-none" aria-hidden>
                —
              </p>
            </label>

            <div className="flex min-w-0 flex-col gap-1.5">
              <div className="flex h-7 items-center justify-between gap-2">
                <span className="truncate text-xs font-medium uppercase tracking-wider text-zinc-500">
                  {mode === "gained" ? "Полученный опыт" : "Необх. уровень"}
                </span>
                <div className="inline-flex h-6 shrink-0 overflow-hidden rounded-md border border-zinc-700/80 bg-zinc-900/80">
                  <button
                    type="button"
                    onClick={() => setCalcMode("gained")}
                    className={[
                      "px-2 text-[0.65rem] font-medium transition-colors",
                      mode === "gained"
                        ? "bg-amber-500/20 text-amber-400"
                        : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300",
                    ].join(" ")}
                  >
                    Опыт
                  </button>
                  <button
                    type="button"
                    onClick={() => setCalcMode("target")}
                    className={[
                      "border-l border-zinc-700/80 px-2 text-[0.65rem] font-medium transition-colors",
                      mode === "target"
                        ? "bg-amber-500/20 text-amber-400"
                        : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300",
                    ].join(" ")}
                  >
                    Уровень
                  </button>
                </div>
              </div>

              {mode === "gained" ? (
                <StepperInput
                  value={gainedRaw}
                  onChange={(raw) => {
                    if (raw === "" || /^\d*$/.test(raw)) setGainedRaw(raw);
                  }}
                  onStep={(dir) => setGainedRaw(stepGained(gainedRaw, dir))}
                  minReached={gainedNum != null && gainedNum <= 0}
                  placeholder="1500000"
                  inputMode="numeric"
                  groupThousands
                  ariaLabel="Полученный опыт"
                />
              ) : (
                <StepperInput
                  value={targetLevelRaw}
                  onChange={(raw) => {
                    if (raw === "" || /^\d{0,3}$/.test(raw)) setTargetLevelRaw(raw);
                  }}
                  onStep={(dir) =>
                    setTargetLevelRaw(
                      stepLevel(targetLevelRaw === "" ? String(MIN_LEVEL) : targetLevelRaw, dir),
                    )
                  }
                  minReached={targetLevelNum != null && targetLevelNum <= MIN_LEVEL}
                  maxReached={targetLevelNum != null && targetLevelNum >= MAX_LEVEL}
                  placeholder="50"
                  inputMode="numeric"
                  ariaLabel="Необходимый уровень"
                  onBlur={() => {
                    const n = parseNum(targetLevelRaw);
                    if (n == null) {
                      setTargetLevelRaw(String(MIN_LEVEL));
                      return;
                    }
                    setTargetLevelRaw(formatInt(Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, n))));
                  }}
                />
              )}

              <p className="min-h-4 truncate text-xs text-zinc-500">
                {mode === "gained" && previewApplied != null && useFatigue ? (
                  <>
                    Зачтётся:{" "}
                    <span className="tabular-nums text-zinc-300">
                      {formatFullNumber(previewApplied)}
                    </span>
                  </>
                ) : mode === "target" && previewNeeded ? (
                  previewNeeded.alreadyReached ? (
                    "Уже достигнут или выше"
                  ) : (
                    <>
                      Нужно:{" "}
                      <span className="tabular-nums text-zinc-300">
                        {formatFullNumber(previewNeeded.neededExp)}
                      </span>
                      {useFatigue && previewNeeded.baseFarmExp !== previewNeeded.neededExp && (
                        <>
                          {" "}
                          · набрать:{" "}
                          <span className="tabular-nums text-zinc-300">
                            {formatFullNumber(previewNeeded.baseFarmExp)}
                          </span>
                        </>
                      )}
                    </>
                  )
                ) : (
                  <span className="text-transparent select-none" aria-hidden>
                    —
                  </span>
                )}
              </p>
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button type="button" className="btn-primary" onClick={calculate}>
            Посчитать
          </button>
        </section>

        <section className="panel w-full shrink-0 space-y-3 p-5 sm:p-6 xl:sticky xl:top-4 xl:w-80">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Результат</p>
          {result?.mode === "gained" ? (
            <>
              <p className="text-3xl font-semibold tracking-tight text-zinc-50 tabular-nums">
                {result.level}
                <span className="ml-2 text-xl font-medium text-amber-400">
                  {formatResultPercent(result.percent)}%
                </span>
              </p>
              <p className="text-sm text-zinc-500">
                Зачтено опыта:{" "}
                <span className="tabular-nums text-zinc-300">{formatFullNumber(result.appliedExp)}</span>
                {result.level >= MAX_LEVEL && result.percent >= 100 && (
                  <span className="ml-2 text-zinc-600">(макс. уровень)</span>
                )}
              </p>
              {activeXpPerMin != null && (
                <p className="text-sm text-zinc-500">
                  Время при{" "}
                  <span className="tabular-nums text-zinc-300">
                    {formatFullNumber(activeXpPerMin)}
                  </span>{" "}
                  опыта/мин:{" "}
                  <span className="tabular-nums text-amber-400">
                    {formatDurationMinutes(
                      result.planMinutes ??
                        (result.breakdown
                          ? fatigueBreakdownMinutes(
                              result.breakdown.green,
                              result.breakdown.orange,
                              result.breakdown.red,
                              activeXpPerMin,
                            )
                          : minutesForExp(result.appliedExp, activeXpPerMin)),
                    )}
                  </span>
                  {result.planDays != null && result.planDays > 1 && (
                    <span className="mt-1 block text-xs text-zinc-500">
                      с учётом сброса fatigue каждые 24 ч · {formatFullNumber(result.planDays)}{" "}
                      дн.
                    </span>
                  )}
                </p>
              )}
              {result.breakdown && (
                <FatigueBreakdownList
                  totalLabel="Набрано по fatigue"
                  green={result.breakdown.green}
                  orange={result.breakdown.orange}
                  red={result.breakdown.red}
                  total={result.breakdown.total}
                  xpPerMin={activeXpPerMin}
                  totalMinutesOverride={result.planMinutes}
                  dayBreakdown={result.dayBreakdown}
                />
              )}
            </>
          ) : result?.mode === "target" ? (
            <>
              <p className="text-3xl font-semibold tracking-tight text-zinc-50 tabular-nums">
                {formatFullNumber(result.neededExp)}
              </p>
              <p className="text-sm text-zinc-500">
                опыта до уровня{" "}
                <span className="tabular-nums text-zinc-300">{result.targetLevel}</span>
              </p>
              {activeXpPerMin != null && (
                <p className="text-sm text-zinc-500">
                  Время:{" "}
                  <span className="tabular-nums text-amber-400">
                    {formatDurationMinutes(
                      result.planMinutes ??
                        (result.breakdown
                          ? fatigueBreakdownMinutes(
                              result.breakdown.green,
                              result.breakdown.orange,
                              result.breakdown.red,
                              activeXpPerMin,
                            )
                          : minutesForExp(result.neededExp, activeXpPerMin)),
                    )}
                  </span>
                  <span className="text-zinc-600">
                    {" "}
                    ({formatFullNumber(activeXpPerMin)} опыта/мин)
                  </span>
                  {result.planDays != null && result.planDays > 1 && (
                    <span className="mt-1 block text-xs text-zinc-500">
                      с учётом сброса fatigue каждые 24 ч · {formatFullNumber(result.planDays)}{" "}
                      дн.
                    </span>
                  )}
                </p>
              )}
              {result.breakdown && (
                <FatigueBreakdownList
                  totalLabel="С учётом fatigue нужно набрать"
                  green={result.breakdown.green}
                  orange={result.breakdown.orange}
                  red={result.breakdown.red}
                  total={result.breakdown.total}
                  xpPerMin={activeXpPerMin}
                  totalMinutesOverride={result.planMinutes}
                  dayBreakdown={result.dayBreakdown}
                />
              )}
            </>
          ) : (
            <p className="text-sm text-zinc-600">Введите данные и нажмите «Посчитать»</p>
          )}
        </section>
      </div>
    </div>
  );
}
