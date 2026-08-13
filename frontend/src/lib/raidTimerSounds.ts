import type { TimerPhase, TimerSnapshot } from "./raidTimers";

export const RAID_SOUND_SOON_URL = "/sound/pesik-pesik-av-av-av.mp3";
export const RAID_SOUND_WINDOW_URL = "/sound/okhaeshechki-dattebaeshechki-poanimeshimsia.mp3";

export const RAID_TIMER_SOUNDS_STORAGE_KEY = "lu4.raid_timer_sounds_enabled";

export type TrackedPhase = TimerPhase | "idle";

export type PhaseAlert = "soon" | "window";

export function readRaidTimerSoundsEnabled(): boolean {
  try {
    return localStorage.getItem(RAID_TIMER_SOUNDS_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeRaidTimerSoundsEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(RAID_TIMER_SOUNDS_STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    // Private mode or quota — ignore.
  }
}

/** Build tracked phase map from current snapshots (no alerts). */
export function snapshotPhases(next: Map<number, TimerSnapshot>): Map<number, TrackedPhase> {
  const out = new Map<number, TrackedPhase>();
  for (const [bossId, snapshot] of next) {
    out.set(bossId, snapshot.phase);
  }
  return out;
}

/**
 * Compare previous and next timer phases; return deduplicated alerts for this tick.
 * Mutates `prev` to match `next` (removes cleared timers, updates phases).
 */
export function detectPhaseAlerts(
  prev: Map<number, TrackedPhase>,
  next: Map<number, TimerSnapshot>,
  options?: { initialize?: boolean },
): PhaseAlert[] {
  const initialize = options?.initialize ?? false;
  const alerts: PhaseAlert[] = [];
  const seen = new Set<PhaseAlert>();

  for (const bossId of prev.keys()) {
    if (!next.has(bossId)) prev.delete(bossId);
  }

  for (const [bossId, snapshot] of next) {
    const previous = prev.get(bossId) ?? "idle";
    const current = snapshot.phase;

    if (!initialize) {
      if (current === "soon" && (previous === "idle" || previous === "waiting")) {
        if (!seen.has("soon")) {
          alerts.push("soon");
          seen.add("soon");
        }
      } else if (current === "window" && previous === "soon") {
        if (!seen.has("window")) {
          alerts.push("window");
          seen.add("window");
        }
      }
    }

    prev.set(bossId, current);
  }

  return alerts;
}

const audioByAlert: Partial<Record<PhaseAlert, HTMLAudioElement>> = {};

function getAudio(alert: PhaseAlert): HTMLAudioElement {
  let audio = audioByAlert[alert];
  if (!audio) {
    audio = new Audio(alert === "soon" ? RAID_SOUND_SOON_URL : RAID_SOUND_WINDOW_URL);
    audio.preload = "auto";
    audioByAlert[alert] = audio;
  }
  return audio;
}

export function preloadRaidTimerSounds(): void {
  getAudio("soon");
  getAudio("window");
}

/** Warm up autoplay after an explicit user gesture (toggle ON). */
export async function unlockRaidTimerSounds(): Promise<void> {
  preloadRaidTimerSounds();
  for (const alert of ["soon", "window"] as const) {
    const audio = getAudio(alert);
    try {
      audio.currentTime = 0;
      audio.volume = 0.001;
      await audio.play();
      audio.pause();
      audio.currentTime = 0;
      audio.volume = 1;
    } catch {
      // Browser may still block until a later gesture — alerts will retry on play.
    }
  }
}

export function playPhaseAlert(alert: PhaseAlert): void {
  const audio = getAudio(alert);
  audio.currentTime = 0;
  void audio.play().catch(() => {
    // Autoplay blocked or missing file — ignore.
  });
}
