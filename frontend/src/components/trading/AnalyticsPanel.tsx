import { formatCompactNumber, formatFullNumber } from "../../lib/formatNumber";
import { StatCard } from "../ui";

interface Analytics {
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  median_price: number | null;
  deal_count: number;
  total_volume: number;
  vwap: number | null;
  price_change: number | null;
  price_change_pct: number | null;
  avg_quantity: number | null;
  std_dev: number | null;
  price_range: number | null;
  unique_sellers: number;
  buy_count: number;
  sell_count: number;
  buy_sell_spread: number | null;
  total_value: number | null;
}

interface Props {
  data: Analytics | undefined;
}

function fmt(value: number | null | undefined): { display: string; full: string } {
  return {
    display: formatCompactNumber(value),
    full: formatFullNumber(value),
  };
}

function pct(value: number | null | undefined): string {
  if (value == null) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export default function AnalyticsPanel({ data }: Props) {
  if (!data) return null;

  const changeColor =
    data.price_change_pct == null
      ? "text-zinc-50"
      : Number(data.price_change_pct) >= 0
        ? "text-emerald-400"
        : "text-red-400";

  const avg = fmt(data.avg_price);
  const vwap = fmt(data.vwap);
  const total = fmt(data.total_value);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-zinc-200">Аналитика периода</h3>
        <p className="mt-1 text-xs text-zinc-500">VWAP, медиана, спред buy/sell и другие метрики</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
        <StatCard title="Мин. цена" value={fmt(data.min_price).display} fullValue={fmt(data.min_price).full} />
        <StatCard title="Макс. цена" value={fmt(data.max_price).display} fullValue={fmt(data.max_price).full} />
        <StatCard
          title="Средняя"
          value={avg.display}
          fullValue={avg.full}
          highlight
          subtitle="ключевая метрика"
        />
        <StatCard title="Медиана" value={fmt(data.median_price).display} fullValue={fmt(data.median_price).full} />
        <StatCard
          title="VWAP"
          value={vwap.display}
          fullValue={vwap.full}
          highlight
          subtitle="средневзвешенная"
        />
        <StatCard title="Сделок" value={data.deal_count.toLocaleString("ru-RU")} />
        <StatCard
          title="Объём"
          value={formatCompactNumber(data.total_volume, 0)}
          fullValue={data.total_volume.toLocaleString("ru-RU")}
        />
        <StatCard title="Сумма" value={total.display} fullValue={total.full} />
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Изменение</p>
          <p className={`mt-2 text-2xl font-semibold tabular-nums sm:text-3xl ${changeColor}`}>
            {pct(data.price_change_pct)}
          </p>
          <p className="mt-1.5 text-xs text-zinc-600" title={fmt(data.price_change).full}>
            {fmt(data.price_change).display} абс.
          </p>
        </div>
        <StatCard title="Сред. кол-во" value={fmt(data.avg_quantity).display} fullValue={fmt(data.avg_quantity).full} />
        <StatCard title="σ (std dev)" value={fmt(data.std_dev).display} fullValue={fmt(data.std_dev).full} />
        <StatCard title="Диапазон" value={fmt(data.price_range).display} fullValue={fmt(data.price_range).full} />
        <StatCard title="Продавцов" value={data.unique_sellers} />
        <StatCard title="Buy / Sell" value={`${data.buy_count} / ${data.sell_count}`} />
        <StatCard
          title="Спред B/S"
          value={fmt(data.buy_sell_spread).display}
          fullValue={fmt(data.buy_sell_spread).full}
          subtitle="min sell − max buy"
        />
      </div>
    </div>
  );
}
