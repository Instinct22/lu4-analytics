import api from "./client";
import type { CatalogItem, CatalogVariant, CraftCatalog } from "../lib/craftCalc";
import type { CraftResourcesPayload, MaterialSources, NpcLootProfile } from "../lib/craftResources";
import type { PeriodState } from "../components/trading/periodUtils";
import { periodQueryParams } from "../components/trading/periodUtils";

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
  category: string;
  kind: "item" | "material";
  variant_index: number;
  yield: number;
  avg_price: number | null;
  last_price: number | null;
  npc_sell: number | null;
  npc_buy: number | null;
  revenue_avg: number | null;
  revenue_last: number | null;
  revenue_npc: number | null;
  revenue_npc_buy: number | null;
  material_cost_avg: number | null;
  material_cost_last: number | null;
  material_cost_npc: number | null;
  material_cost_npc_buy: number | null;
  margin_avg: number | null;
  margin_last: number | null;
  margin_npc: number | null;
  margin_npc_buy: number | null;
};

export type CraftProfitabilityPayload = {
  period: string;
  from: string;
  to: string;
  total: number;
  recipes: ProfitabilityRow[];
};

export type CraftProfitabilityParams = {
  period: PeriodState;
  grades?: string[];
  categories?: string[];
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

export async function getCraftProfitability(
  params: CraftProfitabilityParams,
): Promise<CraftProfitabilityPayload> {
  const { data } = await api.get("/craft/profitability", {
    params: {
      ...periodQueryParams(params.period),
      ...(params.grades?.length ? { grades: params.grades.join(",") } : {}),
      ...(params.categories?.length ? { categories: params.categories.join(",") } : {}),
    },
  });
  return data;
}
