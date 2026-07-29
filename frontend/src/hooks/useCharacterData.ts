import { useQuery } from "@tanstack/react-query";
import { getCharacterClass, getCharacterRaces, getCharacterSkill } from "../api/character";

const HOUR = 1000 * 60 * 60;

/** Race trees with class names, slugs and icons — a few kilobytes. */
export function useCharacterRaces() {
  return useQuery({
    queryKey: ["character", "races"],
    queryFn: getCharacterRaces,
    staleTime: HOUR,
  });
}

export function useCharacterClass(classId: number | null) {
  return useQuery({
    queryKey: ["character", "class", classId],
    queryFn: () => getCharacterClass(classId!),
    enabled: classId != null,
    staleTime: HOUR,
  });
}

export function useCharacterSkill(skillId: number | null) {
  return useQuery({
    queryKey: ["character", "skill", skillId],
    queryFn: () => getCharacterSkill(skillId!),
    enabled: skillId != null,
    staleTime: HOUR,
  });
}
