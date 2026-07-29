import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCraftCatalog, getRecipeClosure } from "../api/craft";
import type { CraftCatalog } from "../lib/craftCalc";

/** Light catalog: all items and set/category trees, without recipe trees. */
export function useCraftCatalog() {
  return useQuery({
    queryKey: ["craft", "catalog"],
    queryFn: getCraftCatalog,
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * Catalog enriched with the recipe closure of one product, which is what the
 * calculator needs to walk nested materials.
 */
export function useCraftProduct(catalog: CraftCatalog | undefined, productId: number | null) {
  const closure = useQuery({
    queryKey: ["craft", "recipes", productId],
    queryFn: () => getRecipeClosure(productId!),
    enabled: productId != null,
    staleTime: 1000 * 60 * 5,
  });

  const merged = useMemo<CraftCatalog | undefined>(() => {
    if (!catalog) return undefined;
    if (!closure.data) return catalog;
    return {
      ...catalog,
      items: { ...catalog.items, ...closure.data.items },
      byProduct: { ...catalog.byProduct, ...closure.data.byProduct },
    };
  }, [catalog, closure.data]);

  return { catalog: merged, isLoading: closure.isLoading, isError: closure.isError };
}
