import api from "./client";

export async function getMarketItems(params: { q?: string; limit?: number }) {
  const { data } = await api.get("/market/items", { params });
  return data;
}

export interface MarketVariants {
  soul_crystals: string[];
  rarities: string[];
  armor_classes: string[];
  enchant_levels: number[];
  has_sealed: boolean;
}

export async function getMarketVariants(entityId: string) {
  const { data } = await api.get("/market/variants", {
    params: { entity_id: entityId },
  });
  return data as MarketVariants;
}

export async function getMarketTimeline(params: {
  entity_id: string;
  interval: string;
  from?: string;
  to?: string;
}) {
  const { data } = await api.get("/market/timeline", { params });
  return data;
}

export async function getMarketChart(params: Record<string, unknown>) {
  const { data } = await api.get("/market/chart", { params });
  return data as TradingChartResponse;
}

export interface ChartDealPoint {
  recorded_at: string;
  price: number | string;
  quantity: number;
  side: string | null;
  seller_name: string;
  total_cost: number | string;
}

export interface TradingChartResponse {
  entity_id: string;
  from_date: string;
  to_date: string;
  deals: ChartDealPoint[];
  volume_buckets: Array<{
    bucket_start: string;
    buy_volume: number;
    sell_volume: number;
  }>;
  excluded_outlier_count?: number;
  outlier_deals?: ChartDealPoint[];
}

export async function getMarketAnalytics(params: Record<string, unknown>) {
  const { data } = await api.get("/market/analytics", { params });
  return data;
}

export interface DailyAvgPricePoint {
  day: string;
  buy_avg_price: number | string | null;
  sell_avg_price: number | string | null;
  buy_deal_count: number;
  sell_deal_count: number;
}

export interface DailyAvgPricesResponse {
  entity_id: string;
  from_date: string;
  to_date: string;
  points: DailyAvgPricePoint[];
  excluded_outlier_count?: number;
}

export async function getDailyAvgPrices(params: Record<string, unknown>) {
  const { data } = await api.get("/market/daily-avg-prices", { params });
  return data as DailyAvgPricesResponse;
}

export async function getOrderBook(params: Record<string, unknown>) {
  const { data } = await api.get("/market/order-book", { params });
  return data;
}

export async function getLuckyMoments(params: Record<string, unknown>) {
  const { data } = await api.get("/market/lucky-moments", { params });
  return data;
}

export async function getItemsOverview(params: Record<string, unknown>) {
  const { data } = await api.get("/market/items-overview", { params });
  return data;
}

export async function getTrades(params: Record<string, unknown>) {
  const { data } = await api.get("/market/trades", { params });
  return data;
}

export async function getPricesByIds(ids: string) {
  const { data } = await api.get("/market/prices-by-ids", { params: { ids } });
  return data;
}

export type CraftMonitorPeriod =
  | "1h"
  | "2h"
  | "3h"
  | "6h"
  | "12h"
  | "1d"
  | "2d"
  | "3d"
  | "7d"
  | "14d"
  | "30d"
  | "custom";

export interface CraftMonitorCard {
  external_id: number;
  entity_id: string | null;
  display_name: string;
  vwap: number | string | null;
  total_quantity: number;
  price_change_pct: number | string | null;
  seller_count: number;
}

export interface CraftMonitorResponse {
  period: string;
  items: CraftMonitorCard[];
}

export async function getCraftMonitor(params: Record<string, string>) {
  const { data } = await api.get("/market/craft-monitor", { params });
  return data as CraftMonitorResponse;
}

export interface BuyPlanLot {
  seller_id: string;
  seller_name: string;
  price: number | string;
  available_quantity: number;
  buy_quantity: number;
  cost: number | string;
  recorded_at: string;
}

export interface BuyPlanResponse {
  entity_id: string;
  requested_quantity: number;
  filled_quantity: number;
  shortfall: number;
  total_cost: number | string;
  avg_fill_price: number | string | null;
  lots: BuyPlanLot[];
}

export async function getBuyPlan(entityId: string, quantity: number) {
  const { data } = await api.get("/market/buy-plan", {
    params: { entity_id: entityId, quantity },
  });
  return data as BuyPlanResponse;
}

export interface TopOfferLot {
  seller_id: string;
  seller_name: string;
  quantity: number;
  price: number | string;
  recorded_at: string;
}

export interface TopOffersResponse {
  entity_id: string;
  sells: TopOfferLot[];
  buys: TopOfferLot[];
}

export async function getTopOffers(
  entityId: string,
  limit = 5,
  range?: { from: string; to: string },
) {
  const { data } = await api.get("/market/top-offers", {
    params: {
      entity_id: entityId,
      limit,
      ...(range ? { from: range.from, to: range.to } : {}),
    },
  });
  return data as TopOffersResponse;
}
