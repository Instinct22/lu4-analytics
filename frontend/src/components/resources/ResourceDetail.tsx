import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { MaterialSources, NpcSource, ResourceEntry } from "../../lib/craftResources";
import { filterSourcesByLevel, wikiUrl } from "../../lib/craftResources";
import LevelRangeControl from "../settings/LevelRangeControl";
import { ItemIcon } from "../craft/CraftCostBar";
import ResourceSourceTable from "./ResourceSourceTable";
import { ReturnLinkBar } from "../ui/ReturnLinkBar";
import type { ReturnLink } from "../../lib/internalNav";

interface Props {
  entry: ResourceEntry;
  sources: MaterialSources | undefined;
  sourcesLoading: boolean;
  minLevel: number;
  maxLevel: number;
  levelBounds: { min: number; max: number };
  onMinLevelChange: (level: number) => void;
  onMaxLevelChange: (level: number) => void;
  onLevelRangeChange?: (next: { min: number; max: number }) => void;
  sliderBounds?: { min: number; max: number };
  onNpcSelect: (source: NpcSource) => void;
  onClose: () => void;
  returnLink?: ReturnLink | null;
}

export default function ResourceDetail({
  entry,
  sources,
  sourcesLoading,
  minLevel,
  maxLevel,
  levelBounds,
  onMinLevelChange,
  onMaxLevelChange,
  onLevelRangeChange,
  sliderBounds,
  onNpcSelect,
  onClose,
  returnLink,
}: Props) {
  const { material } = entry;

  const spoil = useMemo(
    () => filterSourcesByLevel(sources?.spoil ?? [], minLevel, maxLevel),
    [sources, minLevel, maxLevel],
  );
  const drop = useMemo(
    () => filterSourcesByLevel(sources?.drop ?? [], minLevel, maxLevel),
    [sources, minLevel, maxLevel],
  );

  return (
    <div className="panel overflow-hidden">
      <ReturnLinkBar link={returnLink} />
      <div className="flex items-start justify-between gap-3 border-b border-zinc-800/80 px-5 py-4">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <ItemIcon id={material.id} size={48} />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-semibold text-zinc-50">
                <a href={wikiUrl(material.url)} target="_blank" rel="noreferrer" className="hover:text-amber-400">
                  {material.name}
                </a>
              </h3>
              <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{material.grade}</span>
            </div>
            <p className="mt-1 text-sm text-zinc-500">{material.desc}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs text-emerald-400">
                Спойл: {sources ? spoil.length : material.spoil_count} мобов
              </span>
              <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs text-amber-400">
                Дроп: {sources ? drop.length : material.drop_count} мобов
              </span>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 rounded-lg border border-zinc-700 px-2.5 py-1 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
        >
          ✕
        </button>
      </div>

      <div className="max-h-[75vh] overflow-y-auto p-5">
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-3">
          <div className="mb-1.5 flex items-center justify-between gap-2 text-[0.7rem] text-zinc-500">
            <span>Уровень монстров</span>
            <Link to="/settings" className="text-amber-400/80 hover:text-amber-300">
              Настройки
            </Link>
          </div>
          <LevelRangeControl
            value={{ min: minLevel, max: maxLevel }}
            onChange={
              onLevelRangeChange ??
              ((next) => {
                onMinLevelChange(next.min);
                onMaxLevelChange(next.max);
              })
            }
            sliderMin={sliderBounds?.min ?? levelBounds.min}
            sliderMax={sliderBounds?.max ?? levelBounds.max}
            compact
          />
        </div>

        {sourcesLoading && !sources ? (
          <p className="mt-4 text-sm text-zinc-500">Загрузка источников…</p>
        ) : (
          <>
            <ResourceSourceTable sources={spoil} kind="spoil" onNpcClick={onNpcSelect} />
            <ResourceSourceTable sources={drop} kind="drop" onNpcClick={onNpcSelect} />
          </>
        )}
      </div>
    </div>
  );
}
