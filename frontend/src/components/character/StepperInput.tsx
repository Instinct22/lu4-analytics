import { useId, type KeyboardEvent, type ReactNode } from "react";
import { formatGroupedInt, parseGroupedInt } from "../../lib/formatNumber";

type StepperInputProps = {
  value: string;
  onChange: (next: string) => void;
  onStep: (dir: 1 | -1) => void;
  onBlur?: () => void;
  /** Extra key handling before default ArrowUp/Down. Return true to stop. */
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => boolean | void;
  minReached?: boolean;
  maxReached?: boolean;
  placeholder?: string;
  inputMode?: "numeric" | "decimal" | "text";
  suffix?: ReactNode;
  ariaLabel?: string;
  className?: string;
  inputClassName?: string;
  /** Show thousand separators in the field; onChange still receives raw digits. */
  groupThousands?: boolean;
};

/** Quantity-style stepper matching CraftCostBar arrows (▲/▼ column). */
export default function StepperInput({
  value,
  onChange,
  onStep,
  onBlur,
  onKeyDown,
  minReached = false,
  maxReached = false,
  placeholder,
  inputMode = "decimal",
  suffix,
  ariaLabel,
  className = "",
  inputClassName = "",
  groupThousands = false,
}: StepperInputProps) {
  const id = useId();
  const displayValue = groupThousands ? formatGroupedInt(value) : value;
  const displayPlaceholder = groupThousands && placeholder
    ? formatGroupedInt(placeholder)
    : placeholder;

  return (
    <div
      className={[
        "inline-flex h-10 w-full min-w-0 overflow-hidden rounded-xl border border-zinc-700/80 bg-zinc-900/80 shadow-sm",
        "focus-within:border-amber-500/60 focus-within:ring-2 focus-within:ring-amber-500/20",
        className,
      ].join(" ")}
    >
      <input
        id={id}
        type="text"
        inputMode={inputMode}
        autoComplete="off"
        spellCheck={false}
        aria-label={ariaLabel}
        placeholder={displayPlaceholder}
        className={[
          "min-w-0 flex-1 bg-transparent px-3.5 py-2 text-sm tabular-nums text-zinc-100 outline-none placeholder:text-zinc-500",
          inputClassName,
        ].join(" ")}
        value={displayValue}
        onChange={(e) => {
          if (groupThousands) {
            onChange(parseGroupedInt(e.target.value));
            return;
          }
          onChange(e.target.value);
        }}
        onBlur={onBlur}
        onKeyDown={(e) => {
          if (onKeyDown?.(e)) return;
          if (e.key === "ArrowUp") {
            e.preventDefault();
            if (!maxReached) onStep(1);
          } else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (!minReached) onStep(-1);
          }
        }}
      />
      {suffix != null && (
        <span className="flex shrink-0 items-center pr-1.5 text-sm text-zinc-500">{suffix}</span>
      )}
      <div className="flex w-5 shrink-0 flex-col border-l border-zinc-700/80">
        <button
          type="button"
          tabIndex={-1}
          disabled={maxReached}
          className="flex flex-1 items-center justify-center text-[0.55rem] leading-none text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-amber-400 disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-zinc-500"
          onClick={() => onStep(1)}
          aria-label="Увеличить"
        >
          ▲
        </button>
        <button
          type="button"
          tabIndex={-1}
          disabled={minReached}
          className="flex flex-1 items-center justify-center border-t border-zinc-700/80 text-[0.55rem] leading-none text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-amber-400 disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-zinc-500"
          onClick={() => onStep(-1)}
          aria-label="Уменьшить"
        >
          ▼
        </button>
      </div>
    </div>
  );
}
