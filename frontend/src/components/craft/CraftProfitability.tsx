import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getCraftProfitability, type ProfitabilityRow } from "../../api/craft";
import PeriodSelector from "../trading/PeriodSelector";
import { PeriodState } from "../trading/periodUtils";
import { GradePill, ItemIcon } from "./CraftCostBar";

const GRADES = ["NG", "D", "C", "B", "A", "S"] as const;
const CATEGORIES = [
  { key: "weapons", label: "Оружие" },
  { key: "armors", label: "Броня" },
  { key: "jewelry", label: "Украшения" },
  { key: "materials", label: "Материалы" },
  { key: "other", label: "Прочее" },
] as const;

const PAGE_SIZE = 50;

const defaultPeriod = (): PeriodState => ({ period: "1d", from: "", to: "" });

function money(value: number | null | undefined): string {
  if (value == null) return "—";
  return Math.round(value).toLocaleString("ru-RU");
}

function marginClass(value: number | null | undefined): string {
  if (value == null) return "text-zinc-500";
  return value >= 0 ? "text-emerald-400" : "text-rose-400";
}

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border px-2.5 py-1 text-xs font-semibold transition-colors ${
        active
          ? "border-amber-500 bg-amber-600 text-zinc-950"
          : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-amber-500/50"
      }`}
    >
      {label}
    </button>
  );
}

function kindLabel(kind: ProfitabilityRow["kind"]): string {
  return kind === "material" ? "Ресурс" : "Предмет";
}

type SortKey =
  | "product_name"
  | "grade"
  | "kind"
  | "npc_sell"
  | "npc_buy"
  | "revenue_avg"
  | "revenue_last"
  | "revenue_npc"
  | "revenue_npc_buy"
  | "material_cost_avg"
  | "material_cost_last"
  | "material_cost_npc"
  | "material_cost_npc_buy"
  | "margin_avg"
  | "margin_last"
  | "margin_npc"
  | "margin_npc_buy";

const TEXT_SORT_KEYS = new Set<SortKey>(["product_name", "grade", "kind"]);

function gradeIndex(grade: string): number {
  const index = GRADES.indexOf(grade as (typeof GRADES)[number]);
  return index === -1 ? GRADES.length : index;
}

function compareNumeric(
  a: number | null | undefined,
  b: number | null | undefined,
  order: "asc" | "desc",
): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  return order === "asc" ? a - b : b - a;
}

function compareRows(a: ProfitabilityRow, b: ProfitabilityRow, key: SortKey, order: "asc" | "desc") {
  switch (key) {
    case "product_name":
      return order === "asc"
        ? a.product_name.localeCompare(b.product_name, "ru")
        : b.product_name.localeCompare(a.product_name, "ru");
    case "grade":
      return order === "asc"
        ? gradeIndex(a.grade) - gradeIndex(b.grade)
        : gradeIndex(b.grade) - gradeIndex(a.grade);
    case "kind": {
      const left = kindLabel(a.kind);
      const right = kindLabel(b.kind);
      return order === "asc" ? left.localeCompare(right, "ru") : right.localeCompare(left, "ru");
    }
    default:
      return compareNumeric(a[key], b[key], order);
  }
}

function SortableTh({
  label,
  sortKey,
  sortBy,
  sortOrder,
  onSort,
  align = "left",
}: {
  label: string;
  sortKey: SortKey;
  sortBy: SortKey | null;
  sortOrder: "asc" | "desc";
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sortBy === sortKey;
  return (
    <th className={`px-3 py-2 ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex max-w-full items-center gap-0.5 transition-colors hover:text-zinc-300 ${
          align === "right" ? "ml-auto" : ""
        } ${active ? "text-zinc-300" : ""}`}
      >
        <span>{label}</span>
        {active && <span aria-hidden>{sortOrder === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

/** Margins come from server-side market data for the selected period. */
export default function CraftProfitability() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<PeriodState>(defaultPeriod);
  const [grades, setGrades] = useState<Set<string>>(new Set());
  const [categories, setCategories] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<SortKey | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  const gradeList = useMemo(() => (grades.size ? [...grades] : undefined), [grades]);
  const categoryList = useMemo(
    () => (categories.size ? [...categories] : undefined),
    [categories],
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ["craft", "profitability", period, gradeList, categoryList],
    queryFn: () =>
      getCraftProfitability({
        period,
        grades: gradeList,
        categories: categoryList,
      }),
    staleTime: 1000 * 60 * 2,
  });

  useEffect(() => {
    setPage(1);
  }, [period, gradeList, categoryList]);

  const toggleGrade = (grade: string) => {
    setGrades((prev) => {
      const next = new Set(prev);
      if (next.has(grade)) next.delete(grade);
      else next.add(grade);
      return next;
    });
  };

  const toggleCategory = (key: string) => {
    setCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const recipes = data?.recipes ?? [];

  const sortedRecipes = useMemo(() => {
    if (!sortBy) return recipes;
    return [...recipes].sort((a, b) => compareRows(a, b, sortBy, sortOrder));
  }, [recipes, sortBy, sortOrder]);

  const total = sortedRecipes.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pagedRecipes = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return sortedRecipes.slice(start, start + PAGE_SIZE);
  }, [sortedRecipes, page]);

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((order) => (order === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder(TEXT_SORT_KEYS.has(key) ? "asc" : "desc");
    }
    setPage(1);
  };

  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="space-y-4 border-b border-zinc-800/80 px-5 py-4">
        <div>
          <h3 className="text-lg font-semibold text-zinc-50">Прибыльность крафта</h3>
          <p className="mt-1 text-sm text-zinc-500">
            Предметы и крафтовые ресурсы. Цены за выбранный период по данным рынка; NPC sell — из
            каталога.
          </p>
        </div>

        <div>
          <p className="mb-2 text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500">
            Период
          </p>
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>

        <div>
          <p className="mb-2 text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500">
            Грейд
          </p>
          <div className="flex flex-wrap gap-1.5">
            {GRADES.map((g) => (
              <FilterChip
                key={g}
                label={g}
                active={grades.has(g)}
                onClick={() => toggleGrade(g)}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500">
            Категория
          </p>
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((c) => (
              <FilterChip
                key={c.key}
                label={c.label}
                active={categories.has(c.key)}
                onClick={() => toggleCategory(c.key)}
              />
            ))}
          </div>
        </div>
      </div>

      {isLoading ? (
        <p className="px-5 py-6 text-sm text-zinc-500">Расчёт…</p>
      ) : isError ? (
        <p className="px-5 py-6 text-sm text-red-400">Не удалось загрузить данные.</p>
      ) : recipes.length === 0 ? (
        <p className="px-5 py-6 text-sm text-zinc-500">Нет рецептов для выбранных фильтров.</p>
      ) : (
        <>
          <div className="list-scroll overflow-auto">
            <table className="w-full min-w-[1280px] text-sm">
            <thead className="sticky top-0 z-10 bg-zinc-950/95 text-left text-xs uppercase tracking-wider text-zinc-500 backdrop-blur-sm">
              <tr className="border-b border-zinc-800/80">
                <SortableTh
                  label="Предмет"
                  sortKey="product_name"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                />
                <SortableTh
                  label="Грейд"
                  sortKey="grade"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                />
                <SortableTh
                  label="Тип"
                  sortKey="kind"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                />
                <SortableTh
                  label="Средняя"
                  sortKey="revenue_avg"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Посл. сделка"
                  sortKey="revenue_last"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="NPC sell"
                  sortKey="revenue_npc"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="NPC buy"
                  sortKey="revenue_npc_buy"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Мат. ср."
                  sortKey="material_cost_avg"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Мат. посл."
                  sortKey="material_cost_last"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Мат. NPC"
                  sortKey="material_cost_npc"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Мат. NPC buy"
                  sortKey="material_cost_npc_buy"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Маржа ср."
                  sortKey="margin_avg"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Маржа посл."
                  sortKey="margin_last"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Маржа NPC sell"
                  sortKey="margin_npc"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
                <SortableTh
                  label="Маржа NPC buy"
                  sortKey="margin_npc_buy"
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={toggleSort}
                  align="right"
                />
              </tr>
            </thead>
            <tbody>
              {pagedRecipes.map((row) => (
                <tr
                  key={`${row.product_id}-${row.variant_index}`}
                  className="border-t border-zinc-800/50 even:bg-zinc-900/30"
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <ItemIcon id={row.product_id} size={28} />
                      <button
                        type="button"
                        onClick={() => navigate(`/craft?id=${row.product_id}`)}
                        className="max-w-[12rem] truncate text-left font-medium text-sky-400 hover:underline"
                        title={row.product_name}
                      >
                        {row.product_name}
                      </button>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <GradePill grade={row.grade} />
                  </td>
                  <td className="px-3 py-2 text-xs text-zinc-400">{kindLabel(row.kind)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                    {money(row.revenue_avg)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                    {money(row.revenue_last)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                    {money(row.revenue_npc)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                    {money(row.revenue_npc_buy)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {money(row.material_cost_avg)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {money(row.material_cost_last)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {money(row.material_cost_npc)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {money(row.material_cost_npc_buy)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-semibold tabular-nums ${marginClass(row.margin_avg)}`}
                  >
                    {money(row.margin_avg)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-semibold tabular-nums ${marginClass(row.margin_last)}`}
                  >
                    {money(row.margin_last)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-semibold tabular-nums ${marginClass(row.margin_npc)}`}
                  >
                    {money(row.margin_npc)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-semibold tabular-nums ${marginClass(row.margin_npc_buy)}`}
                  >
                    {money(row.margin_npc_buy)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-zinc-800/80 px-5 py-3 text-xs text-zinc-500">
          <span>{total.toLocaleString("ru-RU")} предметов</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="btn-ghost px-2 py-1 disabled:opacity-40"
            >
              ←
            </button>
            <span>
              {page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="btn-ghost px-2 py-1 disabled:opacity-40"
            >
              →
            </button>
          </div>
        </div>
        </>
      )}
    </div>
  );
}
