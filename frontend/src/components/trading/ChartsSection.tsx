import type { ReactNode } from "react";
import PeriodSelector, { PeriodState } from "./PeriodSelector";

interface Props {
  title: string;
  open: boolean;
  onToggle: () => void;
  period: PeriodState;
  onPeriodChange: (next: PeriodState) => void;
  children: ReactNode;
  description?: string;
}

export default function ChartsSection({
  title,
  open,
  onToggle,
  period,
  onPeriodChange,
  children,
  description,
}: Props) {
  return (
    <div className="card !p-0 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-zinc-800/80 px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
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
            <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
            {description ? <p className="mt-0.5 text-xs text-zinc-500">{description}</p> : null}
          </div>
        </button>
        <PeriodSelector value={period} onChange={onPeriodChange} stopPropagation align="end" />
      </div>
      {open ? <div className="p-4">{children}</div> : null}
    </div>
  );
}
