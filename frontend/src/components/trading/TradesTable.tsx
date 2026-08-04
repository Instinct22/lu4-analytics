import { useCallback, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTrades } from "../../api/market";
import { copyText } from "../../lib/copyText";
import { PeriodState, periodQueryParams } from "./periodUtils";

interface TradeRow {
  id: string;
  recorded_at: string;
  seller_name: string;
  quantity: number;
  price: number;
  total_cost: number;
}

interface Props {
  title: string;
  side: "buy" | "sell";
  entityId: string;
  period: PeriodState;
}

type SortKey = "recorded_at" | "price" | "quantity" | "seller_name";

const ROW_HEIGHT = 44;
const HEADER_HEIGHT = 40;
const VISIBLE_ROWS = 12;

/** Shared column track — header and every row must use the exact same template. */
const COLS =
  "grid-cols-[10rem_minmax(0,1fr)_4.75rem_5.25rem_6.5rem] min-[520px]:grid-cols-[10.5rem_minmax(0,1.2fr)_5rem_5.5rem_7rem]";

function formatPrice(value: number): string {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    const ok = await copyText(text);
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={copy}
      className="shrink-0 rounded border border-zinc-700/80 px-1.5 py-0.5 text-[0.65rem] leading-none text-zinc-400 transition-colors hover:border-amber-500/40 hover:text-amber-400"
      title="Копировать ник"
    >
      {copied ? "✓" : "⎘"}
    </button>
  );
}

export default function TradesTable({ title, side, entityId, period }: Props) {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("recorded_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const debounceRef = useRef<number>();
  const onSearchChange = (value: string) => {
    setSearch(value);
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setDebouncedSearch(value.trim());
      setPage(1);
    }, 300);
  };

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["trading-trades", entityId, side, period, debouncedSearch, sortBy, sortOrder, page],
    queryFn: () =>
      getTrades({
        entity_id: entityId,
        side,
        search: debouncedSearch || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        limit: 100,
        ...periodQueryParams(period),
      }),
    enabled: !!entityId,
    placeholderData: (prev) => prev,
  });

  const rows: TradeRow[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / (data?.limit ?? 100)));

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder("desc");
    }
    setPage(1);
  };

  const sortIndicator = (key: SortKey) => {
    if (sortBy !== key) return "";
    return sortOrder === "asc" ? " ↑" : " ↓";
  };

  const virtualRows = useMemo(() => {
    const start = Math.floor(scrollTop / ROW_HEIGHT);
    const end = Math.min(start + VISIBLE_ROWS + 2, rows.length);
    return { start, end, offset: start * ROW_HEIGHT };
  }, [scrollTop, rows.length]);

  const onScroll = useCallback(() => {
    if (scrollRef.current) setScrollTop(scrollRef.current.scrollTop);
  }, []);

  const headCell =
    "flex items-center px-2 text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500";

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
        <input
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Поиск по нику..."
          className="input max-w-xs"
        />
      </div>

      <div
        ref={scrollRef}
        onScroll={rows.length ? onScroll : undefined}
        className="overflow-y-auto overflow-x-hidden rounded-xl border border-zinc-800/80 [scrollbar-gutter:stable]"
        style={{ height: HEADER_HEIGHT + ROW_HEIGHT * VISIBLE_ROWS }}
      >
        <div
          className={`sticky top-0 z-10 grid ${COLS} border-b border-zinc-800/80 bg-zinc-950`}
          style={{ height: HEADER_HEIGHT }}
        >
          <button
            type="button"
            className={`${headCell} cursor-pointer text-left hover:text-zinc-300`}
            onClick={() => toggleSort("recorded_at")}
          >
            Время{sortIndicator("recorded_at")}
          </button>
          <button
            type="button"
            className={`${headCell} cursor-pointer text-left hover:text-zinc-300`}
            onClick={() => toggleSort("seller_name")}
          >
            {side === "buy" ? "Покупатель" : "Продавец"}
            {sortIndicator("seller_name")}
          </button>
          <button
            type="button"
            className={`${headCell} cursor-pointer justify-end hover:text-zinc-300`}
            onClick={() => toggleSort("quantity")}
          >
            Кол-во{sortIndicator("quantity")}
          </button>
          <button
            type="button"
            className={`${headCell} cursor-pointer justify-end hover:text-zinc-300`}
            onClick={() => toggleSort("price")}
          >
            Цена{sortIndicator("price")}
          </button>
          <div className={`${headCell} justify-end`}>Сумма</div>
        </div>

        {isLoading ? (
          <p className="px-4 py-8 text-center text-sm text-zinc-500">Загрузка...</p>
        ) : !rows.length ? (
          <p className="px-4 py-8 text-center text-sm text-zinc-500">Нет данных</p>
        ) : (
          <div style={{ height: rows.length * ROW_HEIGHT, position: "relative" }}>
            <div className="absolute inset-x-0" style={{ top: virtualRows.offset }}>
              {rows.slice(virtualRows.start, virtualRows.end).map((row) => (
                <div
                  key={row.id}
                  className={`grid ${COLS} items-center border-b border-zinc-800/60 hover:bg-zinc-900/50`}
                  style={{ height: ROW_HEIGHT }}
                >
                  <div className="min-w-0 truncate px-2 text-sm tabular-nums text-zinc-400">
                    {new Date(row.recorded_at).toLocaleString("ru-RU")}
                  </div>
                  <div className="flex min-w-0 items-center gap-1.5 px-2">
                    <span
                      className="min-w-0 truncate text-sm font-medium text-zinc-200"
                      title={row.seller_name}
                    >
                      {row.seller_name}
                    </span>
                    <CopyButton text={row.seller_name} />
                  </div>
                  <div className="min-w-0 truncate px-2 text-right text-sm tabular-nums text-zinc-300">
                    {row.quantity.toLocaleString("ru-RU")}
                  </div>
                  <div className="min-w-0 truncate px-2 text-right text-sm tabular-nums text-zinc-200">
                    {formatPrice(row.price)}
                  </div>
                  <div className="min-w-0 truncate px-2 text-right text-sm tabular-nums text-amber-400/90">
                    {formatPrice(row.total_cost)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
        <span>
          {total.toLocaleString("ru-RU")} записей {isFetching && "· обновление..."}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="btn-ghost px-2 py-1 disabled:opacity-40"
          >
            ←
          </button>
          <span>
            {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="btn-ghost px-2 py-1 disabled:opacity-40"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
