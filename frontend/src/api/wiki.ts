import api from "./client";

export async function getWikiEntity(id: string) {
  const { data } = await api.get(`/wiki/entities/${id}`);
  return data;
}

export async function getWikiGraph(id: string) {
  const { data } = await api.get(`/wiki/entities/${id}/graph`);
  return data;
}

export async function getWikiEntityByExternal(entityType: string, externalId: number) {
  const { data } = await api.get(`/wiki/entities/by-external/${entityType}/${externalId}`);
  return data;
}

export async function getNpcLoot(npcId: number) {
  const { data } = await api.get(`/wiki/npc/${npcId}/loot`);
  return data;
}
