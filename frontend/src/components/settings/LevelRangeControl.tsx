import { useCallback, useEffect, useState, type KeyboardEvent } from "react";
import type { LevelRange } from "../../lib/levelRange";
import {
  LEVEL_ABSOLUTE_MAX,
  LEVEL_ABSOLUTE_MIN,
  commitLevelField,
  sanitizeLevelDraft,
} from "../../lib/levelRange";

type Props = {
  value: LevelRange;
  onChange: (next: LevelRange) => void;
  sliderMin?: number;
  sliderMax?: number;
  compact?: boolean;
};

type LevelField = "min" | "max";

export default function LevelRangeControl({
  value,
  onChange,
  sliderMin = LEVEL_ABSOLUTE_MIN,
  sliderMax = LEVEL_ABSOLUTE_MAX,
  compact = false,
}: Props) {
  const [draftMin, setDraftMin] = useState(String(value.min));
  const [draftMax, setDraftMax] = useState(String(value.max));
  const [editingMin, setEditingMin] = useState(false);
  const [editingMax, setEditingMax] = useState(false);

  useEffect(() => {
    if (!editingMin) setDraftMin(String(value.min));
  }, [value.min, editingMin]);

  useEffect(() => {
    if (!editingMax) setDraftMax(String(value.max));
  }, [value.max, editingMax]);

  const setMin = useCallback(
    (min: number) => {
      const next = Math.max(sliderMin, Math.min(min, sliderMax));
      onChange({ ...value, min: Math.min(next, value.max) });
    },
    [onChange, sliderMax, sliderMin, value],
  );

  const setMax = useCallback(
    (max: number) => {
      const next = Math.max(sliderMin, Math.min(max, sliderMax));
      onChange({ ...value, max: Math.max(next, value.min) });
    },
    [onChange, sliderMax, sliderMin, value],
  );

  const commitField = useCallback(
    (field: LevelField) => {
      const raw = field === "min" ? draftMin : draftMax;
      const next = commitLevelField(raw, field, value, sliderMin, sliderMax);
      onChange(next);
      if (field === "min") {
        setDraftMin(String(next.min));
        setEditingMin(false);
      } else {
        setDraftMax(String(next.max));
        setEditingMax(false);
      }
    },
    [draftMax, draftMin, onChange, sliderMax, sliderMin, value],
  );

  const handleDraftChange = (field: LevelField, raw: string) => {
    const next = sanitizeLevelDraft(raw);
    if (field === "min") setDraftMin(next);
    else setDraftMax(next);
  };

  const handleFocus = (field: LevelField) => {
    if (field === "min") {
      setDraftMin(String(value.min));
      setEditingMin(true);
    } else {
      setDraftMax(String(value.max));
      setEditingMax(true);
    }
  };

  const handleKeyDown = (field: LevelField, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitField(field);
      e.currentTarget.blur();
    } else if (e.key === "Escape") {
      if (field === "min") {
        setDraftMin(String(value.min));
        setEditingMin(false);
      } else {
        setDraftMax(String(value.max));
        setEditingMax(false);
      }
      e.currentTarget.blur();
    }
  };

  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      <div className="flex gap-3">
        <label className="flex-1 space-y-1">
          <span className="text-[0.7rem] text-zinc-500">Минимум</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="off"
            className="input tabular-nums"
            value={editingMin ? draftMin : String(value.min)}
            onFocus={() => handleFocus("min")}
            onChange={(e) => handleDraftChange("min", e.target.value)}
            onBlur={() => commitField("min")}
            onKeyDown={(e) => handleKeyDown("min", e)}
          />
        </label>
        <label className="flex-1 space-y-1">
          <span className="text-[0.7rem] text-zinc-500">Максимум</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="off"
            className="input tabular-nums"
            value={editingMax ? draftMax : String(value.max)}
            onFocus={() => handleFocus("max")}
            onChange={(e) => handleDraftChange("max", e.target.value)}
            onBlur={() => commitField("max")}
            onKeyDown={(e) => handleKeyDown("max", e)}
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
