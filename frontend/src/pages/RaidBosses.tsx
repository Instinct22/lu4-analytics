import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import RaidBossDetail from "../components/raid/RaidBossDetail";
import RaidBossMap from "../components/raid/RaidBossMap";
import RaidTimerBanners from "../components/raid/RaidTimerBanners";
import RaidVisibilitySettings from "../components/raid/RaidVisibilitySettings";
import LevelRangeControl from "../components/settings/LevelRangeControl";
import { PageHeader } from "../components/ui";
import { getRaidBosses, getRaidVisibility, putRaidVisibility } from "../api/raid";
import { useAuth } from "../hooks/useAuth";
import { useLevelRange } from "../hooks/useLevelRange";
import { useRaidTimers } from "../hooks/useRaidTimers";
import type { RaidBoss } from "../lib/raidBosses";

const EMPTY_BOSSES: RaidBoss[] = [];
const VISIBILITY_KEY = ["raid", "visibility"] as const;
const SAVE_DEBOUNCE_MS = 400;

export default function RaidBossesPage() {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("feature.raid_timers_write");
  const canViewTimers = hasPermission("feature.raid_timers_view");
  const canViewRoute = hasPermission("feature.raid_route");
  const canManageVisibility = hasPermission("feature.raid_visibility");
  const queryClient = useQueryClient();
  const saveTimer = useRef<number | null>(null);

  const { data: payload, isLoading, isError } = useQuery({
    queryKey: ["raid", "bosses"],
    queryFn: getRaidBosses,
    staleTime: 1000 * 60 * 30,
  });

  const { data: visibility } = useQuery({
    queryKey: VISIBILITY_KEY,
    queryFn: getRaidVisibility,
    staleTime: 1000 * 30,
  });

  const visibilityMutation = useMutation({
    mutationFn: putRaidVisibility,
    onSuccess: (data) => {
      queryClient.setQueryData(VISIBILITY_KEY, data);
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: VISIBILITY_KEY });
    },
  });

  const bosses = payload?.bosses ?? EMPTY_BOSSES;
  const { snapshots, startFromInput, startAuto, clearTimer } = useRaidTimers(
    bosses,
    canWrite,
    canViewTimers,
  );

  const hiddenIds = useMemo(() => new Set(visibility?.hiddenIds ?? []), [visibility]);

  const visibleBosses = useMemo(
    () => bosses.filter((b) => !hiddenIds.has(b.id)),
    [bosses, hiddenIds],
  );

  const levels = useMemo(() => {
    const vals = bosses.map((b) => b.level).filter((n): n is number => n != null);
    if (vals.length === 0) return { min: 20, max: 85 };
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }, [bosses]);

  const { levelRange, setLevelRange, minLevel, maxLevel, sliderBounds } = useLevelRange(levels);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return visibleBosses.filter((b) => {
      const lvl = b.level ?? 0;
      if (lvl < minLevel || lvl > maxLevel) return false;
      if (!q) return true;
      return (
        b.name.toLowerCase().includes(q) ||
        (b.location?.toLowerCase().includes(q) ?? false) ||
        (b.howToReach?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [visibleBosses, query, minLevel, maxLevel]);

  const selected = useMemo(
    () => bosses.find((b) => b.id === selectedId) ?? null,
    [bosses, selectedId],
  );

  const bannerGroups = useMemo(() => {
    const active: { boss: RaidBoss; timer: NonNullable<ReturnType<typeof snapshots.get>> }[] = [];
    const waiting: typeof active = [];
    const overdue: typeof active = [];
    for (const boss of visibleBosses) {
      const timer = snapshots.get(boss.id);
      if (!timer) continue;
      if (timer.phase === "overdue") overdue.push({ boss, timer });
      else if (timer.phase === "soon" || timer.phase === "window") active.push({ boss, timer });
      else if (timer.phase === "waiting") waiting.push({ boss, timer });
    }
    return { active, waiting, overdue };
  }, [visibleBosses, snapshots]);

  useEffect(
    () => () => {
      if (saveTimer.current != null) window.clearTimeout(saveTimer.current);
    },
    [],
  );

  const openSettings = () => {
    setSelectedId(null);
    setSettingsOpen(true);
  };

  const closeSettings = () => setSettingsOpen(false);

  const selectBoss = (id: number) => {
    setSettingsOpen(false);
    setSelectedId(id);
  };

  const toggleVisibility = (bossId: number, visible: boolean) => {
    if (!canManageVisibility) return;
    const current = new Set(queryClient.getQueryData<{ hiddenIds: number[] }>(VISIBILITY_KEY)?.hiddenIds ?? []);
    if (visible) current.delete(bossId);
    else current.add(bossId);
    const nextIds = [...current].sort((a, b) => a - b);
    queryClient.setQueryData(VISIBILITY_KEY, { hiddenIds: nextIds });

    if (saveTimer.current != null) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      visibilityMutation.mutate(nextIds);
    }, SAVE_DEBOUNCE_MS);
  };

  const showRightPanel = settingsOpen || selected != null;

  return (
    <div className="min-h-full">
      <PageHeader title="Рейд Боссы">
        <p className="text-sm text-zinc-500">
          {isLoading
            ? "Загрузка…"
            : `${filtered.length} из ${visibleBosses.length}${
                hiddenIds.size > 0 ? ` · скрыто ${hiddenIds.size}` : ""
              } · карта и дроп`}
        </p>
      </PageHeader>

      {isError && (
        <div className="card mb-5 text-sm text-red-400">Не удалось загрузить рейд-боссов.</div>
      )}

      {canViewTimers && (
        <RaidTimerBanners
          active={bannerGroups.active}
          waiting={bannerGroups.waiting}
          overdue={bannerGroups.overdue}
          onSelect={selectBoss}
          canClear={canWrite}
          onClear={clearTimer}
        />
      )}

      <div className="flex flex-col gap-5 xl:flex-row xl:items-stretch">
        <aside className="flex w-full shrink-0 flex-col gap-3 xl:w-80 2xl:w-96">
          <div className="card space-y-3 !p-4">
            <input
              className="input"
              placeholder="Поиск босса или локации…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div>
              <div className="mb-1.5 flex items-center justify-between gap-2 text-[0.7rem] text-zinc-500">
                <span>Уровень</span>
                <span className="flex items-center gap-2">
                  {canManageVisibility && (
                    <button
                      type="button"
                      onClick={openSettings}
                      className="text-amber-400/80 hover:text-amber-300"
                    >
                      Список РБ
                    </button>
                  )}
                  <Link to="/settings" className="text-amber-400/80 hover:text-amber-300">
                    Настройки
                  </Link>
                </span>
              </div>
              <LevelRangeControl
                value={levelRange}
                onChange={setLevelRange}
                sliderMin={sliderBounds.min}
                sliderMax={sliderBounds.max}
                compact
              />
            </div>
          </div>

          <div className="panel max-h-[28rem] overflow-y-auto xl:max-h-[calc(100vh-17rem)]">
            <ul className="divide-y divide-zinc-800/70">
              {filtered.map((boss) => {
                const active = !settingsOpen && boss.id === selectedId;
                const timer = snapshots.get(boss.id);
                return (
                  <li key={boss.id}>
                    <button
                      type="button"
                      onClick={() => selectBoss(boss.id)}
                      className={[
                        "flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors",
                        active
                          ? "bg-amber-500/10 text-amber-300"
                          : "text-zinc-300 hover:bg-zinc-800/50 hover:text-zinc-100",
                      ].join(" ")}
                    >
                      <span className="w-8 shrink-0 text-xs tabular-nums text-zinc-500">
                        {boss.level ?? "—"}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{boss.name}</span>
                        {boss.respawn && (
                          <span className="mt-0.5 block truncate text-[0.7rem] text-zinc-500">
                            {boss.respawn}
                          </span>
                        )}
                      </span>
                      {canViewTimers && timer && (
                        <span
                          className={`shrink-0 font-mono text-xs font-semibold tabular-nums ${timer.colorClass}`}
                        >
                          {timer.display}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
              {filtered.length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-zinc-500">
                  {isLoading ? "Загрузка…" : "Ничего не найдено"}
                </li>
              )}
            </ul>
          </div>
        </aside>

        <div className="min-h-[32rem] min-w-0 flex-1 xl:min-h-[calc(100vh-12rem)]">
          {payload && (
            <RaidBossMap
              payload={payload}
              bosses={filtered}
              selectedId={settingsOpen ? null : selectedId}
              onSelect={selectBoss}
              timers={canViewTimers ? snapshots : new Map()}
            />
          )}
        </div>

        {showRightPanel && (
          <div className="flex h-[min(40rem,calc(100vh-8rem))] w-full shrink-0 flex-col xl:h-[calc(100vh-12rem)] xl:w-[26rem] 2xl:w-[32rem]">
            {settingsOpen && canManageVisibility ? (
              <RaidVisibilitySettings
                bosses={bosses}
                hiddenIds={hiddenIds}
                onToggle={toggleVisibility}
                onClose={closeSettings}
                saving={visibilityMutation.isPending}
              />
            ) : selected ? (
              <RaidBossDetail
                boss={selected}
                timer={canViewTimers ? snapshots.get(selected.id) ?? null : null}
                canWrite={canWrite}
                canViewRoute={canViewRoute}
                onClose={() => setSelectedId(null)}
                onStart={(hhmm) => startFromInput(selected.id, hhmm)}
                onAuto={() => startAuto(selected.id)}
                onClear={() => clearTimer(selected.id)}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
