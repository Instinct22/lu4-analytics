import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { getPricesByIds } from "../../api/market";
import {
  setTradingCharacterMain,
  updateTradingCharacter,
  type InventoryLine,
  type InventoryLineInput,
  type TradeMode,
  type TradingCharacter,
} from "../../api/trading";
import { formatGroupedInt, parseGroupedInt } from "../../lib/formatNumber";
import {
  mergeClipboardItems,
  useTradingItemClipboard,
  setTradingItemClipboard,
} from "../../lib/tradingItemClipboard";
import { ItemIcon } from "../craft/CraftCostBar";
import { ConfirmDialog } from "../ui";
import TradingItemSelect from "./TradingItemSelect";

const MASTER_COIN_EXTERNAL_ID = 4037;

export type EditableLine = {
  key: string;
  item_external_id: number;
  item_name: string;
  quantity: number;
  unit_price: number;
  catalog_matched: boolean;
};

type Props = {
  character: TradingCharacter;
  canWrite: boolean;
  readOnly?: boolean;
  /** Show Main checkbox (bank ↔ warehouse sync). Requires warehouse sync rights. */
  showMain?: boolean;
  onDeleted?: (id: string) => void;
  onSaved?: (character: TradingCharacter) => void;
  onDeleteRequest?: (id: string) => Promise<void>;
  onMainChanged?: () => void;
};

function formatAdena(value: number) {
  return formatGroupedInt(Math.round(value)) || "0";
}

function parseNonNegInt(raw: string): number {
  const digits = parseGroupedInt(raw);
  if (!digits) return 0;
  return Math.max(0, Number(digits) || 0);
}

function toEditable(items: InventoryLine[] | undefined): EditableLine[] {
  return (items ?? []).map((item, idx) => ({
    key: item.id || `${item.item_external_id}-${idx}`,
    item_external_id: item.item_external_id,
    item_name: item.item_name,
    quantity: Number(item.quantity) || 0,
    unit_price: Number(item.unit_price) || 0,
    catalog_matched:
      item.catalog_matched !== undefined
        ? Boolean(item.catalog_matched)
        : item.item_external_id >= 0,
  }));
}

function linesToInput(lines: EditableLine[]): InventoryLineInput[] {
  return lines.map((line) => ({
    item_external_id: line.item_external_id,
    item_name: line.item_name,
    quantity: line.quantity,
    unit_price: line.unit_price,
  }));
}

function sumLines(lines: EditableLine[]): number {
  return lines.reduce((sum, line) => sum + line.quantity * line.unit_price, 0);
}

export default function CharacterCard({
  character,
  canWrite,
  readOnly = false,
  showMain = false,
  onSaved,
  onDeleteRequest,
  onMainChanged,
}: Props) {
  const editable = canWrite && !readOnly;
  const isMerchant = character.kind === "merchant";
  const isBank = character.kind === "bank";
  const [open, setOpen] = useState(false);
  const [isMain, setIsMain] = useState(() => Boolean(character.is_main));
  const [cleanAdena, setCleanAdena] = useState(() => Math.round(Number(character.clean_adena) || 0));
  const [masterCoin, setMasterCoin] = useState(() => Math.round(Number(character.master_coin) || 0));
  const [masterCoinPrice, setMasterCoinPrice] = useState(() =>
    Math.round(Number(character.master_coin_price) || 0),
  );
  const [description, setDescription] = useState(character.description ?? "");
  const [tradeMode, setTradeMode] = useState<TradeMode>(
    isMerchant ? character.trade_mode || "sell" : "sell",
  );
  const [sellLines, setSellLines] = useState<EditableLine[]>(() =>
    toEditable(character.sell_items?.length ? character.sell_items : character.items),
  );
  const [buyLines, setBuyLines] = useState<EditableLine[]>(() => toEditable(character.buy_items));
  const [dirty, setDirty] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const [copyHint, setCopyHint] = useState("");
  const clipboard = useTradingItemClipboard();
  const hasClipboard = clipboard.items.length > 0;
  const fetchedMcPriceFor = useRef<string | null>(null);

  useEffect(() => {
    setCleanAdena(Math.round(Number(character.clean_adena) || 0));
    setMasterCoin(Math.round(Number(character.master_coin) || 0));
    setMasterCoinPrice(Math.round(Number(character.master_coin_price) || 0));
    setDescription(character.description ?? "");
    setTradeMode(character.kind === "merchant" ? character.trade_mode || "sell" : "sell");
    setSellLines(toEditable(character.sell_items?.length ? character.sell_items : character.items));
    setBuyLines(toEditable(character.buy_items));
    setIsMain(Boolean(character.is_main));
    setDirty(false);
    setError("");
    setCopyHint("");
    fetchedMcPriceFor.current = null;
  }, [character]);

  const mainMut = useMutation({
    mutationFn: (next: boolean) => setTradingCharacterMain(character.id, next),
    onSuccess: (saved) => {
      setIsMain(Boolean(saved.is_main));
      setError("");
      onSaved?.(saved);
      onMainChanged?.();
    },
    onError: () => setError("Не удалось изменить Main"),
  });

  // Pull market MC→adena price when saved price is empty
  useEffect(() => {
    if (!editable) return;
    if (Number(character.master_coin_price) > 0) return;
    if (fetchedMcPriceFor.current === character.id) return;
    fetchedMcPriceFor.current = character.id;
    let cancelled = false;
    void (async () => {
      try {
        const prices = await getPricesByIds(String(MASTER_COIN_EXTERNAL_ID));
        const row = prices?.[String(MASTER_COIN_EXTERNAL_ID)];
        const raw = row?.day_vwap ?? row?.last_price ?? 0;
        const price = Math.round(Number(raw) || 0);
        if (!cancelled && price > 0) {
          setMasterCoinPrice((prev) => (prev > 0 ? prev : price));
          setDirty(true);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [character.id, character.master_coin_price, editable]);

  const isBuy = isMerchant && tradeMode === "buy";
  const lines = isBuy ? buyLines : sellLines;
  const setLines = isBuy ? setBuyLines : setSellLines;

  const sellValue = dirty ? sumLines(sellLines) : Number(character.adena_in_items) || 0;
  const buyCost = dirty ? sumLines(buyLines) : Number(character.buy_cost) || 0;
  const displayClean = dirty ? cleanAdena : Number(character.clean_adena) || 0;
  const displayMasterCoin = dirty ? masterCoin : Number(character.master_coin) || 0;
  const displayMasterCoinPrice = dirty
    ? masterCoinPrice
    : Number(character.master_coin_price) || 0;
  const masterCoinAdena = displayMasterCoin * displayMasterCoinPrice;
  const remainingAfterBuy = displayClean + masterCoinAdena - buyCost;
  const totalDisplay = isBuy ? remainingAfterBuy : displayClean + sellValue + masterCoinAdena;
  const activeListSum = isBuy ? buyCost : sellValue;

  const saveMut = useMutation({
    mutationFn: () =>
      updateTradingCharacter(character.id, {
        clean_adena: cleanAdena,
        master_coin: masterCoin,
        master_coin_price: masterCoinPrice,
        description: description.trim() || null,
        trade_mode: isMerchant ? tradeMode : "sell",
        sell_items: linesToInput(sellLines),
        buy_items: isMerchant ? linesToInput(buyLines) : [],
      }),
    onSuccess: (saved) => {
      setDirty(false);
      setError("");
      onSaved?.(saved);
    },
    onError: () => setError("Не удалось сохранить"),
  });

  const addItem = async (item: { external_id: number; display_name: string; custom?: boolean }) => {
    const name = item.display_name.trim();
    if (!name) return;

    const isCustom = Boolean(item.custom) || item.external_id < 0;
    const duplicate = isCustom
      ? lines.some((l) => l.item_name.toLowerCase() === name.toLowerCase())
      : lines.some((l) => l.item_external_id === item.external_id);
    if (duplicate) {
      setError("Предмет уже в списке");
      return;
    }

    setError("");
    let unitPrice = 0;
    if (!isCustom) {
      try {
        const prices = await getPricesByIds(String(item.external_id));
        const row = prices?.[String(item.external_id)];
        const raw = row?.day_vwap ?? row?.last_price ?? 0;
        unitPrice = Number(raw) || 0;
      } catch {
        unitPrice = 0;
      }
    }

    setLines((prev) => [
      ...prev,
      {
        key: `new-${item.external_id}-${Date.now()}`,
        item_external_id: item.external_id,
        item_name: name,
        quantity: 1,
        unit_price: unitPrice,
        catalog_matched: !isCustom,
      },
    ]);
    setDirty(true);
  };

  const copyItems = () => {
    if (!lines.length) {
      setCopyHint("Нечего копировать");
      return;
    }
    setTradingItemClipboard(linesToInput(lines), character.nick);
    setCopyHint(`Скопировано: ${lines.length}`);
    setError("");
  };

  const pasteItems = () => {
    if (!clipboard.items.length) {
      setError("Буфер пуст — сначала скопируйте предметы у другого персонажа");
      return;
    }
    const { next, added, skipped } = mergeClipboardItems(lines, clipboard.items);
    if (added === 0) {
      setError(skipped ? "Все предметы уже есть в списке" : "Нечего вставлять");
      return;
    }
    setLines(next);
    setDirty(true);
    setError("");
    setCopyHint(
      skipped > 0
        ? `Добавлено: ${added}, пропущено (уже есть): ${skipped}`
        : `Добавлено: ${added}`,
    );
  };

  const switchMode = (mode: TradeMode) => {
    if (!isMerchant || mode === tradeMode) return;
    setTradeMode(mode);
    setDirty(true);
    setError("");
    setCopyHint("");
  };

  return (
    <div className="card !p-0 overflow-hidden">
      <div className="border-b border-zinc-800/80 px-4 py-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-start gap-3 rounded-lg text-left transition hover:opacity-90"
        >
          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-zinc-700/80 bg-zinc-900/60 text-sm font-semibold text-zinc-300">
            {open ? "−" : "+"}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-zinc-100">{character.nick}</h3>
                {isMain && isBank ? (
                  <span className="rounded-md bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-emerald-300">
                    Main
                  </span>
                ) : null}
                {isMerchant ? (
                  <span
                    className={`rounded-md px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${
                      isBuy
                        ? "bg-sky-500/15 text-sky-300"
                        : "bg-amber-500/15 text-amber-300"
                    }`}
                  >
                    {isBuy ? "Покупает" : "Продаёт"}
                  </span>
                ) : null}
              </div>
              <p className="text-base font-semibold tabular-nums text-amber-400 sm:text-lg">
                {isBuy ? "Остаток" : "Итого"}: {formatAdena(totalDisplay)} а
              </p>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
              <span>
                Чистая адена:{" "}
                <span className="tabular-nums text-zinc-300">{formatAdena(displayClean)} а</span>
              </span>
              <span>
                Master Coin:{" "}
                <span className="tabular-nums text-zinc-300">
                  {formatAdena(displayMasterCoin)}
                  {displayMasterCoinPrice > 0
                    ? ` × ${formatAdena(displayMasterCoinPrice)} = ${formatAdena(masterCoinAdena)} а`
                    : ""}
                </span>
              </span>
              {isBuy ? (
                <span>
                  На покупки:{" "}
                  <span className="tabular-nums text-sky-300">{formatAdena(activeListSum)} а</span>
                </span>
              ) : (
                <span>
                  В предметах:{" "}
                  <span className="tabular-nums text-zinc-300">{formatAdena(activeListSum)} а</span>
                </span>
              )}
            </div>
            {!open && (character.description || description) ? (
              <p className="mt-2 line-clamp-2 text-xs text-zinc-500">
                {dirty ? description : character.description}
              </p>
            ) : null}
          </div>
        </button>
      </div>

      {open ? (
        <div className="space-y-4 p-4">
          {isMerchant ? (
            <div className="flex w-fit flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1">
              {(
                [
                  { id: "sell", label: "Продаёт" },
                  { id: "buy", label: "Покупает" },
                ] as const
              ).map((opt) => {
                const active = tradeMode === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={!editable && !active}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (editable) switchMode(opt.id);
                    }}
                    className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                      active
                        ? opt.id === "buy"
                          ? "bg-sky-600 text-zinc-50"
                          : "bg-amber-600 text-zinc-950"
                        : "text-zinc-400 hover:text-zinc-200 disabled:opacity-40"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          ) : null}

          {showMain && isBank ? (
            <label className="flex w-fit items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-amber-500 focus:ring-amber-500/40"
                checked={isMain}
                disabled={!editable || mainMut.isPending || readOnly}
                onChange={(e) => mainMut.mutate(e.target.checked)}
              />
              <span>Main</span>
              <span className="text-xs text-zinc-500">для синхронизации со складом</span>
            </label>
          ) : null}

          {editable ? (
            <>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-zinc-500">Чистая адена</span>
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  spellCheck={false}
                  className="input tabular-nums"
                  value={formatGroupedInt(cleanAdena)}
                  onChange={(e) => {
                    setCleanAdena(parseNonNegInt(e.target.value));
                    setDirty(true);
                  }}
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-zinc-500">Master Coin</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    spellCheck={false}
                    className="input tabular-nums"
                    value={formatGroupedInt(masterCoin)}
                    onChange={(e) => {
                      setMasterCoin(parseNonNegInt(e.target.value));
                      setDirty(true);
                    }}
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-zinc-500">
                    Цена MC (адена)
                  </span>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    spellCheck={false}
                    className="input tabular-nums"
                    value={formatGroupedInt(masterCoinPrice)}
                    onChange={(e) => {
                      setMasterCoinPrice(parseNonNegInt(e.target.value));
                      setDirty(true);
                    }}
                  />
                </label>
              </div>
              {masterCoin > 0 || masterCoinPrice > 0 ? (
                <p className="text-xs text-zinc-500">
                  В Master Coin:{" "}
                  <span className="tabular-nums text-zinc-300">
                    {formatAdena(masterCoin * masterCoinPrice)} а
                  </span>
                </p>
              ) : null}
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-zinc-500">Описание</span>
                <textarea
                  className="input min-h-[4.5rem] resize-y"
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    setDirty(true);
                  }}
                  placeholder="Описание торговца…"
                />
              </label>
              <div>
                <span className="mb-1 block text-xs font-medium text-zinc-500">
                  {isBuy ? "Добавить в список покупок" : "Добавить в инвентарь"}
                </span>
                <TradingItemSelect onSelect={(item) => void addItem(item)} />
              </div>
            </>
          ) : (
            <>
              {character.description ? (
                <p className="text-sm text-zinc-400">{character.description}</p>
              ) : null}
            </>
          )}

          <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
            <div className="border-b border-zinc-800/80 bg-zinc-900/60 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
              {isBuy ? "Список покупок" : "Инвентарь"}
            </div>
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead className="bg-zinc-900/80 text-xs uppercase tracking-wider text-zinc-500">
                <tr>
                  <th className="px-3 py-2 font-semibold">Предмет</th>
                  <th className="px-3 py-2 font-semibold">Кол-во</th>
                  <th className="px-3 py-2 font-semibold">Цена</th>
                  <th className="px-3 py-2 font-semibold">Сумма</th>
                  {editable ? <th className="px-3 py-2 font-semibold" /> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {lines.length === 0 ? (
                  <tr>
                    <td colSpan={editable ? 5 : 4} className="px-3 py-4 text-center text-zinc-500">
                      {isBuy ? "Список покупок пуст" : "Нет предметов"}
                    </td>
                  </tr>
                ) : (
                  lines.map((line) => {
                    const unmatched = !line.catalog_matched || line.item_external_id < 0;
                    return (
                    <tr key={line.key} className="text-zinc-300">
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2.5">
                          <div className="relative shrink-0">
                            <ItemIcon
                              id={unmatched ? null : line.item_external_id}
                              size={36}
                            />
                            {unmatched ? (
                              <span
                                className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-zinc-950"
                                title="Предмет не найден в каталоге"
                                aria-label="Не найден в каталоге"
                              />
                            ) : null}
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium text-zinc-200">{line.item_name}</div>
                            <div className="text-xs text-zinc-600">
                              {unmatched ? "свой предмет" : `#${line.item_external_id}`}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        {editable ? (
                          <input
                            type="text"
                            inputMode="numeric"
                            autoComplete="off"
                            spellCheck={false}
                            className="input w-28 tabular-nums"
                            value={formatGroupedInt(line.quantity)}
                            onChange={(e) => {
                              const quantity = parseNonNegInt(e.target.value);
                              setLines((prev) =>
                                prev.map((row) =>
                                  row.key === line.key ? { ...row, quantity } : row,
                                ),
                              );
                              setDirty(true);
                            }}
                          />
                        ) : (
                          <span className="tabular-nums">{formatAdena(line.quantity)}</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {editable ? (
                          <input
                            type="text"
                            inputMode="numeric"
                            autoComplete="off"
                            spellCheck={false}
                            className="input w-36 tabular-nums"
                            value={formatGroupedInt(Math.round(line.unit_price))}
                            onChange={(e) => {
                              const unit_price = parseNonNegInt(e.target.value);
                              setLines((prev) =>
                                prev.map((row) =>
                                  row.key === line.key ? { ...row, unit_price } : row,
                                ),
                              );
                              setDirty(true);
                            }}
                          />
                        ) : (
                          <span className="tabular-nums">{formatAdena(line.unit_price)}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-zinc-200">
                        {formatAdena(line.quantity * line.unit_price)}
                      </td>
                      {editable ? (
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            className="text-xs text-rose-400 hover:text-rose-300"
                            onClick={() => {
                              setLines((prev) => prev.filter((row) => row.key !== line.key));
                              setDirty(true);
                            }}
                          >
                            Удалить
                          </button>
                        </td>
                      ) : null}
                    </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {isBuy ? (
            <p className="text-sm text-zinc-400">
              Остаток адены после покупок:{" "}
              <span
                className={`font-semibold tabular-nums ${
                  remainingAfterBuy < 0 ? "text-rose-400" : "text-amber-400"
                }`}
              >
                {formatAdena(remainingAfterBuy)} а
              </span>
            </p>
          ) : null}

          {error ? <p className="text-sm text-rose-400">{error}</p> : null}
          {copyHint ? <p className="text-sm text-zinc-400">{copyHint}</p> : null}

          <div className="flex flex-wrap items-center gap-2">
            {lines.length > 0 ? (
              <button
                type="button"
                className="rounded-lg border border-zinc-700/80 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800/60"
                onClick={copyItems}
              >
                Копировать предметы
              </button>
            ) : null}
            {editable && hasClipboard ? (
              <button
                type="button"
                className="rounded-lg border border-amber-500/40 px-3 py-2 text-sm text-amber-200 hover:bg-amber-500/10"
                onClick={pasteItems}
                title={
                  clipboard.sourceNick
                    ? `Из буфера: ${clipboard.sourceNick} (${clipboard.items.length})`
                    : undefined
                }
              >
                Вставить
                {clipboard.sourceNick ? ` «${clipboard.sourceNick}»` : ""} ({clipboard.items.length})
              </button>
            ) : null}
          </div>

          {editable ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn-primary"
                disabled={!dirty || saveMut.isPending}
                onClick={() => saveMut.mutate()}
              >
                {saveMut.isPending ? "Сохранение…" : "Сохранить"}
              </button>
              {onDeleteRequest ? (
                <button
                  type="button"
                  className="rounded-lg border border-rose-500/40 px-3 py-2 text-sm text-rose-300 hover:bg-rose-500/10"
                  onClick={() => setConfirmDelete(true)}
                >
                  Удалить персонажа
                </button>
              ) : null}
              {dirty ? (
                <span className="text-xs text-amber-400/80">Есть несохранённые изменения</span>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {onDeleteRequest ? (
        <ConfirmDialog
          open={confirmDelete}
          title="Удалить персонажа?"
          message={`Персонаж «${character.nick}» и его инвентарь будут удалены.`}
          confirmLabel="Удалить"
          tone="danger"
          onConfirm={() => {
            void onDeleteRequest(character.id).then(() => setConfirmDelete(false));
          }}
          onCancel={() => setConfirmDelete(false)}
        />
      ) : null}
    </div>
  );
}

function mapSnapshotItems(
  items: Array<{
    item_external_id: number;
    item_name: string;
    quantity: number;
    unit_price: string | number;
    catalog_matched?: boolean;
  }> | undefined,
  prefix: string,
): InventoryLine[] {
  return (items ?? []).map((item, idx) => {
    const quantity = Number(item.quantity) || 0;
    const unit_price = Number(item.unit_price) || 0;
    const catalog_matched =
      item.catalog_matched !== undefined
        ? Boolean(item.catalog_matched)
        : item.item_external_id >= 0;
    return {
      id: `${prefix}-${idx}`,
      item_external_id: item.item_external_id,
      item_name: item.item_name,
      quantity,
      unit_price,
      line_total: quantity * unit_price,
      catalog_matched,
    };
  });
}

/** Convert snapshot payload character into TradingCharacter shape for the card. */
export function characterFromSnapshot(
  row: {
    id: string;
    kind: "bank" | "merchant";
    nick: string;
    clean_adena: string | number;
    master_coin?: string | number;
    master_coin_price?: string | number;
    description?: string;
    trade_mode?: TradeMode;
    is_main?: boolean;
    sell_items?: Array<{
      item_external_id: number;
      item_name: string;
      quantity: number;
      unit_price: string | number;
      catalog_matched?: boolean;
    }>;
    buy_items?: Array<{
      item_external_id: number;
      item_name: string;
      quantity: number;
      unit_price: string | number;
      catalog_matched?: boolean;
    }>;
    items?: Array<{
      item_external_id: number;
      item_name: string;
      quantity: number;
      unit_price: string | number;
      catalog_matched?: boolean;
    }>;
  },
  index: number,
): TradingCharacter {
  const sell_items = mapSnapshotItems(row.sell_items ?? row.items, `${row.id}-sell`);
  const buy_items = mapSnapshotItems(row.buy_items, `${row.id}-buy`);
  const adena_in_items = sell_items.reduce((s, i) => s + i.line_total, 0);
  const buy_cost = buy_items.reduce((s, i) => s + i.line_total, 0);
  const clean_adena = Number(row.clean_adena) || 0;
  const master_coin = Number(row.master_coin) || 0;
  const master_coin_price = Number(row.master_coin_price) || 0;
  const master_coin_adena = master_coin * master_coin_price;
  const trade_mode: TradeMode =
    row.kind === "merchant" && row.trade_mode === "buy" ? "buy" : "sell";
  return {
    id: row.id,
    kind: row.kind,
    nick: row.nick,
    clean_adena,
    master_coin,
    master_coin_price,
    master_coin_adena,
    description: row.description || null,
    trade_mode,
    is_main: Boolean(row.is_main) && row.kind === "bank",
    adena_in_items,
    buy_cost,
    total_adena: clean_adena + adena_in_items + master_coin_adena - buy_cost,
    sort_order: index,
    sell_items,
    buy_items,
    items: trade_mode === "buy" ? buy_items : sell_items,
  };
}
