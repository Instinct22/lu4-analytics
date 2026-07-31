import { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getItemSources } from "../../api/items";
import { itemInfo, type CalcNode, type CraftCatalog } from "../../lib/craftCalc";
import { currentReturnPath, resourceNpcPagePath } from "../../lib/internalNav";

interface Props {
  tree: CalcNode;
  catalog: CraftCatalog;
}

function leafIds(node: CalcNode, acc: Set<number> = new Set()): Set<number> {
  if (!node.children.length) {
    acc.add(node.id);
    return acc;
  }
  for (const child of node.children) leafIds(child, acc);
  return acc;
}

function MaterialSourcesBlock({
  materialId,
  name,
  from,
}: {
  materialId: number;
  name: string;
  from: string;
}) {
  const { data } = useQuery({
    queryKey: ["item-sources", materialId],
    queryFn: () => getItemSources(materialId),
    staleTime: 5 * 60_000,
  });

  if (!data || (!data.drops.length && !data.spoils.length)) return null;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
      <p className="mb-2 text-sm font-medium text-zinc-200">{name}</p>
      {data.spoils.slice(0, 3).map((row, i) => (
        <div key={`s-${i}`} className="text-xs text-zinc-500">
          Спойл:{" "}
          <Link
            to={resourceNpcPagePath(row.npc_id, { materialId, from })}
            className="text-amber-400 hover:underline"
          >
            {row.npc_name}
          </Link>{" "}
          · {row.chance}
        </div>
      ))}
      {data.drops.slice(0, 3).map((row, i) => (
        <div key={`d-${i}`} className="text-xs text-zinc-500">
          Дроп:{" "}
          <Link
            to={resourceNpcPagePath(row.npc_id, { materialId, from })}
            className="text-amber-400 hover:underline"
          >
            {row.npc_name}
          </Link>{" "}
          · {row.chance}
        </div>
      ))}
    </div>
  );
}

export default function CraftMaterialSources({ tree, catalog }: Props) {
  const location = useLocation();
  const from = currentReturnPath(location);
  const leaves = useMemo(() => [...leafIds(tree)].slice(0, 8), [tree]);

  if (!leaves.length) return null;

  return (
    <details className="mb-4 rounded-xl border border-zinc-800 bg-zinc-900/30 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-zinc-300">
        Источники материалов (листья рецепта)
      </summary>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {leaves.map((id) => (
          <MaterialSourcesBlock key={id} materialId={id} name={itemInfo(catalog, id).name} from={from} />
        ))}
      </div>
    </details>
  );
}
