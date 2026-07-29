import { useState } from "react";
import { formatStat, itemInfo, TAB_LABELS, type CraftCatalog } from "../../lib/craftCalc";
import CraftCategoryTree from "./CraftCategoryTree";
import { GradePill, ItemIcon } from "./CraftCostBar";

const GRADES = ["", "NG", "D", "C", "B", "A", "S"];
const TABS = ["weapons", "armors", "materials", "other", "sets"] as const;

interface Props {
  catalog: CraftCatalog;
  onSelect: (id: number) => void;
  selectedId?: number | null;
  compact?: boolean;
}

export default function CraftPicker({ catalog, onSelect, selectedId, compact }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("weapons");
  const [gradeFilter, setGradeFilter] = useState("");
  const [search, setSearch] = useState("");

  const chipClass = (active: boolean) =>
    `rounded-lg border px-2.5 py-1 text-xs font-semibold transition-colors ${
      active
        ? "border-amber-500 bg-amber-600 text-zinc-950"
        : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-amber-500/50"
    }`;

  const tabClass = (active: boolean) =>
    `flex-1 rounded-lg px-2 py-2 text-xs font-semibold transition-colors sm:text-sm ${
      active ? "bg-amber-600 text-zinc-950 shadow-sm" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
    }`;

  return (
    <div className={`panel ${compact ? "p-3" : "p-4"}`}>
      {!compact && (
        <div className="mb-4">
          <h2 className="text-xl font-bold text-zinc-50">Крафт Крафтера</h2>
          <p className="text-sm text-zinc-500">
            {catalog.product_count} предметов · {catalog.variant_count} рецептов
          </p>
        </div>
      )}

      <input
        type="search"
        placeholder="Поиск предмета..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="input mb-3"
      />

      <div className="mb-3 flex flex-wrap gap-1.5">
        {GRADES.map((g) => (
          <button key={g || "all"} type="button" className={chipClass(gradeFilter === g)} onClick={() => setGradeFilter(g)}>
            {g || "Все"}
          </button>
        ))}
      </div>

      <div className="mb-4 flex gap-1 rounded-xl bg-zinc-800/80 p-1">
        {TABS.map((t) => (
          <button key={t} type="button" className={tabClass(tab === t)} onClick={() => setTab(t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      <div className="list-scroll pr-1">
        {search ? (
          <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
            <table className="min-w-full text-sm">
              <thead className="border-b border-zinc-800/80 bg-zinc-900/60">
                <tr>
                  <th className="px-2 py-1.5 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                    Предмет
                  </th>
                  <th className="px-2 py-1.5 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                    Грейд
                  </th>
                  <th className="px-2 py-1.5 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                    Характеристики
                  </th>
                </tr>
              </thead>
              <tbody>
                {(catalog.craftableIds ?? Object.keys(catalog.byProduct).map(Number))
                  .filter((id) => {
                    const info = itemInfo(catalog, id);
                    return (
                      info.name.toLowerCase().includes(search.toLowerCase()) &&
                      (!gradeFilter || info.grade === gradeFilter)
                    );
                  })
                  .slice(0, 80)
                  .map((id) => {
                    const info = itemInfo(catalog, id);
                    const active = selectedId === id;
                    const stats = info.stats;
                    const statBits: string[] = [];
                    if (stats?.p_atk != null) statBits.push(`П. ${formatStat(stats.p_atk)}`);
                    if (stats?.m_atk != null) statBits.push(`М. ${formatStat(stats.m_atk)}`);
                    if (stats?.crystals != null) statBits.push(`Крист. ${formatStat(stats.crystals)}`);
                    if (stats?.p_def != null) statBits.push(`Физ. ${formatStat(stats.p_def)}`);
                    if (stats?.m_def != null) statBits.push(`Маг. ${formatStat(stats.m_def)}`);
                    if (stats?.shield_def != null) statBits.push(`Щит ${formatStat(stats.shield_def)}`);
                    return (
                      <tr
                        key={id}
                        onClick={() => onSelect(id)}
                        className={`cursor-pointer border-b border-zinc-800/50 transition-colors last:border-b-0 ${
                          active
                            ? "bg-amber-500/10 ring-1 ring-inset ring-amber-500/30"
                            : "hover:bg-zinc-800/50"
                        }`}
                      >
                        <td className="px-2 py-2">
                          <div className="flex min-w-0 items-center gap-2">
                            <ItemIcon id={id} size={24} />
                            <span className="truncate font-medium text-zinc-100">{info.name}</span>
                          </div>
                        </td>
                        <td className="px-2 py-2">
                          <GradePill grade={info.grade} />
                        </td>
                        <td className="px-2 py-2 text-xs tabular-nums text-zinc-400">
                          {statBits.length > 0 ? statBits.join(" · ") : "—"}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        ) : (
          <CraftCategoryTree
            catalog={catalog}
            tab={tab}
            gradeFilter={gradeFilter}
            search={search}
            onSelect={onSelect}
            selectedId={selectedId}
          />
        )}
      </div>
    </div>
  );
}
