import type { TimerPhase, TimerSnapshot } from "./raidTimers";
import {
  DEFAULT_SOON_SOUND_ID,
  DEFAULT_WINDOW_SOUND_ID,
  getRaidSoundById,
  getRaidSoundUrl,
} from "./raidSoundCatalog";

export const RAID_TIMER_SOUNDS_STORAGE_KEY = "lu4.raid_timer_sounds_enabled";
export const RAID_TIMER_SOUND_SOON_KEY = "lu4.raid_timer_sound_soon";
export const RAID_TIMER_SOUND_WINDOW_KEY = "lu4.raid_timer_sound_window";

export type TrackedPhase = TimerPhase | "idle";
export type PhaseAlert = "soon" | "window";
export type SoundSelectionPhase = PhaseAlert;

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

export function readRaidTimerSoundSelection(phase: SoundSelectionPhase): string {
  const key = phase === "soon" ? RAID_TIMER_SOUND_SOON_KEY : RAID_TIMER_SOUND_WINDOW_KEY;
  const fallback = phase === "soon" ? DEFAULT_SOON_SOUND_ID : DEFAULT_WINDOW_SOUND_ID;
  try {
    const raw = localStorage.getItem(key);
    if (raw && getRaidSoundById(raw)) return raw;
  } catch {
    // ignore
  }
  return fallback;
}

export function writeRaidTimerSoundSelection(phase: SoundSelectionPhase, id: string): void {
  if (!getRaidSoundById(id)) return;
  const key = phase === "soon" ? RAID_TIMER_SOUND_SOON_KEY : RAID_TIMER_SOUND_WINDOW_KEY;
  try {
    localStorage.setItem(key, id);
  } catch {
    // ignore
  }
}

export function getSoundUrlForAlert(alert: PhaseAlert): string {
  if (alert === "soon") {
    return getRaidSoundUrl(readRaidTimerSoundSelection("soon"), DEFAULT_SOON_SOUND_ID);
  }
  return getRaidSoundUrl(readRaidTimerSoundSelection("window"), DEFAULT_WINDOW_SOUND_ID);
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

const audioByUrl = new Map<string, HTMLAudioElement>();
let activeAlert: HTMLAudioElement | null = null;

export function stopPhaseAlert(): void {
  if (!activeAlert) return;
  activeAlert.pause();
  activeAlert.loop = false;
  activeAlert.currentTime = 0;
  activeAlert = null;
}

let previewAudio: HTMLAudioElement | null = null;
let previewPlayingId: string | null = null;

function getAudioForUrl(url: string): HTMLAudioElement {
  let audio = audioByUrl.get(url);
  if (!audio) {
    audio = new Audio(url);
    audio.preload = "auto";
    audioByUrl.set(url, audio);
  }
  return audio;
}

export function preloadRaidTimerSounds(): void {
  getAudioForUrl(getSoundUrlForAlert("soon"));
  getAudioForUrl(getSoundUrlForAlert("window"));
}

/** Warm up autoplay after an explicit user gesture (toggle ON). */
export async function unlockRaidTimerSounds(): Promise<void> {
  preloadRaidTimerSounds();
  for (const alert of ["soon", "window"] as const) {
    const audio = getAudioForUrl(getSoundUrlForAlert(alert));
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

export function playPhaseAlert(alert: PhaseAlert, repeat = false): void {
  stopPhaseAlert();
  stopSoundPreview();
  const audio = getAudioForUrl(getSoundUrlForAlert(alert));
  activeAlert = audio;
  audio.loop = repeat;
  audio.volume = 1;
  audio.currentTime = 0;
  void audio.play().catch(() => {
    // Autoplay blocked or missing file — ignore.
  });
}

export function stopSoundPreview(): void {
  if (!previewAudio) return;
  previewAudio.pause();
  previewAudio.currentTime = 0;
  previewPlayingId = null;
}

export function isSoundPreviewPlaying(id: string): boolean {
  return previewPlayingId === id && previewAudio != null && !previewAudio.paused;
}

export function playSoundPreview(id: string): void {
  const entry = getRaidSoundById(id);
  if (!entry) return;

  if (isSoundPreviewPlaying(id)) {
    stopSoundPreview();
    return;
  }

  stopSoundPreview();
  previewAudio = new Audio(entry.url);
  previewPlayingId = id;
  previewAudio.currentTime = 0;
  void previewAudio.play().catch(() => {
    previewPlayingId = null;
  });
  previewAudio.onended = () => {
    if (previewPlayingId === id) previewPlayingId = null;
  };
}
