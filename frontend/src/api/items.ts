import type { CraftCatalog } from "../lib/craftCalc";
import type { DualsCatalog } from "../lib/dualsCatalog";
import api from "./client";

export interface ItemSourceRow {
  npc_id: number;
  npc_name: string;
  npc_level?: number | null;
  npc_level_raw?: string;
  npc_url?: string;
  amount: string;
  chance: string;
  chance_val?: number;
  locations?: string[];
}

export interface ItemEnchantRow {
  level: number;
  crystals?: number | null;
  fail_crystals?: number | null;
  [key: string]: string | number | null | undefined;
}

export interface ItemEncyclopediaEntry {
  id: number;
  section: "gear" | "other" | "excluded";
  name: string;
  grade: string;
  type: string;
  other_subcategory?: string | null;
  icon?: string | null;
  url?: string;
  slug?: string;
  npc_sell?: number | null;
  category?: string;
  set_name?: string | null;
  stats?: Record<string, number>;
  weight?: number;
  effects?: string;
  description?: string;
  restrictions?: Record<string, boolean>;
  drops?: ItemSourceRow[];
  spoils?: ItemSourceRow[];
  has_drop?: boolean;
  has_spoil?: boolean;
  enchant?: ItemEnchantRow[];
  craft?: { craftable: boolean; variants: unknown[] };
  set?: Record<string, unknown> | null;
  links?: Record<string, unknown>;
  sealed_group?: {
    base_name: string;
    sealed_id: number;
    variants: Array<{ id: number; name: string; armor_type?: string | null }>;
  } | null;
  /** Set when this entry was merged into a canonical item and hidden from listings. */
  exclude_reason?: string | null;
  variant_of?: number | null;
  variant_kind?: string | null;
  /** Pieces this item unseals into; merged away from the catalog listing. */
  unseal_variants?: Array<{
    id: number;
    name?: string | null;
    label?: string | null;
    armor_class?: string | null;
    grade?: string | null;
  }>;
  masterwork?: unknown;
  item_modifiers?: {
    rarity?: Array<{
      name?: string;
      full_name?: string;
      id?: number;
      effect?: string | null;
      sa?: string;
      sa_effect?: string;
      pvp?: boolean;
      from_masterwork?: boolean;
    }>;
    soul_crystals?: Array<{
      name?: string;
      full_name?: string;
      id?: number;
      effect?: string | null;
      applied?: boolean;
      pvp?: boolean;
      weapon_sa?: boolean;
    }>;
    pvp?: {
      available?: boolean;
      full_name?: string;
      id?: number;
      notes?: string | null;
    } | null;
  };
  item_skills?: Array<{ id: number; name: string; url: string }>;
}

export interface ItemCatalogEntry {
  id: number;
  name: string;
  grade: string;
  type: string;
  section: string;
  other_subcategory?: string | null;
  icon?: string | null;
  url?: string;
  npc_sell?: number | null;
  category?: string;
  set_name?: string | null;
  stats?: Record<string, number>;
  weight?: number;
  has_drop?: boolean;
  has_spoil?: boolean;
  craftable?: boolean;
  effects?: string;
}

export interface ItemsCatalogResponse {
  generated_at?: string;
  item_count?: number;
  section_counts?: Record<string, number>;
  items: ItemCatalogEntry[];
}

export interface ItemsBrowseResponse {
  generated_at?: string;
  gear: ItemsCatalogResponse;
  craft: CraftCatalog;
  duals: DualsCatalog | null;
}

export async function getItemsCatalog(section?: "gear" | "other"): Promise<ItemsCatalogResponse> {
  const { data } = await api.get("/items/catalog", { params: section ? { section } : {} });
  return data;
}

export async function getItemsBrowse(): Promise<ItemsBrowseResponse> {
  const { data } = await api.get("/items/browse");
  return data;
}

export async function getItemDetail(itemId: number): Promise<ItemEncyclopediaEntry> {
  const { data } = await api.get(`/items/${itemId}`);
  return data;
}

export async function getItemSources(itemId: number): Promise<{
  id: number;
  drops: ItemSourceRow[];
  spoils: ItemSourceRow[];
}> {
  const { data } = await api.get(`/items/${itemId}/sources`);
  return data;
}

export async function getCraftItemDetail(itemId: number): Promise<ItemEncyclopediaEntry> {
  const { data } = await api.get(`/craft/items/${itemId}`);
  return data;
}
