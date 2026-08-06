import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMarketTimeline } from "../api/market";
import ItemMarketSelect, { MarketItemOption } from "../components/charts/ItemMarketSelect";
import MarketTimelineChart from "../components/charts/MarketTimelineChart";
import TopOffersTables from "../components/charts/TopOffersTables";
import CraftResourcesMonitor from "../components/trading/CraftResourcesMonitor";
import { PeriodState } from "../components/trading/PeriodSelector";
import {
  periodTimeRange,
  timelineIntervalForPeriod,
} from "../components/trading/periodUtils";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useChartHeight } from "../hooks/useMediaQuery";

const defaultPeriod = (): PeriodState => ({
  period: "1d",
  from: "",
  to: "",
});

export default function Dashboard() {
  const [selectedItem, setSelectedItem] = useState<MarketItemOption | null>(null);
  const [period, setPeriod] = useState<PeriodState>(defaultPeriod);
  const [craftOpen, setCraftOpen] = useState(true);
  const chartHeight = useChartHeight(440);

  const interval = timelineIntervalForPeriod(period);
  const timeRange = useMemo(() => periodTimeRange(period), [period]);

  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useQuery({
    queryKey: ["market-timeline", selectedItem?.id, interval, timeRange.from, timeRange.to],
    queryFn: () =>
      getMarketTimeline({
        entity_id: selectedItem!.id,
        interval,
        from: timeRange.from,
        to: timeRange.to,
      }),
    enabled: !!selectedItem?.id,
  });

  const handleOverviewSelect = (id: string, displayName: string) => {
    setSelectedItem({ id, display_name: displayName, record_count: 0 });
  };

  // Chart card padding + header roughly match the offers column height.
  const offersColumnMinHeight = chartHeight + 72;

  return (
    <div className="space-y-8">
      <PageHeader title="Dashboard" />

      <CraftResourcesMonitor
        selectedId={selectedItem?.id ?? null}
        onSelect={handleOverviewSelect}
        period={period}
        onPeriodChange={setPeriod}
        open={craftOpen}
        onToggle={() => setCraftOpen((prev) => !prev)}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)] xl:items-stretch">
        <div
          className="flex min-h-0 flex-col gap-4"
          style={selectedItem ? { minHeight: offersColumnMinHeight } : undefined}
        >
          <div className="card shrink-0">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-400">Предмет</h3>
            <ItemMarketSelect
              selectedId={selectedItem?.id ?? null}
              onSelect={setSelectedItem}
            />
          </div>
          {selectedItem ? (
            <TopOffersTables entityId={selectedItem.id} from={timeRange.from} to={timeRange.to} />
          ) : null}
        </div>

        <div className="min-h-0">
          {!selectedItem ? (
            <div className="card flex h-full min-h-[22rem] flex-col items-center justify-center text-center 2xl:min-h-[32rem]">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 text-2xl text-amber-500">
                ◈
              </div>
              <h3 className="text-lg font-semibold text-zinc-100">Рыночный график</h3>
              <p className="mt-2 max-w-md text-sm text-zinc-500">
                Выберите предмет слева или кликните на карточку крафт-ресурса, чтобы построить график средневзвешенной цены.
              </p>
            </div>
          ) : timelineLoading ? (
            <LoadingState />
          ) : timelineError ? (
            <ErrorState message="Ошибка загрузки графика" />
          ) : (
            <MarketTimelineChart
              title="Adena"
              accent="amber"
              series={timeline.adena}
              interval={interval}
              height={chartHeight}
            />
          )}
        </div>
      </div>
    </div>
  );
}
