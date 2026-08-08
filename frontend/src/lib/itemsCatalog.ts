import type { ItemCatalogEntry, ItemEncyclopediaEntry } from "../api/items";
import {
  formatStat,
  isCraftable,
  itemInfo,
  type CatalogItem,
  type CraftCatalog,
  type ItemCombatStats,
} from "./craftCalc";
import { itemPagePath, setPagePath } from "./internalNav";
import { masterworkSetUrl } from "./itemEncyclopedia";
import { wikiItemUrl as masterworkItemUrlByName } from "./characterData";
import {
  allDualIds,
  allDualProductIds,
  dualItemInfo,
  dualTypeIconUrl,
  DUAL_TYPE_LABELS,
  type DualsCatalog,
  type DualType,
} from "./dualsCatalog";

const DUAL_GEAR_CATEGORY: Record<DualType, GearCategory> = {
  swords: "dual_swords",
  daggers: "dual_daggers",
  blunts: "dual_blunts",
};

export const GRADE_ORDER = ["S", "A", "B", "C", "D", "NG"] as const;

export type GearCategory =
  | "weapon"
  | "armor"
  | "accessory"
  | "dual_swords"
  | "dual_daggers"
  | "dual_blunts";

export const DUAL_GEAR_CATEGORIES: GearCategory[] = [
  "dual_swords",
  "dual_daggers",
  "dual_blunts",
];

export function isDualGearCategory(cat: GearCategory | "all"): boolean {
  return cat === "dual_swords" || cat === "dual_daggers" || cat === "dual_blunts";
}
export type ItemsTab = "items" | "sets" | "other";
export type ItemsSort = "grade" | "name" | "stat" | "price";

export interface GearFacet {
  cat: GearCategory;
  sub: string | null;
  slot: string | null;
}

export interface GearItem extends CatalogItem {
  facet: GearFacet;
  mainStat: { key: string; label: string; val: number | null };
  isDual?: boolean;
  dualType?: "swords" | "daggers" | "blunts";
  iconSrc?: string | null;
}

export interface ArmorSetSummary {
  id: string;
  name: string;
  grade: string;
  memberIds: number[];
  craftableMemberIds: number[];
  memberNames: Record<string, string>;
  iconId: number | null;
  iconSrc: string | null;
  pvp: boolean;
  canonical: boolean;
  effect: string[];
  setPagePath: string;
  setSlug?: string | null;
  setWikiId?: number | null;
  masterworkSetUrl?: string | null;
}

export const CAT_LABELS: Record<GearCategory | "all", string> = {
  all: "Все",
  weapon: "Оружие",
  armor: "Броня",
  accessory: "Аксессуары",
  dual_swords: DUAL_TYPE_LABELS.swords,
  dual_daggers: DUAL_TYPE_LABELS.daggers,
  dual_blunts: DUAL_TYPE_LABELS.blunts,
};

export const SORT_LABELS: Record<ItemsSort, string> = {
  grade: "Грейд",
  name: "Название",
  stat: "Основной стат",
  price: "Цена NPC",
};

const STAT_LABELS: Record<keyof ItemCombatStats, string> = {
  p_atk: "Физ. атака",
  m_atk: "Маг. атака",
  crystals: "Кристаллизация",
  p_def: "Физ. защита",
  m_def: "Маг. защита",
  shield_def: "Защита щита",
};

export function parseGearFacet(type: string): GearFacet | null {
  const parts = type.split(" / ").map((p) => p.trim()).filter(Boolean);
  if (parts.length === 0) return null;
  const head = parts[0].toLowerCase();
  if (head === "weapon") {
    return { cat: "weapon", sub: parts[1] ?? null, slot: parts[2] ?? null };
  }
  if (head === "armor") {
    const sub = parts[1] && parts[1] !== "None" ? parts[1] : null;
    return { cat: "armor", sub, slot: parts[2] ?? null };
  }
  if (head === "accessory") {
    return { cat: "accessory", sub: parts[1] ?? null, slot: null };
  }
  return null;
}

function mainStatFor(item: CatalogItem, facet: GearFacet): GearItem["mainStat"] {
  const s = item.stats;
  if (facet.cat === "weapon") {
    const val = s?.p_atk ?? s?.m_atk ?? null;
    const key = s?.p_atk != null ? "p_atk" : "m_atk";
    return { key, label: STAT_LABELS[key as keyof ItemCombatStats], val };
  }
  if (facet.cat === "armor") {
    if (s?.shield_def != null) {
      return { key: "shield_def", label: STAT_LABELS.shield_def, val: s.shield_def };
    }
    const val = s?.p_def ?? s?.m_def ?? null;
    const key = s?.p_def != null ? "p_def" : "m_def";
    return { key, label: STAT_LABELS[key as keyof ItemCombatStats], val };
  }
  return {
    key: "m_def",
    label: STAT_LABELS.m_def,
    val: s?.m_def ?? s?.p_def ?? null,
  };
}

export function buildGearList(catalog: CraftCatalog): GearItem[] {
  const list: GearItem[] = [];
  for (const raw of Object.values(catalog.items)) {
    if (raw.is_recipe_scroll) continue;
    if ((raw.category || "").startsWith("other/") || (raw.category || "").startsWith("materials/")) {
      continue;
    }
    const facet = parseGearFacet(raw.type || "");
    if (!facet) continue;
    list.push({
      ...raw,
      facet,
      mainStat: mainStatFor(raw, facet),
    });
  }
  return list;
}

function catalogItemFromEntry(entry: ItemCatalogEntry, catalog: CraftCatalog): CatalogItem {
  const fromCraft = catalog.items[String(entry.id)];
  if (fromCraft) return fromCraft;
  return {
    id: entry.id,
    name: entry.name,
    grade: entry.grade,
    type: entry.type,
    category: entry.category || "",
    set_name: entry.set_name ?? null,
    npc_sell: entry.npc_sell ?? null,
    npc_buy: entry.npc_buy ?? null,
    url: "",
    is_recipe_scroll: false,
    icon: entry.icon ?? undefined,
    stats: (entry.stats as ItemCombatStats | null) ?? null,
    description: entry.effects ?? null,
  };
}

/** Gear tab: only encyclopedia `section=gear` items, enriched from craft catalog when present. */
export function buildGearListFromEncyclopedia(
  gearEntries: ItemCatalogEntry[],
  catalog: CraftCatalog,
): GearItem[] {
  const list: GearItem[] = [];
  for (const entry of gearEntries) {
    const raw = catalogItemFromEntry(entry, catalog);
    if (raw.is_recipe_scroll) continue;
    const facet = parseGearFacet(raw.type || entry.type || "");
    if (!facet) continue;
    list.push({
      ...raw,
      facet,
      mainStat: mainStatFor(raw, facet),
      stats: raw.stats ?? (entry.stats as ItemCombatStats | undefined),
    });
  }
  return list;
}

function dualTypeForItem(item: CatalogItem & { dual_type?: DualType }): DualType | null {
  if (item.dual_type) return item.dual_type;
  const part = (item.category || "").split("/")[1];
  if (part === "swords" || part === "daggers" || part === "blunts") return part;
  const lower = (item.type || "").toLowerCase();
  if (lower.includes("dual dagger")) return "daggers";
  if (lower.includes("dual blunt") || lower.includes("dualblunt")) return "blunts";
  if (lower.includes("dualsword") || lower.includes("dual sword")) return "swords";
  return null;
}

export function buildDualGearList(catalog: DualsCatalog): GearItem[] {
  const list: GearItem[] = [];
  for (const id of allDualIds(catalog)) {
    const raw = dualItemInfo(catalog, id);
    const dualType = dualTypeForItem(raw);
    if (!dualType) continue;
    const gearCategory = DUAL_GEAR_CATEGORY[dualType];
    const facet: GearFacet = {
      cat: gearCategory,
      sub: DUAL_TYPE_LABELS[dualType],
      slot: "Two-handed",
    };
    list.push({
      ...raw,
      facet,
      mainStat: mainStatFor(raw, facet),
      isDual: true,
      dualType,
      iconSrc: dualTypeIconUrl(dualType),
    });
  }
  return list;
}

/** Gear tab: encyclopedia gear (excluding duals) + dual catalog entries. */
export function buildItemsGearList(
  craftCatalog: CraftCatalog,
  dualsCatalog?: DualsCatalog | null,
  gearCatalog?: ItemCatalogEntry[] | null,
): GearItem[] {
  // Duals come from their own catalog, so drop every dual product from the
  // encyclopedia side — including variants hidden from the dual listing.
  const dualProductIds = dualsCatalog ? new Set(allDualProductIds(dualsCatalog)) : null;
  const gearEntries = gearCatalog?.length
    ? gearCatalog.filter((entry) => !dualProductIds?.has(entry.id))
    : null;
  const gear = gearEntries?.length
    ? buildGearListFromEncyclopedia(gearEntries, craftCatalog)
    : buildGearList(craftCatalog);
  if (!dualsCatalog) return gear;
  return [...gear, ...buildDualGearList(dualsCatalog)];
}

export function itemIconSrc(id: number): string | null {
  // Item icons are served locally by game id.
  return `/media/images/${id}.png`;
}

/** @deprecated Use itemIconSrc(id) — icons are resolved by item id. */
export function buildArmorSets(catalog: CraftCatalog): ArmorSetSummary[] {
  const sets: ArmorSetSummary[] = [];
  const setMeta = catalog.setMeta || {};
  const craftable = new Set(catalog.craftableIds || Object.keys(catalog.byProduct || {}).map(Number));

  for (const [name, ids] of Object.entries(catalog.sets || {})) {
    if (!ids?.length) continue;
    const meta = setMeta[name];
    if (meta?.canonical === false) continue;

    const pvp = Boolean(meta?.pvp) || /\{?\s*pvp\s*\}?/i.test(name);
    if (pvp) continue;

    const craftableMemberIds = meta?.craftableMemberIds?.length
      ? [...meta.craftableMemberIds]
      : ids.filter((id) => craftable.has(id));
    const memberIds = meta?.allMemberIds?.length ? [...meta.allMemberIds] : [...ids];
    const memberNames = meta?.memberNames || {};

    let grade = meta?.grade || "";
    let iconId: number | null = null;
    for (const id of memberIds) {
      const info = itemInfo(catalog, id);
      if (!grade && info.grade && info.grade !== "NG") grade = info.grade;
      if (iconId == null && catalog.items[String(id)]) iconId = id;
    }
    if (!grade) {
      for (const id of memberIds) {
        const g = itemInfo(catalog, id).grade;
        if (g) {
          grade = g;
          break;
        }
      }
    }

    const iconSrc = iconId != null ? itemIconSrc(iconId) : null;
    const effect = meta?.effect?.length ? [...meta.effect] : meta?.effectRaw ? [meta.effectRaw] : [];

    sets.push({
      id: name,
      name,
      grade: grade || "NG",
      memberIds,
      craftableMemberIds,
      memberNames,
      iconId,
      iconSrc,
      pvp,
      canonical: meta?.canonical ?? true,
      effect,
      setPagePath: setPagePath(name),
      setSlug: meta?.slug ?? null,
      setWikiId: meta?.id ?? null,
      masterworkSetUrl:
        meta?.id != null ? masterworkSetUrl(meta.id, meta.slug) : null,
    });
  }
  return sets.sort(
    (a, b) =>
      GRADE_ORDER.indexOf(a.grade as (typeof GRADE_ORDER)[number]) -
        GRADE_ORDER.indexOf(b.grade as (typeof GRADE_ORDER)[number]) ||
      a.name.localeCompare(b.name),
  );
}

export interface ItemsFilterState {
  cat: GearCategory | "all";
  grade: string | null;
  sub: string | null;
  slot: string | null;
  q: string;
  sort: ItemsSort;
  showNg: boolean;
  hidePvpSets: boolean;
}

export const DEFAULT_ITEMS_FILTER: ItemsFilterState = {
  cat: "all",
  grade: null,
  sub: null,
  slot: null,
  q: "",
  sort: "grade",
  showNg: false,
  hidePvpSets: true,
};

export function filterGear(list: GearItem[], state: ItemsFilterState): GearItem[] {
  const q = state.q.trim().toLowerCase();
  const filtered = list.filter((it) => {
    if (state.cat !== "all") {
      if (isDualGearCategory(state.cat)) {
        if (it.facet.cat !== state.cat) return false;
      } else if (it.facet.cat !== state.cat) {
        return false;
      }
    }
    if (!state.showNg && it.grade === "NG") return false;
    if (state.grade && it.grade !== state.grade) return false;
    if (state.sub && (it.facet.sub || "") !== state.sub) return false;
    if (state.slot && (it.facet.slot || "") !== state.slot) return false;
    if (q && !it.name.toLowerCase().includes(q)) return false;
    return true;
  });

  return filtered.sort((a, b) => {
    if (state.sort === "name") return a.name.localeCompare(b.name);
    if (state.sort === "stat") {
      return (b.mainStat.val ?? -1) - (a.mainStat.val ?? -1) || a.name.localeCompare(b.name);
    }
    if (state.sort === "price") {
      return (b.npc_sell ?? -1) - (a.npc_sell ?? -1) || a.name.localeCompare(b.name);
    }
    return (
      GRADE_ORDER.indexOf(a.grade as (typeof GRADE_ORDER)[number]) -
        GRADE_ORDER.indexOf(b.grade as (typeof GRADE_ORDER)[number]) ||
      a.name.localeCompare(b.name)
    );
  });
}

export function filterSets(sets: ArmorSetSummary[], state: ItemsFilterState): ArmorSetSummary[] {
  const q = state.q.trim().toLowerCase();
  return sets.filter((s) => {
    if (state.hidePvpSets && s.pvp) return false;
    if (state.grade && s.grade !== state.grade) return false;
    if (q && !s.name.toLowerCase().includes(q)) return false;
    return true;
  });
}

export function facetAvailability(list: GearItem[], state: ItemsFilterState) {
  const q = state.q.trim().toLowerCase();
  const okQ = (it: GearItem) => !q || it.name.toLowerCase().includes(q);
  const okNg = (it: GearItem) => state.showNg || it.grade !== "NG";
  const okCat = (it: GearItem) =>
    state.cat === "all" ||
    (isDualGearCategory(state.cat) ? it.facet.cat === state.cat : it.facet.cat === state.cat);
  const okGrade = (it: GearItem) => !state.grade || it.grade === state.grade;
  const okSub = (it: GearItem) => !state.sub || (it.facet.sub || "") === state.sub;
  const okSlot = (it: GearItem) => !state.slot || (it.facet.slot || "") === state.slot;

  const cats = new Set<GearCategory>();
  const grades = new Set<string>();
  const subs = new Set<string>();
  const slots = new Set<string>();
  let anyNg = false;

  for (const it of list) {
    if (!okQ(it)) continue;
    if (okNg(it) && okGrade(it)) {
      cats.add(it.facet.cat);
    }
    if (okNg(it) && okCat(it) && okSub(it) && okSlot(it) && it.grade !== "NG") grades.add(it.grade);
    if (okCat(it) && okSub(it) && okSlot(it) && it.grade === "NG") anyNg = true;
    if (okNg(it) && okCat(it) && okGrade(it) && okSlot(it) && it.facet.sub) subs.add(it.facet.sub);
    if (okNg(it) && okCat(it) && okGrade(it) && okSub(it) && it.facet.slot) slots.add(it.facet.slot);
  }

  return { cats, grades, subs, slots, anyNg };
}

export function cumulativeSetStats(
  catalog: CraftCatalog,
  memberIds: number[],
): Partial<Record<keyof ItemCombatStats, number>> {
  const sum: Partial<Record<keyof ItemCombatStats, number>> = {};
  for (const id of memberIds) {
    const stats = itemInfo(catalog, id).stats;
    if (!stats) continue;
    (Object.keys(STAT_LABELS) as (keyof ItemCombatStats)[]).forEach((key) => {
      const v = stats[key];
      if (typeof v === "number") sum[key] = (sum[key] ?? 0) + v;
    });
  }
  return sum;
}

export function gearStatRows(item: CatalogItem): { label: string; value: string }[] {
  const stats = item.stats;
  if (!stats) return [];
  const rows: { label: string; value: string }[] = [];
  (Object.keys(STAT_LABELS) as (keyof ItemCombatStats)[]).forEach((key) => {
    const v = stats[key];
    if (v != null) rows.push({ label: STAT_LABELS[key], value: formatStat(v) });
  });
  return rows;
}

export function formatNpcPrice(price: number | null | undefined): string {
  if (price == null) return "—";
  return price.toLocaleString("ru-RU");
}

export function itemCraftable(catalog: CraftCatalog, id: number): boolean {
  return isCraftable(catalog, id);
}

export function setMemberCraftable(set: ArmorSetSummary, id: number, catalog?: CraftCatalog): boolean {
  if (set.craftableMemberIds.includes(id)) return true;
  if (catalog) return isCraftable(catalog, id);
  return false;
}

export function setMemberLabel(set: ArmorSetSummary, id: number, catalog: CraftCatalog): string {
  const known = catalog.items[String(id)];
  if (known) return itemInfo(catalog, id).name;
  return set.memberNames[String(id)] || `Предмет #${id}`;
}

/** Helmets, gloves and boots are shared between the armour classes of a family. */
export function findSetsForItem(sets: ArmorSetSummary[], itemId: number): ArmorSetSummary[] {
  return sets.filter((s) => s.memberIds.includes(itemId));
}

export function catalogItemPath(item: CatalogItem): string {
  return itemPagePath(item.id);
}

/** External masterwork.wiki URL for a craft catalog item. */
export function wikiItemUrl(item: CatalogItem): string {
  return masterworkItemUrlByName(item.id, item.name);
}
