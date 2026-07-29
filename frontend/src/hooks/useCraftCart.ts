import { useCallback, useMemo } from "react";
import type { CraftCartPayload } from "../api/preferences";
import type { CartEntry } from "../lib/craftCalc";
import { useCraftCartPreference } from "./usePreferences";

function parseCart(raw: CraftCartPayload): CartEntry[] {
  return Object.entries(raw)
    .map(([id, line]) => ({
      productId: Number(id),
      qty: Math.max(1, Math.floor(Number(line?.qty) || 1)),
      variantIdx: line?.variant,
    }))
    .filter((e) => Number.isFinite(e.productId) && e.productId > 0);
}

function toPayload(entries: CartEntry[]): CraftCartPayload {
  const out: CraftCartPayload = {};
  for (const e of entries) {
    out[String(e.productId)] = {
      qty: e.qty,
      ...(e.variantIdx != null ? { variant: e.variantIdx } : {}),
    };
  }
  return out;
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
    (productId: number, qty: number, variantIdx?: number) => {
      const n = Math.max(1, Math.floor(qty));
      const existing = entries.find((e) => e.productId === productId);
      if (existing) {
        setEntries(
          entries.map((e) =>
            e.productId === productId
              ? {
                  ...e,
                  qty: e.qty + n,
                  variantIdx: variantIdx ?? e.variantIdx,
                }
              : e,
          ),
        );
      } else {
        setEntries([...entries, { productId, qty: n, variantIdx }]);
      }
    },
    [entries, setEntries],
  );

  const remove = useCallback(
    (productId: number) => {
      setEntries(entries.filter((e) => e.productId !== productId));
    },
    [entries, setEntries],
  );

  const setQty = useCallback(
    (productId: number, qty: number) => {
      const n = Math.floor(qty);
      if (n <= 0) {
        setEntries(entries.filter((e) => e.productId !== productId));
        return;
      }
      setEntries(entries.map((e) => (e.productId === productId ? { ...e, qty: n } : e)));
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
