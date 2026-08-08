import api from "./client";
import type { RaidBossesPayload } from "../lib/raidBosses";

export type RaidTimerDto = {
  bossId: number;
  killedAt: string;
  updatedAt: string | null;
};

export type RaidNoteDto = {
  bossId: number;
  note: string;
};

export async function getRaidBosses(): Promise<RaidBossesPayload> {
  const { data } = await api.get("/raid/bosses");
  return data;
}

export async function getRaidTimers(): Promise<RaidTimerDto[]> {
  const { data } = await api.get("/raid/timers");
  return data.timers ?? [];
}

export async function setRaidTimer(bossId: number, killedAt?: Date): Promise<RaidTimerDto> {
  const { data } = await api.post(`/raid/timers/${bossId}`, {
    killed_at: killedAt ? killedAt.toISOString() : null,
  });
  return data;
}

export async function clearRaidTimer(bossId: number): Promise<void> {
  await api.delete(`/raid/timers/${bossId}`);
}

export async function getRaidNotes(): Promise<RaidNoteDto[]> {
  const { data } = await api.get("/raid/notes");
  return data.notes ?? [];
}

export async function putRaidNote(bossId: number, note: string): Promise<RaidNoteDto> {
  const { data } = await api.put(`/raid/notes/${bossId}`, { note });
  return data;
}

export type RaidVisibilityPayload = {
  hiddenIds: number[];
};

export async function getRaidVisibility(): Promise<RaidVisibilityPayload> {
  const { data } = await api.get("/raid/visibility");
  return { hiddenIds: Array.isArray(data?.hiddenIds) ? data.hiddenIds : [] };
}

export async function putRaidVisibility(hiddenIds: number[]): Promise<RaidVisibilityPayload> {
  const { data } = await api.put("/raid/visibility", { hiddenIds });
  return { hiddenIds: Array.isArray(data?.hiddenIds) ? data.hiddenIds : [] };
}
