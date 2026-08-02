import type { LevelRange } from "../../lib/levelRange";
import { LEVEL_ABSOLUTE_MAX, LEVEL_ABSOLUTE_MIN } from "../../lib/levelRange";

type Props = {
  value: LevelRange;
  onChange: (next: LevelRange) => void;
  sliderMin?: number;
  sliderMax?: number;
  compact?: boolean;
};

export default function LevelRangeControl({
  value,
  onChange,
  sliderMin = LEVEL_ABSOLUTE_MIN,
  sliderMax = LEVEL_ABSOLUTE_MAX,
  compact = false,
}: Props) {
  const setMin = (min: number) => {
    const next = Math.max(sliderMin, Math.min(min, sliderMax));
    onChange({ ...value, min: Math.min(next, value.max) });
  };
  const setMax = (max: number) => {
    const next = Math.max(sliderMin, Math.min(max, sliderMax));
    onChange({ ...value, max: Math.max(next, value.min) });
  };

  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      <div className="flex gap-3">
        <label className="flex-1 space-y-1">
          <span className="text-[0.7rem] text-zinc-500">Минимум</span>
          <input
            type="number"
            className="input tabular-nums"
            min={sliderMin}
            max={sliderMax}
            value={value.min}
            onChange={(e) => setMin(Number(e.target.value))}
          />
        </label>
        <label className="flex-1 space-y-1">
          <span className="text-[0.7rem] text-zinc-500">Максимум</span>
          <input
            type="number"
            className="input tabular-nums"
            min={sliderMin}
            max={sliderMax}
            value={value.max}
            onChange={(e) => setMax(Number(e.target.value))}
          />
        </label>
      </div>

      <div>
        <div className="mb-1.5 flex justify-between text-[0.7rem] text-zinc-500">
          <span>Диапазон</span>
          <span className="tabular-nums text-zinc-400">
            {value.min} – {value.max}
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="range"
            min={sliderMin}
            max={sliderMax}
            value={value.min}
            onChange={(e) => setMin(Number(e.target.value))}
            className="w-full accent-amber-500"
          />
          <input
            type="range"
            min={sliderMin}
            max={sliderMax}
            value={value.max}
            onChange={(e) => setMax(Number(e.target.value))}
            className="w-full accent-amber-500"
          />
        </div>
      </div>
    </div>
  );
}
