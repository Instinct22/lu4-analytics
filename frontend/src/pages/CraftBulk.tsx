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
import { buildMultiCraftRollup, applyWarehouseConsumption, computeWarehouseConsumption } from "../lib/craftCalc";

type BulkTab = "warehouse" | "crafts" | "shopping";

export default function CraftBulkPage() {
  const { hasPermission } = useAuth();
  const canSeePrices = hasPermission("feature.craft_prices");
  const { data: baseCatalog, isLoading, error } = useCraftCatalog();
  const { entries, remove, setQty, isEmpty } = useCraftCart();
  const [searchParams] = useSearchParams();
  const [owned, setOwned] = usePreference("craft_owned");
  const [chosenVariants] = usePreference("craft_variants");
  const tabParam = searchParams.get("tab");
  const [tab, setTab] = useState<BulkTab>(() =>
    tabParam === "warehouse" || tabParam === "crafts" || tabParam === "shopping" ? tabParam : "crafts",
  );

  useEffect(() => {
    if (tabParam === "warehouse" || tabParam === "crafts" || tabParam === "shopping") {
      setTab(tabParam);
    }
  }, [tabParam]);

  const productIds = useMemo(() => entries.map((e) => e.productId), [entries]);
  const { catalog: bulkCatalog, isLoading: recipesLoading } = useCraftBulkCatalog(
    baseCatalog,
    productIds,
  );

  const rollup = useMemo(() => {
    if (!bulkCatalog || isEmpty) return [];
    return buildMultiCraftRollup(bulkCatalog, entries, owned, chosenVariants);
  }, [bulkCatalog, entries, owned, chosenVariants, isEmpty]);

  const missingCount = useMemo(() => rollup.filter((e) => e.still > 0).length, [rollup]);

  const allMaterialIds = useMemo(() => {
    const ids = new Set<number>();
    for (const e of rollup) ids.add(e.id);
    for (const [k] of Object.entries(owned)) {
      const n = Number(k);
      if (Number.isFinite(n)) ids.add(n);
    }
    return [...ids];
  }, [rollup, owned]);

  const { serverPrices, manual } = useCraftPrices(allMaterialIds);

  const onOwnedChange = (id: number, val: number) => {
    const next = { ...owned };
    const k = String(id);
    if (val <= 0) delete next[k];
    else next[k] = val;
    setOwned(next);
  };

  const handleCraft = useCallback(
    (productId: number) => {
      const cat = bulkCatalog ?? baseCatalog;
      if (!cat) return;
      const entry = entries.find((e) => e.productId === productId);
      if (!entry) return;
      const variantIdx = entry.variantIdx ?? chosenVariants[String(productId)] ?? 0;
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
      remove(productId);
    },
    [bulkCatalog, baseCatalog, entries, chosenVariants, owned, setOwned, remove],
  );

  if (isLoading) return <LoadingState />;
  if (error || !baseCatalog) {
    return (
      <ErrorState message="Каталог крафта не загружен. Запустите import_datasets.py items_encyclopedia" />
    );
  }

  const catalog = bulkCatalog ?? baseCatalog;
  const loadingRecipes = !isEmpty && recipesLoading;

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
          <CraftShoppingList
            catalog={catalog}
            entries={rollup}
            owned={owned}
            prices={serverPrices}
            manual={manual}
            onOwnedChange={onOwnedChange}
            showPrices={canSeePrices}
            title="Общий список покупок"
            subtitle="Материалы для всех крафтов в корзине с учётом склада"
          />
        </>
      )}
    </div>
  );

  const craftsSection = (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
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
        {tabBtn("warehouse", "Склад")}
        {tabBtn("crafts", "Крафты")}
        {tabBtn("shopping", "Покупки")}
      </div>

      <div className="lg:hidden">
        {tab === "warehouse" && (
          <CraftWarehousePanel
            catalog={catalog}
            owned={owned}
            onOwnedChange={onOwnedChange}
            prices={serverPrices}
            manual={manual}
          />
        )}
        {tab === "crafts" && craftsSection}
        {tab === "shopping" && shoppingSection}
      </div>

      <div className="hidden lg:block">
        <SplitPane
          storageKey="lu4_bulk_craft_ratio"
          defaultRatio={38}
          left={
            <CraftWarehousePanel
              catalog={catalog}
              owned={owned}
              onOwnedChange={onOwnedChange}
              prices={serverPrices}
              manual={manual}
            />
          }
          right={
            <div className="flex flex-col gap-4">
              {craftsSection}
              {shoppingSection}
            </div>
          }
        />
      </div>
    </div>
  );
}
