import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  buildTree,
  formatPrice,
  isCraftable,
  isCraftReady,
  itemInfo,
  treeCost,
  cartEntryKey,
  formatVariantRate,
  variantsFor,
  type CartEntry,
  type CraftCatalog,
  type PriceInfo,
} from "../../lib/craftCalc";
import { GradePill, ItemIcon } from "./CraftCostBar";
import CraftShoppingList from "./CraftShoppingList";
import CraftTreeNode from "./CraftTreeNode";
import ExpandChevron from "./ExpandChevron";

interface Props {
  catalog: CraftCatalog;
  entries: CartEntry[];
  owned: Record<string, number>;
  chosenVariants: Record<string, number>;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  onQtyChange: (productId: number, qty: number, variantIdx: number) => void;
  onRemove: (productId: number, variantIdx: number) => void;
  onCraft: (productId: number, variantIdx: number) => void;
  showPrices?: boolean;
  showApproxCost?: boolean;
  recipesLoading?: boolean;
}

function CraftBulkCartRow({
  catalog,
  entry,
  owned,
  chosenVariants,
  prices,
  manual,
  onOwnedChange,
  onQtyChange,
  onRemove,
  onCraft,
  showPrices,
  showApproxCost = true,
}: {
  catalog: CraftCatalog;
  entry: CartEntry;
  owned: Record<string, number>;
  chosenVariants: Record<string, number>;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
  onOwnedChange: (id: number, val: number) => void;
  onQtyChange: (productId: number, qty: number, variantIdx: number) => void;
  onRemove: (productId: number, variantIdx: number) => void;
  onCraft: (productId: number, variantIdx: number) => void;
  showPrices?: boolean;
  showApproxCost?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [detailTab, setDetailTab] = useState<"tree" | "list">("tree");

  const variantIdx = entry.variantIdx;
  const info = itemInfo(catalog, entry.productId);
  const variants = variantsFor(catalog, entry.productId);
  const variant = variants[variantIdx];
  const variantLabel = formatVariantRate(variant);
  const craftable = isCraftable(catalog, entry.productId);

  const tree = useMemo(
    () =>
      craftable
        ? buildTree(catalog, entry.productId, entry.qty, owned, variantIdx, chosenVariants)
        : null,
    [catalog, entry.productId, entry.qty, owned, variantIdx, chosenVariants, craftable],
  );

  const approxCost = useMemo(() => {
    if (!tree) return null;
    return treeCost(tree, catalog, prices, manual).cost;
  }, [tree, catalog, prices, manual]);

  const canCraft = useMemo(
    () => Boolean(tree && isCraftReady(catalog, tree)),
    [catalog, tree],
  );

  const canExpand = craftable && Boolean(tree);

  const tabBtn = (id: "tree" | "list", label: string) => (
    <button
      type="button"
      className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition-colors ${
        detailTab === id
          ? "bg-amber-600 text-zinc-950 shadow-sm"
          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
      }`}
      onClick={() => setDetailTab(id)}
    >
      {label}
    </button>
  );

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/50">
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          disabled={!canExpand}
          aria-label={expanded ? "Свернуть крафт" : "Развернуть крафт"}
          aria-expanded={expanded}
          onClick={() => canExpand && setExpanded((v) => !v)}
          className={`expand-toggle ${expanded ? "expand-toggle--open" : ""}`}
        >
          {canExpand ? <ExpandChevron open={expanded} /> : null}
        </button>
        <ItemIcon id={entry.productId} size={40} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Link
              to={`/craft?id=${entry.productId}`}
              className="font-semibold text-zinc-100 hover:text-amber-400 hover:underline"
            >
              {info.name}
            </Link>
            <GradePill grade={info.grade} />
            {variants.length > 1 && (
              <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[0.65rem] text-zinc-400">
                {variantLabel || `вариант ${variantIdx + 1}/${variants.length}`}
              </span>
            )}
          </div>
        </div>
        {showApproxCost && (
          <div className="shrink-0 text-right" title="Ориентировочная стоимость крафта">
            <span className="block text-[0.6rem] uppercase tracking-wide text-zinc-600">~стоимость</span>
            <span className="text-sm font-semibold tabular-nums text-amber-400/90">
              {approxCost != null && approxCost > 0 ? formatPrice(approxCost) : "—"}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1 rounded-xl border border-zinc-700/80 bg-zinc-800/80 px-1.5 py-0.5">
          <button
            type="button"
            className="flex h-6 w-6 items-center justify-center rounded-lg text-zinc-300 transition-colors hover:bg-zinc-700"
            onClick={() => onQtyChange(entry.productId, entry.qty - 1, variantIdx)}
          >
            −
          </button>
          <span className="min-w-[1.5rem] text-center text-sm font-bold tabular-nums text-zinc-100">
            {entry.qty}
          </span>
          <button
            type="button"
            className="flex h-6 w-6 items-center justify-center rounded-lg text-zinc-300 transition-colors hover:bg-zinc-700"
            onClick={() => onQtyChange(entry.productId, entry.qty + 1, variantIdx)}
          >
            +
          </button>
        </div>
        <button
          type="button"
          disabled={!canCraft}
          title={canCraft ? "Скрафтить и убрать из списка" : "Не хватает материалов на складе"}
          onClick={() => onCraft(entry.productId, variantIdx)}
          className="shrink-0 rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-zinc-950 transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Скрафтить
        </button>
        <button
          type="button"
          aria-label="Удалить"
          onClick={() => onRemove(entry.productId, variantIdx)}
          className="shrink-0 rounded-lg px-2 py-1 text-sm text-zinc-500 transition-colors hover:bg-red-950/40 hover:text-red-400"
        >
          ✕
        </button>
      </div>

      {expanded && tree && (
        <div className="border-t border-zinc-800/80 bg-zinc-950/40 px-3 py-3">
          <div className="mb-3 flex gap-1 rounded-xl bg-zinc-800/80 p-1">
            {tabBtn("tree", "Дерево")}
            {tabBtn("list", "Покупки")}
          </div>

          {detailTab === "tree" ? (
            <>
              <p className="mb-2 text-xs text-zinc-600">
                Укажите «Есть» — составляющие пересчитаются пропорционально
              </p>
              <div className="space-y-1">
                {tree.children.map((ch, i) => (
                  <CraftTreeNode
                    key={`${ch.id}-${i}`}
                    node={ch}
                    catalog={catalog}
                    prices={prices}
                    manual={manual}
                    owned={owned}
                    onOwnedChange={onOwnedChange}
                    showPrices={showPrices}
                  />
                ))}
              </div>
            </>
          ) : (
            <CraftShoppingList
              catalog={catalog}
              tree={tree}
              owned={owned}
              prices={prices}
              manual={manual}
              onOwnedChange={onOwnedChange}
              showPrices={showPrices}
              title=""
            />
          )}
        </div>
      )}

      {expanded && craftable && !tree && (
        <div className="border-t border-zinc-800/80 px-3 py-4 text-center text-sm text-zinc-500">
          Загрузка рецепта...
        </div>
      )}
    </div>
  );
}

export default function CraftBulkCartList({
  catalog,
  entries,
  owned,
  chosenVariants,
  prices,
  manual,
  onOwnedChange,
  onQtyChange,
  onRemove,
  onCraft,
  showPrices = false,
  showApproxCost = true,
  recipesLoading = false,
}: Props) {
  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-700 px-4 py-8 text-center text-sm text-zinc-500">
        Корзина пуста.{" "}
        <Link to="/craft" className="font-medium text-amber-400 hover:underline">
          Перейти к крафту
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">Выбранные крафты</h3>
        <p className="mt-0.5 text-xs text-zinc-600">
          {entries.length} поз. · нажмите золотую стрелку слева, чтобы развернуть дерево крафта
          {recipesLoading && " · загрузка рецептов..."}
        </p>
      </div>
      {entries.map((entry) => (
        <CraftBulkCartRow
          key={cartEntryKey(entry.productId, entry.variantIdx)}
          catalog={catalog}
          entry={entry}
          owned={owned}
          chosenVariants={chosenVariants}
          prices={prices}
          manual={manual}
          onOwnedChange={onOwnedChange}
          onQtyChange={onQtyChange}
          onRemove={onRemove}
          onCraft={onCraft}
          showPrices={showPrices}
          showApproxCost={showApproxCost}
        />
      ))}
    </div>
  );
}
