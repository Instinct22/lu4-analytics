import api from "./client";
import type { ClassData, RacesResponse, SkillData } from "../lib/characterData";

export async function getCharacterRaces(): Promise<RacesResponse> {
  const { data } = await api.get("/character/races");
  return data;
}

export async function getCharacterClass(classId: number): Promise<ClassData> {
  const { data } = await api.get(`/character/classes/${classId}`);
  return data;
}

export async function getCharacterSkill(skillId: number): Promise<SkillData> {
  const { data } = await api.get(`/character/skills/${skillId}`);
  return data;
}
