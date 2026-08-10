import { useMemo, useRef, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  ReferenceArea,
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

interface ChartMouseEvent {
  activeLabel?: string | number;
  chartX?: number;
}

interface Props {
  deals: DealPoint[];
  volumeBuckets: VolumeBucket[];
  height?: number;
  excludedOutlierCount?: number;
  outlierDeals?: DealPoint[];
  onZoomRange?: (from: Date, to: Date) => void;
  onZoomReset?: () => void;
  canZoom?: boolean;
}

const MIN_ZOOM_MS = 60_000;
const CHART_MARGIN_LEFT = 68;
const CHART_MARGIN_RIGHT = 12;

function formatPrice(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function chartXToTs(
  chartX: number,
  chartWidth: number,
  domainMin: number,
  domainMax: number,
): number {
  const plotWidth = chartWidth - CHART_MARGIN_LEFT - CHART_MARGIN_RIGHT;
  if (plotWidth <= 0 || domainMax <= domainMin) return domainMin;
  const ratio = Math.max(0, Math.min(1, (chartX - CHART_MARGIN_LEFT) / plotWidth));
  return domainMin + ratio * (domainMax - domainMin);
}

function mapScatterPoints(rows: DealPoint[]) {
  return rows.map((d) => ({
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
}

function DealTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: DealPoint & { ts: number; label: string; isOutlier?: boolean } }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/95 px-4 py-3 text-xs shadow-xl backdrop-blur-md">
      <p className="mb-1 font-semibold text-zinc-100">
        {new Date(row.recorded_at).toLocaleString("ru-RU")}
      </p>
      {row.isOutlier ? (
        <p className="mb-1 text-[0.65rem] uppercase tracking-wide text-zinc-500">Статистический выброс</p>
      ) : null}
      <p className={row.side === "buy" ? "text-emerald-400" : "text-red-400"}>
        {row.side === "buy" ? "Покупка" : "Продажа"} · {formatPrice(row.price)}
      </p>
      <p className="mt-1 text-zinc-400">Кол-во: {row.quantity}</p>
      <p className="text-zinc-400">Сумма: {formatPrice(row.total_cost)}</p>
      <p className="mt-1 text-zinc-500">{row.seller_name}</p>
    </div>
  );
}

function outlierLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "сделка скрыта";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "сделки скрыты";
  return "сделок скрыто";
}

export default function TradeChart({
  deals,
  volumeBuckets,
  height = 420,
  excludedOutlierCount = 0,
  outlierDeals = [],
  onZoomRange,
  onZoomReset,
  canZoom = true,
}: Props) {
  const [hiddenSeries, setHiddenSeries] = useState({ buy: false, sell: false, volume: false });
  const [showOutliers, setShowOutliers] = useState(false);
  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null);
  const isSelecting = useRef(false);
  const selectionRef = useRef<{ left: number; right: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scatterData = useMemo(() => mapScatterPoints(deals), [deals]);
  const outlierScatterData = useMemo(
    () =>
      mapScatterPoints(outlierDeals).map((point) => ({
        ...point,
        isOutlier: true,
      })),
    [outlierDeals],
  );

  const buyData = useMemo(() => scatterData.filter((d) => d.side === "buy"), [scatterData]);
  const sellData = useMemo(() => scatterData.filter((d) => d.side === "sell"), [scatterData]);
  const outlierBuyData = useMemo(
    () => (showOutliers ? outlierScatterData.filter((d) => d.side === "buy") : []),
    [outlierScatterData, showOutliers],
  );
  const outlierSellData = useMemo(
    () => (showOutliers ? outlierScatterData.filter((d) => d.side === "sell") : []),
    [outlierScatterData, showOutliers],
  );

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

  const timeDomain = useMemo(() => {
    const allPoints = showOutliers ? [...scatterData, ...outlierScatterData] : scatterData;
    if (!allPoints.length) return { min: 0, max: 0 };
    const values = allPoints.map((d) => d.ts);
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [scatterData, outlierScatterData, showOutliers]);

  const priceDomain = useMemo(() => {
    if (!scatterData.length) return undefined;
    const prices = scatterData.map((d) => d.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const padding = Math.max((max - min) * 0.05, max * 0.02, 1);
    return [min - padding, max + padding] as [number, number];
  }, [scatterData]);

  const zoomEnabled = canZoom && !!onZoomRange;

  const resolveTs = (event: ChartMouseEvent): number | null => {
    if (event.activeLabel != null && event.activeLabel !== "") {
      const parsed = Number(event.activeLabel);
      return Number.isFinite(parsed) ? parsed : null;
    }
    if (event.chartX != null && containerRef.current) {
      return chartXToTs(
        event.chartX,
        containerRef.current.clientWidth,
        timeDomain.min,
        timeDomain.max,
      );
    }
    return null;
  };

  const handleMouseDown = (event: ChartMouseEvent) => {
    if (!zoomEnabled) return;
    const ts = resolveTs(event);
    if (ts == null) return;
    isSelecting.current = true;
    selectionRef.current = { left: ts, right: ts };
    setRefAreaLeft(ts);
    setRefAreaRight(ts);
  };

  const handleMouseMove = (event: ChartMouseEvent) => {
    if (!isSelecting.current || !selectionRef.current) return;
    const ts = resolveTs(event);
    if (ts == null) return;
    selectionRef.current = { ...selectionRef.current, right: ts };
    setRefAreaRight(ts);
  };

  const clearSelection = () => {
    isSelecting.current = false;
    selectionRef.current = null;
    setRefAreaLeft(null);
    setRefAreaRight(null);
  };

  const handleMouseUp = () => {
    const selection = selectionRef.current;
    clearSelection();
    if (!selection || !onZoomRange) return;
    let left = selection.left;
    let right = selection.right;
    if (left > right) [left, right] = [right, left];
    if (right - left < MIN_ZOOM_MS) return;
    onZoomRange(new Date(left), new Date(right));
  };

  const toggleSeries = (key: keyof typeof hiddenSeries) => {
    setHiddenSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const hasDeals = deals.length > 0 || outlierDeals.length > 0;

  if (!hasDeals) {
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
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <span>
            {excludedOutlierCount} {outlierLabel(excludedOutlierCount)} как статистические выбросы
          </span>
          <button
            type="button"
            onClick={() => setShowOutliers((prev) => !prev)}
            className="rounded-lg border border-amber-500/40 bg-zinc-950/40 px-2.5 py-1 text-amber-100 transition hover:bg-amber-500/20"
          >
            {showOutliers ? "Скрыть выбросы" : "Показать выбросы"}
          </button>
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-zinc-100">История сделок</h3>
          <p className="text-xs text-zinc-500">
            {zoomEnabled
              ? "Выделите область мышью для приближения · двойной клик — сброс zoom"
              : "Точки = цена, размер = объём, столбцы = агрегированный volume"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {onZoomReset ? (
            <button
              type="button"
              onClick={onZoomReset}
              className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-amber-300 transition hover:bg-amber-500/20"
            >
              Сбросить zoom
            </button>
          ) : null}
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

      <div
        ref={containerRef}
        style={{ userSelect: zoomEnabled ? "none" : undefined, cursor: zoomEnabled ? "crosshair" : undefined }}
        onDoubleClick={onZoomReset}
      >
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart
            data={volumeData.length ? volumeData : scatterData.length ? scatterData : outlierScatterData}
            margin={{ top: 8, right: CHART_MARGIN_RIGHT, left: 4, bottom: 0 }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={clearSelection}
          >
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
                new Date(ts).toLocaleString("ru-RU", {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              }
            />
            <YAxis
              yAxisId="price"
              domain={priceDomain ?? ["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#a1a1aa" }}
              stroke="#52525b"
              tickFormatter={formatPrice}
              width={64}
            />
            <YAxis yAxisId="volume" orientation="right" hide />
            <ZAxis type="number" dataKey="quantity" range={[30, 400]} />
            <Tooltip content={<DealTooltip />} />
            <Legend wrapperStyle={{ display: "none" }} />

            {refAreaLeft != null && refAreaRight != null ? (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                stroke="#f59e0b"
                strokeOpacity={0.8}
                fill="#f59e0b"
                fillOpacity={0.15}
              />
            ) : null}

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
            {showOutliers && !hiddenSeries.buy && outlierBuyData.length > 0 && (
              <Scatter
                yAxisId="price"
                data={outlierBuyData}
                dataKey="price"
                fill="#71717a"
                fillOpacity={0.55}
                name="Outlier buy"
                isAnimationActive={false}
              />
            )}
            {showOutliers && !hiddenSeries.sell && outlierSellData.length > 0 && (
              <Scatter
                yAxisId="price"
                data={outlierSellData}
                dataKey="price"
                fill="#71717a"
                fillOpacity={0.55}
                name="Outlier sell"
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
