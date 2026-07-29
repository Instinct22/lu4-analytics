import type { ReactNode } from "react";
import {
  CAT_LABELS,
  DUAL_GEAR_CATEGORIES,
  GRADE_ORDER,
  isDualGearCategory,
  SORT_LABELS,
  type GearCategory,
  type ItemsFilterState,
  type ItemsSort,
  type ItemsTab,
} from "../../lib/itemsCatalog";
import { OTHER_SUB_LABELS } from "../../lib/itemEncyclopedia";

const chipClass = (active: boolean) =>
  `rounded-lg border px-2.5 py-1 text-xs font-semibold transition-colors ${
    active
      ? "border-amber-500 bg-amber-600 text-zinc-950"
      : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-amber-500/50"
  }`;

const tabClass = (active: boolean) =>
  `flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
    active ? "bg-amber-600 text-zinc-950 shadow-sm" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
  }`;

interface Props {
  tab: ItemsTab;
  filter: ItemsFilterState;
  available: {
    cats: Set<GearCategory>;
    grades: Set<string>;
    subs: Set<string>;
    slots: Set<string>;
    anyNg: boolean;
  };
  setGrades?: string[];
  otherSubcategories?: string[];
  onTabChange: (tab: ItemsTab) => void;
  onFilterChange: (patch: Partial<ItemsFilterState>) => void;
  countLabel: string;
  children: ReactNode;
}

export default function ItemsToolbar({
  tab,
  filter,
  available,
  setGrades = [],
  otherSubcategories = [],
  onTabChange,
  onFilterChange,
  countLabel,
  children,
}: Props) {
  const gradeVals =
    tab === "items"
      ? GRADE_ORDER.filter((g) => g !== "NG" && (available.grades.has(g) || filter.grade === g))
      : tab === "sets"
        ? GRADE_ORDER.filter((g) => g !== "NG" && (setGrades.includes(g) || filter.grade === g))
        : GRADE_ORDER.filter((g) => filter.grade === g || g !== "NG");

  const subVals = [...available.subs].sort();
  if (filter.sub && !available.subs.has(filter.sub)) subVals.push(filter.sub);
  const slotVals = [...available.slots].sort();
  if (filter.slot && !available.slots.has(filter.slot)) slotVals.push(filter.slot);

  const catOptions = (
    ["weapon", "armor", "accessory", ...DUAL_GEAR_CATEGORIES] as GearCategory[]
  ).filter((c) => available.cats.has(c) || filter.cat === c);

  return (
    <div className="panel p-4">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-zinc-50">
            {tab === "other" ? "Прочие предметы" : tab === "sets" ? "Сеты брони" : "Оружие и броня"}
          </h2>
          <p className="text-sm text-zinc-500">{countLabel}</p>
        </div>
        <div className="flex w-full max-w-md gap-1 rounded-xl bg-zinc-800/80 p-1 sm:w-auto">
          <button type="button" className={tabClass(tab === "items")} onClick={() => onTabChange("items")}>
            Экипировка
          </button>
          <button type="button" className={tabClass(tab === "sets")} onClick={() => onTabChange("sets")}>
            Сеты
          </button>
          <button type="button" className={tabClass(tab === "other")} onClick={() => onTabChange("other")}>
            Прочее
          </button>
        </div>
      </div>

      <div className="mb-3 space-y-2.5">
        {tab === "items" && (
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              className={chipClass(filter.cat === "all")}
              onClick={() => onFilterChange({ cat: "all", sub: null, slot: null })}
            >
              {CAT_LABELS.all}
            </button>
            {catOptions.map((c) => (
              <button
                key={c}
                type="button"
                className={chipClass(filter.cat === c)}
                onClick={() => onFilterChange({ cat: c, sub: null, slot: null })}
              >
                {CAT_LABELS[c]}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 text-[0.7rem] font-medium uppercase tracking-wider text-zinc-600">Грейд</span>
          <button
            type="button"
            className={chipClass(!filter.grade)}
            onClick={() => onFilterChange({ grade: null })}
          >
            Все
          </button>
          {gradeVals.map((g) => (
            <button
              key={g}
              type="button"
              className={chipClass(filter.grade === g)}
              onClick={() => onFilterChange({ grade: g })}
            >
              {g}
            </button>
          ))}
          {tab === "items" && (available.anyNg || filter.showNg) && (
            <button
              type="button"
              className={chipClass(filter.showNg)}
              onClick={() => onFilterChange({ showNg: !filter.showNg })}
            >
              Без грейда
            </button>
          )}
          {tab === "sets" && (
            <button
              type="button"
              className={chipClass(filter.hidePvpSets)}
              onClick={() => onFilterChange({ hidePvpSets: !filter.hidePvpSets })}
            >
              Скрыть PvP
            </button>
          )}
        </div>

        {tab === "other" && otherSubcategories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[0.7rem] font-medium uppercase tracking-wider text-zinc-600">Категория</span>
            <button
              type="button"
              className={chipClass(!filter.sub)}
              onClick={() => onFilterChange({ sub: null })}
            >
              Все
            </button>
            {otherSubcategories.map((s) => (
              <button
                key={s}
                type="button"
                className={chipClass(filter.sub === s)}
                onClick={() => onFilterChange({ sub: s })}
              >
                {OTHER_SUB_LABELS[s] || s}
              </button>
            ))}
          </div>
        )}

        {tab === "items" && !isDualGearCategory(filter.cat) && subVals.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[0.7rem] font-medium uppercase tracking-wider text-zinc-600">Тип</span>
            <button
              type="button"
              className={chipClass(!filter.sub)}
              onClick={() => onFilterChange({ sub: null })}
            >
              Все
            </button>
            {subVals.map((s) => (
              <button
                key={s}
                type="button"
                className={chipClass(filter.sub === s)}
                onClick={() => onFilterChange({ sub: s })}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {tab === "items" && !isDualGearCategory(filter.cat) && slotVals.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[0.7rem] font-medium uppercase tracking-wider text-zinc-600">Слот</span>
            <button
              type="button"
              className={chipClass(!filter.slot)}
              onClick={() => onFilterChange({ slot: null })}
            >
              Все
            </button>
            {slotVals.map((s) => (
              <button
                key={s}
                type="button"
                className={chipClass(filter.slot === s)}
                onClick={() => onFilterChange({ slot: s })}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="search"
            className="input"
            placeholder={
              tab === "sets" ? "Поиск сета…" : tab === "other" ? "Поиск предмета…" : "Поиск по названию…"
            }
            value={filter.q}
            onChange={(e) => onFilterChange({ q: e.target.value })}
          />
          {tab === "items" && (
            <label className="flex shrink-0 items-center gap-2 text-xs text-zinc-500">
              Сортировка
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-sm text-zinc-200"
                value={filter.sort}
                onChange={(e) => onFilterChange({ sort: e.target.value as ItemsSort })}
              >
                {(Object.keys(SORT_LABELS) as ItemsSort[]).map((k) => (
                  <option key={k} value={k}>
                    {SORT_LABELS[k]}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      {children}
    </div>
  );
}
