const KEYS = {
  dailyGreen: "lu4.exp.dailyGreen",
  dailyYellow: "lu4.exp.dailyYellow",
  greenPercent: "lu4.exp.greenFatiguePercent",
  yellowPercent: "lu4.exp.yellowFatiguePercent",
  /** @deprecated migrated to green/yellow percent keys */
  legacyPercent: "lu4.exp.currentFatiguePercent",
  useFatigue: "lu4.exp.useFatigue",
  useXpPerMin: "lu4.exp.useXpPerMin",
  xpPerMin: "lu4.exp.xpPerMin",
} as const;

function readString(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function writeString(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore quota / private mode */
  }
}

export function loadDailyGreen(): string {
  return readString(KEYS.dailyGreen, "");
}

export function loadDailyYellow(): string {
  return readString(KEYS.dailyYellow, "");
}

function loadPercent(key: string): string {
  const own = readString(key, "");
  if (own !== "") return own;
  // Fallback from the old single-percent key.
  return readString(KEYS.legacyPercent, "100");
}

export function loadGreenFatiguePercent(): string {
  return loadPercent(KEYS.greenPercent);
}

export function loadYellowFatiguePercent(): string {
  return loadPercent(KEYS.yellowPercent);
}

export function loadUseFatigue(): boolean {
  return readString(KEYS.useFatigue, "false") === "true";
}

export function saveDailyGreen(value: string) {
  writeString(KEYS.dailyGreen, value);
}

export function saveDailyYellow(value: string) {
  writeString(KEYS.dailyYellow, value);
}

export function saveGreenFatiguePercent(value: string) {
  writeString(KEYS.greenPercent, value);
}

export function saveYellowFatiguePercent(value: string) {
  writeString(KEYS.yellowPercent, value);
}

export function saveUseFatigue(value: boolean) {
  writeString(KEYS.useFatigue, value ? "true" : "false");
}

export function loadUseXpPerMin(): boolean {
  return readString(KEYS.useXpPerMin, "false") === "true";
}

export function saveUseXpPerMin(value: boolean) {
  writeString(KEYS.useXpPerMin, value ? "true" : "false");
}

export function loadXpPerMin(): number | null {
  const raw = readString(KEYS.xpPerMin, "");
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function saveXpPerMin(value: number | null) {
  if (value == null || !Number.isFinite(value) || value <= 0) {
    try {
      localStorage.removeItem(KEYS.xpPerMin);
    } catch {
      /* ignore */
    }
    return;
  }
  writeString(KEYS.xpPerMin, String(value));
}
