export interface UpgradeItem {
  id: number;
  name: string;
  grade: string;
  icon?: string | null;
  npc_sell?: number | null;
  p_atk?: number | null;
  m_atk?: number | null;
}

export interface WeaponUpgradeRow {
  grade: string;
  kind: "physical" | "magic";
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

export const KIND_LABELS: Record<string, string> = {
  physical: "Физическое",
  magic: "Магическое",
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
  if (item.p_atk != null) parts.push(`Физ. ${item.p_atk}`);
  if (item.m_atk != null) parts.push(`Маг. ${item.m_atk}`);
  return parts;
}

export function weaponStatLine(item: UpgradeItem | null): string | null {
  const parts = weaponStatParts(item);
  return parts.length ? parts.join(" · ") : null;
}

export function weaponStatDelta(from: UpgradeItem | null, to: UpgradeItem | null): string | null {
  if (!from || !to) return null;
  const chunks: string[] = [];
  if (from.p_atk != null && to.p_atk != null && from.p_atk !== to.p_atk) {
    const diff = to.p_atk - from.p_atk;
    chunks.push(`Физ. ${diff > 0 ? "+" : ""}${diff}`);
  }
  if (from.m_atk != null && to.m_atk != null && from.m_atk !== to.m_atk) {
    const diff = to.m_atk - from.m_atk;
    chunks.push(`Маг. ${diff > 0 ? "+" : ""}${diff}`);
  }
  return chunks.length ? chunks.join(" · ") : null;
}

export function categoriesForTab(
  catalog: WeaponUpgradesCatalog,
  tab: "NG" | "D",
): { id: string; label: string; kind: string }[] {
  const seen = new Map<string, { id: string; label: string; kind: string }>();
  for (const row of catalog.upgrades) {
    if (row.grade !== tab) continue;
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
): WeaponUpgradeRow[] {
  return catalog.upgrades.filter((u) => u.grade === grade && u.category === category);
}
