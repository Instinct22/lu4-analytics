import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getWikiEntity, getWikiGraph } from "../api/wiki";
import { ItemIcon } from "../components/craft/CraftCostBar";
import WikiArticleBody from "../components/wiki/WikiArticleBody";
import { PageHeader, LoadingState, ErrorState } from "../components/ui";
import { ReturnLinkBar } from "../components/ui/ReturnLinkBar";
import { returnLinkFromParam, wikiPagePath } from "../lib/internalNav";

const CONTENT_LIMIT = 12000;

export default function WikiArticle() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const returnPath = searchParams.get("from");
  const returnLink = useMemo(() => returnLinkFromParam(returnPath), [returnPath]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["wiki-entity", id],
    queryFn: () => getWikiEntity(id!),
    enabled: !!id,
  });

  const { data: related } = useQuery({
    queryKey: ["wiki-graph", id],
    queryFn: () => getWikiGraph(id!),
    enabled: !!id,
  });

  if (isLoading) return <LoadingState />;
  if (error || !data) return <ErrorState message="Статья не найдена" />;

  const hasStats = data.stats && Object.keys(data.stats).length > 0;
  const hasRelated = related?.length > 0;
  const hasAside = hasStats || hasRelated || (data.entity_type === "item" && data.external_id != null);
  const contentMd = data.content_md?.slice(0, CONTENT_LIMIT) ?? null;

  return (
    <div>
      <ReturnLinkBar link={returnLink} />
      <PageHeader title={data.display_name} />
      <p className="mb-4 text-sm text-zinc-500">
        {data.entity_type}
        {data.url ? ` · ${String(data.url).split("?")[0]}` : ""}
      </p>

      <div
        className={`grid gap-6 ${
          hasAside ? "xl:grid-cols-[minmax(0,1fr)_minmax(18rem,24rem)] xl:items-start" : ""
        }`}
      >
        <div className="card">
          <WikiArticleBody
            contentMd={contentMd}
            displayName={data.display_name}
            entityType={data.entity_type}
          />
        </div>

        {hasAside && (
          <aside className="space-y-4 xl:sticky xl:top-6">
            {data.entity_type === "item" && data.external_id != null && (
              <div className="card flex items-center justify-center">
                <ItemIcon id={data.external_id} size={64} />
              </div>
            )}
            {hasStats && (
              <div className="card">
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-zinc-400">
                  Характеристики
                </h3>
                <dl className="space-y-1 text-sm text-zinc-300">
                  {Object.entries(data.stats).map(([k, v]) => (
                    <div key={k}>
                      <span className="font-medium text-zinc-200">{k}:</span> {String(v)}
                    </div>
                  ))}
                </dl>
              </div>
            )}
            {hasRelated && (
              <div className="card">
                <h3 className="mb-2 font-semibold text-zinc-200">Связанные</h3>
                <ul className="space-y-1 text-sm">
                  {related.map((r: { id: string; entity_type: string; display_name: string }) => (
                    <li key={r.id}>
                      <Link
                        to={wikiPagePath(r.entity_type, r.id, returnPath)}
                        className="text-amber-400 hover:underline"
                      >
                        {r.display_name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
