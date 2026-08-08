import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clearRaidTimer, getRaidNotes, getRaidTimers, putRaidNote, setRaidTimer } from "../api/raid";
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
const NOTES_KEY = ["raid", "notes"];

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

  const { data: notes = [] } = useQuery({
    queryKey: NOTES_KEY,
    queryFn: getRaidNotes,
    refetchInterval: 30_000,
    enabled: canView,
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: TIMERS_KEY });
  }, [queryClient]);

  const invalidateNotes = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: NOTES_KEY });
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

  const noteMutation = useMutation({
    mutationFn: ({ bossId, note }: { bossId: number; note: string }) => putRaidNote(bossId, note),
    onSuccess: invalidateNotes,
  });

  const bossById = useMemo(() => {
    const map = new Map<number, RaidBoss>();
    for (const b of bosses) map.set(b.id, b);
    return map;
  }, [bosses]);

  const notesByBossId = useMemo(() => {
    const out = new Map<number, string>();
    for (const entry of notes) {
      const text = entry.note?.trim();
      if (text) out.set(entry.bossId, text);
    }
    return out;
  }, [notes]);

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

  const clearNote = useCallback(
    (bossId: number) => {
      if (!canWrite) return;
      noteMutation.mutate({ bossId, note: "" });
    },
    [canWrite, noteMutation],
  );

  const startFromInput = useCallback(
    (bossId: number, hhmm: string) => {
      const boss = bossById.get(bossId);
      if (!boss || !bossRespawn(boss)) return false;
      const killed = parseKillTimeInput(hhmm);
      if (!killed) return false;
      saveMutation.mutate({ bossId, killedAt: killed });
      clearNote(bossId);
      return true;
    },
    [bossById, saveMutation, clearNote],
  );

  const startAuto = useCallback(
    (bossId: number) => {
      const boss = bossById.get(bossId);
      if (!boss || !bossRespawn(boss)) return false;
      saveMutation.mutate({ bossId, killedAt: new Date() });
      clearNote(bossId);
      return true;
    },
    [bossById, saveMutation, clearNote],
  );

  const clearTimer = useCallback(
    (bossId: number) => {
      clearMutation.mutate(bossId);
      clearNote(bossId);
    },
    [clearMutation, clearNote],
  );

  const saveNote = useCallback(
    (bossId: number, note: string) => {
      if (!canWrite) return;
      noteMutation.mutate({ bossId, note });
    },
    [canWrite, noteMutation],
  );

  return {
    snapshots,
    timers,
    notesByBossId,
    now,
    startFromInput,
    startAuto,
    clearTimer,
    saveNote,
    isSaving: saveMutation.isPending || clearMutation.isPending,
    isSavingNote: noteMutation.isPending,
  };
}
