import type { ItemEncyclopediaEntry } from "../api/items";
import { wikiItemUrl, WIKI_BASE } from "./characterData";

export type { ItemEncyclopediaEntry };

/** External masterwork.wiki URL for an item (original wiki). */
export function masterworkItemUrl(
  entry: Pick<ItemEncyclopediaEntry, "id" | "name" | "slug">,
): string {
  if (entry.slug) {
    return `${WIKI_BASE}/lu4/item/${entry.id}-${entry.slug}`;
  }
  return wikiItemUrl(entry.id, entry.name);
}

export function masterworkSetUrl(id: number, slug?: string | null): string {
  if (slug) return `${WIKI_BASE}/lu4/set/${id}-${slug}`;
  return `${WIKI_BASE}/lu4/set/${id}`;
}

export function restrictionLabels(): Record<string, string> {
  return {
    private_warehouse: "Личный склад",
    clan_warehouse: "Клановый склад",
    transfer_within_account: "Передача в аккаунте",
    trade: "Торговля",
    drop: "Дроп",
    private_store: "Личная лавка",
    enchant: "Заточка",
    attribute: "Атрибут",
    olympiad_use: "Олимпиада",
  };
}

export function statRows(entry: ItemEncyclopediaEntry): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [];
  const labels: Record<string, string> = {
    p_atk: "Физ. атака",
    m_atk: "Маг. атака",
    p_def: "Физ. защита",
    m_def: "Маг. защита",
    shield_def: "Защита щита",
    crystals: "Кристаллы",
    weight: "Вес",
    accuracy: "Точность",
    evasion: "Уклонение",
    crit_rate: "Крит",
    mp_bonus: "MP бонус",
    mp_consume: "Расход MP",
  };
  const stats = entry.stats ?? {};
  for (const [key, label] of Object.entries(labels)) {
    const val = stats[key];
    if (val != null) rows.push({ label, value: String(val) });
  }
  if (entry.weight != null && !stats.weight) {
    rows.push({ label: "Вес", value: String(entry.weight) });
  }
  if (entry.npc_sell != null) {
    rows.push({ label: "Цена NPC", value: entry.npc_sell.toLocaleString("ru-RU") });
  }
  return rows;
}

export const OTHER_SUB_LABELS: Record<string, string> = {
  materials: "Материалы",
  recipes: "Рецепты",
  consumables: "Расходники",
  soulshots: "Соулшоты",
  sealed: "Sealed",
  jewelry: "Бижутерия",
  misc: "Разное",
  money: "Деньги",
};

export function filterOtherItems(
  items: ItemEncyclopediaEntry[],
  q: string,
  grade: string | null,
  sub: string | null,
): ItemEncyclopediaEntry[] {
  const query = q.trim().toLowerCase();
  return items
    .filter((it) => {
      if (/^#\d+$/i.test(it.name.trim())) return false;
      if (grade && it.grade !== grade) return false;
      if (sub && (it.other_subcategory || "misc") !== sub) return false;
      if (query && !it.name.toLowerCase().includes(query)) return false;
      return true;
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}
