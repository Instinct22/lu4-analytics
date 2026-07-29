import { useQuery } from "@tanstack/react-query";
import {
  getCraftItemDetail,
  getItemDetail,
  getItemSources,
  getItemsBrowse,
  getItemsCatalog,
} from "../api/items";

export function useItemsBrowse() {
  return useQuery({
    queryKey: ["items-browse"],
    queryFn: getItemsBrowse,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useItemsCatalog(section?: "gear" | "other", enabled = true) {
  return useQuery({
    queryKey: ["items-catalog", section ?? "all"],
    queryFn: () => getItemsCatalog(section),
    staleTime: 5 * 60_000,
    retry: false,
    enabled,
  });
}

export function useItemDetail(itemId: number | null) {
  return useQuery({
    queryKey: ["item-detail", itemId],
    queryFn: async () => {
      try {
        return await getItemDetail(itemId!);
      } catch {
        return await getCraftItemDetail(itemId!);
      }
    },
    enabled: itemId != null,
    staleTime: 5 * 60_000,
  });
}

export function useItemSources(itemId: number | null, enabled = true) {
  return useQuery({
    queryKey: ["item-sources", itemId],
    queryFn: () => getItemSources(itemId!),
    enabled: itemId != null && enabled,
    staleTime: 5 * 60_000,
  });
}
