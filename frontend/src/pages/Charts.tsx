import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  getLuckyMoments,
  getMarketAnalytics,
  getMarketChart,
  getMarketItems,
  getMarketVariants,
  getOrderBook,
} from "../api/market";
import ItemMarketSelect, { MarketItemOption } from "../components/charts/ItemMarketSelect";
import VariantFilter, { VariantSelection } from "../components/trading/VariantFilter";
import AnalyticsPanel from "../components/trading/AnalyticsPanel";
import ChartsSection from "../components/trading/ChartsSection";
import CraftResourcesMonitor from "../components/trading/CraftResourcesMonitor";
import {
  GatherBuyControls,
  GatherBuyResult,
  useGatherBuyPlan,
} from "../components/trading/GatherBuyPlan";
import LuckyMoments from "../components/trading/LuckyMoments";
import OrderBook from "../components/trading/OrderBook";
import { PeriodState } from "../components/trading/PeriodSelector";
import TradeChart from "../components/trading/TradeChart";
import TradesTable from "../components/trading/TradesTable";
import { periodQueryParams } from "../components/trading/periodUtils";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useChartHeight } from "../hooks/useMediaQuery";

const defaultPeriod = (): PeriodState => ({
  period: "1d",
  from: "",
  to: "",
});

type SectionKey = "craft" | "analytics" | "chart" | "trades" | "orderBook" | "lucky";

const defaultOpen: Record<SectionKey, boolean> = {
  craft: true,
  analytics: true,
  chart: true,
  trades: true,
  orderBook: true,
  lucky: true,
};

export default function Charts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedItem, setSelectedItem] = useState<MarketItemOption | null>(null);
  const [variant, setVariant] = useState<VariantSelection>({
    soulCrystal: null,
    rarity: null,
    armorClass: null,
    sealed: null,
    enchantLevel: null,
  });
  const [period, setPeriod] = useState<PeriodState>(defaultPeriod);
  const [openSections, setOpenSections] = useState(defaultOpen);
  const chartHeight = useChartHeight(420);

  const paramExternalId = useMemo(() => {
    const raw = searchParams.get("external_id");
    if (!raw) return null;
    const id = Number(raw);
    return Number.isFinite(id) ? id : null;
  }, [searchParams]);

  const { data: marketData } = useQuery({
    queryKey: ["market-items", "all"],
    queryFn: () => getMarketItems({ limit: 2000 }),
  });

  useEffect(() => {
    if (paramExternalId == null || !marketData?.items) return;
    const match = marketData.items.find(
      (item: MarketItemOption) => item.external_id === paramExternalId,
    );
    if (!match) return;
    setSelectedItem((prev) => (prev?.id === match.id ? prev : match));
  }, [paramExternalId, marketData]);

  const selectItem = (item: MarketItemOption) => {
    setSelectedItem(item);
    setVariant({
      soulCrystal: null,
      rarity: null,
      armorClass: null,
      sealed: null,
      enchantLevel: null,
    });
    if (item.external_id != null) {
      setSearchParams({ external_id: String(item.external_id) }, { replace: true });
    } else if (searchParams.has("external_id")) {
      setSearchParams({}, { replace: true });
    }
  };

  const periodParams = useMemo(() => periodQueryParams(period), [period]);
  const entityId = selectedItem?.id ?? null;
  const queryEnabled = !!entityId;
  const gather = useGatherBuyPlan(entityId);

  const variantParams = useMemo(() => {
    const params: Record<string, string | number> = {};
    if (variant.soulCrystal) params.soul_crystal = variant.soulCrystal;
    if (variant.rarity) params.rarity = variant.rarity;
    if (variant.armorClass) params.armor_class = variant.armorClass;
    if (variant.sealed) params.sealed = variant.sealed;
    if (variant.enchantLevel != null) {
      params.enchant_level =
        variant.enchantLevel === "clean" ? "clean" : variant.enchantLevel;
    }
    return params;
  }, [variant]);

  const { data: variants } = useQuery({
    queryKey: ["market-variants", entityId],
    queryFn: () => getMarketVariants(entityId!),
    enabled: queryEnabled,
  });

  const { data: chartData, isLoading: chartLoading, error: chartError } = useQuery({
    queryKey: ["trading-chart", entityId, periodParams, variantParams],
    queryFn: () => getMarketChart({ entity_id: entityId, ...periodParams, ...variantParams }),
    enabled: queryEnabled,
  });

  const { data: analytics } = useQuery({
    queryKey: ["trading-analytics", entityId, periodParams, variantParams],
    queryFn: () => getMarketAnalytics({ entity_id: entityId, ...periodParams, ...variantParams }),
    enabled: queryEnabled,
  });

  const { data: orderBook } = useQuery({
    queryKey: ["trading-order-book", entityId, periodParams, variantParams],
    queryFn: () => getOrderBook({ entity_id: entityId, ...periodParams, ...variantParams }),
    enabled: queryEnabled,
  });

  const { data: luckyMoments } = useQuery({
    queryKey: ["trading-lucky", entityId, periodParams, variantParams],
    queryFn: () => getLuckyMoments({ entity_id: entityId, ...periodParams, ...variantParams }),
    enabled: queryEnabled,
  });

  const handleOverviewSelect = (id: string, displayName: string) => {
    const fromList = marketData?.items?.find((item: MarketItemOption) => item.id === id);
    selectItem(fromList ?? { id, display_name: displayName, record_count: 0 });
  };

  const toggleSection = (key: SectionKey) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Графики" />

      <div className="card relative z-40 !py-3 overflow-visible">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <h3 className="shrink-0 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Предмет
            </h3>
            <ItemMarketSelect
              selectedId={selectedItem?.id ?? null}
              onSelect={selectItem}
            />
          </div>
          <div className="shrink-0 border-t border-zinc-800/80 pt-3 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
            <GatherBuyControls
              entityId={entityId}
              draftQty={gather.draftQty}
              onDraftQtyChange={gather.setDraftQty}
              onGather={gather.gather}
              loading={gather.isFetching}
            />
          </div>
        </div>
        {selectedItem &&
        ((variants?.soul_crystals?.length ?? 0) > 0 ||
          (variants?.rarities?.length ?? 0) > 0 ||
          (variants?.armor_classes?.length ?? 0) > 0 ||
          (variants?.enchant_levels?.length ?? 0) > 0 ||
          variants?.has_sealed) ? (
          <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-zinc-800/80 pt-3">
            <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Вариант
            </span>
            <VariantFilter variants={variants} value={variant} onChange={setVariant} />
          </div>
        ) : null}
        <GatherBuyResult
          visible={gather.requestedQty != null && !!entityId}
          data={gather.data}
          loading={gather.isFetching}
          error={gather.isError}
          itemName={selectedItem?.display_name ?? null}
        />
      </div>

      <CraftResourcesMonitor
        selectedId={entityId}
        onSelect={handleOverviewSelect}
        period={period}
        onPeriodChange={setPeriod}
        open={openSections.craft}
        onToggle={() => toggleSection("craft")}
      />

      {!selectedItem ? (
        <div className="card flex min-h-[200px] flex-col items-center justify-center text-center">
          <h3 className="text-lg font-semibold text-zinc-100">Аналитика торговли</h3>
          <p className="mt-2 max-w-lg text-sm text-zinc-500">
            Выберите предмет выше или кликните на карточку крафт-ресурса.
          </p>
        </div>
      ) : (
        <>
          <ChartsSection
            title="Аналитика"
            open={openSections.analytics}
            onToggle={() => toggleSection("analytics")}
            period={period}
            onPeriodChange={setPeriod}
          >
            <AnalyticsPanel data={analytics} />
          </ChartsSection>

          <ChartsSection
            title="График сделок"
            open={openSections.chart}
            onToggle={() => toggleSection("chart")}
            period={period}
            onPeriodChange={setPeriod}
          >
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
          </ChartsSection>

          <ChartsSection
            title="Таблицы сделок"
            open={openSections.trades}
            onToggle={() => toggleSection("trades")}
            period={period}
            onPeriodChange={setPeriod}
          >
            <div className="grid gap-6 xl:grid-cols-2">
              <TradesTable
                title="Таблица продаж"
                side="sell"
                entityId={entityId!}
                period={period}
                soulCrystal={variant.soulCrystal}
                rarity={variant.rarity}
                armorClass={variant.armorClass}
                sealed={variant.sealed}
                enchantLevel={variant.enchantLevel}
              />
              <TradesTable
                title="Таблица покупок"
                side="buy"
                entityId={entityId!}
                period={period}
                soulCrystal={variant.soulCrystal}
                rarity={variant.rarity}
                armorClass={variant.armorClass}
                sealed={variant.sealed}
                enchantLevel={variant.enchantLevel}
              />
            </div>
          </ChartsSection>

          <ChartsSection
            title="Стакан"
            open={openSections.orderBook}
            onToggle={() => toggleSection("orderBook")}
            period={period}
            onPeriodChange={setPeriod}
          >
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
          </ChartsSection>

          <ChartsSection
            title="Удачные моменты"
            open={openSections.lucky}
            onToggle={() => toggleSection("lucky")}
            period={period}
            onPeriodChange={setPeriod}
          >
            <LuckyMoments events={luckyMoments?.events ?? []} />
          </ChartsSection>
        </>
      )}
    </div>
  );
}
