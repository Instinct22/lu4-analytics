import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getCraftProfitability } from "../../api/craft";
import { ItemIcon } from "./CraftCostBar";

function money(value: number): string {
  return Math.round(value).toLocaleString("ru-RU");
}

/** Margins come from SQL over market statistics, not from the browser. */
export default function CraftProfitability() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["craft", "profitability", 25],
    queryFn: () => getCraftProfitability(25),
    staleTime: 1000 * 60 * 5,
  });

  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="border-b border-zinc-800/80 px-5 py-4">
        <h3 className="text-lg font-semibold text-zinc-50">Прибыльность крафта</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Выручка по рыночной цене минус прямые материалы. Считается на сервере по данным рынка.
        </p>
      </div>

      {isLoading ? (
        <p className="px-5 py-6 text-sm text-zinc-500">Расчёт…</p>
      ) : isError || !data?.length ? (
        <p className="px-5 py-6 text-sm text-zinc-500">
          Нет рецептов, у которых все материалы имеют рыночную цену.
        </p>
      ) : (
        <div className="list-scroll overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
                <th className="px-3 py-2">Предмет</th>
                <th className="px-3 py-2 text-right">Цена</th>
                <th className="px-3 py-2 text-right">Материалы</th>
                <th className="px-3 py-2 text-right">Маржа</th>
                <th className="px-3 py-2 text-right">%</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
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
                        className="text-left font-medium text-sky-400 hover:underline"
                      >
                        {row.product_name}
                      </button>
                      <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[0.65rem] text-zinc-400">
                        {row.grade}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-300">
                    {money(row.revenue)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {money(row.material_cost)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-semibold tabular-nums ${
                      row.margin >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {money(row.margin)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-400">
                    {row.margin_pct == null ? "—" : `${row.margin_pct.toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
