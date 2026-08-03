import { useQuery } from "@tanstack/react-query";
import { getCraftMonitor, type CraftMonitorCard } from "../../api/market";
import { LoadingState } from "../ui";
import PeriodSelector, { PeriodState } from "./PeriodSelector";
import { periodQueryParams } from "./periodUtils";

interface Props {
  selectedId: string | null;
  onSelect: (entityId: string, displayName: string) => void;
  period: PeriodState;
  onPeriodChange: (next: PeriodState) => void;
  open: boolean;
  onToggle: () => void;
}

function formatPrice(value: number | string | null): string {
  if (value == null) return "—";
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

function ChangeBadge({ value }: { value: number | string | null }) {
  if (value == null) {
    return <span className="text-xs tabular-nums text-zinc-500">н/д</span>;
  }
  const change = Number(value);
  return (
    <span
      className={`text-xs font-medium tabular-nums ${
        change >= 0 ? "text-emerald-400" : "text-red-400"
      }`}
    >
      {change >= 0 ? "+" : ""}
      {change.toFixed(1)}%
    </span>
  );
}

function MonitorCard({
  item,
  active,
  onSelect,
}: {
  item: CraftMonitorCard;
  active: boolean;
  onSelect: (entityId: string, displayName: string) => void;
}) {
  const disabled = !item.entity_id;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => {
        if (item.entity_id) onSelect(item.entity_id, item.display_name);
      }}
      className={`rounded-xl border p-3 text-left transition-all ${
        disabled
          ? "cursor-not-allowed border-zinc-800/60 bg-zinc-950/30 opacity-60"
          : active
            ? "border-amber-500/40 bg-amber-500/10 ring-1 ring-amber-500/20"
            : "border-zinc-800/80 bg-zinc-950/40 hover:border-zinc-700 hover:bg-zinc-900/60"
      }`}
    >
      <p className="truncate text-sm font-medium text-zinc-100">{item.display_name}</p>
      <div className="mt-2 flex items-baseline justify-between gap-2">
        <span className="text-lg font-semibold tabular-nums text-zinc-50">
          {formatPrice(item.vwap)}
        </span>
        <ChangeBadge value={item.price_change_pct} />
      </div>
      <div className="mt-2 text-[0.65rem] text-zinc-500">
        Кол-во: {item.total_quantity.toLocaleString("ru-RU")}
      </div>
    </button>
  );
}

export default function CraftResourcesMonitor({
  selectedId,
  onSelect,
  period,
  onPeriodChange,
  open,
  onToggle,
}: Props) {
  const periodParams = periodQueryParams(period);

  const { data, isLoading, error } = useQuery({
    queryKey: ["craft-monitor", periodParams],
    queryFn: () => getCraftMonitor(periodParams),
    refetchInterval: 60_000,
  });

  const items = data?.items ?? [];

  return (
    <div className="card !p-0 overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-800/80 px-4 py-3">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left transition hover:opacity-90"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-zinc-700/80 bg-zinc-900/60 text-sm font-semibold text-zinc-300">
            {open ? "−" : "+"}
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-zinc-200">Крафт-ресурсы</h3>
            <p className="mt-0.5 text-xs text-zinc-500">
              VWAP и объём по последним лотам продавцов · % за выбранный период
            </p>
          </div>
        </button>
        <PeriodSelector value={period} onChange={onPeriodChange} stopPropagation />
      </div>

      {open ? (
        <div className="p-4">
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <p className="text-sm text-red-400">Не удалось загрузить мониторинг</p>
          ) : !items.length ? (
            <p className="text-sm text-zinc-500">Нет выбранных ресурсов.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[2200px]:grid-cols-6">
              {items.map((item) => (
                <MonitorCard
                  key={item.external_id}
                  item={item}
                  active={item.entity_id === selectedId}
                  onSelect={onSelect}
                />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
