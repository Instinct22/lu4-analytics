export const PERIOD_PRESETS = [
  { key: "1h", label: "1ч" },
  { key: "2h", label: "2ч" },
  { key: "3h", label: "3ч" },
  { key: "6h", label: "6ч" },
  { key: "12h", label: "12ч" },
  { key: "1d", label: "1д" },
  { key: "3d", label: "3д" },
] as const;

export type PeriodKey = (typeof PERIOD_PRESETS)[number]["key"] | "custom";

export interface PeriodState {
  period: PeriodKey;
  from: string;
  to: string;
}

const PERIOD_HOURS: Record<Exclude<PeriodKey, "custom">, number> = {
  "1h": 1,
  "2h": 2,
  "3h": 3,
  "6h": 6,
  "12h": 12,
  "1d": 24,
  "3d": 72,
};

/** Bucket step for market timeline charts, derived from the selected period length. */
export function timelineIntervalForPeriod(state: PeriodState): string {
  let hours = PERIOD_HOURS["1d"];
  if (state.period === "custom" && state.from && state.to) {
    hours = Math.max(
      (new Date(state.to).getTime() - new Date(state.from).getTime()) / 3_600_000,
      1 / 60,
    );
  } else if (state.period !== "custom") {
    hours = PERIOD_HOURS[state.period];
  }

  if (hours <= 1) return "1m";
  if (hours <= 6) return "5m";
  if (hours <= 24) return "30m";
  return "1h";
}

/** Absolute from/to for endpoints that filter by recorded_at (e.g. market timeline). */
export function periodTimeRange(state: PeriodState): { from: string; to: string } {
  if (state.period === "custom" && state.from && state.to) {
    return { from: new Date(state.from).toISOString(), to: new Date(state.to).toISOString() };
  }
  const hours =
    state.period !== "custom" ? PERIOD_HOURS[state.period] : PERIOD_HOURS["1d"];
  const to = new Date();
  const from = new Date(to.getTime() - hours * 3_600_000);
  return { from: from.toISOString(), to: to.toISOString() };
}

export function periodQueryParams(state: PeriodState): Record<string, string> {
  if (state.period === "custom" && state.from && state.to) {
    return { from: new Date(state.from).toISOString(), to: new Date(state.to).toISOString() };
  }
  if (state.period !== "custom") {
    return { period: state.period };
  }
  return { period: "1d" };
}
