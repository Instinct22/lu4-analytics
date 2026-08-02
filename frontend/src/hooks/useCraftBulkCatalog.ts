import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { getRecipeClosure } from "../api/craft";
import type { CraftCatalog } from "../lib/craftCalc";

export function useCraftBulkCatalog(
  baseCatalog: CraftCatalog | undefined,
  productIds: number[],
) {
  const uniqueIds = useMemo(
    () => [...new Set(productIds.filter((id) => Number.isFinite(id) && id > 0))],
    [productIds],
  );

  const closures = useQueries({
    queries: uniqueIds.map((productId) => ({
      queryKey: ["craft", "recipes", productId],
      queryFn: () => getRecipeClosure(productId),
      enabled: productId > 0,
      staleTime: 1000 * 60 * 5,
    })),
  });

  const merged = useMemo<CraftCatalog | undefined>(() => {
    if (!baseCatalog) return undefined;
    let items = { ...baseCatalog.items };
    let byProduct = { ...(baseCatalog.byProduct ?? {}) };
    for (const q of closures) {
      if (!q.data) continue;
      items = { ...items, ...q.data.items };
      byProduct = { ...byProduct, ...(q.data.byProduct ?? {}) };
    }
    return { ...baseCatalog, items, byProduct };
  }, [baseCatalog, closures]);

  const isLoading = closures.some((q) => q.isLoading);
  const isError = closures.some((q) => q.isError);

  return { catalog: merged, isLoading, isError };
}
