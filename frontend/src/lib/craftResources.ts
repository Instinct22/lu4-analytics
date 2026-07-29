export const MASTERWORK_WIKI_BASE = "https://masterwork.wiki";

export interface ResourceLocation {
  name: string;
  url: string;
}

export interface NpcSource {
  npc_id: number;
  npc_url: string;
  npc_name: string;
  npc_level: string;
  amount: string;
  chance: string;
  chance_val: number;
  locations: ResourceLocation[];
}

export interface ResourceTreeNode {
  id: number;
  name: string;
  grade: string;
  url: string;
  amount: number;
  children: ResourceTreeNode[];
}

export type ResourceSection = "base" | "craft";

/** Material without its spoil/drop arrays: those are fetched per material. */
export interface ResourceMaterial {
  id: number;
  section: ResourceSection;
  name: string;
  grade: string;
  url: string;
  desc: string;
  crafter_level: number | null;
  skill_level: string | null;
  mp: string | null;
  success: string | null;
  recipe_url: string | null;
  tree: ResourceTreeNode[];
  spoil_count: number;
  drop_count: number;
  source_count: number;
}

export interface CraftResourcesPayload {
  generated_at: string;
  min_npc_level: number | null;
  max_npc_level: number | null;
  materials: ResourceMaterial[];
}

export interface MaterialSources {
  material_id: number;
  spoil: NpcSource[];
  drop: NpcSource[];
}

export interface ResourceEntry {
  material: ResourceMaterial;
  section: ResourceSection;
}

export function wikiUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${MASTERWORK_WIKI_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export function allResources(payload: CraftResourcesPayload): ResourceEntry[] {
  return payload.materials.map((material) => ({ material, section: material.section }));
}

export function findResource(payload: CraftResourcesPayload, id: number): ResourceEntry | undefined {
  return allResources(payload).find((e) => e.material.id === id);
}

export function materialHasFarmSources(
  material: Pick<ResourceMaterial, "spoil_count" | "drop_count">,
): boolean {
  return material.spoil_count > 0 || material.drop_count > 0;
}

export function farmResourceIds(payload: CraftResourcesPayload): Set<number> {
  return new Set(payload.materials.filter(materialHasFarmSources).map((m) => m.id));
}

export interface NpcLootEntry {
  materialId: number;
  materialName: string;
  materialGrade: string;
  materialUrl: string;
  amount: string;
  chance: string;
  chance_val: number;
}

export interface NpcLootProfile {
  npc_id: number;
  npc_name: string;
  npc_url: string;
  npc_level: string;
  locations: ResourceLocation[];
  spoils: NpcLootEntry[];
  drops: NpcLootEntry[];
}

/** Profile of an NPC the user has no loot data for yet. */
export function npcProfileFromSource(source: NpcSource): NpcLootProfile {
  return {
    npc_id: source.npc_id,
    npc_name: source.npc_name,
    npc_url: source.npc_url,
    npc_level: source.npc_level,
    locations: source.locations,
    spoils: [],
    drops: [],
  };
}

/** Levels arrive either as "36" or in wiki form "Lv. 36". */
export function parseNpcLevel(level: string): number | null {
  const match = /\d+/.exec(level ?? "");
  return match ? Number(match[0]) : null;
}

/** The wiki reports chances as "99.990000%": keep at most two decimals. */
export function formatChance(chance: string): string {
  const match = /^(\d+(?:\.\d+)?)\s*%?$/.exec((chance ?? "").trim());
  if (!match) return chance ?? "";
  const value = Number(match[1]);
  if (!Number.isFinite(value)) return chance;
  const rounded = value >= 1 ? value.toFixed(2) : value.toPrecision(2);
  return `${Number(rounded)}%`;
}

export function npcLevelBounds(payload: CraftResourcesPayload): { min: number; max: number } {
  return { min: payload.min_npc_level ?? 1, max: payload.max_npc_level ?? 80 };
}

export function filterSourcesByLevel(
  sources: NpcSource[],
  minLevel: number,
  maxLevel: number,
): NpcSource[] {
  return sources.filter((src) => {
    const lv = parseNpcLevel(src.npc_level);
    if (lv == null) return false;
    return lv >= minLevel && lv <= maxLevel;
  });
}
