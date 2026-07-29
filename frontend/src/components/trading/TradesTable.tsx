import { useCallback, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTrades } from "../../api/market";
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
const VISIBLE_ROWS = 12;

function formatPrice(value: number): string {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-lg border border-zinc-700/80 px-2 py-1 text-[0.65rem] text-zinc-400 transition-colors hover:border-amber-500/40 hover:text-amber-400"
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

      <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-zinc-950/60 text-xs uppercase tracking-wider text-zinc-500">
            <tr>
              <th className="cursor-pointer px-4 py-3" onClick={() => toggleSort("recorded_at")}>
                Время{sortIndicator("recorded_at")}
              </th>
              <th className="cursor-pointer px-4 py-3" onClick={() => toggleSort("seller_name")}>
                {side === "buy" ? "Покупатель" : "Продавец"}
                {sortIndicator("seller_name")}
              </th>
              <th className="px-4 py-3" />
              <th className="cursor-pointer px-4 py-3 text-right" onClick={() => toggleSort("quantity")}>
                Кол-во{sortIndicator("quantity")}
              </th>
              <th className="cursor-pointer px-4 py-3 text-right" onClick={() => toggleSort("price")}>
                Цена{sortIndicator("price")}
              </th>
              <th className="px-4 py-3 text-right">Сумма</th>
            </tr>
          </thead>
        </table>

        {isLoading ? (
          <p className="px-4 py-8 text-center text-sm text-zinc-500">Загрузка...</p>
        ) : !rows.length ? (
          <p className="px-4 py-8 text-center text-sm text-zinc-500">Нет данных</p>
        ) : (
          <div
            ref={scrollRef}
            onScroll={onScroll}
            className="overflow-y-auto"
            style={{ maxHeight: ROW_HEIGHT * VISIBLE_ROWS }}
          >
            <div style={{ height: rows.length * ROW_HEIGHT, position: "relative" }}>
              <table
                className="absolute w-full min-w-[640px] text-left text-sm"
                style={{ top: virtualRows.offset }}
              >
                <tbody className="divide-y divide-zinc-800/60">
                  {rows.slice(virtualRows.start, virtualRows.end).map((row) => (
                    <tr key={row.id} className="hover:bg-zinc-900/50" style={{ height: ROW_HEIGHT }}>
                      <td className="px-4 py-2 tabular-nums text-zinc-400">
                        {new Date(row.recorded_at).toLocaleString("ru-RU")}
                      </td>
                      <td className="max-w-[180px] truncate px-4 py-2 font-medium text-zinc-200">
                        {row.seller_name}
                      </td>
                      <td className="px-4 py-2">
                        <CopyButton text={row.seller_name} />
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-zinc-300">{row.quantity}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-zinc-200">
                        {formatPrice(row.price)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-amber-400/90">
                        {formatPrice(row.total_cost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
