import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../api/stats";
import { getMarketTimeline } from "../api/market";
import ItemMarketSelect, { MarketItemOption } from "../components/charts/ItemMarketSelect";
import MarketTimelineChart from "../components/charts/MarketTimelineChart";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../components/ui";
import { useChartHeight } from "../hooks/useMediaQuery";

const INTERVALS = [
  { key: "5s", label: "5s" },
  { key: "15s", label: "15s" },
  { key: "1m", label: "1m" },
  { key: "5m", label: "5m" },
  { key: "30m", label: "30m" },
  { key: "1h", label: "1h" },
] as const;

type IntervalKey = (typeof INTERVALS)[number]["key"];

export default function Dashboard() {
  const [selectedItem, setSelectedItem] = useState<MarketItemOption | null>(null);
  const [interval, setInterval] = useState<IntervalKey>("5m");
  const chartHeight = useChartHeight(440);

  const { data: dashboard, isLoading: dashboardLoading, error: dashboardError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useQuery({
    queryKey: ["market-timeline", selectedItem?.id, interval],
    queryFn: () =>
      getMarketTimeline({ entity_id: selectedItem!.id, interval }),
    enabled: !!selectedItem?.id,
  });

  const stats = useMemo(() => {
    if (!timeline) return null;
    const allPoints = [
      ...timeline.adena.buy,
      ...timeline.adena.sell,
      ...timeline.master_coin.buy,
      ...timeline.master_coin.sell,
    ];
    const sellers = allPoints.reduce((sum, point) => sum + point.seller_count, 0);
    const records = allPoints.reduce((sum, point) => sum + point.record_count, 0);
    return { buckets: allPoints.length, sellers, records };
  }, [timeline]);

  if (dashboardLoading) return <LoadingState />;
  if (dashboardError) return <ErrorState message="Ошибка загрузки dashboard" />;

  const counts = dashboard.entity_counts || {};

  return (
    <div className="space-y-8">
      <PageHeader title="Dashboard">
        <div className="flex flex-wrap gap-2">
          {INTERVALS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setInterval(item.key)}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-all ${
                interval === item.key
                  ? "bg-amber-500 text-zinc-950 shadow-sm"
                  : "border border-zinc-700/80 bg-zinc-900/80 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Предметы" value={counts.item || 0} />
        <StatCard title="NPC" value={counts.npc || 0} />
        <StatCard title="Записей цен" value={dashboard.total_market_records} />
        <StatCard title="Интервал" value={interval} subtitle="шаг временной оси" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)]">
        <div className="card h-fit xl:sticky xl:top-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-400">Предмет</h3>
          <ItemMarketSelect
            selectedId={selectedItem?.id ?? null}
            onSelect={setSelectedItem}
          />
        </div>

        <div className="space-y-6">
          {!selectedItem ? (
            <div className="card flex min-h-[22rem] flex-col items-center justify-center text-center 2xl:min-h-[32rem]">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 text-2xl text-amber-500">
                ◈
              </div>
              <h3 className="text-lg font-semibold text-zinc-100">Рыночный график</h3>
              <p className="mt-2 max-w-md text-sm text-zinc-500">
                Выберите предмет слева, чтобы построить график медианной цены по данным сканирования торговцев.
              </p>
            </div>
          ) : timelineLoading ? (
            <LoadingState />
          ) : timelineError ? (
            <ErrorState message="Ошибка загрузки графика" />
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard title="Интервалов" value={stats?.buckets ?? 0} subtitle={selectedItem.display_name} />
                <StatCard title="Продавцов в точках" value={stats?.sellers ?? 0} />
                <StatCard title="Записей в точках" value={stats?.records ?? 0} />
              </div>

              <MarketTimelineChart
                title="Adena"
                accent="amber"
                series={timeline.adena}
                interval={interval}
                height={chartHeight}
              />

              <MarketTimelineChart
                title="Master Coin"
                accent="violet"
                series={timeline.master_coin}
                interval={interval}
                height={chartHeight}
              />
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-zinc-200">Последние импорты</h3>
        {!dashboard.recent_imports?.length ? (
          <p className="text-sm text-zinc-500">Импортов пока нет</p>
        ) : (
          <ul className="divide-y divide-zinc-800/80 text-sm">
            {dashboard.recent_imports.map(
              (item: {
                id: string;
                source: string;
                records_count: number;
                matched_count: number;
                created_at: string;
              }) => (
                <li key={item.id} className="flex justify-between gap-4 py-3 first:pt-0 last:pb-0">
                  <span className="font-medium text-zinc-300">{item.source}</span>
                  <span className="tabular-nums text-zinc-500">
                    {item.matched_count}/{item.records_count} — {new Date(item.created_at).toLocaleString("ru-RU")}
                  </span>
                </li>
              ),
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
