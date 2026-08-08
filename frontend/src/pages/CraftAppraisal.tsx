import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getCraftAppraisal,
  type AppraisalGrade,
  type AppraisalType,
} from "../api/craft";
import { ItemIcon, GradePill } from "../components/craft/CraftCostBar";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { formatPrice } from "../lib/craftCalc";

const GRADES: AppraisalGrade[] = ["NG", "D", "C", "B", "A", "S"];
const TYPES: { key: AppraisalType; label: string }[] = [
  { key: "weapon", label: "Оружие" },
  { key: "armor", label: "Броня" },
  { key: "jewelry", label: "Бижутерия" },
];

function dash(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatPrice(value);
}

function MarginCell({
  value,
  pct,
}: {
  value: number | null | undefined;
  pct: number | null | undefined;
}) {
  return (
    <td
      className={`px-3 py-2 text-right font-semibold tabular-nums ${
        value == null ? "text-zinc-500" : value >= 0 ? "text-emerald-400" : "text-rose-400"
      }`}
    >
      {dash(value)}
      {pct != null && (
        <span className="ml-1 text-[0.65rem] font-normal text-zinc-500">{pct.toFixed(1)}%</span>
      )}
    </td>
  );
}

export default function CraftAppraisalPage() {
  const [grade, setGrade] = useState<AppraisalGrade>("C");
  const [itemType, setItemType] = useState<AppraisalType>("weapon");

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ["craft", "appraisal", grade, itemType],
    queryFn: () => getCraftAppraisal({ grade, type: itemType, limit: 200 }),
    staleTime: 1000 * 60 * 5,
  });

  const rows = data?.items ?? [];
  const subtitle = useMemo(() => {
    const typeLabel = TYPES.find((t) => t.key === itemType)?.label ?? itemType;
    return `${grade} · ${typeLabel} · все варианты рецепта · сортировка по марже крафт→рынок`;
  }, [grade, itemType]);

  return (
    <div className="min-h-full">
      <PageHeader title="Оценка крафта" />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1">
          {GRADES.map((g) => (
            <button
              key={g}
              type="button"
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                grade === g
                  ? "bg-amber-600 text-zinc-950 shadow-sm"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
              }`}
              onClick={() => setGrade(g)}
            >
              {g}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1">
          {TYPES.map((t) => (
            <button
              key={t.key}
              type="button"
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                itemType === t.key
                  ? "bg-amber-600 text-zinc-950 shadow-sm"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
              }`}
              onClick={() => setItemType(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        {isFetching && !isLoading && (
          <span className="text-xs text-zinc-500">Обновление…</span>
        )}
      </div>

      <div className="panel overflow-hidden">
        <div className="border-b border-zinc-800/80 px-5 py-4">
          <h3 className="text-lg font-semibold text-zinc-50">Самые прибыльные</h3>
          <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message="Не удалось загрузить оценку крафта" />
        ) : rows.length === 0 ? (
          <p className="px-5 py-6 text-sm text-zinc-500">
            Нет крафтовых предметов для выбранного грейда и типа.
          </p>
        ) : (
          <div className="list-scroll overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead>
                <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
                  <th className="px-3 py-2">Предмет</th>
                  <th className="px-3 py-2 text-right">Крафт</th>
                  <th className="px-3 py-2 text-right">Рынок</th>
                  <th className="px-3 py-2 text-right">Магазин</th>
                  <th className="px-3 py-2 text-right">Кристаллы</th>
                  <th className="px-3 py-2 text-right">Маржа рынок</th>
                  <th className="px-3 py-2 text-right">Маржа магазин</th>
                  <th className="px-3 py-2 text-right">Маржа кристаллы</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={`${row.product_id}-${row.variant_index}`}
                    className="border-t border-zinc-800/50 even:bg-zinc-900/30"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <ItemIcon id={row.product_id} size={28} />
                        <Link
                          to={`/craft?id=${row.product_id}`}
                          className="font-medium text-sky-400 hover:underline"
                        >
                          {row.product_name}
                        </Link>
                        <GradePill grade={row.grade} />
                        {row.rate != null && (
                          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[0.65rem] text-zinc-400">
                            {row.rate}%
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                      {dash(row.craft_cost)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                      {dash(row.market_price)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                      {dash(row.shop_price)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                      {dash(row.crystal_price)}
                      {row.crystal_amount != null && row.crystal_price != null && (
                        <span className="ml-1 text-[0.65rem] text-zinc-600">
                          ×{row.crystal_amount}
                        </span>
                      )}
                    </td>
                    <MarginCell value={row.margin_market} pct={row.margin_market_pct} />
                    <MarginCell value={row.margin_shop} pct={row.margin_shop_pct} />
                    <MarginCell value={row.margin_crystal} pct={row.margin_crystal_pct} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
