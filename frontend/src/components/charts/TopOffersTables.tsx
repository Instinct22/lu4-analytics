import { useQuery } from "@tanstack/react-query";
import { getTopOffers, type TopOfferLot } from "../../api/market";
import { LoadingState } from "../ui";

interface Props {
  entityId: string;
  from: string;
  to: string;
}

function formatPrice(value: number | string): string {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

function OfferTable({
  title,
  rows,
  accent,
}: {
  title: string;
  rows: TopOfferLot[];
  accent: "red" | "emerald";
}) {
  const titleClass = accent === "red" ? "text-red-400" : "text-emerald-400";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950/40">
      <h4 className={`shrink-0 px-3 py-2 text-xs font-semibold uppercase tracking-wider ${titleClass}`}>
        {title}
      </h4>
      {!rows.length ? (
        <p className="px-3 pb-3 text-sm text-zinc-500">Нет лотов</p>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-zinc-950/95 text-[0.65rem] uppercase text-zinc-500">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">Ник</th>
                <th className="px-3 py-1.5 text-right font-medium">Кол-во</th>
                <th className="px-3 py-1.5 text-right font-medium">Цена</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.seller_id}-${row.recorded_at}-${row.price}`}
                  className="border-t border-zinc-800/50"
                >
                  <td className="truncate px-3 py-1.5 font-medium text-zinc-200" title={row.seller_name}>
                    {row.seller_name}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-zinc-400">
                    {row.quantity.toLocaleString("ru-RU")}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-zinc-100">
                    {formatPrice(row.price)}
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

export default function TopOffersTables({ entityId, from, to }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["top-offers", entityId, from, to],
    queryFn: () => getTopOffers(entityId, 5, { from, to }),
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-xl border border-zinc-800/80">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-xl border border-zinc-800/80 px-3">
        <p className="text-sm text-red-400">Не удалось загрузить лоты</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <OfferTable title="Продажа · топ-5 дешёвых" rows={data?.sells ?? []} accent="red" />
      <OfferTable title="Покупка · топ-5 дорогих" rows={data?.buys ?? []} accent="emerald" />
    </div>
  );
}
