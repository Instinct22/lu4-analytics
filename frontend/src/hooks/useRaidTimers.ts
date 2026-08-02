import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clearRaidTimer, getRaidTimers, setRaidTimer } from "../api/raid";
import type { RaidBoss } from "../lib/raidBosses";
import {
  bossRespawn,
  clearStoredTimers,
  evaluateTimer,
  loadStoredTimers,
  parseKillTimeInput,
  type TimerSnapshot,
} from "../lib/raidTimers";

const TIMERS_KEY = ["raid", "timers"];

/** Timers are shared by the whole server, so they live in the database. */
export function useRaidTimers(bosses: RaidBoss[], canWrite: boolean, canView = true) {
  const queryClient = useQueryClient();
  const [now, setNow] = useState(() => Date.now());

  const { data: timers = [], isSuccess } = useQuery({
    queryKey: TIMERS_KEY,
    queryFn: getRaidTimers,
    refetchInterval: 30_000,
    enabled: canView,
  });

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: TIMERS_KEY });
  }, [queryClient]);

  const saveMutation = useMutation({
    mutationFn: ({ bossId, killedAt }: { bossId: number; killedAt?: Date }) =>
      setRaidTimer(bossId, killedAt),
    onSuccess: invalidate,
  });

  const clearMutation = useMutation({
    mutationFn: (bossId: number) => clearRaidTimer(bossId),
    onSuccess: invalidate,
  });

  const bossById = useMemo(() => {
    const map = new Map<number, RaidBoss>();
    for (const b of bosses) map.set(b.id, b);
    return map;
  }, [bosses]);

  const snapshots = useMemo(() => {
    const out = new Map<number, TimerSnapshot>();
    for (const entry of timers) {
      const boss = bossById.get(entry.bossId);
      if (!boss) continue;
      const respawn = bossRespawn(boss);
      if (!respawn) continue;
      const killedAt = Date.parse(entry.killedAt);
      if (!Number.isFinite(killedAt)) continue;
      out.set(entry.bossId, evaluateTimer(killedAt, respawn, now));
    }
    return out;
  }, [timers, bossById, now]);

  // One-time handover of timers kept in localStorage before they went global.
  const migratedRef = useRef(false);
  useEffect(() => {
    if (migratedRef.current || !canWrite || !isSuccess) return;
    const legacy = loadStoredTimers();
    const legacyIds = Object.keys(legacy);
    if (legacyIds.length === 0) return;
    migratedRef.current = true;

    const onServer = new Set(timers.map((t) => t.bossId));
    void (async () => {
      for (const id of legacyIds) {
        const bossId = Number(id);
        const killedAt = new Date(legacy[id]?.killedAt ?? "");
        if (onServer.has(bossId) || !Number.isFinite(killedAt.getTime())) continue;
        try {
          await setRaidTimer(bossId, killedAt);
        } catch {
          // Boss may no longer exist upstream — drop the stale entry.
        }
      }
      clearStoredTimers();
      invalidate();
    })();
  }, [canWrite, isSuccess, timers, invalidate]);

  const startFromInput = useCallback(
    (bossId: number, hhmm: string) => {
      const boss = bossById.get(bossId);
      if (!boss || !bossRespawn(boss)) return false;
      const killed = parseKillTimeInput(hhmm);
      if (!killed) return false;
      saveMutation.mutate({ bossId, killedAt: killed });
      return true;
    },
    [bossById, saveMutation],
  );

  const startAuto = useCallback(
    (bossId: number) => {
      const boss = bossById.get(bossId);
      if (!boss || !bossRespawn(boss)) return false;
      saveMutation.mutate({ bossId, killedAt: new Date() });
      return true;
    },
    [bossById, saveMutation],
  );

  const clearTimer = useCallback(
    (bossId: number) => {
      clearMutation.mutate(bossId);
    },
    [clearMutation],
  );

  return {
    snapshots,
    timers,
    now,
    startFromInput,
    startAuto,
    clearTimer,
    isSaving: saveMutation.isPending || clearMutation.isPending,
  };
}
