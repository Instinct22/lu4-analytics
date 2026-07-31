/** In-app navigation paths — no external wiki URLs. */

export function currentReturnPath(location: { pathname: string; search: string }): string {
  return `${location.pathname}${location.search}`;
}

export function itemPagePath(id: number, from?: string | null): string {
  const params = new URLSearchParams({ id: String(id) });
  if (from) params.set("from", from);
  return `/items?${params.toString()}`;
}

export function resourcePagePath(id: number, from?: string | null): string {
  const params = new URLSearchParams({ id: String(id) });
  if (from) params.set("from", from);
  return `/resources?${params.toString()}`;
}

export function resourceNpcPagePath(
  npcId: number,
  opts?: { materialId?: number | null; from?: string | null },
): string {
  const params = new URLSearchParams({ npc: String(npcId) });
  if (opts?.materialId != null) params.set("id", String(opts.materialId));
  if (opts?.from) params.set("from", opts.from);
  return `/resources?${params.toString()}`;
}

export function wikiPagePath(entityType: string, entityId: string, from?: string | null): string {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  const query = params.toString();
  return query ? `/wiki/${entityType}/${entityId}?${query}` : `/wiki/${entityType}/${entityId}`;
}

export function setPagePath(setId: string): string {
  return `/items?set=${encodeURIComponent(setId)}`;
}

export function characterSkillPath(skillId: number): string {
  return `/character?skill=${skillId}`;
}

/** Only allow same-origin relative paths (open redirect guard). */
export function isSafeReturnPath(path: string | null | undefined): path is string {
  return !!path && path.startsWith("/") && !path.startsWith("//");
}

export function returnPathLabel(path: string): string {
  if (path.startsWith("/craft/upgrades")) return "Апгрейд NG/D";
  if (path.startsWith("/craft/bulk")) return "Склад";
  if (path.startsWith("/craft")) return "Крафт";
  if (path.startsWith("/resources")) return "Ресурсы";
  if (path.startsWith("/items")) return "Предметы";
  if (path.startsWith("/character")) return "Персонаж";
  return "Назад";
}

export interface ReturnLink {
  href: string;
  label: string;
}

export function returnLinkFromParam(from: string | null | undefined): ReturnLink | null {
  if (!isSafeReturnPath(from)) return null;
  return { href: from, label: returnPathLabel(from) };
}
