import api from "./client";

export type QuestNpc = {
  id: number | null;
  name: string;
  icon?: string | null;
};

export type QuestReward = {
  item_id: number | null;
  name: string;
  grade?: string | null;
  icon?: string | null;
  qty?: number | null;
};

export type QuestStep = {
  title: string;
  text: string;
  images: string[];
};

export type QuestBrief = {
  id: number;
  slug: string;
  name: string;
  level_min: number | null;
  level_max: number | null;
  description: string;
  start_npc: QuestNpc | null;
  reward_count: number;
};

export type QuestDetail = {
  id: number;
  slug: string;
  name: string;
  url?: string | null;
  source_url?: string | null;
  level_min: number | null;
  level_max: number | null;
  description: string;
  start_npc: QuestNpc | null;
  rewards: QuestReward[];
  steps: QuestStep[];
};

export type QuestCatalogResponse = {
  quests: QuestBrief[];
  count: number;
  generated_at?: string | null;
};

export async function getQuests(params?: {
  min_level?: number;
  max_level?: number;
  q?: string;
}): Promise<QuestCatalogResponse> {
  const { data } = await api.get("/quests", { params });
  return data;
}

export async function getQuest(id: number): Promise<QuestDetail> {
  const { data } = await api.get(`/quests/${id}`);
  return data;
}
