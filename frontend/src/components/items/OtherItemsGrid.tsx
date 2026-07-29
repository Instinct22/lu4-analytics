import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import { OTHER_SUB_LABELS } from "../../lib/itemEncyclopedia";
import type { ItemEncyclopediaEntry } from "../../api/items";

interface Props {
  items: ItemEncyclopediaEntry[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  compact?: boolean;
}

export default function OtherItemsGrid({ items, selectedId, onSelect, compact }: Props) {
  if (!items.length) {
    return <p className="py-8 text-center text-sm text-zinc-500">Нет предметов в этой категории</p>;
  }

  return (
    <div
      className={`grid gap-2 ${compact ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"}`}
    >
      {items.map((item) => {
        const active = selectedId === item.id;
        const sub = item.other_subcategory ? OTHER_SUB_LABELS[item.other_subcategory] || item.other_subcategory : "";
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
            className={`flex items-start gap-2 rounded-xl border p-2.5 text-left transition-colors ${
              active
                ? "border-amber-500/60 bg-amber-500/10 ring-1 ring-amber-500/30"
                : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-800/60"
            }`}
          >
            <ItemIcon id={item.id} size={36} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1">
                <span className="truncate text-sm font-semibold text-zinc-100">{item.name}</span>
                <GradePill grade={item.grade} />
              </div>
              {sub && <p className="truncate text-[0.65rem] text-zinc-500">{sub}</p>}
              <div className="mt-1 flex flex-wrap gap-1">
                {item.has_drop && (
                  <span className="rounded bg-zinc-800 px-1 py-0.5 text-[0.6rem] text-zinc-400">дроп</span>
                )}
                {item.has_spoil && (
                  <span className="rounded bg-zinc-800 px-1 py-0.5 text-[0.6rem] text-zinc-400">спойл</span>
                )}
                {item.craft?.craftable && (
                  <span className="rounded bg-emerald-500/15 px-1 py-0.5 text-[0.6rem] text-emerald-400">крафт</span>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
