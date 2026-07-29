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

function fmt(value: number | null | undefined): string {
  if (value == null) return "—";
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
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

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-zinc-200">Аналитика периода</h3>
        <p className="mt-1 text-xs text-zinc-500">VWAP, медиана, спред buy/sell и другие метрики</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8">
        <StatCard title="Мин. цена" value={fmt(data.min_price)} />
        <StatCard title="Макс. цена" value={fmt(data.max_price)} />
        <StatCard title="Средняя" value={fmt(data.avg_price)} />
        <StatCard title="Медиана" value={fmt(data.median_price)} />
        <StatCard title="VWAP" value={fmt(data.vwap)} subtitle="средневзвешенная" />
        <StatCard title="Сделок" value={data.deal_count} />
        <StatCard title="Объём" value={data.total_volume.toLocaleString("ru-RU")} />
        <StatCard title="Сумма" value={fmt(data.total_value)} />
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Изменение</p>
          <p className={`mt-2 text-3xl font-semibold tabular-nums ${changeColor}`}>
            {pct(data.price_change_pct)}
          </p>
          <p className="mt-1.5 text-xs text-zinc-600">{fmt(data.price_change)} абс.</p>
        </div>
        <StatCard title="Сред. кол-во" value={fmt(data.avg_quantity)} />
        <StatCard title="σ (std dev)" value={fmt(data.std_dev)} />
        <StatCard title="Диапазон" value={fmt(data.price_range)} />
        <StatCard title="Продавцов" value={data.unique_sellers} />
        <StatCard title="Buy / Sell" value={`${data.buy_count} / ${data.sell_count}`} />
        <StatCard title="Спред B/S" value={fmt(data.buy_sell_spread)} subtitle="min sell − max buy" />
      </div>
    </div>
  );
}
