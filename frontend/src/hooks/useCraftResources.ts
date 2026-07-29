import { useQuery } from "@tanstack/react-query";
import { getCraftResources, getMaterialSources, getNpcMaterials } from "../api/craft";

/** Material list without spoil/drop rows: those are loaded per material. */
export function useCraftResources(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["craft", "resources"],
    queryFn: getCraftResources,
    staleTime: 1000 * 60 * 60,
    enabled: options?.enabled ?? true,
  });
}

export function useMaterialSources(materialId: number | null) {
  return useQuery({
    queryKey: ["craft", "resources", "sources", materialId],
    queryFn: () => getMaterialSources(materialId!),
    enabled: materialId != null,
    staleTime: 1000 * 60 * 30,
  });
}

export function useNpcMaterials(npcId: number | null) {
  return useQuery({
    queryKey: ["craft", "resources", "npc", npcId],
    queryFn: () => getNpcMaterials(npcId!),
    enabled: npcId != null,
    staleTime: 1000 * 60 * 30,
  });
}
