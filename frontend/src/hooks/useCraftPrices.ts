import { useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPricesByIds } from "../api/market";
import { usePreference } from "./usePreferences";
import { type PriceInfo } from "../lib/craftCalc";

export function useCraftPrices(itemIds: number[]) {
  const unique = useMemo(
    () => [...new Set(itemIds.filter((id) => id > 0))].sort((a, b) => a - b),
    [itemIds],
  );

  const idsKey = unique.join(",");

  const { data: serverPrices = {}, isLoading } = useQuery({
    queryKey: ["craft-prices", idsKey],
    queryFn: async () => {
      if (unique.length === 0) return {} as Record<string, PriceInfo>;
      return (await getPricesByIds(unique.join(","))) as Record<string, PriceInfo>;
    },
    enabled: unique.length > 0,
    staleTime: 1000 * 60 * 5,
  });

  const [manual, setManual] = usePreference("craft_prices");

  const setManualPrice = useCallback(
    (id: number, val: number | null) => {
      const next = { ...manual };
      const k = String(id);
      if (val == null || val <= 0) delete next[k];
      else next[k] = val;
      setManual(next);
    },
    [manual, setManual],
  );

  return { serverPrices, manual, setManualPrice, isLoading };
}
