import { useCallback, useEffect, useRef, useState } from "react";
import type { TimerSnapshot } from "../lib/raidTimers";
import {
  detectPhaseAlerts,
  playPhaseAlert,
  playSoundPreview,
  readRaidTimerSoundSelection,
  readRaidTimerSoundsEnabled,
  snapshotPhases,
  stopSoundPreview,
  unlockRaidTimerSounds,
  writeRaidTimerSoundSelection,
  writeRaidTimerSoundsEnabled,
  type TrackedPhase,
} from "../lib/raidTimerSounds";

export function useRaidTimerSounds() {
  const [enabled, setEnabledState] = useState(() => readRaidTimerSoundsEnabled());
  const [soonSoundId, setSoonSoundIdState] = useState(() => readRaidTimerSoundSelection("soon"));
  const [windowSoundId, setWindowSoundIdState] = useState(() => readRaidTimerSoundSelection("window"));

  useEffect(() => () => stopSoundPreview(), []);

  const setEnabled = useCallback((value: boolean) => {
    setEnabledState(value);
    writeRaidTimerSoundsEnabled(value);
    if (value) {
      void unlockRaidTimerSounds();
    }
  }, []);

  const toggleEnabled = useCallback(() => {
    setEnabledState((prev) => {
      const next = !prev;
      writeRaidTimerSoundsEnabled(next);
      if (next) {
        void unlockRaidTimerSounds();
      }
      return next;
    });
  }, []);

  const setSoonSound = useCallback((id: string) => {
    writeRaidTimerSoundSelection("soon", id);
    setSoonSoundIdState(id);
  }, []);

  const setWindowSound = useCallback((id: string) => {
    writeRaidTimerSoundSelection("window", id);
    setWindowSoundIdState(id);
  }, []);

  const previewSound = useCallback((id: string) => {
    playSoundPreview(id);
  }, []);

  return {
    enabled,
    setEnabled,
    toggleEnabled,
    soonSoundId,
    windowSoundId,
    setSoonSound,
    setWindowSound,
    previewSound,
  };
}

export function useRaidTimerSoundAlerts(
  snapshots: Map<number, TimerSnapshot>,
  enabled: boolean,
) {
  const prevPhasesRef = useRef<Map<number, TrackedPhase>>(new Map());
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      initializedRef.current = false;
      prevPhasesRef.current = new Map();
      return;
    }

    if (!initializedRef.current) {
      prevPhasesRef.current = snapshotPhases(snapshots);
      detectPhaseAlerts(prevPhasesRef.current, snapshots, { initialize: true });
      initializedRef.current = true;
      return;
    }

    const alerts = detectPhaseAlerts(prevPhasesRef.current, snapshots);
    for (const alert of alerts) {
      playPhaseAlert(alert);
    }
  }, [snapshots, enabled]);
}
