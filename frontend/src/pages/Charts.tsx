import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getItemsOverview,
  getLuckyMoments,
  getMarketAnalytics,
  getMarketChart,
  getOrderBook,
} from "../api/market";
import ItemMarketSelect, { MarketItemOption } from "../components/charts/ItemMarketSelect";
import AnalyticsPanel from "../components/trading/AnalyticsPanel";
import ItemsOverview from "../components/trading/ItemsOverview";
import LuckyMoments from "../components/trading/LuckyMoments";
import OrderBook from "../components/trading/OrderBook";
import PeriodSelector, { PeriodState } from "../components/trading/PeriodSelector";
import TradeChart from "../components/trading/TradeChart";
import TradesTable from "../components/trading/TradesTable";
import { periodQueryParams } from "../components/trading/periodUtils";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useChartHeight } from "../hooks/useMediaQuery";

const defaultPeriod = (): PeriodState => ({
  period: "24h",
  from: "",
  to: "",
});

export default function Charts() {
  const [selectedItem, setSelectedItem] = useState<MarketItemOption | null>(null);
  const [period, setPeriod] = useState<PeriodState>(defaultPeriod);
  const chartHeight = useChartHeight(420);

  const periodParams = useMemo(() => periodQueryParams(period), [period]);
  const entityId = selectedItem?.id ?? null;

  const queryEnabled = !!entityId;

  const { data: chartData, isLoading: chartLoading, error: chartError } = useQuery({
    queryKey: ["trading-chart", entityId, periodParams],
    queryFn: () => getMarketChart({ entity_id: entityId, ...periodParams }),
    enabled: queryEnabled,
  });

  const { data: analytics } = useQuery({
    queryKey: ["trading-analytics", entityId, periodParams],
    queryFn: () => getMarketAnalytics({ entity_id: entityId, ...periodParams }),
    enabled: queryEnabled,
  });

  const { data: orderBook } = useQuery({
    queryKey: ["trading-order-book", entityId, periodParams],
    queryFn: () => getOrderBook({ entity_id: entityId, ...periodParams }),
    enabled: queryEnabled,
  });

  const { data: luckyMoments } = useQuery({
    queryKey: ["trading-lucky", entityId, periodParams],
    queryFn: () => getLuckyMoments({ entity_id: entityId, ...periodParams }),
    enabled: queryEnabled,
  });

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["trading-overview", periodParams],
    queryFn: () => getItemsOverview(periodParams),
    refetchInterval: 60_000,
  });

  const handleOverviewSelect = (id: string, displayName: string) => {
    setSelectedItem({ id, display_name: displayName, record_count: 0 });
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Графики">
        <PeriodSelector value={period} onChange={setPeriod} />
      </PageHeader>

      <div className="card">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-400">Выбор предмета</h3>
        <div className="w-full lg:max-w-2xl">
          <ItemMarketSelect
            selectedId={selectedItem?.id ?? null}
            onSelect={setSelectedItem}
          />
        </div>
      </div>

      {overviewLoading ? (
        <LoadingState />
      ) : (
        <ItemsOverview
          items={overview?.items ?? []}
          selectedId={entityId}
          onSelect={handleOverviewSelect}
        />
      )}

      {!selectedItem ? (
        <div className="card flex min-h-[360px] flex-col items-center justify-center text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 text-2xl text-amber-500">
            ◉
          </div>
          <h3 className="text-lg font-semibold text-zinc-100">Аналитика торговли</h3>
          <p className="mt-2 max-w-lg text-sm text-zinc-500">
            Выберите предмет выше или кликните на карточку в мини-мониторинге. Все компоненты обновятся автоматически
            при смене предмета или периода.
          </p>
        </div>
      ) : (
        <>
          <AnalyticsPanel data={analytics} />

          {chartLoading ? (
            <LoadingState />
          ) : chartError ? (
            <ErrorState message="Ошибка загрузки графика" />
          ) : (
            <TradeChart
              deals={chartData?.deals ?? []}
              volumeBuckets={chartData?.volume_buckets ?? []}
              height={chartHeight}
            />
          )}

          <div className="grid gap-6 xl:grid-cols-2">
            <TradesTable
              title="Таблица продаж"
              side="sell"
              entityId={entityId!}
              period={period}
            />
            <TradesTable
              title="Таблица покупок"
              side="buy"
              entityId={entityId!}
              period={period}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,26rem)]">
            <OrderBook
              buys={(orderBook?.buys ?? []).map((l: { price: number; volume: number }) => ({
                price: Number(l.price),
                volume: l.volume,
              }))}
              sells={(orderBook?.sells ?? []).map((l: { price: number; volume: number }) => ({
                price: Number(l.price),
                volume: l.volume,
              }))}
            />
            <LuckyMoments events={luckyMoments?.events ?? []} />
          </div>
        </>
      )}
    </div>
  );
}
