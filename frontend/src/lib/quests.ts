/** Quest helpers shared by list + detail UI. */

import { mediaUrl } from "../api/client";

export const QUEST_LEVEL_FALLBACK_MAX = 99;

export function formatQuestLevel(
  levelMin: number | null | undefined,
  levelMax: number | null | undefined,
): string {
  if (levelMin == null && levelMax == null) return "—";
  if (levelMin != null && levelMax == null) return `${levelMin}+`;
  if (levelMin != null && levelMax != null) {
    if (levelMin === levelMax) return String(levelMin);
    return `${levelMin}–${levelMax}`;
  }
  return String(levelMax);
}

export function effectiveQuestLevelMax(
  levelMin: number | null | undefined,
  levelMax: number | null | undefined,
): number | null {
  if (levelMax != null) return levelMax;
  if (levelMin != null) return QUEST_LEVEL_FALLBACK_MAX;
  return null;
}

/** Quest is available when its level window intersects the filter range. */
export function questOverlapsLevelRange(
  levelMin: number | null | undefined,
  levelMax: number | null | undefined,
  filterMin: number,
  filterMax: number,
): boolean {
  if (levelMin == null && levelMax == null) return true;
  const qMin = levelMin ?? 0;
  const qMax = effectiveQuestLevelMax(levelMin, levelMax) ?? QUEST_LEVEL_FALLBACK_MAX;
  return qMin <= filterMax && qMax >= filterMin;
}

export function i64IconUrl(icon: string | null | undefined): string | null {
  if (!icon) return null;
  if (icon.startsWith("http") || icon.startsWith("/media/")) return icon;
  const file = icon.replace(/^\/?i64\//, "").replace(/^\/+/, "");
  return mediaUrl(`images/i64/${file}`);
}

/** Remote wiki upload paths are not mirrored locally — keep absolute wiki URL. */
export function questStepImageUrl(src: string | null | undefined): string | null {
  if (!src) return null;
  if (src.startsWith("http")) return src;
  if (src.startsWith("/upload/")) return `https://masterwork.wiki${src}`;
  if (src.startsWith("/i64/")) return i64IconUrl(src);
  return src;
}
