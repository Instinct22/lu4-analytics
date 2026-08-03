import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCraftResources } from "../../api/craft";
import { getMarketItems } from "../../api/market";
import { MASTER_COIN_EXTERNAL_ID, withMasterCoin } from "../../lib/craftResources";

export interface MarketItemOption {
  id: string;
  external_id?: number | null;
  display_name: string;
  record_count: number;
}

interface Props {
  selectedId: string | null;
  onSelect: (item: MarketItemOption) => void;
}

export default function ItemMarketSelect({ selectedId, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const { data: marketData, isFetching } = useQuery({
    queryKey: ["market-items", "all"],
    queryFn: () => getMarketItems({ limit: 2000 }),
  });

  const { data: resourcesData } = useQuery({
    queryKey: ["craft-resources"],
    queryFn: getCraftResources,
  });

  const resourceIds = useMemo(() => {
    const ids = withMasterCoin(resourcesData?.materials ?? []).map((m) => m.id);
    ids.push(MASTER_COIN_EXTERNAL_ID);
    return new Set(ids);
  }, [resourcesData?.materials]);

  const items: MarketItemOption[] = marketData?.items ?? [];

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const { resources, others } = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? items.filter(
          (item) =>
            item.display_name.toLowerCase().includes(q) ||
            (item.external_id != null && String(item.external_id).includes(q)),
        )
      : items;

    const res: MarketItemOption[] = [];
    const rest: MarketItemOption[] = [];
    for (const item of filtered) {
      if (item.external_id != null && resourceIds.has(item.external_id)) res.push(item);
      else rest.push(item);
    }
    res.sort((a, b) => a.display_name.localeCompare(b.display_name, "ru"));
    rest.sort((a, b) => a.display_name.localeCompare(b.display_name, "ru"));
    return { resources: res, others: rest };
  }, [items, resourceIds, search]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pick = (item: MarketItemOption) => {
    onSelect(item);
    setOpen(false);
    setSearch("");
  };

  return (
    <div ref={rootRef} className={`relative min-w-0 flex-1 ${open ? "z-50" : "z-10"}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="input flex w-full items-center justify-between gap-2 text-left"
      >
        <span className={`truncate text-sm ${selectedItem ? "text-zinc-100" : "text-zinc-500"}`}>
          {selectedItem ? selectedItem.display_name : "Выберите предмет…"}
        </span>
        <span className="shrink-0 text-zinc-500">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div className="absolute left-0 right-0 z-50 mt-1 overflow-hidden rounded-xl border border-zinc-700/80 bg-zinc-950 shadow-xl">
          <div className="border-b border-zinc-800/80 p-2">
            <input
              autoFocus
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск…"
              className="input"
            />
          </div>
          <div className="max-h-72 overflow-y-auto" role="listbox">
            {isFetching && !items.length ? (
              <p className="px-3 py-4 text-center text-sm text-zinc-500">Загрузка…</p>
            ) : !resources.length && !others.length ? (
              <p className="px-3 py-4 text-center text-sm text-zinc-500">Предметы не найдены</p>
            ) : (
              <>
                {resources.length > 0 && (
                  <Section
                    title="Ресурсы"
                    items={resources}
                    selectedId={selectedId}
                    onPick={pick}
                  />
                )}
                {others.length > 0 && (
                  <Section
                    title="Предметы"
                    items={others}
                    selectedId={selectedId}
                    onPick={pick}
                  />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  items,
  selectedId,
  onPick,
}: {
  title: string;
  items: MarketItemOption[];
  selectedId: string | null;
  onPick: (item: MarketItemOption) => void;
}) {
  return (
    <div>
      <div className="sticky top-0 bg-zinc-900/95 px-3 py-1.5 text-[0.65rem] font-semibold uppercase tracking-wider text-zinc-500 backdrop-blur">
        {title}
      </div>
      <ul className="divide-y divide-zinc-800/60">
        {items.map((item) => {
          const active = item.id === selectedId;
          return (
            <li key={item.id}>
              <button
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => onPick(item)}
                className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left transition-colors ${
                  active
                    ? "bg-amber-500/10 text-amber-100"
                    : "text-zinc-300 hover:bg-zinc-900/80"
                }`}
              >
                <span className="truncate text-sm font-medium">{item.display_name}</span>
                <span className="shrink-0 text-xs tabular-nums text-zinc-500">
                  {item.record_count}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
