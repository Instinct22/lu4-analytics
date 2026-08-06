import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import QuestDetailPanel from "../components/quests/QuestDetail";
import LevelRangeControl from "../components/settings/LevelRangeControl";
import { PageHeader, LoadingState, ErrorState } from "../components/ui";
import { getQuest, getQuests, type QuestBrief } from "../api/quests";
import { useLevelRange } from "../hooks/useLevelRange";
import {
  formatQuestLevel,
  questOverlapsLevelRange,
} from "../lib/quests";

const EMPTY: QuestBrief[] = [];

export default function QuestsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const selectedId = useMemo(() => {
    const raw = searchParams.get("id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }, [searchParams]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quests", "catalog"],
    queryFn: () => getQuests(),
    staleTime: 1000 * 60 * 30,
  });

  const quests = data?.quests ?? EMPTY;

  const levels = useMemo(() => {
    const mins = quests.map((q) => q.level_min).filter((n): n is number => n != null);
    const maxs = quests
      .map((q) => q.level_max ?? (q.level_min != null ? 99 : null))
      .filter((n): n is number => n != null);
    if (mins.length === 0) return { min: 1, max: 85 };
    return { min: Math.min(...mins), max: Math.max(...maxs, ...mins) };
  }, [quests]);

  const { levelRange, setLevelRange, minLevel, maxLevel, sliderBounds } = useLevelRange(levels);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return quests.filter((quest) => {
      if (!questOverlapsLevelRange(quest.level_min, quest.level_max, minLevel, maxLevel)) {
        return false;
      }
      if (!q) return true;
      const npc = quest.start_npc?.name?.toLowerCase() ?? "";
      return (
        quest.name.toLowerCase().includes(q) ||
        quest.description.toLowerCase().includes(q) ||
        npc.includes(q)
      );
    });
  }, [quests, query, minLevel, maxLevel]);

  const { data: selected, isFetching: detailLoading } = useQuery({
    queryKey: ["quests", "detail", selectedId],
    queryFn: () => getQuest(selectedId!),
    enabled: selectedId != null,
    staleTime: 1000 * 60 * 30,
  });

  useEffect(() => {
    if (selectedId == null && filtered.length > 0) return;
    if (selectedId != null && !quests.some((q) => q.id === selectedId)) {
      setSearchParams({}, { replace: true });
    }
  }, [filtered.length, quests, selectedId, setSearchParams]);

  const selectQuest = (id: number) => {
    setSearchParams({ id: String(id) });
  };

  const clearSelection = () => {
    setSearchParams({});
  };

  return (
    <div className="min-h-full">
      <PageHeader title="Квесты">
        <p className="text-sm text-zinc-500">
          {isLoading
            ? "Загрузка…"
            : `${filtered.length} из ${quests.length} · фильтр по пересечению уровней`}
        </p>
      </PageHeader>

      {isError && <ErrorState message="Не удалось загрузить квесты." />}

      <div className="flex flex-col gap-5 xl:flex-row xl:items-stretch">
        <aside className="flex w-full shrink-0 flex-col gap-3 xl:w-80 2xl:w-96">
          <div className="card space-y-3 !p-4">
            <input
              className="input"
              placeholder="Поиск квеста или NPC…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div>
              <div className="mb-1.5 flex items-center justify-between gap-2 text-[0.7rem] text-zinc-500">
                <span>Уровень</span>
                <Link to="/settings" className="text-amber-400/80 hover:text-amber-300">
                  Настройки
                </Link>
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
            {isLoading ? (
              <LoadingState />
            ) : (
              <ul className="divide-y divide-zinc-800/70">
                {filtered.map((quest) => {
                  const active = quest.id === selectedId;
                  return (
                    <li key={quest.id}>
                      <button
                        type="button"
                        onClick={() => selectQuest(quest.id)}
                        className={[
                          "flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors",
                          active
                            ? "bg-amber-950/40 text-amber-100"
                            : "text-zinc-300 hover:bg-zinc-900/80",
                        ].join(" ")}
                      >
                        <span className="mt-0.5 w-12 shrink-0 text-xs tabular-nums text-zinc-500">
                          {formatQuestLevel(quest.level_min, quest.level_max)}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{quest.name}</span>
                          {quest.start_npc?.name && (
                            <span className="mt-0.5 block truncate text-xs text-zinc-500">
                              {quest.start_npc.name}
                            </span>
                          )}
                        </span>
                      </button>
                    </li>
                  );
                })}
                {filtered.length === 0 && (
                  <li className="px-3 py-6 text-center text-sm text-zinc-500">
                    Нет квестов в выбранном диапазоне
                  </li>
                )}
              </ul>
            )}
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          {selectedId == null && (
            <div className="card text-sm text-zinc-500">
              Выберите квест, чтобы открыть описание, награды и этапы прохождения.
            </div>
          )}
          {selectedId != null && detailLoading && !selected && <LoadingState />}
          {selectedId != null && selected && (
            <QuestDetailPanel quest={selected} onClose={clearSelection} />
          )}
          {selectedId != null && !detailLoading && !selected && (
            <ErrorState message="Квест не найден." />
          )}
        </div>
      </div>
    </div>
  );
}
