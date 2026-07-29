import { useMemo, useState } from "react";
import {
  Bar,
  Brush,
  CartesianGrid,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

interface DealPoint {
  recorded_at: string;
  price: number;
  quantity: number;
  side: string | null;
  seller_name: string;
  total_cost: number;
}

interface VolumeBucket {
  bucket_start: string;
  buy_volume: number;
  sell_volume: number;
}

interface Props {
  deals: DealPoint[];
  volumeBuckets: VolumeBucket[];
  height?: number;
}

function formatPrice(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function DealTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: DealPoint & { ts: number; label: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/95 px-4 py-3 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-1 font-semibold text-zinc-100">
        {new Date(row.recorded_at).toLocaleString("ru-RU")}
      </p>
      <p className={row.side === "buy" ? "text-emerald-400" : "text-red-400"}>
        {row.side === "buy" ? "Покупка" : "Продажа"} · {formatPrice(row.price)}
      </p>
      <p className="mt-1 text-zinc-400">Кол-во: {row.quantity}</p>
      <p className="text-zinc-400">Сумма: {formatPrice(row.total_cost)}</p>
      <p className="mt-1 text-zinc-500">{row.seller_name}</p>
    </div>
  );
}

export default function TradeChart({ deals, volumeBuckets, height = 420 }: Props) {
  const [hiddenSeries, setHiddenSeries] = useState({ buy: false, sell: false, volume: false });

  const scatterData = useMemo(() => {
    return deals.map((d) => ({
      ...d,
      price: Number(d.price),
      total_cost: Number(d.total_cost),
      ts: new Date(d.recorded_at).getTime(),
      label: new Date(d.recorded_at).toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }),
    }));
  }, [deals]);

  const buyData = useMemo(() => scatterData.filter((d) => d.side === "buy"), [scatterData]);
  const sellData = useMemo(() => scatterData.filter((d) => d.side === "sell"), [scatterData]);

  const volumeData = useMemo(
    () =>
      volumeBuckets.map((b) => ({
        ...b,
        ts: new Date(b.bucket_start).getTime(),
        label: new Date(b.bucket_start).toLocaleString("ru-RU", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }),
      })),
    [volumeBuckets],
  );

  const toggleSeries = (key: keyof typeof hiddenSeries) => {
    setHiddenSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!deals.length) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/40"
      >
        <p className="text-sm text-zinc-500">Нет сделок за выбранный период</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/80 to-zinc-950/90 p-4 shadow-panel">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100">История сделок</h3>
          <p className="text-xs text-zinc-500">
            Recharts · точки = цена, размер = объём, столбцы = агрегированный volume
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs">
          {(["buy", "sell", "volume"] as const).map((key) => {
            const labels = { buy: "Покупки", sell: "Продажи", volume: "Объём" };
            const colors = { buy: "text-emerald-400", sell: "text-red-400", volume: "text-violet-400" };
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleSeries(key)}
                className={`inline-flex items-center gap-1.5 transition-opacity ${colors[key]} ${
                  hiddenSeries[key] ? "opacity-40 line-through" : ""
                }`}
              >
                {labels[key]}
              </button>
            );
          })}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={volumeData.length ? volumeData : scatterData} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#3f3f46" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            minTickGap={40}
            tickFormatter={(ts) =>
              new Date(ts).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
            }
          />
          <YAxis
            yAxisId="price"
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            tickFormatter={formatPrice}
            width={64}
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <ZAxis type="number" dataKey="quantity" range={[30, 400]} />
          <Tooltip content={<DealTooltip />} />
          <Legend wrapperStyle={{ display: "none" }} />

          {!hiddenSeries.volume && volumeData.length > 0 && (
            <>
              <Bar yAxisId="volume" dataKey="buy_volume" fill="#34d399" fillOpacity={0.35} name="Buy vol" />
              <Bar yAxisId="volume" dataKey="sell_volume" fill="#f87171" fillOpacity={0.35} name="Sell vol" />
            </>
          )}

          {!hiddenSeries.buy && (
            <Scatter
              yAxisId="price"
              data={buyData}
              dataKey="price"
              fill="#34d399"
              name="Buy"
              isAnimationActive={false}
            />
          )}
          {!hiddenSeries.sell && (
            <Scatter
              yAxisId="price"
              data={sellData}
              dataKey="price"
              fill="#f87171"
              name="Sell"
              isAnimationActive={false}
            />
          )}

          <Brush
            dataKey="ts"
            height={24}
            stroke="#f59e0b"
            fill="#27272a"
            tickFormatter={(ts) =>
              new Date(ts).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
            }
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
