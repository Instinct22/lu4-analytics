import api from "./client";
import type { RaidBossesPayload } from "../lib/raidBosses";

export type RaidTimerDto = {
  bossId: number;
  killedAt: string;
  updatedAt: string | null;
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
