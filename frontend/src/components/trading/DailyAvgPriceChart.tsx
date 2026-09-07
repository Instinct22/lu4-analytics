import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface DailyAvgPricePoint {
  day: string;
  buy_avg_price: number | null;
  sell_avg_price: number | null;
  buy_deal_count: number;
  sell_deal_count: number;
}

interface Props {
  points: DailyAvgPricePoint[];
  height?: number;
  excludedOutlierCount?: number;
}

function formatPrice(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function formatDayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
  });
}

function formatTooltipDay(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function outlierLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "сделка скрыта";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "сделки скрыты";
  return "сделок скрыто";
}

function TooltipContent({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{
    payload: {
      tooltipLabel: string;
      buy: number | null;
      sell: number | null;
      buy_deal_count: number;
      sell_deal_count: number;
    };
  }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/95 px-4 py-3 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-2 font-semibold text-zinc-100">{row.tooltipLabel}</p>
      {row.buy != null ? (
        <p className="text-emerald-400">
          Покупки · {formatPrice(row.buy)} · {row.buy_deal_count} сд.
        </p>
      ) : null}
      {row.sell != null ? (
        <p className={row.buy != null ? "mt-1 text-red-400" : "text-red-400"}>
          Продажи · {formatPrice(row.sell)} · {row.sell_deal_count} сд.
        </p>
      ) : null}
    </div>
  );
}

export default function DailyAvgPriceChart({
  points,
  height = 420,
  excludedOutlierCount = 0,
}: Props) {
  const [hiddenSeries, setHiddenSeries] = useState({ buy: false, sell: false });

  const data = useMemo(
    () =>
      points.map((point) => ({
        ...point,
        ts: new Date(point.day).getTime(),
        label: formatDayLabel(point.day),
        tooltipLabel: formatTooltipDay(point.day),
        buy: point.buy_avg_price != null ? Number(point.buy_avg_price) : null,
        sell: point.sell_avg_price != null ? Number(point.sell_avg_price) : null,
      })),
    [points],
  );

  const hasData = data.some((row) => row.buy != null || row.sell != null);

  const priceDomain = useMemo(() => {
    const prices = data.flatMap((row) => [row.buy, row.sell].filter((v): v is number => v != null));
    if (!prices.length) return undefined;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const padding = Math.max((max - min) * 0.05, max * 0.02, 1);
    return [min - padding, max + padding] as [number, number];
  }, [data]);

  const toggleSeries = (key: keyof typeof hiddenSeries) => {
    setHiddenSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!hasData) {
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
      {excludedOutlierCount > 0 ? (
        <div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {excludedOutlierCount} {outlierLabel(excludedOutlierCount)} как статистические выбросы
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100">Средняя цена по дням</h3>
          <p className="text-xs text-zinc-500">Арифметическое среднее цен сделок · buy / sell</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {(["buy", "sell"] as const).map((key) => {
            const labels = { buy: "Покупки", sell: "Продажи" };
            const colors = { buy: "text-emerald-400", sell: "text-red-400" };
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
        <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#3f3f46" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(ts) => formatDayLabel(new Date(ts).toISOString())}
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            minTickGap={40}
          />
          <YAxis
            domain={priceDomain ?? ["auto", "auto"]}
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            tickFormatter={formatPrice}
            width={64}
          />
          <Tooltip content={<TooltipContent />} />
          <Legend wrapperStyle={{ display: "none" }} />
          {!hiddenSeries.buy ? (
            <Line
              type="monotone"
              dataKey="buy"
              stroke="#34d399"
              strokeWidth={2}
              dot={{ r: 3, fill: "#34d399" }}
              connectNulls={false}
              isAnimationActive={false}
              name="Покупки"
            />
          ) : null}
          {!hiddenSeries.sell ? (
            <Line
              type="monotone"
              dataKey="sell"
              stroke="#f87171"
              strokeWidth={2}
              dot={{ r: 3, fill: "#f87171" }}
              connectNulls={false}
              isAnimationActive={false}
              name="Продажи"
            />
          ) : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
