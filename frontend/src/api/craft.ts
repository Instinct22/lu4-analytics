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

export type AppraisalGrade = "NG" | "D" | "C" | "B" | "A" | "S";
export type AppraisalType = "weapon" | "armor" | "jewelry";

export type AppraisalRow = {
  product_id: number;
  product_name: string;
  grade: string;
  type: string;
  category: string;
  variant_index: number;
  rate: number | null;
  yield: number;
  craft_cost: number | null;
  market_price: number | null;
  shop_price: number | null;
  crystal_amount: number | null;
  crystal_price: number | null;
  margin_market: number | null;
  margin_market_pct: number | null;
  margin_shop: number | null;
  margin_shop_pct: number | null;
  margin_crystal: number | null;
  margin_crystal_pct: number | null;
  margin?: number | null;
  margin_pct?: number | null;
};

export type AppraisalResponse = {
  grade: AppraisalGrade;
  type: AppraisalType;
  items: AppraisalRow[];
};

export async function getCraftAppraisal(params: {
  grade: AppraisalGrade;
  type: AppraisalType;
  limit?: number;
}): Promise<AppraisalResponse> {
  const { data } = await api.get("/craft/appraisal", {
    params: { grade: params.grade, type: params.type, limit: params.limit ?? 100 },
  });
  return data;
}
