export type UpgradeKind = "physical" | "magic" | "armor" | "jewelry";

export interface UpgradeItem {
  id: number;
  name: string;
  grade: string;
  icon?: string | null;
  npc_sell?: number | null;
  p_atk?: number | null;
  m_atk?: number | null;
  p_def?: number | null;
  m_def?: number | null;
}

export interface WeaponUpgradeRow {
  grade: string;
  kind: UpgradeKind;
  category: string;
  category_label: string;
  from_ids: number[];
  cost_adena: number | null;
  to_ids: number[];
}

export interface NgToDPair {
  from_id: number;
  to_id: number;
}

export interface NgToDExchange {
  coupon_id: number;
  coupon_name: string;
  npc: string;
  profession: string;
  from_ids: number[];
  to_ids: number[];
  pairs: NgToDPair[];
}

export interface WeaponUpgradesCatalog {
  generated_at?: string | null;
  source_url?: string;
  info: {
    where: string;
    ng_to_d_where: string;
    ng_rule: string;
    d_rule: string;
    tax_note: string;
    how: string;
  };
  upgrades: WeaponUpgradeRow[];
  ng_to_d: NgToDExchange | null;
  items: Record<string, UpgradeItem>;
}

export type UpgradeTab = "NG" | "D" | "NG_TO_D";

export const UPGRADE_TABS: { id: UpgradeTab; label: string }[] = [
  { id: "NG", label: "NG апгрейды" },
  { id: "D", label: "D апгрейды" },
  { id: "NG_TO_D", label: "NG → D обмен" },
];

export const UPGRADE_KINDS: { id: UpgradeKind; label: string; icon: string }[] = [
  { id: "physical", label: "Оружие физ.", icon: "⚔" },
  { id: "magic", label: "Оружие маг.", icon: "✦" },
  { id: "armor", label: "Броня", icon: "🛡" },
  { id: "jewelry", label: "Бижутерия", icon: "💍" },
];

export const KIND_LABELS: Record<string, string> = {
  physical: "Физическое оружие",
  magic: "Магическое оружие",
  armor: "Броня",
  jewelry: "Бижутерия",
};

export function upgradeItem(catalog: WeaponUpgradesCatalog, id: number): UpgradeItem | null {
  return catalog.items[String(id)] ?? null;
}

export function formatAdena(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("ru-RU");
}

export function weaponStatParts(item: UpgradeItem | null): string[] {
  if (!item) return [];
  const parts: string[] = [];
  if (item.p_atk != null) parts.push(`Ф.атк ${item.p_atk}`);
  if (item.m_atk != null) parts.push(`М.атк ${item.m_atk}`);
  if (item.p_def != null) parts.push(`Ф.защ ${item.p_def}`);
  if (item.m_def != null) parts.push(`М.защ ${item.m_def}`);
  return parts;
}

export function weaponStatLine(item: UpgradeItem | null): string | null {
  const parts = weaponStatParts(item);
  return parts.length ? parts.join(" · ") : null;
}

const STAT_DELTA_LABELS: { key: keyof UpgradeItem; label: string }[] = [
  { key: "p_atk", label: "Ф.атк" },
  { key: "m_atk", label: "М.атк" },
  { key: "p_def", label: "Ф.защ" },
  { key: "m_def", label: "М.защ" },
];

export function weaponStatDelta(from: UpgradeItem | null, to: UpgradeItem | null): string | null {
  if (!from || !to) return null;
  const chunks: string[] = [];
  for (const { key, label } of STAT_DELTA_LABELS) {
    const a = from[key];
    const b = to[key];
    if (typeof a === "number" && typeof b === "number" && a !== b) {
      const diff = b - a;
      chunks.push(`${label} ${diff > 0 ? "+" : ""}${diff}`);
    }
  }
  return chunks.length ? chunks.join(" · ") : null;
}

export function availableGradesForKind(
  catalog: WeaponUpgradesCatalog,
  kind: UpgradeKind,
): ("NG" | "D")[] {
  const grades: ("NG" | "D")[] = [];
  for (const grade of ["NG", "D"] as const) {
    if (catalog.upgrades.some((u) => u.kind === kind && u.grade === grade)) {
      grades.push(grade);
    }
  }
  return grades;
}

export function categoriesForTab(
  catalog: WeaponUpgradesCatalog,
  tab: "NG" | "D",
  kind: UpgradeKind,
): { id: string; label: string; kind: string }[] {
  const seen = new Map<string, { id: string; label: string; kind: string }>();
  for (const row of catalog.upgrades) {
    if (row.grade !== tab || row.kind !== kind) continue;
    const key = `${row.kind}:${row.category}`;
    if (!seen.has(key)) {
      seen.set(key, { id: row.category, label: row.category_label, kind: row.kind });
    }
  }
  return [...seen.values()];
}

export function upgradesForCategory(
  catalog: WeaponUpgradesCatalog,
  grade: "NG" | "D",
  category: string,
  kind: UpgradeKind,
): WeaponUpgradeRow[] {
  return catalog.upgrades.filter(
    (u) => u.grade === grade && u.category === category && u.kind === kind,
  );
}
