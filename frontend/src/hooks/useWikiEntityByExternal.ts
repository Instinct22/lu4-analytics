import { useQuery } from "@tanstack/react-query";
import { getWikiEntityByExternal } from "../api/wiki";

export interface WikiEntityDetail {
  id: string;
  entity_type: string;
  external_id: number | null;
  display_name: string;
  name: string;
  url: string;
  summary: string | null;
  image_path: string | null;
  stats: Record<string, unknown> | null;
  content_md: string | null;
}

export function useWikiEntityByExternal(entityType: string, externalId: number | null) {
  return useQuery({
    queryKey: ["wiki-by-external", entityType, externalId],
    queryFn: async () =>
      (await getWikiEntityByExternal(entityType, externalId!)) as WikiEntityDetail,
    enabled: externalId != null,
    staleTime: 1000 * 60 * 30,
  });
}
