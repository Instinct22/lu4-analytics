import { useSyncExternalStore } from "react";
import type { InventoryLineInput } from "../api/trading";

export type TradingClipboardItem = InventoryLineInput;

type Snapshot = {
  items: TradingClipboardItem[];
  sourceNick: string | null;
};

let snapshot: Snapshot = { items: [], sourceNick: null };
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function setTradingItemClipboard(items: TradingClipboardItem[], sourceNick: string) {
  snapshot = {
    items: items.map((item) => ({
      item_external_id: item.item_external_id,
      item_name: item.item_name,
      quantity: item.quantity,
      unit_price: item.unit_price,
    })),
    sourceNick,
  };
  emit();
}

export function clearTradingItemClipboard() {
  snapshot = { items: [], sourceNick: null };
  emit();
}

export function getTradingItemClipboard(): Snapshot {
  return snapshot;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useTradingItemClipboard(): Snapshot {
  return useSyncExternalStore(subscribe, getTradingItemClipboard, getTradingItemClipboard);
}

/** Merge clipboard into current lines; skip duplicates by id (or name for custom). */
export function mergeClipboardItems(
  current: Array<{
    key: string;
    item_external_id: number;
    item_name: string;
    quantity: number;
    unit_price: number;
  }>,
  clipboard: TradingClipboardItem[],
): { next: typeof current; added: number; skipped: number } {
  const existingIds = new Set(
    current.filter((row) => row.item_external_id >= 0).map((row) => row.item_external_id),
  );
  const existingNames = new Set(
    current
      .filter((row) => row.item_external_id < 0)
      .map((row) => row.item_name.toLowerCase()),
  );

  const next = [...current];
  let added = 0;
  let skipped = 0;
  const stamp = Date.now();

  for (const item of clipboard) {
    const isCustom = item.item_external_id < 0;
    const dup = isCustom
      ? existingNames.has(item.item_name.toLowerCase())
      : existingIds.has(item.item_external_id);
    if (dup) {
      skipped += 1;
      continue;
    }
    if (isCustom) existingNames.add(item.item_name.toLowerCase());
    else existingIds.add(item.item_external_id);

    next.push({
      key: `paste-${item.item_external_id}-${stamp}-${added}`,
      item_external_id: item.item_external_id,
      item_name: item.item_name,
      quantity: item.quantity,
      unit_price: Number(item.unit_price) || 0,
    });
    added += 1;
  }

  return { next, added, skipped };
}
