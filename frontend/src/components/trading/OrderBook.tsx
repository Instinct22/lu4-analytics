import { useMemo, useState } from "react";

interface Level {
  price: number;
  volume: number;
}

interface Props {
  buys: Level[];
  sells: Level[];
}

type SortKey = "price" | "volume";
type SortOrder = "asc" | "desc";

function formatPrice(value: number): string {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function sortLevels(levels: Level[], sortKey: SortKey, sortOrder: SortOrder): Level[] {
  return [...levels].sort((a, b) => {
    const diff = sortKey === "price" ? a.price - b.price : a.volume - b.volume;
    return sortOrder === "asc" ? diff : -diff;
  });
}

function SortHeader({
  label,
  active,
  order,
  align = "left",
  onClick,
}: {
  label: string;
  active: boolean;
  order: SortOrder;
  align?: "left" | "right";
  onClick: () => void;
}) {
  return (
    <th className={`px-3 py-2 ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        type="button"
        onClick={onClick}
        className={[
          "inline-flex items-center gap-1 uppercase transition-colors",
          align === "right" ? "ml-auto" : "",
          active ? "text-zinc-200" : "text-zinc-500 hover:text-zinc-300",
        ].join(" ")}
      >
        {label}
        {active && <span aria-hidden>{order === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

function LevelTable({
  title,
  levels,
  accent,
  defaultPriceOrder,
}: {
  title: string;
  levels: Level[];
  accent: "emerald" | "red";
  defaultPriceOrder: SortOrder;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("price");
  const [sortOrder, setSortOrder] = useState<SortOrder>(defaultPriceOrder);

  const sortedLevels = useMemo(
    () => sortLevels(levels, sortKey, sortOrder),
    [levels, sortKey, sortOrder],
  );

  const maxVol = Math.max(...sortedLevels.map((l) => l.volume), 1);
  const color = accent === "emerald" ? "bg-emerald-500/30" : "bg-red-500/30";

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortOrder(key === "price" ? defaultPriceOrder : "desc");
  };

  return (
    <div>
      <h4
        className={`mb-3 text-xs font-semibold uppercase tracking-wider ${accent === "emerald" ? "text-emerald-400" : "text-red-400"}`}
      >
        {title}
      </h4>
      {!levels.length ? (
        <p className="text-sm text-zinc-500">Нет уровней</p>
      ) : (
        <div className="max-h-72 overflow-y-auto rounded-xl border border-zinc-800/80">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-zinc-950/90 text-xs">
              <tr>
                <SortHeader
                  label="Цена"
                  active={sortKey === "price"}
                  order={sortOrder}
                  onClick={() => toggleSort("price")}
                />
                <SortHeader
                  label="Объём"
                  active={sortKey === "volume"}
                  order={sortOrder}
                  align="right"
                  onClick={() => toggleSort("volume")}
                />
              </tr>
            </thead>
            <tbody>
              {sortedLevels.map((level) => (
                <tr key={`${title}-${level.price}-${level.volume}`} className="relative border-t border-zinc-800/40">
                  <td className="relative px-3 py-2 tabular-nums text-zinc-200">
                    <div
                      className={`absolute inset-y-0 left-0 ${color}`}
                      style={{ width: `${(level.volume / maxVol) * 100}%` }}
                    />
                    <span className="relative">{formatPrice(level.price)}</span>
                  </td>
                  <td className="relative px-3 py-2 text-right tabular-nums text-zinc-400">
                    {level.volume.toLocaleString("ru-RU")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function OrderBook({ buys, sells }: Props) {
  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-zinc-200">Стакан заявок</h3>
        <p className="mt-1 text-xs text-zinc-500">
          Агрегация по цене за выбранный период · сортировка по клику на заголовок
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <LevelTable title="Продажи" levels={sells} accent="red" defaultPriceOrder="asc" />
        <LevelTable title="Покупки" levels={buys} accent="emerald" defaultPriceOrder="desc" />
      </div>
    </div>
  );
}
