import api from "./client";
import type { CatalogItem, CatalogVariant, CraftCatalog } from "../lib/craftCalc";
import type { CraftResourcesPayload, MaterialSources, NpcLootProfile } from "../lib/craftResources";

/** Variants of a product plus every craftable material it depends on. */
export type RecipeClosure = {
  product_id: number;
  byProduct: Record<string, CatalogVariant[]>;
  items: Record<string, CatalogItem>;
};

export type ProfitabilityRow = {
  product_id: number;
  product_name: string;
  grade: string;
  variant_index: number;
  yield: number;
  unit_price: number;
  revenue: number;
  material_cost: number;
  margin: number;
  margin_pct: number | null;
};

export async function getCraftCatalog(): Promise<CraftCatalog> {
  const { data } = await api.get("/craft/catalog");
  return data;
}

export async function getRecipeClosure(productId: number): Promise<RecipeClosure> {
  const { data } = await api.get(`/craft/recipes/${productId}`);
  return data;
}

export async function getCraftResources(): Promise<CraftResourcesPayload> {
  const { data } = await api.get("/craft/resources");
  return data;
}

export async function getMaterialSources(materialId: number): Promise<MaterialSources> {
  const { data } = await api.get(`/craft/resources/${materialId}/sources`);
  return data;
}

export async function getNpcMaterials(npcId: number): Promise<NpcLootProfile> {
  const { data } = await api.get(`/craft/resources/npc/${npcId}`);
  return data;
}

export async function getCraftProfitability(limit = 100): Promise<ProfitabilityRow[]> {
  const { data } = await api.get("/craft/profitability", { params: { limit } });
  return data.recipes ?? [];
}
