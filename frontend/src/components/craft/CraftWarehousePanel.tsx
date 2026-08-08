import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { syncTradingWarehouse } from "../../api/trading";
import {
  effectivePrice,
  formatPrice,
  itemInfo,
  warehouseTotalValue,
  type CraftCatalog,
  type CraftPricePeriod,
  type PriceInfo,
} from "../../lib/craftCalc";
import {
  setWarehouseWallet,
  warehouseAdena,
  warehouseMasterCoin,
} from "../../lib/craftWarehouseWallet";
import { formatGroupedInt, parseGroupedInt } from "../../lib/formatNumber";
import { GradePill, HaveInput, ItemIcon } from "./CraftCostBar";

interface Props {
  catalog: CraftCatalog;
  owned: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  onOwnedReplace?: (next: Record<string, number>) => void;
  prices?: Record<string, PriceInfo>;
  manual?: Record<string, number>;
  showPrices?: boolean;
  period?: CraftPricePeriod;
  /** Bank ↔ warehouse sync (requires trading_write + craft_warehouse). */
  canSyncBank?: boolean;
}

function parseNonNegInt(raw: string): number {
  const digits = parseGroupedInt(raw);
  if (!digits) return 0;
  return Math.max(0, Number(digits) || 0);
}

export default function CraftWarehousePanel({
  catalog,
  owned,
  onOwnedChange,
  onOwnedReplace,
  prices = {},
  manual = {},
  showPrices = false,
  period = "main",
  canSyncBank = false,
}: Props) {
  const [search, setSearch] = useState("");
  const [syncError, setSyncError] = useState("");
  const [syncHint, setSyncHint] = useState("");

  const adena = warehouseAdena(owned);
  const masterCoin = warehouseMasterCoin(owned);

  const warehouseEntries = useMemo(() => {
    return Object.entries(owned)
      .map(([id, qty]) => ({ id: Number(id), qty: Math.floor(Number(qty)) }))
      .filter((e) => Number.isFinite(e.id) && e.id > 0 && e.qty > 0)
      .sort((a, b) => itemInfo(catalog, a.id).name.localeCompare(itemInfo(catalog, b.id).name));
  }, [owned, catalog]);

  const warehouseValue = useMemo(
    () => warehouseTotalValue(catalog, owned, prices, manual, period),
    [catalog, owned, prices, manual, period],
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

  const updateWallet = (nextAdena: number, nextMaster: number) => {
    if (!onOwnedReplace) return;
    onOwnedReplace(setWarehouseWallet(owned, nextAdena, nextMaster));
  };

  const syncMut = useMutation({
    mutationFn: () => syncTradingWarehouse("to_bank"),
    onSuccess: (result) => {
      setSyncError("");
      setSyncHint(
        `Main (${result.character_nick}) обновлён: ${result.item_count} поз., ` +
          `${Math.round(Number(result.adena) || 0)} а, ${Math.round(Number(result.master_coin) || 0)} MC`,
      );
    },
    onError: (err: unknown) => {
      setSyncHint("");
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setSyncError(
        typeof detail === "string"
          ? detail
          : "Не удалось синхронизировать с банком. Проверьте Main.",
      );
    },
  });

  return (
    <div className="panel flex h-full flex-col overflow-hidden p-4">
      <div className="mb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-zinc-50">Склад ресурсов</h2>
            <p className="mt-1 text-sm text-zinc-500">
              {warehouseEntries.length} позиций · синхронизируется с калькулятором крафта
            </p>
          </div>
          {canSyncBank ? (
            <button
              type="button"
              className="btn-ghost shrink-0"
              disabled={syncMut.isPending}
              title="Записать склад в персонажа Main в Банке"
              onClick={() => {
                if (
                  !window.confirm(
                    "Заменить инвентарь Main в Банке предметами, аденой и Master Coin со склада?",
                  )
                ) {
                  return;
                }
                setSyncError("");
                setSyncHint("");
                syncMut.mutate();
              }}
            >
              {syncMut.isPending ? "Синхронизация…" : "Синхронизировать с банком"}
            </button>
          ) : null}
        </div>
        {syncError ? <p className="mt-2 text-sm text-rose-400">{syncError}</p> : null}
        {syncHint ? <p className="mt-2 text-sm text-emerald-400">{syncHint}</p> : null}
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
        {onOwnedReplace ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-zinc-500">Адена</span>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                spellCheck={false}
                className="input tabular-nums"
                value={formatGroupedInt(adena)}
                onChange={(e) => updateWallet(parseNonNegInt(e.target.value), masterCoin)}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-zinc-500">Master Coin</span>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                spellCheck={false}
                className="input tabular-nums"
                value={formatGroupedInt(masterCoin)}
                onChange={(e) => updateWallet(adena, parseNonNegInt(e.target.value))}
              />
            </label>
          </div>
        ) : null}
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
            const unitPrice = effectivePrice(entry.id, prices, manual, catalog, period);
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
