import { useMemo, useState, type ReactNode } from "react";
import type { RaidBoss } from "../../lib/raidBosses";
import type { TimerSnapshot } from "../../lib/raidTimers";

type Entry = { boss: RaidBoss; timer: TimerSnapshot };

type Props = {
  active: Entry[];
  waiting: Entry[];
  overdue: Entry[];
  onSelect: (id: number) => void;
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

function CollapsibleTimerSection({
  title,
  titleClassName,
  containerClassName,
  count,
  open,
  onToggle,
  borderClassName,
  children,
}: {
  title: string;
  titleClassName: string;
  containerClassName: string;
  count: number;
  open: boolean;
  onToggle: () => void;
  borderClassName: string;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-2xl border shadow-panel ${containerClassName}`}>
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={open}
            aria-label={open ? "Свернуть" : "Развернуть"}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-zinc-700/80 bg-zinc-900/60 text-sm font-semibold text-zinc-300 transition hover:border-amber-500/40 hover:text-amber-300"
          >
            {open ? "−" : "+"}
          </button>
          <p className={`text-[0.7rem] font-medium uppercase tracking-wider ${titleClassName}`}>
            {title}
          </p>
        </div>
        <span className="shrink-0 text-xs tabular-nums text-zinc-500">{count}</span>
      </div>
      {open && (
        <div className={`flex flex-wrap gap-2 border-t px-4 py-3 ${borderClassName}`}>{children}</div>
      )}
    </div>
  );
}

export default function RaidTimerBanners({ active, waiting, overdue, onSelect }: Props) {
  const [waitingOpen, setWaitingOpen] = useState(false);
  const [redOpen, setRedOpen] = useState(false);

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

  if (sortedActive.length === 0 && sortedWaiting.length === 0 && sortedOverdue.length === 0) {
    return null;
  }

  return (
    <div className="mb-5 space-y-2">
      {sortedActive.length > 0 && (
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 px-4 py-3 shadow-panel">
          <p className="mb-2 text-[0.7rem] font-medium uppercase tracking-wider text-amber-400/90">
            Скоро / окно респа
          </p>
          <div className="flex flex-wrap gap-2">
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
        >
          {sortedOverdue.map((e) => (
            <Chip key={e.boss.id} entry={e} onSelect={onSelect} />
          ))}
        </CollapsibleTimerSection>
      )}
    </div>
  );
}
