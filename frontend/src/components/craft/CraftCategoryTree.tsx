import { isArmorItem, isWeaponItem, itemInfo, SUB_LABELS, type CraftCatalog } from "../../lib/craftCalc";
import { CraftArmorStatCells, CraftWeaponStatCells } from "./CraftItemStats";
import { GradePill, ItemIcon } from "./CraftCostBar";

const ARMOR_SUB_ORDER = ["heavy", "light", "magic", "helmets", "gloves", "boots", "shields", "misc"];

function orderedSubKeys(group: Record<string, unknown>, tab: string): string[] {
  const keys = Object.keys(group ?? {});
  if (tab !== "armors") return keys;
  const order = ARMOR_SUB_ORDER.filter((k) => keys.includes(k));
  const rest = keys.filter((k) => !ARMOR_SUB_ORDER.includes(k)).sort();
  return [...order, ...rest];
}

interface Props {
  catalog: CraftCatalog;
  tab: string;
  gradeFilter: string;
  search: string;
  onSelect: (id: number) => void;
  selectedId?: number | null;
}

function matchesSearch(catalog: CraftCatalog, id: number, q: string) {
  if (!q) return true;
  return itemInfo(catalog, id).name.toLowerCase().includes(q.toLowerCase());
}

function matchesGrade(catalog: CraftCatalog, id: number, grade: string) {
  if (!grade) return true;
  return itemInfo(catalog, id).grade === grade;
}

type StatMode = "weapon" | "armor" | "none";

function StatHeader({ mode }: { mode: StatMode }) {
  const thClass = "px-2 py-1.5 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500";
  if (mode === "weapon") {
    return (
      <>
        <th className={thClass}>П. атака</th>
        <th className={thClass}>М. атака</th>
        <th className={thClass}>Кристализация</th>
      </>
    );
  }
  if (mode === "armor") {
    return (
      <>
        <th className={thClass}>Физ. защ.</th>
        <th className={thClass}>Маг. защ.</th>
        <th className={thClass}>Щит</th>
      </>
    );
  }
  return null;
}

function StatCells({
  catalog,
  id,
  mode,
}: {
  catalog: CraftCatalog;
  id: number;
  mode: StatMode;
}) {
  if (mode === "weapon") {
    const info = itemInfo(catalog, id);
    if (!isWeaponItem(info)) {
      return (
        <>
          <td className="text-xs text-zinc-600">—</td>
          <td className="text-xs text-zinc-600">—</td>
          <td className="text-xs text-zinc-600">—</td>
        </>
      );
    }
    return <CraftWeaponStatCells catalog={catalog} id={id} />;
  }
  if (mode === "armor") {
    const info = itemInfo(catalog, id);
    if (!isArmorItem(info)) {
      return (
        <>
          <td className="text-xs text-zinc-600">—</td>
          <td className="text-xs text-zinc-600">—</td>
          <td className="text-xs text-zinc-600">—</td>
        </>
      );
    }
    return <CraftArmorStatCells catalog={catalog} id={id} />;
  }
  return null;
}

function ItemList({
  ids,
  catalog,
  onSelect,
  selectedId,
  statMode = "none",
}: {
  ids: number[];
  catalog: CraftCatalog;
  onSelect: (id: number) => void;
  selectedId?: number | null;
  statMode?: StatMode;
}) {
  if (ids.length === 0) {
    return <p className="text-sm text-zinc-500">Нет предметов</p>;
  }

  if (statMode === "none") {
    return (
      <div className="grid gap-1.5 sm:grid-cols-1">
        {ids.map((id) => {
          const info = itemInfo(catalog, id);
          const active = selectedId === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onSelect(id)}
              className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-left transition-all ${
                active
                  ? "border-amber-500/80 bg-amber-500/10 ring-2 ring-amber-500/20"
                  : "border-zinc-800/80 bg-zinc-900/50 hover:border-amber-500/40 hover:bg-zinc-800/50"
              }`}
            >
              <ItemIcon id={id} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-100">{info.name}</span>
              <GradePill grade={info.grade} />
            </button>
          );
        })}
      </div>
    );
  }

  return (
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
            <StatHeader mode={statMode} />
          </tr>
        </thead>
        <tbody>
          {ids.map((id) => {
            const info = itemInfo(catalog, id);
            const active = selectedId === id;
            const stats = info.stats;
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
                {stats ? (
                  <StatCells catalog={catalog} id={id} mode={statMode} />
                ) : (
                  <>
                    <td className="text-xs text-zinc-600">—</td>
                    <td className="text-xs text-zinc-600">—</td>
                    <td className="text-xs text-zinc-600">—</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function CraftCategoryTree({
  catalog,
  tab,
  gradeFilter,
  search,
  onSelect,
  selectedId,
}: Props) {
  const q = search.trim().toLowerCase();
  const sectionTitle = "mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500";

  if (tab === "sets") {
    const setEntries = Object.entries(catalog.sets ?? {}).filter(([, ids]) =>
      ids.some((id) => matchesSearch(catalog, id, q) && matchesGrade(catalog, id, gradeFilter)),
    );
    return (
      <div className="space-y-4">
        {setEntries.map(([name, ids]) => {
          const filtered = ids.filter(
            (id) => matchesSearch(catalog, id, q) && matchesGrade(catalog, id, gradeFilter),
          );
          if (filtered.length === 0) return null;
          return (
            <div key={name} className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
              <h3 className="mb-2 font-semibold text-zinc-100">{name}</h3>
              <ItemList ids={filtered} catalog={catalog} onSelect={onSelect} selectedId={selectedId} />
            </div>
          );
        })}
      </div>
    );
  }

  const cats = catalog.categories;
  if (!cats) return null;

  if (tab === "weapons" || tab === "armors") {
    const group = tab === "weapons" ? cats.weapons : cats.armors;
    const statMode: StatMode = tab === "weapons" ? "weapon" : "armor";
    return (
      <div className="space-y-5">
        {orderedSubKeys(group ?? {}, tab).map((sub) => {
          const grades = (group ?? {})[sub];
          const allIds: number[] = [];
          if (typeof grades === "object" && !Array.isArray(grades)) {
            for (const ids of Object.values(grades as Record<string, number[]>)) {
              allIds.push(
                ...ids.filter(
                  (id) => matchesSearch(catalog, id, q) && matchesGrade(catalog, id, gradeFilter),
                ),
              );
            }
          }
          if (allIds.length === 0) return null;
          return (
            <div key={sub}>
              <h3 className={sectionTitle}>{SUB_LABELS[sub] ?? sub}</h3>
              <ItemList
                ids={allIds.sort((a, b) =>
                  itemInfo(catalog, a).name.localeCompare(itemInfo(catalog, b).name),
                )}
                catalog={catalog}
                onSelect={onSelect}
                selectedId={selectedId}
                statMode={statMode}
              />
            </div>
          );
        })}
      </div>
    );
  }

  if (tab === "materials") {
    const allIds: number[] = [];
    for (const ids of Object.values(cats.materials ?? {})) {
      allIds.push(
        ...ids.filter(
          (id) => matchesSearch(catalog, id, q) && matchesGrade(catalog, id, gradeFilter),
        ),
      );
    }
    return (
      <ItemList
        ids={allIds.sort((a, b) => itemInfo(catalog, a).name.localeCompare(itemInfo(catalog, b).name))}
        catalog={catalog}
        onSelect={onSelect}
        selectedId={selectedId}
      />
    );
  }

  return (
    <div className="space-y-5">
      {Object.entries(cats.other ?? {}).map(([sub, ids]) => {
        const filtered = ids.filter(
          (id) => matchesSearch(catalog, id, q) && matchesGrade(catalog, id, gradeFilter),
        );
        if (filtered.length === 0) return null;
        return (
          <div key={sub}>
            <h3 className={sectionTitle}>{SUB_LABELS[sub] ?? sub}</h3>
            <ItemList ids={filtered} catalog={catalog} onSelect={onSelect} selectedId={selectedId} />
          </div>
        );
      })}
    </div>
  );
}