import type { CatalogItem, CatalogVariant, ItemCombatStats } from "./craftCalc";
import { isWeaponItem } from "./craftCalc";

export type DualType = "swords" | "daggers" | "blunts";

export interface DualsCatalog {
  generated_at: string;
  product_count: number;
  variant_count: number;
  items: Record<string, CatalogItem & { dual_type?: DualType }>;
  byProduct: Record<
    string,
    (CatalogVariant & {
      source?: string;
      npc?: string;
      sa?: string | null;
    })[]
  >;
  categories: Record<DualType, Record<string, number[]>>;
  notes?: {
    craft_npc?: string;
    craft_location?: string;
    article_url?: string;
  };
}

export const DUAL_TYPE_LABELS: Record<DualType, string> = {
  swords: "Dual Sword",
  daggers: "Dual Dagger",
  blunts: "Dual Blunt",
};

/** Shared wiki icons — one per dual weapon family (from post 561 / item pages). */
export const DUAL_TYPE_ICONS: Record<DualType, string> = {
  swords: "weapon_dual_sword_i00.png",
  daggers: "dual_dagger_i00.png",
  blunts: "weapon_r_dualblunt_i00.png",
};

export function dualTypeIconUrl(dualType: DualType | string | undefined | null): string | null {
  if (!dualType) return null;
  const file = DUAL_TYPE_ICONS[dualType as DualType];
  if (!file) return null;
  return `/media/images/${file}`;
}

export function dualItemInfo(catalog: DualsCatalog, id: number): CatalogItem & { dual_type?: DualType } {
  return (
    catalog.items[String(id)] ?? {
      id,
      name: `#${id}`,
      grade: "",
      type: "Other",
      category: "other/misc",
      set_name: null,
      npc_sell: null,
      url: `/lu4/item/${id}`,
      is_recipe_scroll: false,
      stats: null,
      description: null,
    }
  );
}

export function dualVariants(catalog: DualsCatalog, id: number) {
  return catalog.byProduct[String(id)] ?? [];
}

/** True when material is a weapon (opens Craft page). */
export function isDualMaterialWeapon(catalog: DualsCatalog, id: number): boolean {
  const info = dualItemInfo(catalog, id);
  if (isWeaponItem(info)) return true;
  return (info.type || "").toLowerCase().startsWith("weapon");
}

/** Every craftable dual id, including variants that are hidden from listings. */
export function allDualProductIds(catalog: DualsCatalog): number[] {
  return Object.keys(catalog.byProduct).map(Number);
}

export function allDualIds(catalog: DualsCatalog): number[] {
  return allDualProductIds(catalog).filter((id) => {
    const name = catalog.items[String(id)]?.name ?? "";
    // Rare dual variants (e.g. "Axe*Axe - Earth") are merged into the base dual entry.
    return !name.includes(" - ");
  });
}
