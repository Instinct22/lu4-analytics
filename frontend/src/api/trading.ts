import api from "./client";

export type CharacterKind = "bank" | "merchant";
export type TradeMode = "sell" | "buy";

export type InventoryLine = {
  id: string;
  item_external_id: number;
  item_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  catalog_matched?: boolean;
};

export type TradingCharacter = {
  id: string;
  kind: CharacterKind;
  nick: string;
  clean_adena: number;
  master_coin: number;
  master_coin_price: number;
  master_coin_adena: number;
  description: string | null;
  trade_mode: TradeMode;
  adena_in_items: number;
  buy_cost: number;
  total_adena: number;
  sort_order: number;
  updated_at?: string | null;
  sell_items: InventoryLine[];
  buy_items: InventoryLine[];
  items: InventoryLine[];
};

export type InventoryLineInput = {
  item_external_id: number;
  item_name: string;
  quantity: number;
  unit_price: number;
};

export type SnapshotListItem = {
  id: string;
  created_at: string;
  label: string | null;
};

export type SnapshotPayloadItem = {
  item_external_id: number;
  item_name: string;
  quantity: number;
  unit_price: string | number;
};

export type SnapshotPayloadCharacter = {
  id: string;
  kind: CharacterKind;
  nick: string;
  clean_adena: string | number;
  master_coin?: string | number;
  master_coin_price?: string | number;
  master_coin_adena?: string | number;
  description?: string;
  trade_mode?: TradeMode;
  adena_in_items?: string | number;
  buy_cost?: string | number;
  total_adena?: string | number;
  sell_items?: SnapshotPayloadItem[];
  buy_items?: SnapshotPayloadItem[];
  items?: SnapshotPayloadItem[];
};

export type SnapshotDetail = {
  id: string;
  created_at: string;
  label: string | null;
  payload: { characters?: SnapshotPayloadCharacter[] };
};

export type ItemSearchHit = {
  external_id: number;
  display_name: string;
};

export type ItemCatalogHit = {
  external_id: number;
  display_name: string;
  group: "resource" | "item";
};

export async function listTradingCharacters() {
  const { data } = await api.get<{ characters: TradingCharacter[] }>("/trading/characters");
  return data;
}

export async function createTradingCharacter(body: { kind: CharacterKind; nick: string }) {
  const { data } = await api.post<TradingCharacter>("/trading/characters", body);
  return data;
}

export async function updateTradingCharacter(
  id: string,
  body: {
    clean_adena: number;
    master_coin: number;
    master_coin_price: number;
    description: string | null;
    trade_mode: TradeMode;
    sell_items: InventoryLineInput[];
    buy_items: InventoryLineInput[];
  },
) {
  const { data } = await api.put<TradingCharacter>(`/trading/characters/${id}`, body);
  return data;
}

export async function deleteTradingCharacter(id: string) {
  await api.delete(`/trading/characters/${id}`);
}

export async function searchTradingItems(q: string, limit = 30) {
  const { data } = await api.get<{ items: ItemSearchHit[] }>("/trading/item-search", {
    params: { q, limit },
  });
  return data;
}

export async function getTradingItemCatalog() {
  const { data } = await api.get<{ items: ItemCatalogHit[] }>("/trading/item-catalog");
  return data;
}

export async function listTradingSnapshots() {
  const { data } = await api.get<{ snapshots: SnapshotListItem[] }>("/trading/snapshots");
  return data;
}

export async function createTradingSnapshot(label?: string | null) {
  const { data } = await api.post<SnapshotDetail>("/trading/snapshots", { label: label ?? null });
  return data;
}

export async function getTradingSnapshot(id: string) {
  const { data } = await api.get<SnapshotDetail>(`/trading/snapshots/${id}`);
  return data;
}
