import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCraftCart } from "../../hooks/useCraftCart";
import { itemInfo, type CraftCatalog } from "../../lib/craftCalc";
import BulkCraftIcon from "./BulkCraftIcon";
import { GradePill, ItemIcon } from "./CraftCostBar";

interface Props {
  catalog?: CraftCatalog;
}

export default function CraftCartWidget({ catalog }: Props) {
  const { entries, totalCount, isEmpty, remove } = useCraftCart();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label="Массовый крафт"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-700/80 bg-zinc-800/80 text-amber-400/90 transition-colors hover:border-amber-500/50 hover:text-amber-300"
      >
        <BulkCraftIcon />
        {!isEmpty && (
          <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-amber-500 px-1 text-[0.65rem] font-bold tabular-nums text-zinc-950">
            {totalCount > 99 ? "99+" : totalCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-zinc-700/80 bg-zinc-900 shadow-xl ring-1 ring-zinc-800">
          <div className="border-b border-zinc-800/80 px-4 py-3">
            <h3 className="text-sm font-semibold text-zinc-100">Массовый крафт</h3>
            <p className="mt-0.5 text-xs text-zinc-500">
              {isEmpty ? "Корзина пуста" : `${entries.length} поз. · ${totalCount} шт.`}
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto p-2">
            {isEmpty ? (
              <p className="px-2 py-4 text-center text-sm text-zinc-500">
                Добавьте предметы из калькулятора крафта
              </p>
            ) : (
              entries.map((entry) => {
                const info = catalog ? itemInfo(catalog, entry.productId) : null;
                return (
                  <div
                    key={entry.productId}
                    className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-zinc-800/60"
                  >
                    <ItemIcon id={entry.productId} size={32} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1">
                        <span className="truncate text-sm font-medium text-zinc-100">
                          {info?.name ?? `#${entry.productId}`}
                        </span>
                        {info?.grade && <GradePill grade={info.grade} />}
                      </div>
                      <span className="text-xs tabular-nums text-zinc-500">×{entry.qty}</span>
                    </div>
                    <button
                      type="button"
                      aria-label="Удалить"
                      onClick={() => remove(entry.productId)}
                      className="shrink-0 rounded-lg px-2 py-1 text-sm text-zinc-500 transition-colors hover:bg-red-950/40 hover:text-red-400"
                    >
                      ✕
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <div className="border-t border-zinc-800/80 p-2">
            <button
              type="button"
              disabled={isEmpty}
              onClick={() => {
                setOpen(false);
                navigate("/craft/bulk");
              }}
              className="w-full rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Открыть массовый крафт
            </button>
            {!isEmpty && (
              <Link
                to="/craft/bulk"
                onClick={() => setOpen(false)}
                className="mt-1 block text-center text-xs text-amber-400/80 hover:text-amber-400 hover:underline"
              >
                Перейти на страницу →
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
