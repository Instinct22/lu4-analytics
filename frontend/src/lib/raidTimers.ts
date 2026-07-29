/** Raid boss respawn timer helpers. */

import { mediaUrl } from "../api/client";
import type { RaidBoss } from "./raidBosses";

export type TimerPhase = "idle" | "waiting" | "soon" | "window" | "overdue";

export type ParsedRespawn = {
  /** Milliseconds until earliest possible spawn (base − variance). */
  minMs: number;
  /** Milliseconds until latest possible spawn (base + variance). */
  maxMs: number;
  label: string;
};

const HOUR = 3_600_000;
const MINUTE = 60_000;
const SOON_MS = 30 * MINUTE;

/** "6 hours ± 2 hours" | "9 hours ± 1 hour" */
const RESPAWN_RE =
  /(\d+)\s*hours?\s*[±+\-]\s*(\d+)\s*hours?/i;

export function parseRespawn(raw: string | null | undefined): ParsedRespawn | null {
  if (!raw) return null;
  const text = raw.replace(/\ufffd/g, "±").trim();
  if (/^fixed$/i.test(text)) return null;
  const m = text.match(RESPAWN_RE);
  if (!m) return null;
  const baseH = Number(m[1]);
  const varH = Number(m[2]);
  if (!Number.isFinite(baseH) || !Number.isFinite(varH)) return null;
  const baseMs = baseH * HOUR;
  const varMs = varH * HOUR;
  return {
    minMs: Math.max(0, baseMs - varMs),
    maxMs: baseMs + varMs,
    label: text,
  };
}

/** Respawn window of a boss, preferring the seconds computed on import. */
export function bossRespawn(boss: RaidBoss): ParsedRespawn | null {
  const { respawnMinSec, respawnMaxSec } = boss;
  if (respawnMinSec != null && respawnMaxSec != null) {
    return {
      minMs: respawnMinSec * 1000,
      maxMs: respawnMaxSec * 1000,
      label: boss.respawn ?? "",
    };
  }
  return parseRespawn(boss.respawn);
}

export type TimerSnapshot = {
  phase: TimerPhase;
  /** Signed ms until min spawn: negative = past min. Used for waiting/soon sort. */
  remainingToMinMs: number;
  /** Signed ms until max (100%) spawn: negative = past max. */
  remainingToMaxMs: number;
  display: string;
  colorClass: string;
};

export function evaluateTimer(killedAtMs: number, respawn: ParsedRespawn, nowMs: number): TimerSnapshot {
  const minAt = killedAtMs + respawn.minMs;
  const maxAt = killedAtMs + respawn.maxMs;
  const remainingToMinMs = minAt - nowMs;
  const remainingToMaxMs = maxAt - nowMs;

  let phase: TimerPhase;
  if (nowMs >= maxAt) phase = "overdue";
  else if (nowMs >= minAt) phase = "window";
  else if (remainingToMinMs <= SOON_MS) phase = "soon";
  else phase = "waiting";

  // waiting/soon → countdown to min; window → countdown to 100% (max); overdue → +past max
  let displayMs: number;
  let overtime = false;
  if (phase === "waiting" || phase === "soon") {
    displayMs = remainingToMinMs;
  } else if (phase === "window") {
    displayMs = remainingToMaxMs;
  } else {
    displayMs = Math.abs(remainingToMaxMs);
    overtime = true;
  }

  return {
    phase,
    remainingToMinMs,
    remainingToMaxMs,
    display: formatTimerDisplay(displayMs, overtime),
    colorClass: phaseColorClass(phase),
  };
}

export function phaseColorClass(phase: TimerPhase): string {
  switch (phase) {
    case "soon":
      return "text-orange-400";
    case "window":
      return "text-emerald-400";
    case "overdue":
      return "text-red-400";
    case "waiting":
      return "text-zinc-100";
    default:
      return "text-zinc-500";
  }
}

export function formatTimerDisplay(ms: number, overtime = false): string {
  const totalSec = Math.floor(Math.abs(ms) / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const body =
    h > 0
      ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      : `${m}:${String(s).padStart(2, "0")}`;
  return overtime ? `+${body}` : body;
}

/** Parse HH:MM as kill time on the most recent occurrence ≤ now. */
export function parseKillTimeInput(hhmm: string, now = new Date()): Date | null {
  const m = hhmm.trim().match(/^(\d{2}):(\d{2})$/);
  if (!m) return null;
  const hours = Number(m[1]);
  const minutes = Number(m[2]);
  if (hours > 23 || minutes > 59) return null;
  const d = new Date(now);
  d.setSeconds(0, 0);
  d.setHours(hours, minutes, 0, 0);
  if (d.getTime() > now.getTime()) {
    d.setDate(d.getDate() - 1);
  }
  return d;
}

/**
 * Mask raw keystrokes into HH:MM.
 * Preserves `:` so hour/minute segments stay in place while editing.
 * Auto-inserts `:` after two hour digits when typing without a separator.
 * Clamps hours 00–23 and minutes 00–59 once a segment is complete.
 */
export function maskTimeInput(raw: string): string {
  const cleaned = raw.replace(/[^\d:]/g, "");
  if (!cleaned) return "";

  const colonIdx = cleaned.indexOf(":");
  let hours: string;
  let minutes: string;
  let showColon: boolean;

  if (colonIdx >= 0) {
    showColon = true;
    hours = cleaned.slice(0, colonIdx).replace(/\D/g, "").slice(0, 2);
    minutes = cleaned.slice(colonIdx + 1).replace(/\D/g, "").slice(0, 2);
  } else {
    const digits = cleaned.replace(/\D/g, "").slice(0, 4);
    if (digits.length <= 2) {
      hours = digits;
      minutes = "";
      showColon = false;
    } else {
      hours = digits.slice(0, 2);
      minutes = digits.slice(2);
      showColon = true;
    }
  }

  if (hours.length === 2) {
    const h = Math.min(23, Number(hours));
    hours = String(h).padStart(2, "0");
  }

  if (minutes.length === 2) {
    const m = Math.min(59, Number(minutes));
    minutes = String(m).padStart(2, "0");
  }

  if (!showColon) return hours;
  if (!minutes) return `${hours}:`;
  return `${hours}:${minutes}`;
}

export function formatHm(date: Date): string {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export const TIMER_STORAGE_KEY = "lu4.raidBossTimers.v1";

export type StoredTimers = Record<string, { killedAt: string }>;

export function loadStoredTimers(): StoredTimers {
  try {
    const raw = localStorage.getItem(TIMER_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as StoredTimers;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function clearStoredTimers(): void {
  localStorage.removeItem(TIMER_STORAGE_KEY);
}

export function dropIconUrl(icon: string | null | undefined): string | null {
  if (!icon) return null;
  if (icon.startsWith("http")) return icon;
  return mediaUrl(`images/i64/${icon}`);
}

/** Local raid boss portrait under /media/images/raid-bosses/. */
export function raidBossImageUrl(image: string | null | undefined): string | null {
  if (!image) return null;
  if (image.startsWith("http")) return image;
  const path = image.startsWith("images/") ? image : `images/${image.replace(/^\/+/, "")}`;
  return mediaUrl(path);
}
