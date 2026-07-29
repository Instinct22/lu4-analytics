/** In-app navigation paths — no external wiki URLs. */

export function itemPagePath(id: number): string {
  return `/items?id=${id}`;
}

export function setPagePath(setId: string): string {
  return `/items?set=${encodeURIComponent(setId)}`;
}

export function characterSkillPath(skillId: number): string {
  return `/character?skill=${skillId}`;
}
