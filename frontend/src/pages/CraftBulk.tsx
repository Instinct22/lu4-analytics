import { useMemo, useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CraftBulkCartList from "../components/craft/CraftBulkCartList";
import CraftCartWidget from "../components/craft/CraftCartWidget";
import CraftShoppingList from "../components/craft/CraftShoppingList";
import CraftWarehousePanel from "../components/craft/CraftWarehousePanel";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import SplitPane from "../components/ui/SplitPane";
import { useAuth } from "../hooks/useAuth";
import { useCraftBulkCatalog } from "../hooks/useCraftBulkCatalog";
import { useCraftCart } from "../hooks/useCraftCart";
import { useCraftCatalog } from "../hooks/useCraftCatalog";
import { useCraftPrices } from "../hooks/useCraftPrices";
import { usePreference } from "../hooks/usePreferences";
import {
  applyWarehouseConsumption,
  buildMultiCraftRollup,
  computeWarehouseConsumption,
  CRAFT_PRICE_PERIODS,
  type CraftPricePeriod,
} from "../lib/craftCalc";

function collectRollupIds(rollup: { id: number }[], into: Set<number>) {
  for (const e of rollup) into.add(e.id);
}

type BulkTab = "warehouse" | "crafts" | "shopping";

export default function CraftBulkPage() {
  const { hasPermission } = useAuth();
  const canSeePrices = hasPermission("feature.craft_prices");
  const canBulk = hasPermission("feature.craft_bulk");
  const canWarehouse = hasPermission("feature.craft_warehouse");
  const warehouseOnly = canWarehouse && !canBulk;
  const { data: baseCatalog, isLoading, error } = useCraftCatalog();
  const { entries, remove, setQty, isEmpty } = useCraftCart();
  const [searchParams] = useSearchParams();
  const [owned, setOwned] = usePreference("craft_owned");
  const canSyncBank = canWarehouse && hasPermission("feature.trading_write");
  const [chosenVariants] = usePreference("craft_variants");
  const [pricePeriod, setPricePeriod] = useState<CraftPricePeriod>("main");
  const tabParam = searchParams.get("tab");

  const resolveTab = useCallback((): BulkTab => {
    if (tabParam === "warehouse" && canWarehouse) return "warehouse";
    if (tabParam === "crafts" && canBulk) return "crafts";
    if (tabParam === "shopping" && canBulk) return "shopping";
    return canBulk ? "crafts" : "warehouse";
  }, [tabParam, canWarehouse, canBulk]);

  const [tab, setTab] = useState<BulkTab>(resolveTab);

  useEffect(() => {
    setTab(resolveTab());
  }, [resolveTab]);

  const productIds = useMemo(() => (canBulk ? entries.map((e) => e.productId) : []), [canBulk, entries]);
  const { catalog: bulkCatalog, isLoading: recipesLoading } = useCraftBulkCatalog(
    baseCatalog,
    productIds,
  );

  const rollup = useMemo(() => {
    if (!canBulk || !bulkCatalog || isEmpty) return [];
    return buildMultiCraftRollup(bulkCatalog, entries, owned, chosenVariants);
  }, [canBulk, bulkCatalog, entries, owned, chosenVariants, isEmpty]);

  const missingCount = useMemo(() => rollup.filter((e) => e.still > 0).length, [rollup]);

  const allMaterialIds = useMemo(() => {
    const ids = new Set<number>();
    if (canBulk && bulkCatalog && !isEmpty) {
      collectRollupIds(rollup, ids);
      // Full mats ignoring warehouse — needed for craft-cost pricing.
      collectRollupIds(buildMultiCraftRollup(bulkCatalog, entries, {}, chosenVariants), ids);
      for (const e of entries) ids.add(e.productId);
    }
    for (const [k] of Object.entries(owned)) {
      const n = Number(k);
      if (Number.isFinite(n)) ids.add(n);
    }
    return [...ids];
  }, [canBulk, bulkCatalog, isEmpty, rollup, entries, owned, chosenVariants]);

  const { serverPrices, manual } = useCraftPrices(
    canSeePrices ? allMaterialIds : [],
    pricePeriod,
  );

  const onOwnedChange = (id: number, val: number) => {
    const next = { ...owned };
    const k = String(id);
    if (val <= 0) delete next[k];
    else next[k] = val;
    setOwned(next);
  };

  const handleCraft = useCallback(
    (productId: number, variantIdx: number) => {
      const cat = bulkCatalog ?? baseCatalog;
      if (!cat) return;
      const entry = entries.find(
        (e) => e.productId === productId && e.variantIdx === variantIdx,
      );
      if (!entry) return;
      const consumed = computeWarehouseConsumption(
        cat,
        productId,
        entry.qty,
        owned,
        variantIdx,
        chosenVariants,
      );
      if (!consumed) return;
      setOwned(applyWarehouseConsumption(owned, consumed));
      remove(productId, variantIdx);
    },
    [bulkCatalog, baseCatalog, entries, chosenVariants, owned, setOwned, remove],
  );

  if (isLoading) return <LoadingState />;
  if (error || !baseCatalog) {
    return (
      <ErrorState message="Каталог крафта не загружен. Запустите import_datasets.py items_encyclopedia" />
    );
  }

  if (warehouseOnly) {
    return (
      <div className="min-h-full">
        <PageHeader title="Склад ресурсов" />
        {canSeePrices && (
          <div className="mb-4 flex flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1">
            {CRAFT_PRICE_PERIODS.map((p) => (
              <button
                key={p.key}
                type="button"
                className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition-colors ${
                  pricePeriod === p.key
                    ? "bg-amber-600 text-zinc-950 shadow-sm"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
                onClick={() => setPricePeriod(p.key)}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
        <CraftWarehousePanel
          catalog={baseCatalog}
          owned={owned}
          onOwnedChange={onOwnedChange}
          onOwnedReplace={setOwned}
          prices={serverPrices}
          manual={manual}
          showPrices={canSeePrices}
          period={pricePeriod}
          canSyncBank={canSyncBank}
        />
      </div>
    );
  }

  const catalog = bulkCatalog ?? baseCatalog;
  const loadingRecipes = !isEmpty && recipesLoading;

  const periodChips = canSeePrices ? (
    <div className="mb-3 flex flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1">
      {CRAFT_PRICE_PERIODS.map((p) => (
        <button
          key={p.key}
          type="button"
          className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition-colors ${
            pricePeriod === p.key
              ? "bg-amber-600 text-zinc-950 shadow-sm"
              : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          }`}
          onClick={() => setPricePeriod(p.key)}
        >
          {p.label}
        </button>
      ))}
    </div>
  ) : null;

  const tabBtn = (id: BulkTab, label: string) => (
    <button
      type="button"
      className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
        tab === id
          ? "bg-amber-600 text-zinc-950 shadow-sm"
          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
      }`}
      onClick={() => setTab(id)}
    >
      {label}
    </button>
  );

  const shoppingSection = (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
      {loadingRecipes ? (
        <LoadingState />
      ) : isEmpty ? (
        <p className="py-6 text-center text-sm text-zinc-500">
          Добавьте крафты в корзину на{" "}
          <Link to="/craft" className="font-medium text-amber-400 hover:underline">
            странице крафта
          </Link>
        </p>
      ) : (
        <>
          <div className="mb-3 rounded-lg border border-zinc-800/80 bg-zinc-950/40 px-3 py-2 text-sm">
            {missingCount === 0 ? (
              <span className="text-emerald-400">Все материалы есть на складе</span>
            ) : (
              <span className="text-amber-300">
                Не хватает материалов: <strong>{missingCount}</strong>
              </span>
            )}
          </div>
          {periodChips}
          <CraftShoppingList
            catalog={catalog}
            entries={rollup}
            owned={owned}
            prices={serverPrices}
            manual={manual}
            onOwnedChange={onOwnedChange}
            showPrices={canSeePrices}
            period={pricePeriod}
            title="Общий список покупок"
            subtitle="Материалы для всех крафтов в корзине с учётом склада"
          />
        </>
      )}
    </div>
  );

  const craftsSection = (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
      {periodChips}
      <CraftBulkCartList
        catalog={catalog}
        entries={entries}
        owned={owned}
        chosenVariants={chosenVariants}
        prices={serverPrices}
        manual={manual}
        onOwnedChange={onOwnedChange}
        onQtyChange={setQty}
        onRemove={remove}
        onCraft={handleCraft}
        showPrices={canSeePrices}
        showApproxCost
        period={pricePeriod}
        recipesLoading={loadingRecipes}
      />
    </div>
  );

  return (
    <div className="min-h-full">
      <PageHeader title="Массовый крафт">
        <CraftCartWidget catalog={catalog} />
      </PageHeader>

      <div className="mb-4 flex gap-1 rounded-xl bg-zinc-800/80 p-1 lg:hidden">
        {canWarehouse && tabBtn("warehouse", "Склад")}
        {canBulk && tabBtn("crafts", "Крафты")}
        {canBulk && tabBtn("shopping", "Покупки")}
      </div>

      <div className="lg:hidden">
        {canWarehouse && tab === "warehouse" && (
          <>
            {periodChips}
            <CraftWarehousePanel
              catalog={catalog}
              owned={owned}
              onOwnedChange={onOwnedChange}
              onOwnedReplace={setOwned}
              prices={serverPrices}
              manual={manual}
              showPrices={canSeePrices}
              period={pricePeriod}
              canSyncBank={canSyncBank}
            />
          </>
        )}
        {canBulk && tab === "crafts" && craftsSection}
        {canBulk && tab === "shopping" && shoppingSection}
      </div>

      <div className="hidden lg:block">
        {canWarehouse ? (
          <SplitPane
            storageKey="lu4_bulk_craft_ratio"
            defaultRatio={38}
            left={
              <CraftWarehousePanel
                catalog={catalog}
                owned={owned}
                onOwnedChange={onOwnedChange}
                onOwnedReplace={setOwned}
                prices={serverPrices}
                manual={manual}
                showPrices={canSeePrices}
                period={pricePeriod}
                canSyncBank={canSyncBank}
              />
            }
            right={
              <div className="flex flex-col gap-4">
                {craftsSection}
                {shoppingSection}
              </div>
            }
          />
        ) : (
          <div className="flex flex-col gap-4">
            {craftsSection}
            {shoppingSection}
          </div>
        )}
      </div>
    </div>
  );
}
