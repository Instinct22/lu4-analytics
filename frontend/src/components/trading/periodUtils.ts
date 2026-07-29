export const PERIOD_PRESETS = [
  { key: "1h", label: "1 час" },
  { key: "6h", label: "6 часов" },
  { key: "12h", label: "12 часов" },
  { key: "24h", label: "24 часа" },
  { key: "3d", label: "3 дня" },
  { key: "7d", label: "7 дней" },
  { key: "30d", label: "30 дней" },
] as const;

export type PeriodKey = (typeof PERIOD_PRESETS)[number]["key"] | "custom";

export interface PeriodState {
  period: PeriodKey;
  from: string;
  to: string;
}

export function periodQueryParams(state: PeriodState): Record<string, string> {
  if (state.period === "custom" && state.from && state.to) {
    return { from: new Date(state.from).toISOString(), to: new Date(state.to).toISOString() };
  }
  if (state.period !== "custom") {
    return { period: state.period };
  }
  return { period: "24h" };
}
