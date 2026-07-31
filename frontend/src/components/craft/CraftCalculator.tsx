import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  applyWarehouseConsumption,
  buildTree,
  computeWarehouseConsumption,
  isCraftReady,
  itemInfo,
  variantsFor,
  type CalcNode,
  type CraftCatalog,
} from "../../lib/craftCalc";
import { currentReturnPath, itemPagePath } from "../../lib/internalNav";
import { masterworkItemUrl } from "../../lib/itemEncyclopedia";
import { useCraftPrices } from "../../hooks/useCraftPrices";
import { useAuth } from "../../hooks/useAuth";
import { usePreference } from "../../hooks/usePreferences";
import { useCraftCart } from "../../hooks/useCraftCart";
import CraftCostBar, { GradePill, HaveInput, ItemIcon } from "./CraftCostBar";
import CraftMaterialSources from "./CraftMaterialSources";
import { CraftItemDescription, CraftItemStatsPanel } from "./CraftItemStats";
import CraftShoppingList from "./CraftShoppingList";
import CraftTreeNode from "./CraftTreeNode";
import { useItemDetail } from "../../hooks/useItemEncyclopedia";
import SplitPane from "../ui/SplitPane";

interface Props {
  catalog: CraftCatalog;
  productId: number;
  onClose: () => void;
}

function collectIds(node: CalcNode | null, acc: Set<number>) {
  if (!node) return;
  acc.add(node.id);
  for (const c of node.children) collectIds(c, acc);
}

export default function CraftCalculator({ catalog, productId, onClose }: Props) {
  const location = useLocation();
  const from = currentReturnPath(location);
  const { hasPermission } = useAuth();
  const { add: addToCart } = useCraftCart();
  const canSeePrices = hasPermission("feature.craft_prices");
  const [qty, setQty] = useState(1);
  const [owned, setOwned] = usePreference("craft_owned");
  const [chosenVariants, setChosenVariants] = usePreference("craft_variants");
  const [variantIdx, setVariantIdx] = useState(0);
  const [tab, setTab] = useState<"tree" | "list">("tree");
  const [showPrices, setShowPrices] = useState(false);
  const [priceEdit, setPriceEdit] = useState<Record<string, string>>({});

  const variants = variantsFor(catalog, productId);
  const product = itemInfo(catalog, productId);
  const { data: encyclopedia } = useItemDetail(productId);

  useEffect(() => {
    setVariantIdx(chosenVariants[String(productId)] ?? 0);
    setQty(1);
  }, [productId]); // eslint-disable-line react-hooks/exhaustive-deps -- reset only on product change

  const tree = useMemo(
    () => buildTree(catalog, productId, qty, owned, variantIdx, chosenVariants),
    [catalog, productId, qty, owned, variantIdx, chosenVariants],
  );

  const canCraft = useMemo(
    () => Boolean(tree && isCraftReady(catalog, tree)),
    [catalog, tree],
  );

  const allIds = useMemo(() => {
    const s = new Set<number>([productId]);
    if (tree) collectIds(tree, s);
    return [...s];
  }, [tree, productId]);

  const { serverPrices, manual, setManualPrice } = useCraftPrices(canSeePrices ? allIds : []);

  const onOwnedChange = (id: number, val: number) => {
    const next = { ...owned };
    const k = String(id);
    if (val <= 0) delete next[k];
    else next[k] = val;
    setOwned(next);
  };

  const onVariantChange = (idx: number) => {
    setVariantIdx(idx);
    setChosenVariants({ ...chosenVariants, [String(productId)]: idx });
  };

  const handleCraft = () => {
    const consumed = computeWarehouseConsumption(
      catalog,
      productId,
      qty,
      owned,
      variantIdx,
      chosenVariants,
    );
    if (!consumed) return;
    setOwned(applyWarehouseConsumption(owned, consumed));
  };

  if (!tree) return null;

  const tabBtn = (id: "tree" | "list", label: string) => (
    <button
      type="button"
      className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
        tab === id
          ? "bg-amber-600 text-zinc-950 shadow-sm"
          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
      }`}
      onClick={() => setTab(id)}
    >
      {label}
    </button>
  );

  return (
    <div className="panel flex flex-col overflow-hidden shadow-glow">
      <div className="flex flex-wrap items-center gap-3 border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-3">
        <ItemIcon id={productId} size={44} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-zinc-50">{product.name}</h2>
            <GradePill grade={product.grade} />
          </div>
          <p className="text-xs text-zinc-500">
            Крафтер {variants[variantIdx]?.crafter_level ?? "—"} lvl ·{" "}
            {variants[variantIdx]?.success ?? "—"}
            {encyclopedia?.stats?.weight != null && ` · ${encyclopedia.stats.weight} weight`}
          </p>
          <CraftItemStatsPanel catalog={catalog} id={productId} />
          {encyclopedia?.effects && (
            <p className="mt-1 max-w-prose text-xs leading-relaxed text-zinc-400">{encyclopedia.effects}</p>
          )}
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs">
            <Link
              to={itemPagePath(productId, from)}
              className="font-medium text-amber-400 underline-offset-2 hover:underline"
            >
              Локальная вики →
            </Link>
            {encyclopedia && (
              <a
                href={masterworkItemUrl(encyclopedia)}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-amber-400 underline-offset-2 hover:underline"
              >
                Masterwork Wiki ↗
              </a>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 rounded-xl border border-zinc-700/80 bg-zinc-800/80 px-2 py-1">
          <button
            type="button"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-300 transition-colors hover:bg-zinc-700"
            onClick={() => setQty((q) => Math.max(1, q - 1))}
          >
            −
          </button>
          <span className="min-w-[2rem] text-center font-bold tabular-nums text-zinc-100">{qty}</span>
          <button
            type="button"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-300 transition-colors hover:bg-zinc-700"
            onClick={() => setQty((q) => q + 1)}
          >
            +
          </button>
        </div>
        <button
          type="button"
          disabled={!canCraft}
          title={canCraft ? "Списать материалы со склада" : "Не хватает материалов на складе"}
          onClick={handleCraft}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Скрафтить
        </button>
        <button
          type="button"
          onClick={() => addToCart(productId, qty, variantIdx)}
          className="rounded-lg border border-amber-600/50 bg-amber-950/40 px-3 py-1.5 text-xs font-semibold text-amber-300 transition-colors hover:bg-amber-900/50"
        >
          В список
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-3 py-1.5 text-sm text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          aria-label="Закрыть"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          {variants.length > 1 &&
            variants.map((v, i) => (
              <button
                key={v.recipe_id}
                type="button"
                className={`rounded-lg border px-3 py-1 text-xs font-semibold transition-colors ${
                  i === variantIdx
                    ? "border-amber-500 bg-amber-600 text-zinc-950"
                    : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-amber-500/50"
                }`}
                onClick={() => onVariantChange(i)}
              >
                {v.rate != null ? `${v.rate}%` : `#${i + 1}`}
              </button>
            ))}
          {canSeePrices && (
            <button
              type="button"
              className="rounded-lg border border-zinc-700 bg-zinc-800/80 px-3 py-1 text-xs font-medium text-zinc-300 transition-colors hover:border-amber-500/50"
              onClick={() => setShowPrices(!showPrices)}
            >
              {showPrices ? "Скрыть цены" : "Задать цены"}
            </button>
          )}
        </div>

        {canSeePrices && showPrices && (
          <div className="mb-4 rounded-xl border border-zinc-800/80 bg-zinc-900/50 p-3">
            <p className="mb-2 text-xs text-zinc-500">Ручные цены переопределяют рынок</p>
            <div className="grid max-h-40 gap-2 overflow-y-auto sm:grid-cols-2">
              {allIds.slice(0, 40).map((id) => {
                const info = itemInfo(catalog, id);
                return (
                  <label key={id} className="flex items-center gap-2 text-xs">
                    <span className="min-w-0 flex-1 truncate text-zinc-300">{info.name}</span>
                    <HaveInput
                      value={priceEdit[String(id)] ?? manual[String(id)] ?? ""}
                      onChange={(n) => {
                        setPriceEdit((p) => ({ ...p, [String(id)]: String(n || "") }));
                        setManualPrice(id, n > 0 ? n : null);
                      }}
                    />
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {canSeePrices && (
          <CraftCostBar catalog={catalog} tree={tree} prices={serverPrices} manual={manual} />
        )}

        <CraftItemDescription catalog={catalog} id={productId} />

        {tree && <CraftMaterialSources tree={tree} catalog={catalog} />}

        <div className="mb-3 flex gap-1 rounded-xl bg-zinc-800/80 p-1 lg:hidden">
          {tabBtn("tree", "Дерево")}
          {tabBtn("list", "Покупки")}
        </div>

        <div className="lg:hidden">
          <div
            className={`rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3 ${
              tab === "list" ? "hidden" : ""
            }`}
          >
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-zinc-500">Дерево крафта</h3>
            <p className="mb-2 text-xs text-zinc-600">
              Укажите «Есть» — составляющие пересчитаются пропорционально
            </p>
            <div className="space-y-1">
              {tree.children.map((ch, i) => (
                <CraftTreeNode
                  key={`${ch.id}-${i}`}
                  node={ch}
                  catalog={catalog}
                  prices={serverPrices}
                  manual={manual}
                  owned={owned}
                  onOwnedChange={onOwnedChange}
                  showPrices={canSeePrices}
                />
              ))}
            </div>
          </div>
          <div
            className={`rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3 ${
              tab === "tree" ? "hidden" : ""
            }`}
          >
            <CraftShoppingList
              catalog={catalog}
              tree={tree}
              owned={owned}
              prices={serverPrices}
              manual={manual}
              onOwnedChange={onOwnedChange}
              showPrices={canSeePrices}
            />
          </div>
        </div>

        <div className="hidden lg:block">
          <SplitPane
            left={
              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
                <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-zinc-500">Дерево крафта</h3>
                <p className="mb-2 text-xs text-zinc-600">
                  Укажите «Есть» — составляющие пересчитаются пропорционально
                </p>
                <div className="space-y-1">
                  {tree.children.map((ch, i) => (
                    <CraftTreeNode
                      key={`${ch.id}-${i}`}
                      node={ch}
                      catalog={catalog}
                      prices={serverPrices}
                      manual={manual}
                      owned={owned}
                      onOwnedChange={onOwnedChange}
                      showPrices={canSeePrices}
                    />
                  ))}
                </div>
              </div>
            }
            right={
              <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
                <CraftShoppingList
                  catalog={catalog}
                  tree={tree}
                  owned={owned}
                  prices={serverPrices}
                  manual={manual}
                  onOwnedChange={onOwnedChange}
                  showPrices={canSeePrices}
                />
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
