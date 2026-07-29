import { useMemo, useState } from "react";
import {
  buildTree,
  effectivePrice,
  formatPrice,
  isCraftable,
  itemInfo,
  shoppingItems,
  type CalcNode,
  type CraftCatalog,
  type PriceInfo,
  type RollupEntry,
} from "../../lib/craftCalc";
import { GradePill, HaveInput, ItemIcon } from "./CraftCostBar";
import CraftItemLink from "./CraftItemLink";
import CraftTreeNode from "./CraftTreeNode";
import ExpandChevron from "./ExpandChevron";

interface Props {
  catalog: CraftCatalog;
  tree?: CalcNode;
  entries?: RollupEntry[];
  owned: Record<string, number>;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  showPrices?: boolean;
  title?: string;
  subtitle?: string;
}

function ShoppingRow({
  entry,
  catalog,
  owned,
  prices,
  manual,
  onOwnedChange,
  showPrices = false,
}: {
  entry: RollupEntry;
  catalog: CraftCatalog;
  owned: Record<string, number>;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  showPrices?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const info = itemInfo(catalog, entry.id);
  const still = entry.still;
  const price = showPrices ? effectivePrice(entry.id, prices, manual, catalog) : null;
  const total = price != null ? price * still : null;
  // Prefer catalog recipe so merged rows (e.g. VoP from several branches) still decompose.
  const canExpand = (entry.craftable || isCraftable(catalog, entry.id)) && still > 0;

  const composition = useMemo(() => {
    if (!expanded || !canExpand) return null;
    // Ignore owned of this product — `still` is already net; keep ingredient owned.
    const ownedForParts = { ...owned };
    delete ownedForParts[String(entry.id)];
    return buildTree(catalog, entry.id, still, ownedForParts);
  }, [expanded, canExpand, catalog, entry.id, still, owned]);

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/50">
      <div className="flex items-center gap-3 px-3 py-2.5">
        {canExpand ? (
          <button
            type="button"
            className={`expand-toggle ${expanded ? "expand-toggle--open" : ""}`}
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? "Свернуть" : "Развернуть"}
          >
            <ExpandChevron open={expanded} />
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}
        <ItemIcon id={entry.id} size={36} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <CraftItemLink
              id={entry.id}
              name={info.name}
              catalog={catalog}
              className="break-words font-semibold text-zinc-100 hover:text-amber-400 hover:underline"
            />
            <GradePill grade={info.grade} />
            {canExpand && (
              <span className="rounded-full bg-amber-950/80 px-2 py-0.5 text-[0.65rem] font-medium text-amber-300">
                можно скрафтить
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
            <label className="flex items-center gap-1.5">
              Есть
              <HaveInput
                value={owned[String(entry.id)] ?? ""}
                onChange={(v) => onOwnedChange(entry.id, v)}
              />
            </label>
            {entry.owned > 0 && (
              <span className="text-emerald-400">
                учтено {entry.owned} из {entry.need}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-lg font-bold tabular-nums text-zinc-100">×{still}</div>
          {showPrices && (
            <div className="text-sm font-semibold tabular-nums text-amber-400">
              {total != null ? formatPrice(total) : "—"}
            </div>
          )}
        </div>
      </div>
      {expanded && composition && composition.children.length > 0 && (
        <div className="border-t border-zinc-800/80 bg-zinc-950/40 px-3 py-2">
          <p className="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-zinc-600">
            Состав для крафта ×{still}
          </p>
          {composition.children.map((ch, i) => (
            <CraftTreeNode
              key={`${ch.id}-${i}`}
              node={ch}
              catalog={catalog}
              prices={prices}
              manual={manual}
              owned={owned}
              onOwnedChange={onOwnedChange}
              depth={0}
              showPrices={showPrices}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CraftShoppingList({
  catalog,
  tree,
  entries: entriesProp,
  owned,
  prices,
  manual,
  onOwnedChange,
  showPrices = false,
  title = "Список покупок",
  subtitle = "Одинаковые ресурсы из разных веток объединены. Разверните крафтовые — чтобы увидеть состав.",
}: Props) {
  const items = entriesProp ?? (tree ? shoppingItems(catalog, tree) : []);

  return (
    <div className="space-y-2">
      {title ? (
        <div className="mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-zinc-600">{subtitle}</p>}
        </div>
      ) : null}
      {items.length === 0 && (
        <p className="rounded-xl border border-dashed border-zinc-700 px-4 py-6 text-center text-sm text-zinc-500">
          Все материалы уже есть
        </p>
      )}
      {items.map((e) => (
        <ShoppingRow
          key={e.id}
          entry={e}
          catalog={catalog}
          owned={owned}
          prices={prices}
          manual={manual}
          onOwnedChange={onOwnedChange}
          showPrices={showPrices}
        />
      ))}
    </div>
  );
}
