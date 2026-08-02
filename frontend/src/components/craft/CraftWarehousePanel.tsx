import { useMemo, useState } from "react";
import {
  effectivePrice,
  formatPrice,
  itemInfo,
  warehouseTotalValue,
  type CraftCatalog,
  type PriceInfo,
} from "../../lib/craftCalc";
import { GradePill, HaveInput, ItemIcon } from "./CraftCostBar";

interface Props {
  catalog: CraftCatalog;
  owned: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  prices?: Record<string, PriceInfo>;
  manual?: Record<string, number>;
  showPrices?: boolean;
}

export default function CraftWarehousePanel({
  catalog,
  owned,
  onOwnedChange,
  prices = {},
  manual = {},
  showPrices = false,
}: Props) {
  const [search, setSearch] = useState("");

  const warehouseEntries = useMemo(() => {
    return Object.entries(owned)
      .map(([id, qty]) => ({ id: Number(id), qty: Math.floor(Number(qty)) }))
      .filter((e) => Number.isFinite(e.id) && e.id > 0 && e.qty > 0)
      .sort((a, b) => itemInfo(catalog, a.id).name.localeCompare(itemInfo(catalog, b.id).name));
  }, [owned, catalog]);

  const warehouseValue = useMemo(
    () => warehouseTotalValue(catalog, owned, prices, manual),
    [catalog, owned, prices, manual],
  );

  const searchResults = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    const ownedIds = new Set(warehouseEntries.map((e) => e.id));
    return Object.values(catalog.items)
      .filter((item) => {
        if (ownedIds.has(item.id)) return false;
        const hay = `${item.name} ${item.id}`.toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 12);
  }, [search, catalog.items, warehouseEntries]);

  const addMaterial = (id: number) => {
    onOwnedChange(id, (owned[String(id)] ?? 0) + 1);
    setSearch("");
  };

  const removeMaterial = (id: number) => {
    onOwnedChange(id, 0);
  };

  return (
    <div className="panel flex h-full flex-col overflow-hidden p-4">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-zinc-50">Склад ресурсов</h2>
        <p className="mt-1 text-sm text-zinc-500">
          {warehouseEntries.length} позиций · синхронизируется с калькулятором крафта
        </p>
        <div className="mt-2 rounded-xl border border-zinc-800/80 bg-zinc-900/50 px-3 py-2">
          <span className="text-[0.65rem] font-medium uppercase tracking-wide text-zinc-600">
            Стоимость склада
          </span>
          <p className="text-lg font-bold tabular-nums text-amber-400">
            {showPrices && warehouseValue.total != null ? formatPrice(warehouseValue.total) : "—"}
            {showPrices && warehouseValue.partial && warehouseValue.total != null && (
              <span className="ml-2 text-xs font-normal text-zinc-500">частично</span>
            )}
          </p>
        </div>
      </div>

      <input
        type="search"
        placeholder="Добавить ресурс..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="input mb-3"
      />

      {searchResults.length > 0 && (
        <div className="mb-3 max-h-40 overflow-y-auto rounded-xl border border-zinc-800/80 bg-zinc-900/50 p-1">
          {searchResults.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => addMaterial(item.id)}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-zinc-800/60"
            >
              <ItemIcon id={item.id} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm text-zinc-200">{item.name}</span>
              <GradePill grade={item.grade} />
            </button>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
        {warehouseEntries.length === 0 ? (
          <p className="rounded-xl border border-dashed border-zinc-700 px-4 py-8 text-center text-sm text-zinc-500">
            Склад пуст. Найдите материал через поиск выше или укажите «Есть» в калькуляторе крафта.
          </p>
        ) : (
          warehouseEntries.map((entry) => {
            const info = itemInfo(catalog, entry.id);
            const unitPrice = effectivePrice(entry.id, prices, manual, catalog);
            const lineTotal = unitPrice != null ? unitPrice * entry.qty : null;
            return (
              <div
                key={entry.id}
                className="flex items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/50 px-3 py-2.5"
              >
                <ItemIcon id={entry.id} size={36} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold text-zinc-100">{info.name}</span>
                    <GradePill grade={info.grade} />
                  </div>
                  {showPrices && lineTotal != null && (
                    <p className="text-xs tabular-nums text-zinc-500">{formatPrice(lineTotal)}</p>
                  )}
                </div>
                <HaveInput
                  value={entry.qty}
                  onChange={(v) => onOwnedChange(entry.id, v)}
                />
                <button
                  type="button"
                  aria-label="Удалить"
                  onClick={() => removeMaterial(entry.id)}
                  className="shrink-0 rounded-lg px-2 py-1 text-sm text-zinc-500 transition-colors hover:bg-red-950/40 hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
