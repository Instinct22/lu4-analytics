import api from "./client";

export async function getMarketItems(params: { q?: string; limit?: number }) {
  const { data } = await api.get("/market/items", { params });
  return data;
}

export async function getMarketTimeline(params: {
  entity_id: string;
  interval: string;
}) {
  const { data } = await api.get("/market/timeline", { params });
  return data;
}

export async function getMarketChart(params: Record<string, unknown>) {
  const { data } = await api.get("/market/chart", { params });
  return data;
}

export async function getMarketAnalytics(params: Record<string, unknown>) {
  const { data } = await api.get("/market/analytics", { params });
  return data;
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
