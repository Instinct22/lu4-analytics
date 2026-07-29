import { mediaUrl } from "../../api/client";
import {
  effectivePrice,
  formatPrice,
  GRADE_COLORS,
  itemInfo,
  treeCost,
  walkLeaves,
  type CalcNode,
  type CraftCatalog,
  type PriceInfo,
} from "../../lib/craftCalc";

interface Props {
  catalog: CraftCatalog;
  tree: CalcNode;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
}

export default function CraftCostBar({ catalog, tree, prices, manual }: Props) {
  const cheapest = treeCost(tree, catalog, prices, manual).cost;
  const leafAcc = { craftAll: 0, recipes: 0, missing: new Set<number>() };
  walkLeaves(tree, catalog, prices, manual, leafAcc);

  return (
    <div className="mb-4 space-y-2">
      <div className="flex items-center justify-between rounded-xl border border-amber-900/40 bg-amber-950/30 px-4 py-3">
        <span className="text-xs font-bold uppercase tracking-wide text-amber-200/70">
          Ориентировочная стоимость
        </span>
        <span className="text-lg font-bold tabular-nums text-amber-300">
          {cheapest != null ? formatPrice(cheapest) : "—"}
          {leafAcc.missing.size > 0 && (
            <span className="ml-2 text-xs font-normal text-zinc-500">
              ({leafAcc.missing.size} без цены)
            </span>
          )}
        </span>
      </div>
      <p className="text-xs text-zinc-500">
        Покупка базовых материалов:{" "}
        <span className="font-semibold text-zinc-200">{formatPrice(leafAcc.craftAll)}</span>
      </p>
    </div>
  );
}

export function ItemIcon({
  id,
  size = 32,
  src,
}: {
  id?: number | null;
  size?: number;
  src?: string | null;
}) {
  const resolved = src ?? (id != null ? mediaUrl(`images/${id}.png`) : null);
  return (
    <div
      className="flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80"
      style={{ width: size, height: size }}
    >
      {resolved ? (
        <img
          src={resolved}
          alt=""
          width={size}
          height={size}
          className="h-full w-full object-contain"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : null}
    </div>
  );
}

export function GradePill({ grade }: { grade: string }) {
  if (!grade) return null;
  return (
    <span
      className="rounded px-1.5 py-0.5 text-[0.65rem] font-bold text-zinc-900"
      style={{ background: GRADE_COLORS[grade] || "#9aa6ad" }}
    >
      {grade}
    </span>
  );
}

export function ItemPrice({
  id,
  qty,
  catalog,
  prices,
  manual,
}: {
  id: number;
  qty: number;
  catalog: CraftCatalog;
  prices: Record<string, PriceInfo>;
  manual: Record<string, number>;
}) {
  const p = effectivePrice(id, prices, manual, catalog);
  if (p == null) return <span className="text-xs text-zinc-600">—</span>;
  return (
    <span className="text-xs font-semibold tabular-nums text-amber-400">{formatPrice(p * qty)}</span>
  );
}

export function HaveInput({
  value,
  onChange,
  className = "",
}: {
  value: number | string;
  onChange: (val: number) => void;
  className?: string;
}) {
  const num =
    typeof value === "number"
      ? value
      : value === ""
        ? 0
        : Math.max(0, parseInt(String(value).replace(/\D/g, ""), 10) || 0);
  const display = value === "" || value === 0 ? "" : String(num);

  const commitDigits = (raw: string) => {
    const digits = raw.replace(/\D/g, "");
    onChange(digits === "" ? 0 : parseInt(digits, 10));
  };

  return (
    <div
      className={`inline-flex h-7 overflow-hidden rounded-md border border-zinc-700 bg-zinc-900 focus-within:border-amber-500/60 focus-within:ring-2 focus-within:ring-amber-500/20 ${className}`}
    >
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        autoComplete="off"
        className="w-12 min-w-0 bg-transparent px-2 py-0.5 text-right text-xs font-semibold tabular-nums text-zinc-100 outline-none placeholder:text-zinc-600"
        value={display}
        placeholder="0"
        onChange={(e) => commitDigits(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "ArrowUp") {
            e.preventDefault();
            onChange(num + 1);
            return;
          }
          if (e.key === "ArrowDown") {
            e.preventDefault();
            onChange(Math.max(0, num - 1));
            return;
          }
          if (
            e.ctrlKey ||
            e.metaKey ||
            e.altKey ||
            [
              "Backspace",
              "Delete",
              "Tab",
              "Escape",
              "Enter",
              "ArrowLeft",
              "ArrowRight",
              "Home",
              "End",
            ].includes(e.key)
          ) {
            return;
          }
          if (!/^\d$/.test(e.key)) e.preventDefault();
        }}
        onPaste={(e) => {
          e.preventDefault();
          commitDigits(e.clipboardData.getData("text"));
        }}
      />
      <div className="flex w-4 shrink-0 flex-col border-l border-zinc-700/80">
        <button
          type="button"
          tabIndex={-1}
          className="flex flex-1 items-center justify-center text-[0.5rem] leading-none text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-amber-400"
          onClick={() => onChange(num + 1)}
          aria-label="Увеличить"
        >
          ▲
        </button>
        <button
          type="button"
          tabIndex={-1}
          disabled={num <= 0}
          className="flex flex-1 items-center justify-center border-t border-zinc-700/80 text-[0.5rem] leading-none text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-amber-400 disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-zinc-500"
          onClick={() => onChange(Math.max(0, num - 1))}
          aria-label="Уменьшить"
        >
          ▼
        </button>
      </div>
    </div>
  );
}

