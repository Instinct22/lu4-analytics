import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMarketItems } from "../../api/market";

export interface MarketItemOption {
  id: string;
  display_name: string;
  record_count: number;
}

interface Props {
  selectedId: string | null;
  onSelect: (item: MarketItemOption) => void;
}

export default function ItemMarketSelect({ selectedId, onSelect }: Props) {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(search.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  const { data: topItems } = useQuery({
    queryKey: ["market-items", ""],
    queryFn: () => getMarketItems({ limit: 20 }),
  });

  const { data: searchItems, isFetching } = useQuery({
    queryKey: ["market-items", debounced],
    queryFn: () => getMarketItems({ q: debounced, limit: 20 }),
    enabled: debounced.length >= 2,
  });

  const items: MarketItemOption[] = useMemo(() => {
    const source = debounced.length >= 2 ? searchItems?.items : topItems?.items;
    return source ?? [];
  }, [debounced, searchItems, topItems]);

  const selectedItem = useMemo(() => {
    const pool = [...(topItems?.items ?? []), ...(searchItems?.items ?? [])];
    return pool.find((item: MarketItemOption) => item.id === selectedId) ?? null;
  }, [selectedId, topItems, searchItems]);

  return (
    <div className="space-y-3">
      <div className="relative">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Поиск предмета с рыночными данными..."
          className="input pr-10"
        />
        {isFetching && (
          <span className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin rounded-full border-2 border-zinc-600 border-t-amber-500" />
        )}
      </div>

      {selectedItem && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          <p className="text-xs uppercase tracking-wider text-amber-500/80">Выбранный предмет</p>
          <p className="mt-1 font-semibold text-zinc-100">{selectedItem.display_name}</p>
          <p className="mt-0.5 text-xs text-zinc-500">{selectedItem.record_count.toLocaleString("ru-RU")} записей</p>
        </div>
      )}

      <div className="max-h-56 overflow-y-auto rounded-xl border border-zinc-800/80 bg-zinc-950/40">
        {!items.length ? (
          <p className="px-4 py-6 text-center text-sm text-zinc-500">Предметы не найдены</p>
        ) : (
          <ul className="divide-y divide-zinc-800/60">
            {items.map((item) => {
              const active = item.id === selectedId;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item)}
                    className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors ${
                      active
                        ? "bg-amber-500/10 text-amber-100"
                        : "hover:bg-zinc-900/80 text-zinc-300"
                    }`}
                  >
                    <span className="truncate text-sm font-medium">{item.display_name}</span>
                    <span className="shrink-0 text-xs tabular-nums text-zinc-500">{item.record_count}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
