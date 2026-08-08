import { useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getTradingItemCatalog,
  type ItemCatalogHit,
  type ItemSearchHit,
} from "../../api/trading";
import { ItemIcon } from "../craft/CraftCostBar";

export type TradingSelectItem = ItemSearchHit & {
  custom?: boolean;
  group?: "resource" | "item";
};

interface Props {
  onSelect: (item: TradingSelectItem) => void;
  disabled?: boolean;
}

type MenuBox = { top: number; left: number; width: number; maxHeight: number };

/** Negative synthetic id for custom (non-wiki) items. */
export function nextCustomItemId(): number {
  return -Math.abs(Date.now() % 1_000_000_000) - Math.floor(Math.random() * 1000);
}

export default function TradingItemSelect({ onSelect, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [menuBox, setMenuBox] = useState<MenuBox | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const { data, isFetching } = useQuery({
    queryKey: ["trading-item-catalog"],
    queryFn: getTradingItemCatalog,
    staleTime: 1000 * 60 * 30,
    enabled: open,
  });

  const catalog = data?.items ?? [];
  const q = search.trim().toLowerCase();

  const { resources, others } = useMemo(() => {
    const filtered = q
      ? catalog.filter(
          (item) =>
            item.display_name.toLowerCase().includes(q) ||
            String(item.external_id).includes(q),
        )
      : catalog;

    const res: ItemCatalogHit[] = [];
    const rest: ItemCatalogHit[] = [];
    for (const item of filtered) {
      if (item.group === "resource") res.push(item);
      else rest.push(item);
    }
    return { resources: res, others: rest };
  }, [catalog, q]);

  const canCreate =
    q.length >= 1 &&
    !catalog.some((item) => item.display_name.toLowerCase() === q);

  const updateMenuBox = () => {
    const btn = buttonRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const gap = 4;
    const preferredHeight = 480;
    const spaceBelow = window.innerHeight - rect.bottom - gap - 8;
    const spaceAbove = rect.top - gap - 8;
    const openUp = spaceBelow < 240 && spaceAbove > spaceBelow;
    const maxHeight = Math.min(preferredHeight, Math.max(200, openUp ? spaceAbove : spaceBelow));
    const width = Math.max(rect.width, Math.min(560, window.innerWidth - 16));
    let left = rect.left;
    if (left + width > window.innerWidth - 8) {
      left = Math.max(8, window.innerWidth - width - 8);
    }
    const top = openUp ? rect.top - gap - maxHeight : rect.bottom + gap;
    setMenuBox({ top, left, width, maxHeight });
  };

  useLayoutEffect(() => {
    if (!open) {
      setMenuBox(null);
      return;
    }
    updateMenuBox();
    const onReposition = () => updateMenuBox();
    window.addEventListener("resize", onReposition);
    window.addEventListener("scroll", onReposition, true);
    return () => {
      window.removeEventListener("resize", onReposition);
      window.removeEventListener("scroll", onReposition, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pick = (item: TradingSelectItem) => {
    onSelect(item);
    setOpen(false);
    setSearch("");
  };

  const createCustom = () => {
    const name = search.trim();
    if (!name) return;
    pick({
      external_id: nextCustomItemId(),
      display_name: name,
      custom: true,
    });
  };

  const onSearchKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const visible = [...resources, ...others];
    if (visible.length === 1) {
      pick(visible[0]);
    } else if (canCreate) {
      createCustom();
    }
  };

  const listMaxHeight = menuBox ? Math.max(140, menuBox.maxHeight - (canCreate ? 108 : 56)) : 360;

  return (
    <div ref={rootRef} className="relative min-w-0 flex-1">
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="input flex w-full items-center justify-between gap-2 text-left disabled:opacity-50"
      >
        <span className="truncate text-sm text-zinc-500">Добавить предмет…</span>
        <span className="shrink-0 text-zinc-500">{open ? "▴" : "▾"}</span>
      </button>

      {open &&
        menuBox &&
        createPortal(
          <div
            ref={menuRef}
            style={{
              position: "fixed",
              top: menuBox.top,
              left: menuBox.left,
              width: menuBox.width,
              maxHeight: menuBox.maxHeight,
              zIndex: 80,
            }}
            className="flex flex-col overflow-hidden rounded-xl border border-zinc-700/80 bg-zinc-950 shadow-2xl ring-1 ring-zinc-800/80"
          >
            <div className="shrink-0 border-b border-zinc-800/80 p-2">
              <input
                autoFocus
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={onSearchKeyDown}
                placeholder="Поиск или своё название…"
                className="input"
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto" style={{ maxHeight: listMaxHeight }} role="listbox">
              {isFetching && !catalog.length ? (
                <p className="px-3 py-4 text-center text-sm text-zinc-500">Загрузка…</p>
              ) : !resources.length && !others.length ? (
                <p className="px-3 py-4 text-center text-sm text-zinc-500">
                  {q ? "В базе не найдено" : "Список предметов пуст"}
                </p>
              ) : (
                <>
                  {resources.length > 0 ? (
                    <Section title="Ресурсы" items={resources} onPick={pick} />
                  ) : null}
                  {others.length > 0 ? (
                    <Section title="Предметы" items={others} onPick={pick} />
                  ) : null}
                </>
              )}
            </div>
            {canCreate ? (
              <div className="shrink-0 border-t border-zinc-800/80 p-2">
                <button
                  type="button"
                  onClick={createCustom}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-amber-200 transition-colors hover:bg-amber-500/10"
                >
                  <span className="min-w-0 truncate">
                    Создать «<span className="font-semibold">{search.trim()}</span>»
                  </span>
                  <span className="shrink-0 text-xs text-amber-500/80">свой предмет</span>
                </button>
              </div>
            ) : null}
          </div>,
          document.body,
        )}
    </div>
  );
}

function Section({
  title,
  items,
  onPick,
}: {
  title: string;
  items: ItemCatalogHit[];
  onPick: (item: ItemCatalogHit) => void;
}) {
  return (
    <div>
      <div className="sticky top-0 z-10 bg-zinc-900/95 px-3 py-1.5 text-[0.65rem] font-semibold uppercase tracking-wider text-zinc-500 backdrop-blur">
        {title}
      </div>
      <ul className="divide-y divide-zinc-800/60">
        {items.map((item) => (
          <li key={`${item.group}-${item.external_id}`}>
            <button
              type="button"
              role="option"
              onClick={() => onPick(item)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left text-zinc-300 transition-colors hover:bg-zinc-900/80"
            >
              <ItemIcon id={item.external_id} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.display_name}</span>
              <span className="shrink-0 text-xs tabular-nums text-zinc-500">#{item.external_id}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
