import { useQuery } from "@tanstack/react-query";
import { getNpcLoot } from "../api/wiki";

export interface NpcItemLootEntry {
  item_id: number;
  item_name: string;
  item_grade: string;
  item_url: string;
  amount: string;
  chance: string;
  chance_val: number;
}

export interface NpcLootResponse {
  spoils: NpcItemLootEntry[];
  drops: NpcItemLootEntry[];
}

export function useNpcLoot(npcId: number | null) {
  return useQuery({
    queryKey: ["npc-loot", npcId],
    queryFn: async () => (await getNpcLoot(npcId!)) as NpcLootResponse,
    enabled: npcId != null,
    staleTime: 1000 * 60 * 60,
  });
}
