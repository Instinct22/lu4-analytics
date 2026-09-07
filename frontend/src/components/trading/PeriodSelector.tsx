import type { ChangeEvent, MouseEvent } from "react";
import {
  dateToDatetimeLocal,
  PeriodKey,
  PERIOD_PRESETS,
  PeriodState,
} from "./periodUtils";

interface Props {
  value: PeriodState;
  onChange: (next: PeriodState) => void;
  /** Stop click from toggling parent collapsible headers. */
  stopPropagation?: boolean;
  /** Chip row alignment — `end` for section headers, `start` for full-width panels. */
  align?: "start" | "end";
}

const HOUR_PRESETS = PERIOD_PRESETS.slice(0, 6);
const DAY_PRESETS = PERIOD_PRESETS.slice(6);

const chipClass = (active: boolean) =>
  `shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
    active
      ? "bg-amber-500 text-zinc-950 shadow-sm ring-1 ring-amber-400/30"
      : "border border-zinc-700/80 bg-zinc-900/80 text-zinc-400 hover:border-zinc-600 hover:bg-zinc-800/80 hover:text-zinc-200"
  }`;

const inputClass =
  "min-w-0 flex-1 rounded-lg border border-zinc-700/80 bg-zinc-950/80 px-2.5 py-1.5 text-xs text-zinc-100 shadow-sm transition-colors focus:border-amber-500/60 focus:outline-none focus:ring-2 focus:ring-amber-500/20 [color-scheme:dark]";

function defaultCustomRange(): Pick<PeriodState, "from" | "to"> {
  const to = new Date();
  const from = new Date(to.getTime() - 24 * 3_600_000);
  return { from: dateToDatetimeLocal(from), to: dateToDatetimeLocal(to) };
}

export default function PeriodSelector({
  value,
  onChange,
  stopPropagation = false,
  align = "end",
}: Props) {
  const guard = (event: MouseEvent | ChangeEvent) => {
    if (stopPropagation) event.stopPropagation();
  };

  const selectPreset = (key: PeriodKey) => {
    onChange({ ...value, period: key });
  };

  const selectCustom = () => {
    const defaults = defaultCustomRange();
    onChange({
      period: "custom",
      from: value.from || defaults.from,
      to: value.to || defaults.to,
    });
  };

  const alignClass = align === "start" ? "items-start" : "items-end";

  return (
    <div
      className={`flex min-w-0 max-w-full flex-col gap-2 ${alignClass}`}
      onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
    >
      <div
        className={`flex max-w-full flex-wrap gap-1 ${
          align === "start" ? "justify-start" : "justify-end"
        }`}
      >
        {HOUR_PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={(e) => {
              guard(e);
              selectPreset(preset.key);
            }}
            className={chipClass(value.period === preset.key)}
          >
            {preset.label}
          </button>
        ))}

        <span
          className="mx-0.5 hidden h-6 w-px shrink-0 self-center bg-zinc-700/70 sm:block"
          aria-hidden
        />

        {DAY_PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={(e) => {
              guard(e);
              selectPreset(preset.key);
            }}
            className={chipClass(value.period === preset.key)}
          >
            {preset.label}
          </button>
        ))}

        <button
          type="button"
          onClick={(e) => {
            guard(e);
            selectCustom();
          }}
          className={chipClass(value.period === "custom")}
        >
          Период
        </button>
      </div>

      <div
        className={`grid w-full max-w-md transition-[grid-template-rows,opacity] duration-200 ease-out ${
          value.period === "custom"
            ? "grid-rows-[1fr] opacity-100"
            : "pointer-events-none grid-rows-[0fr] opacity-0"
        }`}
        aria-hidden={value.period !== "custom"}
      >
        <div className="overflow-hidden">
          <div
            className={`rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-2.5 shadow-inner transition-transform duration-200 ease-out ${
              value.period === "custom" ? "translate-y-0" : "-translate-y-1"
            }`}
          >
            <div className="mb-2 text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500">
              Свой диапазон
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label className="flex min-w-0 flex-1 items-center gap-2">
                <span className="shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  С
                </span>
                <input
                  type="datetime-local"
                  value={value.from}
                  onChange={(e) => {
                    guard(e);
                    onChange({ ...value, from: e.target.value });
                  }}
                  className={inputClass}
                />
              </label>
              <span className="hidden shrink-0 text-zinc-600 sm:inline" aria-hidden>
                —
              </span>
              <label className="flex min-w-0 flex-1 items-center gap-2">
                <span className="shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  По
                </span>
                <input
                  type="datetime-local"
                  value={value.to}
                  onChange={(e) => {
                    guard(e);
                    onChange({ ...value, to: e.target.value });
                  }}
                  className={inputClass}
                />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { PeriodKey, PeriodState };
