import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CraftCalculator from "../components/craft/CraftCalculator";
import CraftCartWidget from "../components/craft/CraftCartWidget";
import CraftPicker from "../components/craft/CraftPicker";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useCraftCatalog, useCraftProduct } from "../hooks/useCraftCatalog";
import { isCraftable, itemInfo } from "../lib/craftCalc";

export default function CraftPage() {
  const { data: catalog, isLoading, error } = useCraftCatalog();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const paramId = useMemo(() => {
    const raw = searchParams.get("id");
    if (!raw) return null;
    const id = Number(raw);
    return Number.isFinite(id) ? id : null;
  }, [searchParams]);

  useEffect(() => {
    if (paramId != null) setSelectedId(paramId);
  }, [paramId]);

  const { catalog: productCatalog, isLoading: recipesLoading } = useCraftProduct(
    catalog,
    selectedId,
  );

  const select = (id: number) => {
    setSelectedId(id);
    setSearchParams({ id: String(id) }, { replace: true });
  };

  const close = () => {
    setSelectedId(null);
    setSearchParams({}, { replace: true });
  };

  if (isLoading) return <LoadingState />;
  if (error || !catalog) {
    return (
      <ErrorState message="Каталог крафта не загружен. Запустите import_datasets.py items_encyclopedia" />
    );
  }

  const craftable = selectedId != null && isCraftable(catalog, selectedId);
  const knownItem = selectedId != null && Boolean(catalog.items[String(selectedId)]);

  return (
    <div className="min-h-full">
      <PageHeader title="Крафт предметов">
        <CraftCartWidget catalog={catalog} />
      </PageHeader>

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <div
          className={`shrink-0 transition-all ${
            selectedId ? "xl:w-[22rem] 2xl:w-[26rem]" : "w-full"
          }`}
        >
          <CraftPicker
            catalog={catalog}
            onSelect={select}
            selectedId={selectedId}
            compact={!!selectedId}
          />
        </div>

        {selectedId != null && craftable ? (
          <div className="min-w-0 flex-1 xl:sticky xl:top-4">
            {recipesLoading || !productCatalog?.byProduct[String(selectedId)] ? (
              <LoadingState />
            ) : (
              <CraftCalculator
                key={selectedId}
                catalog={productCatalog}
                productId={selectedId}
                onClose={close}
              />
            )}
          </div>
        ) : selectedId != null ? (
          <div key={selectedId} className="panel min-w-0 flex-1 p-6 xl:sticky xl:top-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-zinc-50">
                  {knownItem ? itemInfo(catalog, selectedId).name : `Предмет #${selectedId}`}
                </h2>
                <p className="mt-2 text-sm text-zinc-400">
                  У этого оружия нет рецепта крафтера в каталоге. Его можно купить, добыть или
                  использовать как материал для дуала у кузнеца Pushkin.
                </p>
              </div>
              <button
                type="button"
                onClick={close}
                className="rounded-lg px-3 py-1.5 text-sm text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
              >
                ✕
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
