export interface ItemCombatStats {
  p_atk?: number | null;
  m_atk?: number | null;
  crystals?: number | null;
  p_def?: number | null;
  m_def?: number | null;
  shield_def?: number | null;
}

export interface CatalogItem {
  id: number;
  name: string;
  grade: string;
  type: string;
  category: string;
  set_name: string | null;
  npc_sell: number | null;
  url: string;
  is_recipe_scroll: boolean;
  icon?: string;
  stats?: ItemCombatStats | null;
  description?: string | null;
}

export interface TreeMaterial {
  id: number;
  amount: number;
  children: TreeMaterial[];
}

export interface CatalogVariant {
  recipe_id: number;
  recipe_url: string;
  rate: number | null;
  crafter_level: number;
  skill_level: string | null;
  mp: string | null;
  success: string | null;
  yield: number;
  tree: TreeMaterial[];
  direct: { id: number; amount: number }[];
}

export interface CraftCatalog {
  generated_at: string;
  product_count: number;
  variant_count: number;
  items: Record<string, CatalogItem>;
  /** Recipe variants of the products fetched so far, keyed by product id. */
  byProduct: Record<string, CatalogVariant[]>;
  /** Every craftable product, including those whose variants are not loaded. */
  craftableIds?: number[];
  /** Materials with spoil/drop sources on the Resources tab. */
  farmMaterialIds?: number[];
  categories: {
    weapons: Record<string, Record<string, number[]>>;
    armors: Record<string, Record<string, number[]>>;
    materials: Record<string, number[]>;
    other: Record<string, number[]>;
  };
  sets: Record<string, number[]>;
  setMeta?: Record<string, SetMeta>;
}

export interface SetMeta {
  id?: number;
  slug?: string;
  name: string;
  grade: string;
  url?: string;
  icon?: string;
  pvp?: boolean;
  canonical?: boolean;
  effect?: string[];
  effectRaw?: string;
  craftableMemberIds: number[];
  allMemberIds: number[];
  memberNames?: Record<string, string>;
}

export interface PriceInfo {
  avg_price: number | null;
  last_price: number | null;
  npc_sell: number | null;
}

export interface CalcNode {
  id: number;
  want: number;
  net: number;
  base: boolean;
  children: CalcNode[];
  recipeScroll?: boolean;
  recipeConsumed?: boolean;
  recipe?: CatalogVariant;
}

export interface RollupEntry {
  id: number;
  need: number;
  owned: number;
  still: number;
  scroll: boolean;
  consumed: boolean;
  craftable: boolean;
  isBase: boolean;
  fromList: { pid: number; amt: number }[];
  node?: CalcNode;
}

export interface CartEntry {
  productId: number;
  qty: number;
  variantIdx: number;
}

/** Stable storage key for a cart line (product + recipe variant). */
export function cartEntryKey(productId: number, variantIdx = 0): string {
  return `${productId}:${variantIdx}`;
}

export function parseCartEntryKey(
  key: string,
  line?: { qty?: number; variant?: number },
): CartEntry | null {
  const qty = Math.max(1, Math.floor(Number(line?.qty) || 1));
  const colon = key.indexOf(":");
  if (colon >= 0) {
    const productId = Number(key.slice(0, colon));
    const parsedVariant = Number(key.slice(colon + 1));
    if (!Number.isFinite(productId) || productId <= 0) return null;
    const variantIdx = Number.isFinite(parsedVariant)
      ? Math.max(0, Math.floor(parsedVariant))
      : Math.max(0, Math.floor(Number(line?.variant) || 0));
    return { productId, qty, variantIdx };
  }

  const productId = Number(key);
  if (!Number.isFinite(productId) || productId <= 0) return null;
  return {
    productId,
    qty,
    variantIdx: Math.max(0, Math.floor(Number(line?.variant) || 0)),
  };
}

export function formatVariantRate(variant: CatalogVariant | undefined): string {
  if (!variant) return "";
  if (variant.rate != null) return `${variant.rate}%`;
  if (variant.success) return variant.success;
  return "";
}

export function ownedToRemaining(owned: Record<string, number>): Map<number, number> {
  const remaining = new Map<number, number>();
  for (const [k, v] of Object.entries(owned)) {
    const n = Math.floor(Number(v));
    if (n > 0) remaining.set(Number(k), n);
  }
  return remaining;
}

export const MARKET_MARKUP = 1.5;

export function itemInfo(catalog: CraftCatalog, id: number): CatalogItem {
  return (
    catalog.items[String(id)] ?? {
      id,
      name: `#${id}`,
      grade: "",
      type: "Other",
      category: "other/misc",
      set_name: null,
      npc_sell: null,
      url: "",
      is_recipe_scroll: false,
      stats: null,
      description: null,
    }
  );
}

export function isWeaponItem(info: CatalogItem): boolean {
  return info.category.startsWith("weapons/");
}

export function isArmorItem(info: CatalogItem): boolean {
  return info.category.startsWith("armors/");
}

export function formatStat(value: number | null | undefined): string {
  if (value == null) return "—";
  return String(value);
}

export function variantsFor(catalog: CraftCatalog, id: number): CatalogVariant[] {
  return catalog.byProduct?.[String(id)] ?? [];
}

const craftableSets = new WeakMap<CraftCatalog, Set<number>>();

/** Craftability is known for the whole catalog even when trees are not loaded. */
export function isCraftable(catalog: CraftCatalog, id: number): boolean {
  let ids = craftableSets.get(catalog);
  if (!ids) {
    ids = new Set(catalog.craftableIds ?? Object.keys(catalog.byProduct ?? {}).map(Number));
    craftableSets.set(catalog, ids);
  }
  return ids.has(id);
}

export function isRecipeScroll(catalog: CraftCatalog, id: number, recipeId?: number): boolean {
  const info = itemInfo(catalog, id);
  if (info.is_recipe_scroll) return true;
  if (recipeId != null && id === recipeId) return true;
  return /recipe/i.test(info.name);
}

function consumeOwned(remaining: Map<number, number>, id: number, want: number): number {
  const have = remaining.get(id) ?? 0;
  const used = Math.min(have, want);
  if (used > 0) remaining.set(id, have - used);
  return want - used;
}

function buildFromMaterial(
  catalog: CraftCatalog,
  mat: TreeMaterial,
  crafts: number,
  remaining: Map<number, number>,
  variantIdx: number,
  chosenVariants: Record<string, number>,
  depth: number,
): CalcNode {
  const id = mat.id;
  const scroll = isRecipeScroll(catalog, id);
  // Nested trees are pre-baked for one parent craft line; `crafts` must stay >1 when qty grows.
  // Recipe scrolls (C+ etc.) are consumed per craft — scale with qty like other mats.
  const want = Math.max(0, Math.round((mat.amount || 1) * crafts));
  const net = consumeOwned(remaining, id, want);
  const hasChildren = (mat.children?.length ?? 0) > 0;
  const craftable = isCraftable(catalog, id);

  const node: CalcNode = {
    id,
    want,
    net,
    base: !hasChildren && !craftable,
    children: [],
    recipeScroll: scroll,
    // In Lu4 C+ recipes are consumed each craft; keep flag for UI/cost paths.
    recipeConsumed: scroll,
  };

  if (scroll) {
    return node;
  }

  // Fraction of this material still needed after owned stock (scales nested ingredients).
  const childScale = want > 0 ? net / want : 0;
  const childCrafts = crafts * childScale;

  if (hasChildren) {
    for (const ch of mat.children) {
      if (childCrafts <= 0) continue;
      node.children.push(
        buildFromMaterial(catalog, ch, childCrafts, remaining, variantIdx, chosenVariants, depth + 1),
      );
    }
  } else if (craftable && depth < 12 && net > 0) {
    const vi = chosenVariants[String(id)] ?? 0;
    const variants = variantsFor(catalog, id);
    const variant = variants[vi] ?? variants[0];
    if (variant) {
      node.recipe = variant;
      for (const ch of variant.tree) {
        node.children.push(
          buildFromMaterial(catalog, ch, net, remaining, vi, chosenVariants, depth + 1),
        );
      }
    }
  }

  node.base = node.children.length === 0;
  return node;
}

export function buildTree(
  catalog: CraftCatalog,
  productId: number,
  qty: number,
  owned: Record<string, number>,
  variantIdx = 0,
  chosenVariants: Record<string, number> = {},
  sharedRemaining?: Map<number, number>,
): CalcNode | null {
  const variants = variantsFor(catalog, productId);
  const variant = variants[variantIdx] ?? variants[0];
  if (!variant) return null;

  const remaining = sharedRemaining ?? ownedToRemaining(owned);

  const crafts = Math.max(1, qty);
  const children: CalcNode[] = [];
  for (const mat of variant.tree) {
    children.push(
      buildFromMaterial(catalog, mat, crafts, remaining, variantIdx, chosenVariants, 0),
    );
  }

  consumeOwned(remaining, productId, 0);
  return {
    id: productId,
    want: crafts,
    net: crafts,
    base: false,
    children,
    recipe: variant,
  };
}

export function buildMultiCraftRollup(
  catalog: CraftCatalog,
  cart: CartEntry[],
  owned: Record<string, number>,
  chosenVariants: Record<string, number> = {},
): RollupEntry[] {
  if (cart.length === 0) return [];

  const remaining = ownedToRemaining(owned);
  const items: RollupEntry[] = [];

  for (const entry of cart) {
    const variantIdx = entry.variantIdx ?? chosenVariants[String(entry.productId)] ?? 0;
    const tree = buildTree(
      catalog,
      entry.productId,
      entry.qty,
      owned,
      variantIdx,
      chosenVariants,
      remaining,
    );
    if (tree) items.push(...shoppingItems(catalog, tree));
  }

  return mergeShoppingById(items).sort((a, b) => {
    if (a.craftable !== b.craftable) return a.craftable ? -1 : 1;
    return itemInfo(catalog, a.id).name.localeCompare(itemInfo(catalog, b.id).name);
  });
}

export function effectivePrice(
  id: number,
  prices: Record<string, PriceInfo>,
  manual: Record<string, number>,
  catalog?: CraftCatalog,
): number | null {
  const mk = String(id);
  if (manual[mk] != null && manual[mk] > 0) return manual[mk];
  const p = prices[mk];
  if (p?.avg_price != null && p.avg_price > 0) return p.avg_price;
  if (p?.last_price != null && p.last_price > 0) return p.last_price;
  const npc = p?.npc_sell ?? (catalog ? itemInfo(catalog, id).npc_sell : null);
  if (npc != null && npc > 0) return npc * MARKET_MARKUP;
  return null;
}

export function treeCost(
  node: CalcNode,
  catalog: CraftCatalog,
  prices: Record<string, PriceInfo>,
  manual: Record<string, number>,
): { cost: number | null; crafted: Set<number> } {
  if (node.net <= 0 || (node.recipeScroll && !node.recipeConsumed)) {
    return { cost: 0, crafted: new Set() };
  }

  const buy = effectivePrice(node.id, prices, manual, catalog);
  const buyTot = buy != null ? buy * node.net : null;

  if (node.base || node.children.length === 0) {
    return { cost: buyTot, crafted: new Set() };
  }

  let craft = 0;
  let ok = true;
  const crafted = new Set<number>();
  for (const c of node.children) {
    const cc = treeCost(c, catalog, prices, manual);
    if (cc.cost == null) {
      ok = false;
      break;
    }
    craft += cc.cost;
    cc.crafted.forEach((x) => crafted.add(x));
  }

  if (ok && (buyTot == null || craft <= buyTot)) {
    crafted.add(node.id);
    return { cost: craft, crafted };
  }
  return { cost: buyTot, crafted: new Set() };
}

export interface LeafAcc {
  craftAll: number;
  recipes: number;
  missing: Set<number>;
}

export function walkLeaves(
  node: CalcNode,
  catalog: CraftCatalog,
  prices: Record<string, PriceInfo>,
  manual: Record<string, number>,
  acc: LeafAcc,
) {
  if (node.net <= 0) return;
  const craftableNode = !node.base && node.children.length > 0;
  if (craftableNode) {
    for (const c of node.children) walkLeaves(c, catalog, prices, manual, acc);
    return;
  }
  if (node.recipeScroll && !node.recipeConsumed) return;
  const b = effectivePrice(node.id, prices, manual, catalog);
  if (b == null) acc.missing.add(node.id);
  acc.craftAll += (b ?? 0) * node.net;
}

export function shoppingItems(catalog: CraftCatalog, tree: CalcNode): RollupEntry[] {
  const items: RollupEntry[] = [];

  function walk(n: CalcNode, isRoot: boolean) {
    if (!isRoot && n.net > 0) {
      if (n.recipeScroll) {
        items.push({
          id: n.id,
          need: n.want,
          owned: n.want - n.net,
          still: n.net,
          scroll: true,
          consumed: !!n.recipeConsumed,
          craftable: false,
          isBase: true,
          fromList: [],
          node: n,
        });
      } else {
        const hasBuiltChildren = !n.base && n.children.length > 0;
        const craftable = hasBuiltChildren || isCraftable(catalog, n.id);
        items.push({
          id: n.id,
          need: n.want,
          owned: n.want - n.net,
          still: n.net,
          scroll: false,
          consumed: !!n.recipeConsumed,
          craftable,
          isBase: !craftable,
          fromList: [],
          node: n,
        });
      }
    }
    for (const c of n.children) walk(c, false);
  }

  walk(tree, true);

  return mergeShoppingById(items).sort((a, b) => {
    if (a.craftable !== b.craftable) return a.craftable ? -1 : 1;
    return itemInfo(catalog, a.id).name.localeCompare(itemInfo(catalog, b.id).name);
  });
}

/** Sum duplicate materials (e.g. Varnish used in several craft branches). */
export function isCraftReady(catalog: CraftCatalog, tree: CalcNode): boolean {
  return shoppingItems(catalog, tree).every((entry) => entry.still <= 0);
}

/** Warehouse amounts consumed to craft `qty` of `productId`, or null if materials are missing. */
export function computeWarehouseConsumption(
  catalog: CraftCatalog,
  productId: number,
  qty: number,
  owned: Record<string, number>,
  variantIdx = 0,
  chosenVariants: Record<string, number> = {},
): Map<number, number> | null {
  const remaining = ownedToRemaining(owned);
  const before = new Map(remaining);
  const tree = buildTree(catalog, productId, qty, owned, variantIdx, chosenVariants, remaining);
  if (!tree || !isCraftReady(catalog, tree)) return null;

  const consumed = new Map<number, number>();
  for (const [id, startQty] of before) {
    const used = startQty - (remaining.get(id) ?? 0);
    if (used > 0) consumed.set(id, used);
  }
  return consumed;
}

export function applyWarehouseConsumption(
  owned: Record<string, number>,
  consumed: Map<number, number>,
): Record<string, number> {
  const next = { ...owned };
  for (const [id, used] of consumed) {
    const key = String(id);
    const left = Math.floor(Number(next[key] ?? 0)) - used;
    if (left <= 0) delete next[key];
    else next[key] = left;
  }
  return next;
}

export function warehouseTotalValue(
  catalog: CraftCatalog,
  owned: Record<string, number>,
  prices: Record<string, PriceInfo>,
  manual: Record<string, number>,
): { total: number | null; partial: boolean } {
  let total = 0;
  let pricedAny = false;
  let partial = false;

  for (const [key, qtyRaw] of Object.entries(owned)) {
    const qty = Math.floor(Number(qtyRaw));
    if (qty <= 0) continue;
    const id = Number(key);
    if (!Number.isFinite(id)) continue;

    const price = effectivePrice(id, prices, manual, catalog);
    if (price == null) {
      partial = true;
      continue;
    }
    pricedAny = true;
    total += price * qty;
  }

  if (!pricedAny) return { total: null, partial };
  return { total, partial };
}

export function mergeShoppingById(items: RollupEntry[]): RollupEntry[] {
  const map = new Map<number, RollupEntry>();
  for (const e of items) {
    const prev = map.get(e.id);
    if (!prev) {
      map.set(e.id, { ...e });
      continue;
    }
    prev.need += e.need;
    prev.still += e.still;
    prev.owned = prev.need - prev.still;
    prev.craftable = prev.craftable || e.craftable;
    prev.isBase = prev.isBase && e.isBase;
    prev.scroll = prev.scroll || e.scroll;
    prev.consumed = prev.consumed || e.consumed;
    if (e.craftable && e.node && (!prev.node || e.node.children.length > (prev.node.children.length ?? 0))) {
      prev.node = e.node;
    }
  }
  return [...map.values()];
}

/** @deprecated use shoppingItems */
export function formatPrice(n: number | null): string {
  if (n == null) return "—";
  const v = Math.round(n);
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(v >= 10_000_000 ? 0 : 1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(v >= 100_000 ? 0 : 1)}K`;
  return String(v);
}

export const GRADE_COLORS: Record<string, string> = {
  S: "#d98fff",
  A: "#e7b34e",
  B: "#ee6f63",
  C: "#52a8ee",
  D: "#54c98a",
  NG: "#9aa6ad",
};

export const TAB_LABELS: Record<string, string> = {
  weapons: "Оружие",
  armors: "Броня",
  jewelry: "Бижутерия",
  materials: "Материалы",
  other: "Прочее",
  sets: "Сеты",
};

export const SUB_LABELS: Record<string, string> = {
  swords: "Мечи",
  daggers: "Кинжалы",
  bows: "Луки",
  blunts: "Дубины",
  poles: "Копья",
  fists: "Кастеты",
  duals: "Duals",
  crossbows: "Арбалеты",
  rapier: "Рапиры",
  heavy: "Тяжёлая",
  light: "Лёгкая",
  magic: "Магическая",
  helmets: "Шлемы",
  boots: "Ботинки",
  gloves: "Перчатки",
  shields: "Щиты",
  soulshots: "Soulshot",
  sealed: "Sealed",
  recipes: "Рецепты",
  jewelry: "Бижутерия",
  consumables: "Расходники",
  misc: "Разное",
};
