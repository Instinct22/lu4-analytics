import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ArmorSetDetailPanel from "../components/items/ArmorSetDetailPanel";
import ArmorSetsGrid from "../components/items/ArmorSetsGrid";
import ItemDetailPanel from "../components/items/ItemDetailPanel";
import ItemEncyclopediaPanel from "../components/items/ItemEncyclopediaPanel";
import ItemsGrid from "../components/items/ItemsGrid";
import ItemsToolbar from "../components/items/ItemsToolbar";
import OtherItemsGrid from "../components/items/OtherItemsGrid";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useItemDetail, useItemsBrowse, useItemsCatalog } from "../hooks/useItemEncyclopedia";
import {
  buildArmorSets,
  buildItemsGearList,
  DEFAULT_ITEMS_FILTER,
  DUAL_GEAR_CATEGORIES,
  facetAvailability,
  filterGear,
  filterSets,
  GRADE_ORDER,
  isDualGearCategory,
  type GearCategory,
  type ItemsFilterState,
  type ItemsTab,
} from "../lib/itemsCatalog";
import { filterOtherItems } from "../lib/itemEncyclopedia";
import type { ItemEncyclopediaEntry } from "../api/items";
import type { CraftCatalog } from "../lib/craftCalc";
import { isSafeReturnPath, returnLinkFromParam } from "../lib/internalNav";

export default function ItemsPage() {
  const navigate = useNavigate();
  const { data: browse, isLoading: browseLoading, error: browseError } = useItemsBrowse();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState<ItemsTab>("items");
  const [filter, setFilter] = useState<ItemsFilterState>(DEFAULT_ITEMS_FILTER);

  const { data: otherCatalog, isLoading: otherLoading } = useItemsCatalog("other", tab === "other");

  const catalog = browse?.craft as CraftCatalog | undefined;
  const dualsCatalog = browse?.duals ?? null;
  const gearCatalog = browse?.gear;

  const paramId = useMemo(() => {
    const raw = searchParams.get("id");
    if (!raw) return null;
    const id = Number(raw);
    return Number.isFinite(id) ? id : null;
  }, [searchParams]);

  const paramSet = searchParams.get("set");
  const returnPath = searchParams.get("from");
  const returnLink = useMemo(() => returnLinkFromParam(returnPath), [returnPath]);

  const gearList = useMemo(
    () =>
      catalog
        ? buildItemsGearList(catalog, dualsCatalog, gearCatalog?.items ?? null)
        : [],
    [catalog, dualsCatalog, gearCatalog],
  );
  const allSets = useMemo(() => (catalog ? buildArmorSets(catalog) : []), [catalog]);
  const craftableIds = useMemo(
    () => new Set(catalog?.craftableIds ?? Object.keys(catalog?.byProduct ?? {}).map(Number)),
    [catalog],
  );

  const otherItems = useMemo(() => {
    const raw = (otherCatalog?.items ?? []) as ItemEncyclopediaEntry[];
    return filterOtherItems(raw, filter.q, filter.grade, filter.sub);
  }, [otherCatalog, filter.q, filter.grade, filter.sub]);

  const otherSubcategories = useMemo(() => {
    const subs = new Set<string>();
    for (const it of otherCatalog?.items ?? []) {
      if (it.other_subcategory) subs.add(it.other_subcategory);
    }
    return [...subs].sort();
  }, [otherCatalog]);

  const available = useMemo(() => facetAvailability(gearList, filter), [gearList, filter]);
  const visibleItems = useMemo(() => filterGear(gearList, filter), [gearList, filter]);
  const visibleSets = useMemo(() => filterSets(allSets, filter), [allSets, filter]);

  const setGrades = useMemo(() => {
    const q = filter.q.trim().toLowerCase();
    const grades = new Set<string>();
    for (const s of allSets) {
      if (filter.hidePvpSets && s.pvp) continue;
      if (q && !s.name.toLowerCase().includes(q)) continue;
      if (s.grade !== "NG") grades.add(s.grade);
    }
    return GRADE_ORDER.filter((g) => g !== "NG" && grades.has(g));
  }, [allSets, filter.hidePvpSets, filter.q]);

  const selectedGear = useMemo(() => {
    if (paramId == null || tab === "other") return null;
    return gearList.find((g) => g.id === paramId) ?? null;
  }, [gearList, paramId, tab]);

  // Items outside the gear list — the "other" section plus variants merged out of
  // the catalog (unseal results, rare/PvP versions) — are fetched on demand so that
  // links inside a detail panel always resolve to a real page.
  const fallbackDetailId = paramId != null && selectedGear == null ? paramId : null;
  const { data: fallbackEntry, isLoading: fallbackLoading } = useItemDetail(fallbackDetailId);

  const selectedSet = useMemo(() => {
    if (!paramSet) return null;
    return allSets.find((s) => s.id === paramSet) ?? null;
  }, [allSets, paramSet]);

  useEffect(() => {
    if (paramSet) setTab("sets");
    else if (fallbackEntry?.section === "other") setTab("other");
    else if (paramId != null) setTab("items");
  }, [paramId, paramSet, fallbackEntry]);

  useEffect(() => {
    const rawCat = searchParams.get("cat");
    if (!rawCat) return;
    const allowed: GearCategory[] = ["weapon", "armor", "accessory", ...DUAL_GEAR_CATEGORIES];
    if (!allowed.includes(rawCat as GearCategory)) return;
    setFilter((prev) => ({
      ...prev,
      cat: rawCat as GearCategory,
      sub: null,
      slot: null,
    }));
    setTab("items");
  }, [searchParams]);

  const patchFilter = (patch: Partial<ItemsFilterState>) => {
    setFilter((prev) => ({ ...prev, ...patch }));
  };

  const selectItem = (id: number) => {
    const params: Record<string, string> = { id: String(id) };
    if (isSafeReturnPath(returnPath)) params.from = returnPath;
    setSearchParams(params, { replace: true });
  };

  const selectSet = (id: string) => {
    const params: Record<string, string> = { set: id };
    if (isSafeReturnPath(returnPath)) params.from = returnPath;
    setSearchParams(params, { replace: true });
  };

  const closeDetail = () => {
    if (returnLink) {
      navigate(returnLink.href);
      return;
    }
    setSearchParams({}, { replace: true });
  };

  const onTabChange = (next: ItemsTab) => {
    setTab(next);
    setFilter((prev) => ({
      ...prev,
      q: "",
      grade: null,
      sub: null,
      slot: null,
      cat: "all",
    }));
    setSearchParams({}, { replace: true });
  };

  if (browseLoading) return <LoadingState />;
  if (browseError || !catalog) {
    return (
      <ErrorState message="Каталог предметов не загружен. Запустите finalize_encyclopedia.py и import_datasets.py items_encyclopedia" />
    );
  }

  const detailOpen =
    selectedGear != null || selectedSet != null || fallbackEntry != null || fallbackLoading;
  const countLabel =
    tab === "items"
      ? `${visibleItems.length} из ${gearList.length} предметов`
      : tab === "sets"
        ? `${visibleSets.length} из ${allSets.filter((s) => !(filter.hidePvpSets && s.pvp)).length} сетов`
        : `${otherItems.length} из ${otherCatalog?.items?.length ?? 0} предметов`;

  return (
    <div className="min-h-full">
      <PageHeader title="Предметы">
        <p className="text-sm text-zinc-500">
          Энциклопедия экипировки, материалов и расходников · связь с крафтом
          {!dualsCatalog ? " · каталог дуалов недоступен" : ""}
        </p>
      </PageHeader>

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <div
          className={`shrink-0 transition-all ${
            detailOpen ? "xl:w-[30rem] 2xl:w-[36rem]" : "w-full"
          }`}
        >
          <ItemsToolbar
            tab={tab}
            filter={filter}
            available={available}
            setGrades={setGrades}
            otherSubcategories={otherSubcategories}
            onTabChange={onTabChange}
            onFilterChange={patchFilter}
            countLabel={countLabel}
          >
            {tab === "items" ? (
              <ItemsGrid
                items={visibleItems}
                selectedId={paramId}
                craftableIds={craftableIds}
                onSelect={selectItem}
                compact={detailOpen}
              />
            ) : tab === "sets" ? (
              <ArmorSetsGrid
                sets={visibleSets}
                selectedId={paramSet}
                onSelect={selectSet}
                compact={detailOpen}
              />
            ) : otherLoading ? (
              <LoadingState />
            ) : (
              <OtherItemsGrid
                items={otherItems}
                selectedId={paramId}
                onSelect={selectItem}
                compact={detailOpen}
              />
            )}
          </ItemsToolbar>
        </div>

        {selectedGear ? (
          <div className="min-w-0 flex-1 xl:sticky xl:top-4">
            <ItemDetailPanel
              key={selectedGear.id}
              catalog={catalog}
              dualsCatalog={dualsCatalog}
              item={selectedGear}
              sets={allSets}
              onClose={closeDetail}
              onOpenSet={selectSet}
              returnLink={returnLink}
              returnPath={returnPath}
            />
          </div>
        ) : fallbackEntry ? (
          <div className="min-w-0 flex-1 xl:sticky xl:top-4">
            <ItemEncyclopediaPanel
              key={fallbackEntry.id}
              entry={fallbackEntry}
              onClose={closeDetail}
              craftLink={fallbackEntry.craft?.craftable ? `/craft?id=${fallbackEntry.id}` : null}
              returnLink={returnLink}
              returnPath={returnPath}
            />
          </div>
        ) : fallbackLoading ? (
          <div className="min-w-0 flex-1 xl:sticky xl:top-4">
            <LoadingState />
          </div>
        ) : selectedSet ? (
          <div className="min-w-0 flex-1 xl:sticky xl:top-4">
            <ArmorSetDetailPanel
              key={selectedSet.id}
              catalog={catalog}
              set={selectedSet}
              onClose={closeDetail}
              onSelectItem={selectItem}
            />
          </div>
        ) : (
          <div className="panel hidden flex-1 items-center justify-center border-dashed p-12 xl:flex">
            <div className="max-w-sm text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/80 ring-1 ring-zinc-700/80">
                <span className="text-2xl text-amber-500">▣</span>
              </div>
              <p className="text-lg font-medium text-zinc-300">
                {tab === "sets" ? "Выберите сет" : "Выберите предмет"}
              </p>
              <p className="mt-2 text-sm text-zinc-500">
                Полная энциклопедия: статы, дроп, спойл, заточка, крафт
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
