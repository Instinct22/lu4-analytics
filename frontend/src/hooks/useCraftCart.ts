import { useCallback, useMemo } from "react";
import type { CraftCartPayload } from "../api/preferences";
import {
  cartEntryKey,
  parseCartEntryKey,
  type CartEntry,
} from "../lib/craftCalc";
import { useCraftCartPreference } from "./usePreferences";

function parseCart(raw: CraftCartPayload): CartEntry[] {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];

  const map = new Map<string, CartEntry>();
  for (const [key, line] of Object.entries(raw)) {
    const entry = parseCartEntryKey(key, line);
    if (!entry || entry.qty <= 0) continue;
    const dedupeKey = cartEntryKey(entry.productId, entry.variantIdx);
    const prev = map.get(dedupeKey);
    map.set(
      dedupeKey,
      prev ? { ...prev, qty: prev.qty + entry.qty } : entry,
    );
  }
  return [...map.values()];
}

function toPayload(entries: CartEntry[]): CraftCartPayload {
  const out: CraftCartPayload = {};
  for (const e of entries) {
    out[cartEntryKey(e.productId, e.variantIdx)] = {
      qty: e.qty,
      variant: e.variantIdx,
    };
  }
  return out;
}

function sameLine(a: CartEntry, productId: number, variantIdx: number): boolean {
  return a.productId === productId && a.variantIdx === variantIdx;
}

export function useCraftCart() {
  const [raw, setRaw] = useCraftCartPreference();

  const entries = useMemo(() => parseCart(raw), [raw]);

  const totalCount = useMemo(
    () => entries.reduce((sum, e) => sum + e.qty, 0),
    [entries],
  );

  const setEntries = useCallback(
    (next: CartEntry[]) => setRaw(toPayload(next)),
    [setRaw],
  );

  const add = useCallback(
    (productId: number, qty: number, variantIdx = 0) => {
      const n = Math.max(1, Math.floor(qty));
      const vi = Math.max(0, Math.floor(variantIdx));
      const existing = entries.find((e) => sameLine(e, productId, vi));
      if (existing) {
        setEntries(
          entries.map((e) =>
            sameLine(e, productId, vi) ? { ...e, qty: e.qty + n } : e,
          ),
        );
      } else {
        setEntries([...entries, { productId, qty: n, variantIdx: vi }]);
      }
    },
    [entries, setEntries],
  );

  const remove = useCallback(
    (productId: number, variantIdx = 0) => {
      const vi = Math.max(0, Math.floor(variantIdx));
      setEntries(entries.filter((e) => !sameLine(e, productId, vi)));
    },
    [entries, setEntries],
  );

  const setQty = useCallback(
    (productId: number, qty: number, variantIdx = 0) => {
      const vi = Math.max(0, Math.floor(variantIdx));
      const n = Math.floor(qty);
      if (n <= 0) {
        setEntries(entries.filter((e) => !sameLine(e, productId, vi)));
        return;
      }
      setEntries(
        entries.map((e) => (sameLine(e, productId, vi) ? { ...e, qty: n } : e)),
      );
    },
    [entries, setEntries],
  );

  const clear = useCallback(() => setRaw({}), [setRaw]);

  return {
    entries,
    totalCount,
    isEmpty: entries.length === 0,
    add,
    remove,
    setQty,
    clear,
  };
}
