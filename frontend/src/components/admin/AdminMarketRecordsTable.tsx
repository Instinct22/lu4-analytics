import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  bulkDeleteMarketRecords,
  bulkUpdateMarketRecords,
  listMarketRecords,
  type MarketRecordAdminItem,
  type MarketRecordUpdateItem,
  type MarketRecordsFilters,
} from "../../api/admin";
import { LoadingState } from "../ui";

const LIMIT = 50;

type DraftRow = {
  recorded_at: string;
  product_name_raw: string;
  seller_name: string;
  price: string;
  currency: string;
  side: string;
  quantity: string;
};

function formatLoginAt(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatMarketPrice(value: number | string) {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function formatMarketSide(side: string | null) {
  if (side === "buy") return "Покупка";
  if (side === "sell") return "Продажа";
  return side || "—";
}

function toLocalInputValue(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toISOString();
}

function rowToDraft(row: MarketRecordAdminItem): DraftRow {
  return {
    recorded_at: toLocalInputValue(row.recorded_at),
    product_name_raw: row.product_name_raw,
    seller_name: row.seller_name,
    price: String(row.price),
    currency: row.currency,
    side: row.side ?? "",
    quantity: row.quantity == null ? "" : String(row.quantity),
  };
}

const emptyFilters: MarketRecordsFilters = {
  date_from: "",
  date_to: "",
  product: "",
  seller: "",
  price: "",
  currency: "",
  side: "",
  quantity: "",
};

const filterInputClass = "input mt-1 w-full min-w-[6rem] px-2 py-1 text-xs";

interface Props {
  outliersOnly?: boolean;
}

export default function AdminMarketRecordsTable({ outliersOnly = false }: Props) {
  const qc = useQueryClient();
  const queryKeyPrefix = outliersOnly ? "admin-market-outliers" : "admin-market-records";
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<MarketRecordsFilters>(emptyFilters);
  const [debounced, setDebounced] = useState<MarketRecordsFilters>(emptyFilters);
  const debounceRef = useRef<number>();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({});
  const [actionError, setActionError] = useState("");

  const onFilterChange = (key: keyof MarketRecordsFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setDebounced((prev) => ({ ...prev, [key]: value }));
      setPage(1);
      setSelected(new Set());
      setEditing(false);
      setDrafts({});
    }, 300);
  };

  const query = useQuery({
    queryKey: [queryKeyPrefix, page, debounced],
    queryFn: () => {
      const filtersForApi: MarketRecordsFilters = {
        ...debounced,
        outliers_only: outliersOnly || undefined,
      };
      if (filtersForApi.date_from) {
        filtersForApi.date_from = fromLocalInputValue(filtersForApi.date_from);
      }
      if (filtersForApi.date_to) {
        filtersForApi.date_to = fromLocalInputValue(filtersForApi.date_to);
      }
      return listMarketRecords(page, LIMIT, filtersForApi);
    },
    refetchInterval: editing ? false : 5000,
    placeholderData: (prev) => prev,
  });

  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / (query.data?.limit ?? LIMIT)));

  useEffect(() => {
    setSelected((prev) => {
      const ids = new Set(items.map((r) => r.id));
      const next = new Set([...prev].filter((id) => ids.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [items]);

  const allPageSelected = items.length > 0 && items.every((r) => selected.has(r.id));
  const selectedCount = selected.size;

  const invalidateLists = () => {
    qc.invalidateQueries({ queryKey: ["admin-market-records"] });
    qc.invalidateQueries({ queryKey: ["admin-market-outliers"] });
  };

  const toggleAll = () => {
    if (allPageSelected) {
      setSelected(new Set());
      return;
    }
    setSelected(new Set(items.map((r) => r.id)));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const startEdit = () => {
    if (!selectedCount) return;
    const next: Record<string, DraftRow> = {};
    for (const row of items) {
      if (selected.has(row.id)) next[row.id] = rowToDraft(row);
    }
    setDrafts(next);
    setEditing(true);
    setActionError("");
  };

  const cancelEdit = () => {
    setEditing(false);
    setDrafts({});
    setActionError("");
  };

  const updateDraft = (id: string, key: keyof DraftRow, value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...prev[id], [key]: value },
    }));
  };

  const deleteMut = useMutation({
    mutationFn: bulkDeleteMarketRecords,
    onSuccess: () => {
      setSelected(new Set());
      setEditing(false);
      setDrafts({});
      setActionError("");
      invalidateLists();
    },
    onError: () => setActionError("Не удалось удалить записи"),
  });

  const updateMut = useMutation({
    mutationFn: bulkUpdateMarketRecords,
    onSuccess: () => {
      setSelected(new Set());
      setEditing(false);
      setDrafts({});
      setActionError("");
      invalidateLists();
    },
    onError: () => setActionError("Не удалось сохранить изменения"),
  });

  const onDeleteSelected = () => {
    if (!selectedCount) return;
    if (!confirm(`Удалить выбранные записи (${selectedCount})?`)) return;
    deleteMut.mutate([...selected]);
  };

  const onSave = () => {
    const payload: MarketRecordUpdateItem[] = [];
    for (const id of selected) {
      const draft = drafts[id];
      if (!draft) continue;
      const price = Number(String(draft.price).replace(",", "."));
      if (!Number.isFinite(price)) {
        setActionError("Некорректная цена в одной из строк");
        return;
      }
      const quantityRaw = draft.quantity.trim();
      let quantity: number | null = null;
      if (quantityRaw !== "") {
        quantity = Number(quantityRaw);
        if (!Number.isFinite(quantity) || !Number.isInteger(quantity)) {
          setActionError("Некорректное количество в одной из строк");
          return;
        }
      }
      if (!draft.product_name_raw.trim() || !draft.seller_name.trim()) {
        setActionError("Товар и продавец не могут быть пустыми");
        return;
      }
      if (!draft.recorded_at) {
        setActionError("Дата обязательна");
        return;
      }
      payload.push({
        id,
        product_name_raw: draft.product_name_raw.trim(),
        seller_name: draft.seller_name.trim(),
        price,
        currency: draft.currency.trim() || "adena",
        side: draft.side.trim() || null,
        quantity,
        recorded_at: fromLocalInputValue(draft.recorded_at),
      });
    }
    if (!payload.length) return;
    updateMut.mutate(payload);
  };

  const busy = deleteMut.isPending || updateMut.isPending;

  const hasActiveFilters = useMemo(
    () =>
      Object.entries(debounced).some(
        ([key, value]) =>
          key !== "outliers_only" && value != null && String(value).trim() !== "",
      ),
    [debounced],
  );

  return (
    <>
      <div className="panel space-y-3 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Фильтры</h3>
            <p className="mt-0.5 text-xs text-zinc-500">
              {outliersOnly
                ? "Сделки с аномальной ценой (IQR, 30 дней) · автообновление каждые 5 сек"
                : "Таблица market_records · автообновление каждые 5 сек"}
              {editing ? " · на паузе во время редактирования" : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-zinc-600 bg-zinc-900"
                checked={allPageSelected}
                onChange={toggleAll}
                disabled={!items.length || editing}
              />
              Выбрать все
            </label>
            {hasActiveFilters && (
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-xs"
                onClick={() => {
                  setFilters(emptyFilters);
                  setDebounced(emptyFilters);
                  setPage(1);
                  setSelected(new Set());
                  setEditing(false);
                  setDrafts({});
                }}
              >
                Сбросить фильтры
              </button>
            )}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
          <label className="text-xs text-zinc-500">
            Дата с
            <input
              type="datetime-local"
              className={filterInputClass}
              value={filters.date_from ?? ""}
              onChange={(e) => onFilterChange("date_from", e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-500">
            Дата по
            <input
              type="datetime-local"
              className={filterInputClass}
              value={filters.date_to ?? ""}
              onChange={(e) => onFilterChange("date_to", e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-500">
            Товар
            <input
              className={filterInputClass}
              value={filters.product ?? ""}
              onChange={(e) => onFilterChange("product", e.target.value)}
              placeholder="Название…"
            />
          </label>
          <label className="text-xs text-zinc-500">
            Продавец
            <input
              className={filterInputClass}
              value={filters.seller ?? ""}
              onChange={(e) => onFilterChange("seller", e.target.value)}
              placeholder="Ник…"
            />
          </label>
          <label className="text-xs text-zinc-500">
            Цена
            <input
              className={filterInputClass}
              value={filters.price ?? ""}
              onChange={(e) => onFilterChange("price", e.target.value)}
              placeholder="100"
            />
          </label>
          <label className="text-xs text-zinc-500">
            Валюта
            <input
              className={filterInputClass}
              value={filters.currency ?? ""}
              onChange={(e) => onFilterChange("currency", e.target.value)}
              placeholder="adena"
            />
          </label>
          <label className="text-xs text-zinc-500">
            Сторона
            <select
              className={filterInputClass}
              value={filters.side ?? ""}
              onChange={(e) => onFilterChange("side", e.target.value)}
            >
              <option value="">Все</option>
              <option value="buy">Покупка</option>
              <option value="sell">Продажа</option>
            </select>
          </label>
          <label className="text-xs text-zinc-500">
            Кол-во
            <input
              className={filterInputClass}
              value={filters.quantity ?? ""}
              onChange={(e) => onFilterChange("quantity", e.target.value)}
              placeholder="1"
            />
          </label>
        </div>
      </div>

      {(selectedCount > 0 || editing) && (
        <div className="panel flex flex-wrap items-center gap-3 p-4">
          <span className="text-sm text-zinc-300">Выбрано: {selectedCount}</span>
          {!editing ? (
            <>
              <button
                type="button"
                className="btn-ghost px-3 py-1.5 text-sm text-amber-300"
                disabled={busy}
                onClick={startEdit}
              >
                Изменить
              </button>
              <button
                type="button"
                className="btn-ghost px-3 py-1.5 text-sm text-red-400"
                disabled={busy}
                onClick={onDeleteSelected}
              >
                Удалить
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn-primary px-3 py-1.5 text-sm"
                disabled={busy}
                onClick={onSave}
              >
                {updateMut.isPending ? "Сохранение…" : "Сохранить"}
              </button>
              <button
                type="button"
                className="btn-ghost px-3 py-1.5 text-sm"
                disabled={busy}
                onClick={cancelEdit}
              >
                Отмена
              </button>
            </>
          )}
          {actionError && <span className="text-sm text-red-300">{actionError}</span>}
        </div>
      )}

      <div className="card overflow-hidden p-0">
        <div className="border-b border-zinc-800/80 px-5 py-4">
          <h3 className="text-sm font-semibold text-zinc-200">
            {outliersOnly ? "Подозрительные сделки" : "Записи рынка"}
          </h3>
          <p className="mt-1 text-xs text-zinc-500">
            {outliersOnly
              ? "Сделки, скрытые на графиках как статистические выбросы. Можно править или удалить."
              : "Сырые данные, из которых строятся графики. Выберите строки для удаления или правки."}
          </p>
        </div>

        {query.isLoading ? (
          <div className="p-8">
            <LoadingState />
          </div>
        ) : query.isError ? (
          <p className="px-5 py-8 text-sm text-red-300">Не удалось загрузить записи</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                    <th className="w-10 px-3 py-3">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-zinc-600 bg-zinc-900"
                        checked={allPageSelected}
                        onChange={toggleAll}
                        disabled={!items.length || editing}
                        aria-label="Выбрать все на странице"
                      />
                    </th>
                    <th className="px-3 py-3 font-medium">Дата</th>
                    <th className="px-3 py-3 font-medium">Товар</th>
                    <th className="px-3 py-3 font-medium">Продавец</th>
                    <th className="px-3 py-3 font-medium">Цена</th>
                    <th className="px-3 py-3 font-medium">Валюта</th>
                    <th className="px-3 py-3 font-medium">Сторона</th>
                    <th className="px-3 py-3 font-medium">Кол-во</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-zinc-500">
                        {hasActiveFilters
                          ? "Ничего не найдено"
                          : outliersOnly
                            ? "Выбросов за последние 30 дней не найдено"
                            : "Записей пока нет"}
                      </td>
                    </tr>
                  ) : (
                    items.map((row) => {
                      const isSelected = selected.has(row.id);
                      const isRowEditing = editing && isSelected;
                      const draft = drafts[row.id];
                      return (
                        <tr
                          key={row.id}
                          className={`border-b border-zinc-800/50 ${
                            isSelected ? "bg-amber-950/20" : ""
                          }`}
                        >
                          <td className="px-3 py-3">
                            <input
                              type="checkbox"
                              className="h-4 w-4 rounded border-zinc-600 bg-zinc-900"
                              checked={isSelected}
                              disabled={editing}
                              onChange={() => toggleOne(row.id)}
                              aria-label={`Выбрать ${row.product_name_raw}`}
                            />
                          </td>
                          <td className="whitespace-nowrap px-3 py-3 text-zinc-300">
                            {isRowEditing && draft ? (
                              <input
                                type="datetime-local"
                                className="input w-[12.5rem] px-2 py-1 text-xs"
                                value={draft.recorded_at}
                                onChange={(e) =>
                                  updateDraft(row.id, "recorded_at", e.target.value)
                                }
                              />
                            ) : (
                              formatLoginAt(row.recorded_at)
                            )}
                          </td>
                          <td className="px-3 py-3 text-zinc-200">
                            {isRowEditing && draft ? (
                              <input
                                className="input w-full min-w-[10rem] px-2 py-1 text-xs"
                                value={draft.product_name_raw}
                                onChange={(e) =>
                                  updateDraft(row.id, "product_name_raw", e.target.value)
                                }
                              />
                            ) : (
                              <>
                                <p className="font-medium">
                                  {row.item_name || row.product_name_raw}
                                </p>
                                {row.item_name &&
                                  row.product_name_raw !== row.item_name && (
                                    <p className="text-[0.65rem] text-zinc-500">
                                      {row.product_name_raw}
                                    </p>
                                  )}
                              </>
                            )}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">
                            {isRowEditing && draft ? (
                              <input
                                className="input w-full min-w-[8rem] px-2 py-1 text-xs"
                                value={draft.seller_name}
                                onChange={(e) =>
                                  updateDraft(row.id, "seller_name", e.target.value)
                                }
                              />
                            ) : (
                              row.seller_name
                            )}
                          </td>
                          <td className="px-3 py-3 font-mono text-xs text-zinc-200">
                            {isRowEditing && draft ? (
                              <input
                                className="input w-24 px-2 py-1 text-xs"
                                value={draft.price}
                                onChange={(e) => updateDraft(row.id, "price", e.target.value)}
                              />
                            ) : (
                              <div className="flex flex-wrap items-center gap-2">
                                <span>{formatMarketPrice(row.price)}</span>
                                {row.is_outlier ? (
                                  <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[0.65rem] font-medium uppercase tracking-wide text-amber-300">
                                    выброс
                                  </span>
                                ) : null}
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-3 text-zinc-400">
                            {isRowEditing && draft ? (
                              <input
                                className="input w-24 px-2 py-1 text-xs"
                                value={draft.currency}
                                onChange={(e) =>
                                  updateDraft(row.id, "currency", e.target.value)
                                }
                              />
                            ) : (
                              row.currency
                            )}
                          </td>
                          <td className="px-3 py-3">
                            {isRowEditing && draft ? (
                              <select
                                className="input px-2 py-1 text-xs"
                                value={draft.side}
                                onChange={(e) => updateDraft(row.id, "side", e.target.value)}
                              >
                                <option value="">—</option>
                                <option value="buy">Покупка</option>
                                <option value="sell">Продажа</option>
                              </select>
                            ) : (
                              <span
                                className={`rounded-lg px-2 py-0.5 text-xs font-medium ${
                                  row.side === "buy"
                                    ? "bg-emerald-950/60 text-emerald-300"
                                    : row.side === "sell"
                                      ? "bg-amber-950/60 text-amber-300"
                                      : "bg-zinc-800 text-zinc-400"
                                }`}
                              >
                                {formatMarketSide(row.side)}
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-zinc-300">
                            {isRowEditing && draft ? (
                              <input
                                className="input w-20 px-2 py-1 text-xs"
                                value={draft.quantity}
                                onChange={(e) =>
                                  updateDraft(row.id, "quantity", e.target.value)
                                }
                              />
                            ) : (
                              row.quantity ?? "—"
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-zinc-800/80 px-5 py-3 text-xs text-zinc-500">
              <span>
                {total.toLocaleString("ru-RU")} записей
                {query.isFetching && !editing && " · обновление..."}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1 || editing}
                  onClick={() => {
                    setPage((p) => Math.max(1, p - 1));
                    setSelected(new Set());
                  }}
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                >
                  ←
                </button>
                <span>
                  {page} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages || editing}
                  onClick={() => {
                    setPage((p) => p + 1);
                    setSelected(new Set());
                  }}
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                >
                  →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
