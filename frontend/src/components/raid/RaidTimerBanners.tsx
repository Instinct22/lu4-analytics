import { useMemo, useState, type MouseEvent, type ReactNode } from "react";
import { ConfirmDialog } from "../ui";
import type { RaidBoss } from "../../lib/raidBosses";
import type { TimerSnapshot } from "../../lib/raidTimers";

type Entry = { boss: RaidBoss; timer: TimerSnapshot };

type PendingClear =
  | { type: "one"; bossId: number; bossName: string }
  | { type: "all"; count: number };

type Props = {
  active: Entry[];
  waiting: Entry[];
  overdue: Entry[];
  onSelect: (id: number) => void;
  canClear?: boolean;
  onClear?: (bossId: number) => void;
};

function Chip({ entry, onSelect }: { entry: Entry; onSelect: (id: number) => void }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(entry.boss.id)}
      className="inline-flex items-center gap-2 rounded-xl bg-zinc-950/50 px-2.5 py-1.5 text-left ring-1 ring-zinc-700/70 transition hover:ring-amber-500/40"
    >
      <span className="max-w-[10rem] truncate text-xs text-zinc-200">{entry.boss.name}</span>
      <span className={`font-mono text-xs font-semibold tabular-nums ${entry.timer.colorClass}`}>
        {entry.timer.display}
      </span>
    </button>
  );
}

function OverdueChip({
  entry,
  onSelect,
  onRequestClear,
  canClear,
}: {
  entry: Entry;
  onSelect: (id: number) => void;
  onRequestClear: (entry: Entry) => void;
  canClear: boolean;
}) {
  const handleClear = (e: MouseEvent) => {
    e.stopPropagation();
    onRequestClear(entry);
  };

  return (
    <div className="inline-flex items-stretch overflow-hidden rounded-xl bg-zinc-950/50 ring-1 ring-red-900/50">
      <button
        type="button"
        onClick={() => onSelect(entry.boss.id)}
        className="inline-flex items-center gap-2 px-2.5 py-1.5 text-left transition hover:bg-red-950/30"
      >
        <span className="max-w-[10rem] truncate text-xs text-zinc-200">{entry.boss.name}</span>
        <span className={`font-mono text-xs font-semibold tabular-nums ${entry.timer.colorClass}`}>
          {entry.timer.display}
        </span>
      </button>
      {canClear && (
        <button
          type="button"
          onClick={handleClear}
          aria-label={`Сбросить таймер ${entry.boss.name}`}
          className="flex w-8 shrink-0 items-center justify-center border-l border-red-900/40 text-sm text-red-400 transition hover:bg-red-900/40 hover:text-red-200"
        >
          ×
        </button>
      )}
    </div>
  );
}

function CollapsibleTimerSection({
  title,
  titleClassName,
  containerClassName,
  count,
  open,
  onToggle,
  borderClassName,
  headerExtra,
  children,
}: {
  title: string;
  titleClassName: string;
  containerClassName: string;
  count: number;
  open: boolean;
  onToggle: () => void;
  borderClassName: string;
  headerExtra?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-2xl border shadow-panel ${containerClassName}`}>
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-label={open ? "Свернуть" : "Развернуть"}
          className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left transition hover:opacity-90"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-zinc-700/80 bg-zinc-900/60 text-sm font-semibold text-zinc-300">
            {open ? "−" : "+"}
          </span>
          <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
            <p className={`text-[0.7rem] font-medium uppercase tracking-wider ${titleClassName}`}>
              {title}
            </p>
            <span className="shrink-0 text-xs tabular-nums text-zinc-500">{count}</span>
          </div>
        </button>
        {headerExtra}
      </div>
      {open && (
        <div className={`flex flex-wrap gap-2 border-t px-4 py-3 ${borderClassName}`}>{children}</div>
      )}
    </div>
  );
}

export default function RaidTimerBanners({
  active,
  waiting,
  overdue,
  onSelect,
  canClear = false,
  onClear,
}: Props) {
  const [waitingOpen, setWaitingOpen] = useState(false);
  const [redOpen, setRedOpen] = useState(false);
  const [pendingClear, setPendingClear] = useState<PendingClear | null>(null);

  const sortedActive = useMemo(
    () =>
      [...active].sort((a, b) => {
        const order = { soon: 0, window: 1, waiting: 2, overdue: 3, idle: 4 } as const;
        const d = order[a.timer.phase] - order[b.timer.phase];
        if (d !== 0) return d;
        if (a.timer.phase === "window") {
          return a.timer.remainingToMaxMs - b.timer.remainingToMaxMs;
        }
        return a.timer.remainingToMinMs - b.timer.remainingToMinMs;
      }),
    [active],
  );

  const sortedWaiting = useMemo(
    () => [...waiting].sort((a, b) => a.timer.remainingToMinMs - b.timer.remainingToMinMs),
    [waiting],
  );

  const sortedOverdue = useMemo(
    () => [...overdue].sort((a, b) => b.timer.remainingToMaxMs - a.timer.remainingToMaxMs),
    [overdue],
  );

  const clearOverdue = onClear ?? (() => {});

  const confirmDialog = useMemo(() => {
    if (!pendingClear) return null;
    if (pendingClear.type === "one") {
      return {
        title: "Сброс таймера",
        message: `Сбросить таймер «${pendingClear.bossName}»?`,
        confirmLabel: "Сбросить",
      };
    }
    return {
      title: "Сброс таймеров",
      message:
        pendingClear.count === 1
          ? "Сбросить просроченный таймер?"
          : `Сбросить все ${pendingClear.count} просроченных таймеров?`,
      confirmLabel: "Сбросить все",
    };
  }, [pendingClear]);

  const handleConfirmClear = () => {
    if (!pendingClear) return;
    if (pendingClear.type === "one") {
      clearOverdue(pendingClear.bossId);
    } else {
      for (const entry of sortedOverdue) {
        clearOverdue(entry.boss.id);
      }
    }
    setPendingClear(null);
  };

  if (sortedActive.length === 0 && sortedWaiting.length === 0 && sortedOverdue.length === 0) {
    return null;
  }

  return (
    <>
      <div className="mb-5 space-y-2">
        {sortedActive.length > 0 && (
          <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 shadow-panel">
            <div className="flex items-center justify-end px-4 py-3">
              <p className="text-[0.7rem] font-medium uppercase tracking-wider text-amber-400/90">
                Скоро / окно респа
              </p>
              <span className="ml-2 shrink-0 text-xs tabular-nums text-zinc-500">
                {sortedActive.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 border-t border-amber-500/15 px-4 py-3">
              {sortedActive.map((e) => (
                <Chip key={e.boss.id} entry={e} onSelect={onSelect} />
              ))}
            </div>
          </div>
        )}

        {sortedWaiting.length > 0 && (
          <CollapsibleTimerSection
            title="Активные таймеры"
            titleClassName="text-zinc-300"
            containerClassName="border-zinc-700/60 bg-zinc-900/40"
            count={sortedWaiting.length}
            open={waitingOpen}
            onToggle={() => setWaitingOpen((v) => !v)}
            borderClassName="border-zinc-800/80"
          >
            {sortedWaiting.map((e) => (
              <Chip key={e.boss.id} entry={e} onSelect={onSelect} />
            ))}
          </CollapsibleTimerSection>
        )}

        {sortedOverdue.length > 0 && (
          <CollapsibleTimerSection
            title="Просроченные таймеры"
            titleClassName="text-red-400/90"
            containerClassName="border-red-900/40 bg-red-950/20"
            count={sortedOverdue.length}
            open={redOpen}
            onToggle={() => setRedOpen((v) => !v)}
            borderClassName="border-red-900/30"
            headerExtra={
              canClear ? (
                <button
                  type="button"
                  onClick={() => setPendingClear({ type: "all", count: sortedOverdue.length })}
                  className="shrink-0 rounded-lg border border-red-800/60 bg-red-950/40 px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-wide text-red-300 transition hover:border-red-600/60 hover:bg-red-900/50 hover:text-red-100"
                >
                  Сбросить все
                </button>
              ) : null
            }
          >
            {sortedOverdue.map((e) => (
              <OverdueChip
                key={e.boss.id}
                entry={e}
                onSelect={onSelect}
                onRequestClear={(entry) =>
                  setPendingClear({
                    type: "one",
                    bossId: entry.boss.id,
                    bossName: entry.boss.name,
                  })
                }
                canClear={canClear}
              />
            ))}
          </CollapsibleTimerSection>
        )}
      </div>

      <ConfirmDialog
        open={pendingClear != null}
        title={confirmDialog?.title ?? ""}
        message={confirmDialog?.message ?? ""}
        confirmLabel={confirmDialog?.confirmLabel}
        tone="danger"
        onConfirm={handleConfirmClear}
        onCancel={() => setPendingClear(null)}
      />
    </>
  );
}
