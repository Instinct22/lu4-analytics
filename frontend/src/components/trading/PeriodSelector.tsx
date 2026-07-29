import { PeriodKey, PERIOD_PRESETS, PeriodState } from "./periodUtils";

interface Props {
  value: PeriodState;
  onChange: (next: PeriodState) => void;
}

export default function PeriodSelector({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-wrap gap-2">
        {PERIOD_PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={() => onChange({ ...value, period: preset.key })}
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-all ${
              value.period === preset.key
                ? "bg-amber-500 text-zinc-950 shadow-sm"
                : "border border-zinc-700/80 bg-zinc-900/80 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
            }`}
          >
            {preset.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onChange({ ...value, period: "custom" })}
          className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-all ${
            value.period === "custom"
              ? "bg-amber-500 text-zinc-950 shadow-sm"
              : "border border-zinc-700/80 bg-zinc-900/80 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
          }`}
        >
          Произвольный
        </button>
      </div>

      {value.period === "custom" && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="datetime-local"
            value={value.from}
            onChange={(e) => onChange({ ...value, from: e.target.value })}
            className="input w-auto"
          />
          <span className="text-zinc-500">—</span>
          <input
            type="datetime-local"
            value={value.to}
            onChange={(e) => onChange({ ...value, to: e.target.value })}
            className="input w-auto"
          />
        </div>
      )}
    </div>
  );
}

export type { PeriodKey, PeriodState };
