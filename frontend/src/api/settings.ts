import api from "./client";
import type { LevelRange } from "../lib/levelRange";

export async function getLevelRestriction(): Promise<LevelRange> {
  const { data } = await api.get("/settings/level-restriction");
  return { min: data.min, max: data.max };
}

export async function getLevelPreset(): Promise<LevelRange> {
  const { data } = await api.get("/settings/level-preset");
  return { min: data.min, max: data.max };
}
