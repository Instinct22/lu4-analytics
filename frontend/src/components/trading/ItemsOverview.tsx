import { Line, LineChart, ResponsiveContainer } from "recharts";

interface ItemCard {
  entity_id: string;
  display_name: string;
  current_price: number;
  price_change_pct: number;
  total_volume: number;
  deal_count: number;
  sparkline: number[];
}

interface Props {
  items: ItemCard[];
  onSelect: (entityId: string, displayName: string) => void;
  selectedId: string | null;
}

function MiniSparkline({ data }: { data: number[] }) {
  const chartData = data.map((value, i) => ({ i, value }));
  if (!chartData.length) return <div className="h-10 w-full rounded bg-zinc-800/40" />;

  const up = data.length >= 2 && data[data.length - 1] >= data[0];
  const stroke = up ? "#34d399" : "#f87171";

  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={chartData}>
        <Line type="monotone" dataKey="value" stroke={stroke} strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function ItemsOverview({ items, onSelect, selectedId }: Props) {
  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-zinc-200">Мини-мониторинг предметов</h3>
        <p className="mt-1 text-xs text-zinc-500">Все предметы с активностью за период · клик для выбора</p>
      </div>

      {!items.length ? (
        <p className="text-sm text-zinc-500">Нет данных за период</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[2200px]:grid-cols-6">
          {items.map((item) => {
            const change = Number(item.price_change_pct);
            const active = item.entity_id === selectedId;
            return (
              <button
                key={item.entity_id}
                type="button"
                onClick={() => onSelect(item.entity_id, item.display_name)}
                className={`rounded-xl border p-3 text-left transition-all ${
                  active
                    ? "border-amber-500/40 bg-amber-500/10 ring-1 ring-amber-500/20"
                    : "border-zinc-800/80 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900/60"
                }`}
              >
                <p className="truncate text-sm font-medium text-zinc-100">{item.display_name}</p>
                <div className="mt-2 flex items-baseline justify-between gap-2">
                  <span className="text-lg font-semibold tabular-nums text-zinc-50">
                    {Number(item.current_price).toLocaleString("ru-RU", { maximumFractionDigits: 0 })}
                  </span>
                  <span className={`text-xs font-medium tabular-nums ${change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {change >= 0 ? "+" : ""}
                    {change.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2">
                  <MiniSparkline data={item.sparkline} />
                </div>
                <div className="mt-2 flex justify-between text-[0.65rem] text-zinc-500">
                  <span>Vol: {item.total_volume.toLocaleString("ru-RU")}</span>
                  <span>{item.deal_count} сделок</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
