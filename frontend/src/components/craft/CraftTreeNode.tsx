import { useState } from "react";
import {
  effectivePrice,
  formatPrice,
  isCraftable,
  itemInfo,
  type CalcNode,
  type CraftCatalog,
  type CraftPricePeriod,
  type PriceInfo,
} from "../../lib/craftCalc";
import { GradePill, HaveInput, ItemIcon, ItemPrice } from "./CraftCostBar";
import CraftItemLink from "./CraftItemLink";
import ExpandChevron from "./ExpandChevron";

interface Props {
  node: CalcNode;
  catalog: CraftCatalog;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
  owned: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  depth?: number;
  showPrices?: boolean;
  period?: CraftPricePeriod;
}

export default function CraftTreeNode({
  node,
  catalog,
  prices,
  manual,
  owned,
  onOwnedChange,
  depth = 0,
  showPrices = false,
  period = "main",
}: Props) {
  const info = itemInfo(catalog, node.id);
  const hasChildren = node.children.length > 0;
  const [expanded, setExpanded] = useState(false);
  const craftable = isCraftable(catalog, node.id) && hasChildren;
  const covered = node.want > node.net;

  const buyPrice = showPrices ? effectivePrice(node.id, prices, manual, catalog, period) : null;
  let craftSubtotal = 0;
  let craftOk = true;
  if (showPrices) {
    for (const c of node.children) {
      const p = effectivePrice(c.id, prices, manual, catalog, period);
      if (p == null) craftOk = false;
      else craftSubtotal += p * c.net;
    }
  }

  return (
    <div style={{ marginLeft: depth * 14 }}>
      <div className="craft-tree-row group flex items-center gap-2">
        {hasChildren ? (
          <button
            type="button"
            className={`expand-toggle ${expanded ? "expand-toggle--open" : ""}`}
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? "Свернуть" : "Развернуть"}
            aria-expanded={expanded}
          >
            <ExpandChevron open={expanded} />
          </button>
        ) : (
          <span className="w-5 shrink-0" aria-hidden />
        )}
        <ItemIcon id={node.id} size={24} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <CraftItemLink
              id={node.id}
              name={info.name}
              catalog={catalog}
              className="break-words text-sm font-medium text-zinc-100 hover:text-amber-400 hover:underline"
            />
            <GradePill grade={info.grade} />
            {node.recipeScroll && (
              <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[0.6rem] font-semibold uppercase text-amber-200">
                рецепт
              </span>
            )}
            {craftable && (
              <span className="rounded bg-zinc-700/80 px-1.5 py-0.5 text-[0.6rem] font-medium text-zinc-300">
                крафт
              </span>
            )}
          </div>
          <div className="text-xs text-zinc-500">
            Всего ×{node.want}
            {covered && (
              <span className="ml-1.5 font-medium text-emerald-400">→ нужно ×{node.net}</span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <label className="flex items-center gap-1.5 text-xs text-zinc-500">
            Есть
            <HaveInput
              value={owned[String(node.id)] ?? ""}
              onChange={(v) => onOwnedChange(node.id, v)}
            />
          </label>
          {showPrices && craftable && craftOk && buyPrice != null && node.net > 0 && (
            <span className="text-[0.65rem] text-zinc-600">
              крафт {formatPrice(craftSubtotal)} · купить {formatPrice(buyPrice * node.net)}
            </span>
          )}
          {showPrices && node.net > 0 && (
            <ItemPrice
              id={node.id}
              qty={node.net}
              catalog={catalog}
              prices={prices}
              manual={manual}
              period={period}
            />
          )}
        </div>
      </div>
      {expanded &&
        node.children.map((ch, i) => (
          <CraftTreeNode
            key={`${ch.id}-${i}`}
            node={ch}
            catalog={catalog}
            prices={prices}
            manual={manual}
            owned={owned}
            onOwnedChange={onOwnedChange}
            period={period}
            depth={depth + 1}
            showPrices={showPrices}
          />
        ))}
    </div>
  );
}
