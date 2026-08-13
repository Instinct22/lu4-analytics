import { useCallback, useEffect, useRef, useState } from "react";
import type { TimerSnapshot } from "../lib/raidTimers";
import {
  detectPhaseAlerts,
  playPhaseAlert,
  readRaidTimerSoundsEnabled,
  snapshotPhases,
  unlockRaidTimerSounds,
  writeRaidTimerSoundsEnabled,
  type TrackedPhase,
} from "../lib/raidTimerSounds";

export function useRaidTimerSounds() {
  const [enabled, setEnabledState] = useState(() => readRaidTimerSoundsEnabled());

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

  return { enabled, setEnabled, toggleEnabled };
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
