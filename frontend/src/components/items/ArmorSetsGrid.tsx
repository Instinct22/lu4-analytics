import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import type { ArmorSetSummary } from "../../lib/itemsCatalog";

interface Props {
  sets: ArmorSetSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Список сжат в боковую колонку — деталь открыта справа. */
  compact?: boolean;
}

export default function ArmorSetsGrid({ sets, selectedId, onSelect, compact }: Props) {
  if (sets.length === 0) {
    return <p className="py-10 text-center text-sm text-zinc-500">Нет сетов по фильтру</p>;
  }

  const cols = compact
    ? "sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2"
    : "sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 min-[2200px]:grid-cols-5";

  return (
    <div className={`list-scroll grid grid-cols-1 gap-2 pr-1 ${cols}`}>
      {sets.map((s) => {
        const active = selectedId === s.id;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
              active
                ? "border-amber-500/40 bg-amber-500/10 ring-1 ring-amber-500/25"
                : "border-zinc-800/80 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-800/50"
            }`}
          >
            <div className="relative">
              <ItemIcon id={s.iconId} src={s.iconSrc} size={40} />
              <div className="absolute -bottom-1 -right-1">
                <GradePill grade={s.grade} />
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="truncate font-medium text-zinc-100">{s.name}</span>
                {s.pvp && (
                  <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide text-rose-400">
                    PvP
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[0.7rem] text-zinc-500">
                {s.memberIds.length}{" "}
                {s.memberIds.length === 1 ? "часть" : s.memberIds.length < 5 ? "части" : "частей"}
                {s.effect.length > 0 ? ` · ${s.effect.length} бонусов` : ""}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
