import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TimelinePoint {
  bucket_start: string;
  median_price: number;
  weighted_avg: number | null;
  seller_count: number;
  record_count: number;
  min_price: number;
  max_price: number;
}

interface SideSeries {
  buy: TimelinePoint[];
  sell: TimelinePoint[];
}

interface Props {
  title: string;
  accent: "amber" | "violet";
  series: SideSeries;
  interval: string;
  height?: number;
}

const ACCENTS = {
  amber: {
    buy: { stroke: "#34d399", fillId: "buyGradientAmber", sellFillId: "sellGradientAmber" },
    sell: { stroke: "#f87171" },
    grid: "#3f3f46",
  },
  violet: {
    buy: { stroke: "#a78bfa", fillId: "buyGradientViolet", sellFillId: "sellGradientViolet" },
    sell: { stroke: "#fb7185" },
    grid: "#3f3f46",
  },
};

function getTimeSpanMs(points: TimelinePoint[]): number {
  if (!points.length) return 0;
  const times = points.map((p) => new Date(p.bucket_start).getTime());
  return Math.max(...times) - Math.min(...times);
}

function formatBucketLabel(iso: string, interval: string, spanMs: number): string {
  const date = new Date(iso);
  const oneDay = 24 * 60 * 60 * 1000;
  const showDate = spanMs > oneDay;

  if (showDate) {
    if (interval === "1h" || interval === "30m") {
      return date.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    return date.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: interval.endsWith("s") ? "2-digit" : undefined,
    });
  }

  if (interval.endsWith("s")) {
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function formatTooltipLabel(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatPrice(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function mergeSeries(buy: TimelinePoint[], sell: TimelinePoint[], interval: string) {
  const spanMs = getTimeSpanMs([...buy, ...sell]);
  const map = new Map<
    string,
    {
      bucket_start: string;
      ts: number;
      label: string;
      tooltipLabel: string;
      buy: number | null;
      sell: number | null;
      buyMeta: TimelinePoint | null;
      sellMeta: TimelinePoint | null;
    }
  >();

  const chartPrice = (point: TimelinePoint) =>
    point.weighted_avg != null ? Number(point.weighted_avg) : Number(point.median_price);

  for (const point of buy) {
    map.set(point.bucket_start, {
      bucket_start: point.bucket_start,
      ts: new Date(point.bucket_start).getTime(),
      label: formatBucketLabel(point.bucket_start, interval, spanMs),
      tooltipLabel: formatTooltipLabel(point.bucket_start),
      buy: chartPrice(point),
      sell: null,
      buyMeta: point,
      sellMeta: null,
    });
  }

  for (const point of sell) {
    const existing = map.get(point.bucket_start);
    if (existing) {
      existing.sell = chartPrice(point);
      existing.sellMeta = point;
    } else {
      map.set(point.bucket_start, {
        bucket_start: point.bucket_start,
        ts: new Date(point.bucket_start).getTime(),
        label: formatBucketLabel(point.bucket_start, interval, spanMs),
        tooltipLabel: formatTooltipLabel(point.bucket_start),
        buy: null,
        sell: chartPrice(point),
        buyMeta: null,
        sellMeta: point,
      });
    }
  }

  return Array.from(map.values()).sort((a, b) => a.ts - b.ts);
}

function TooltipContent({
  active,
  payload,
  currencyTitle,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; payload: ReturnType<typeof mergeSeries>[number] }>;
  currencyTitle: string;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;

  return (
    <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/95 px-4 py-3 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-2 font-semibold text-zinc-100">{row.tooltipLabel}</p>
      <p className="mb-2 text-[0.65rem] uppercase tracking-wider text-zinc-500">{currencyTitle}</p>
      {row.buyMeta && (
        <div className="mb-2 border-b border-zinc-800 pb-2">
          <p className="font-medium text-emerald-400">Buy · средневзв. {formatPrice(row.buy ?? 0)}</p>
          <p className="mt-1 text-zinc-400">
            Продавцов: {row.buyMeta.seller_count} · Записей: {row.buyMeta.record_count}
          </p>
          <p className="text-zinc-500">Медиана: {formatPrice(Number(row.buyMeta.median_price))}</p>
        </div>
      )}
      {row.sellMeta && (
        <div>
          <p className="font-medium text-red-400">Sell · средневзв. {formatPrice(row.sell ?? 0)}</p>
          <p className="mt-1 text-zinc-400">
            Продавцов: {row.sellMeta.seller_count} · Записей: {row.sellMeta.record_count}
          </p>
          <p className="text-zinc-500">Медиана: {formatPrice(Number(row.sellMeta.median_price))}</p>
        </div>
      )}
    </div>
  );
}

export default function MarketTimelineChart({ title, accent, series, interval, height = 420 }: Props) {
  const data = useMemo(() => mergeSeries(series.buy, series.sell, interval), [series, interval]);
  const colors = ACCENTS[accent];
  const hasData = data.some((row) => row.buy != null || row.sell != null);
  const spanMs = useMemo(() => {
    if (!data.length) return 0;
    return data[data.length - 1].ts - data[0].ts;
  }, [data]);

  const tickFormatter = (ts: number) => {
    const iso = new Date(ts).toISOString();
    return formatBucketLabel(iso, interval, spanMs);
  };

  if (!hasData) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/40"
      >
        <p className="text-sm text-zinc-500">Нет данных для {title}</p>
      </div>
    );
  }

  const gradientId = accent === "amber" ? "Amber" : "Violet";

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/80 to-zinc-950/90 p-4 shadow-panel">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
          <p className="text-xs text-zinc-500">Средневзвешенная цена за интервал · buy / sell</p>
        </div>
        <div className="flex gap-3 text-xs">
          <span className="inline-flex items-center gap-1.5 text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Buy
          </span>
          <span className="inline-flex items-center gap-1.5 text-red-400">
            <span className="h-2 w-2 rounded-full bg-red-400" />
            Sell
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id={`buyGradient${gradientId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
            </linearGradient>
            <linearGradient id={`sellGradient${gradientId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f87171" stopOpacity={0.22} />
              <stop offset="100%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={colors.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={tickFormatter}
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            minTickGap={40}
            angle={-20}
            textAnchor="end"
            height={52}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            stroke="#52525b"
            tickFormatter={formatPrice}
            width={64}
          />
          <Tooltip content={<TooltipContent currencyTitle={title} />} />
          <Legend wrapperStyle={{ display: "none" }} />
          <Area
            type="monotone"
            dataKey="buy"
            stroke="none"
            fill={`url(#buyGradient${gradientId})`}
            connectNulls
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="sell"
            stroke="none"
            fill={`url(#sellGradient${gradientId})`}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="buy"
            stroke={colors.buy.stroke}
            strokeWidth={2.5}
            dot={{ r: 3, strokeWidth: 0, fill: colors.buy.stroke }}
            activeDot={{ r: 5, stroke: "#18181b", strokeWidth: 2 }}
            connectNulls
            name="Buy"
          />
          <Line
            type="monotone"
            dataKey="sell"
            stroke={colors.sell.stroke}
            strokeWidth={2.5}
            dot={{ r: 3, strokeWidth: 0, fill: colors.sell.stroke }}
            activeDot={{ r: 5, stroke: "#18181b", strokeWidth: 2 }}
            connectNulls
            name="Sell"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
