import { mediaUrl } from "../api/client";

export const WIKI_BASE = "https://masterwork.wiki";

export interface ClassTreeNode {
  id: number;
  name: string;
  slug: string;
  icon: string;
  portrait: string;
  children: ClassTreeNode[];
}

export interface RaceBranch {
  type: "warrior" | "mage";
  root: ClassTreeNode;
}

export interface Race {
  id: string;
  name: string;
  branches: RaceBranch[];
}

export interface SpellbookRef {
  id: number;
  name: string;
  grade: string | null;
}

export interface ClassSkillEntry {
  skill_id: number;
  skill_level: number;
  name: string;
  sp: number | null;
  spellbook: SpellbookRef | null;
  unlocked_at_level?: number;
}

export interface ClassData {
  id: number;
  name: string;
  slug: string;
  icon: string;
  portrait: string;
  race_id?: string | null;
  levels: number[];
  skills_by_level: Record<string, ClassSkillEntry[]>;
  skills_up_to_level: Record<string, ClassSkillEntry[]>;
}

export interface SkillLevelData {
  description: string;
  stats: Record<string, string>;
}

export interface SkillData {
  id: number;
  name: string;
  icon: string;
  type: string;
  levels: Record<string, SkillLevelData>;
  available_for: Array<{ class_name: string; level: number }>;
}

/** Response of /api/character/races: classes and skills are fetched separately. */
export interface RacesResponse {
  generated_at: string | null;
  wiki_base: string;
  races: Race[];
}

export function formatSp(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("ru-RU");
}

export function skillsUpToLevel(
  classData: ClassData,
  level: number,
): ClassSkillEntry[] {
  const key = String(level);
  if (classData.skills_up_to_level[key]) {
    return classData.skills_up_to_level[key];
  }
  const cumulative: ClassSkillEntry[] = [];
  const seen = new Map<number, ClassSkillEntry>();
  for (const lv of classData.levels) {
    if (lv > level) break;
    for (const entry of classData.skills_by_level[String(lv)] ?? []) {
      seen.set(entry.skill_id, { ...entry, unlocked_at_level: lv });
    }
  }
  seen.forEach((v) => cumulative.push(v));
  return cumulative;
}

export function skillLevelRange(skill: SkillData): number[] {
  return Object.keys(skill.levels)
    .map(Number)
    .filter((n) => Number.isFinite(n))
    .sort((a, b) => a - b);
}

export function findRaceById(races: Race[], raceId: string): Race | undefined {
  return races.find((r) => r.id === raceId);
}

function* walkClassNodes(races: Race[]): Generator<ClassTreeNode> {
  const stack: ClassTreeNode[] = [];
  for (const race of races) {
    for (const branch of race.branches) stack.push(branch.root);
  }
  while (stack.length > 0) {
    const node = stack.pop()!;
    yield node;
    for (const child of node.children) stack.push(child);
  }
}

/** Class nodes carry name and slug, so wiki links need no class payload. */
export function findClassNodeByName(races: Race[], name: string): ClassTreeNode | undefined {
  for (const node of walkClassNodes(races)) {
    if (node.name === name) return node;
  }
  return undefined;
}

export function findClassInTree(node: ClassTreeNode, classId: number): ClassTreeNode | undefined {
  if (node.id === classId) return node;
  for (const child of node.children) {
    const found = findClassInTree(child, classId);
    if (found) return found;
  }
  return undefined;
}

export function defaultLevelForClass(classData: ClassData): number {
  return classData.levels[classData.levels.length - 1] ?? 1;
}

export function classUnlockEntry(
  classData: ClassData,
  skillId: number,
): ClassSkillEntry | undefined {
  for (const lv of classData.levels) {
    const hit = (classData.skills_by_level[String(lv)] ?? []).find((e) => e.skill_id === skillId);
    if (hit) return { ...hit, unlocked_at_level: lv };
  }
  return undefined;
}

export function slugifyWiki(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function wikiUrl(path: string, wikiBase: string = WIKI_BASE): string {
  if (path.startsWith("http")) return path;
  return `${wikiBase}${path.startsWith("/") ? path : `/${path}`}`;
}

export function wikiClassesUrl(wikiBase: string = WIKI_BASE): string {
  return wikiUrl("/lu4/classes", wikiBase);
}

export function wikiClassUrl(slug: string, level?: number, wikiBase: string = WIKI_BASE): string {
  const base = `/lu4/class/${slug}`;
  return wikiUrl(level != null ? `${base}/${level}` : base, wikiBase);
}

export function wikiSkillUrl(
  skillId: number,
  skillName: string,
  level: number,
  wikiBase: string = WIKI_BASE,
): string {
  const slug = slugifyWiki(skillName);
  return wikiUrl(`/lu4/skill/${skillId}${slug ? `-${slug}` : ""}/${level}`, wikiBase);
}

export function wikiItemUrl(itemId: number, itemName?: string, wikiBase: string = WIKI_BASE): string {
  const slug = itemName ? slugifyWiki(itemName) : "";
  return wikiUrl(`/lu4/item/${itemId}${slug ? `-${slug}` : ""}`, wikiBase);
}
