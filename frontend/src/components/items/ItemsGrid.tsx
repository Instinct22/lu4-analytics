import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import { formatNpcPrice, type GearItem } from "../../lib/itemsCatalog";
import { formatStat } from "../../lib/craftCalc";

interface Props {
  items: GearItem[];
  selectedId: number | null;
  craftableIds: Set<number>;
  onSelect: (id: number) => void;
  /** Список сжат в боковую колонку — деталь открыта справа. */
  compact?: boolean;
}

export default function ItemsGrid({ items, selectedId, craftableIds, onSelect, compact }: Props) {
  if (items.length === 0) {
    return <p className="py-10 text-center text-sm text-zinc-500">Нет предметов по фильтру</p>;
  }

  const cols = compact
    ? "sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2"
    : "sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 min-[2200px]:grid-cols-5";

  return (
    <div className={`list-scroll grid grid-cols-1 gap-2 pr-1 ${cols}`}>
      {items.map((it) => {
        const active = selectedId === it.id;
        const craftable = craftableIds.has(it.id);
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => onSelect(it.id)}
            className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
              active
                ? "border-amber-500/40 bg-amber-500/10 ring-1 ring-amber-500/25"
                : "border-zinc-800/80 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-800/50"
            }`}
          >
            <div className="relative">
              <ItemIcon id={it.id} size={40} src={it.iconSrc} />
              <div className="absolute -bottom-1 -right-1">
                <GradePill grade={it.grade} />
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="truncate font-medium text-zinc-100">{it.name}</span>
                {craftable && (
                  <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide text-emerald-400">
                    Крафт
                  </span>
                )}
              </div>
              <p className="mt-0.5 truncate text-[0.7rem] text-zinc-500">
                {[it.facet.sub, it.facet.slot].filter(Boolean).join(" · ") || it.type}
              </p>
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[0.7rem] text-zinc-400">
                {it.mainStat.val != null && (
                  <span>
                    <span className="text-zinc-600">{it.mainStat.label}</span>{" "}
                    <span className="font-semibold tabular-nums text-zinc-200">
                      {formatStat(it.mainStat.val)}
                    </span>
                  </span>
                )}
                {it.npc_sell != null && (
                  <span className="tabular-nums text-amber-500/80">{formatNpcPrice(it.npc_sell)}</span>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
