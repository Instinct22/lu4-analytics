import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBuyPlan, type BuyPlanResponse } from "../../api/market";
import { formatCompactNumber, formatFullNumber } from "../../lib/formatNumber";

interface Props {
  entityId: string | null;
  itemName: string | null;
}

/** Compact controls for the item-select row (right side). */
export function GatherBuyControls({
  entityId,
  draftQty,
  onDraftQtyChange,
  onGather,
  loading,
}: {
  entityId: string | null;
  draftQty: string;
  onDraftQtyChange: (value: string) => void;
  onGather: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label className="mb-1 block text-[0.65rem] font-semibold uppercase tracking-wider text-zinc-500">
          Собрать
        </label>
        <input
          type="text"
          inputMode="numeric"
          value={draftQty}
          onChange={(e) => onDraftQtyChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onGather();
          }}
          disabled={!entityId}
          placeholder="Кол-во"
          className="input w-28 tabular-nums sm:w-36"
          aria-label="Количество для сбора"
        />
      </div>
      <button
        type="button"
        className="btn-primary"
        disabled={!entityId || loading}
        onClick={onGather}
      >
        {loading ? "…" : "Собрать"}
      </button>
    </div>
  );
}

export function useGatherBuyPlan(entityId: string | null) {
  const [draftQty, setDraftQty] = useState("1000");
  const [requestedQty, setRequestedQty] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["buy-plan", entityId, requestedQty],
    queryFn: () => getBuyPlan(entityId!, requestedQty!),
    enabled: !!entityId && requestedQty != null && requestedQty > 0,
  });

  const gather = () => {
    if (!entityId) return;
    const qty = Math.floor(Number(draftQty.replace(/\s/g, "").replace(",", ".")));
    if (!Number.isFinite(qty) || qty < 1) return;
    setRequestedQty(qty);
    if (requestedQty === qty) void query.refetch();
  };

  return {
    draftQty,
    setDraftQty,
    gather,
    requestedQty,
    data: query.data,
    isFetching: query.isFetching,
    isError: query.isError,
  };
}

export function GatherBuyResult({
  data,
  loading,
  error,
  itemName,
  visible,
}: {
  data: BuyPlanResponse | undefined;
  loading: boolean;
  error: boolean;
  itemName: string | null;
  visible: boolean;
}) {
  if (!visible) return null;
  if (loading && !data) {
    return <p className="mt-3 text-sm text-zinc-500">Считаем оптимальных продавцов…</p>;
  }
  if (error) {
    return <p className="mt-3 text-sm text-red-400">Не удалось построить план закупки</p>;
  }
  if (!data) return null;

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950/40">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-800/80 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-zinc-200">
            План закупки{itemName ? `: ${itemName}` : ""}
          </h3>
          <p className="mt-0.5 text-xs text-zinc-500">
            Актуальные sell-лоты · от самой низкой цены ·{" "}
            {data.filled_quantity.toLocaleString("ru-RU")} /{" "}
            {data.requested_quantity.toLocaleString("ru-RU")} шт.
            {data.shortfall > 0
              ? ` · не хватает ${data.shortfall.toLocaleString("ru-RU")}`
              : ""}
          </p>
        </div>
        <div className="text-right text-xs text-zinc-400">
          <div>
            Итого:{" "}
            <span
              className="font-semibold tabular-nums text-amber-400"
              title={formatFullNumber(Number(data.total_cost))}
            >
              {formatCompactNumber(Number(data.total_cost))}
            </span>
          </div>
          {data.avg_fill_price != null && (
            <div className="mt-0.5">
              Ср. цена:{" "}
              <span className="tabular-nums text-zinc-200">
                {formatFullNumber(Number(data.avg_fill_price))}
              </span>
            </div>
          )}
        </div>
      </div>

      {!data.lots.length ? (
        <p className="px-4 py-6 text-sm text-zinc-500">Нет актуальных sell-лотов по предмету</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="bg-zinc-950/60 text-[0.65rem] uppercase tracking-wider text-zinc-500">
              <tr>
                <th className="px-4 py-2 font-medium">Продавец</th>
                <th className="px-4 py-2 font-medium">Цена</th>
                <th className="px-4 py-2 font-medium">В лоте</th>
                <th className="px-4 py-2 font-medium">Купить</th>
                <th className="px-4 py-2 font-medium">Сумма</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/70">
              {data.lots.map((lot) => (
                <tr key={`${lot.seller_id}-${lot.recorded_at}`} className="hover:bg-zinc-900/50">
                  <td className="px-4 py-2 font-medium text-zinc-100">{lot.seller_name}</td>
                  <td className="px-4 py-2 tabular-nums text-zinc-200">
                    {formatFullNumber(Number(lot.price))}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-zinc-400">
                    {lot.available_quantity.toLocaleString("ru-RU")}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-amber-300">
                    {lot.buy_quantity.toLocaleString("ru-RU")}
                  </td>
                  <td
                    className="px-4 py-2 tabular-nums text-zinc-200"
                    title={formatFullNumber(Number(lot.cost))}
                  >
                    {formatCompactNumber(Number(lot.cost))}
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
