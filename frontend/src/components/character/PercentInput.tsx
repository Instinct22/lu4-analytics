import StepperInput from "./StepperInput";

/**
 * Complete value: 0–100 with at most 4 decimals.
 * Accepts 99.99, 99.9999, 100, 100.0000, 0.5, etc.
 */
const COMPLETE_RE = /^(?:100(?:[.,]0{1,4})?|\d{1,2}(?:[.,]\d{1,4})?)$/;

export function isValidPercentInput(raw: string): boolean {
  const trimmed = raw.trim();
  if (!COMPLETE_RE.test(trimmed)) return false;
  const n = Number(trimmed.replace(",", "."));
  return Number.isFinite(n) && n >= 0 && n <= 100;
}

export function parsePercentInput(raw: string): number | null {
  if (!isValidPercentInput(raw)) return null;
  return Number(raw.trim().replace(",", "."));
}

function formatPercent(n: number): string {
  const clamped = Math.min(100, Math.max(0, n));
  if (Number.isInteger(clamped)) return String(clamped);
  return clamped.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function stepPercent(raw: string, delta: number): string {
  const current = parsePercentInput(raw) ?? 0;
  const next = Math.round((current + delta) * 10000) / 10000;
  return formatPercent(next);
}

/**
 * Normalize typing into 0–100 with up to 4 decimals.
 * After 2 integer digits, further digits auto-insert "." (99 → 995 becomes 99.5).
 * "100" is allowed as a special case.
 */
function normalizePercentTyping(raw: string): string | null {
  if (raw === "") return "";
  const normalized = raw.replace(",", ".");
  if (!/^[\d.]*$/.test(normalized)) return null;
  if ((normalized.match(/\./g) ?? []).length > 1) return null;

  const dot = normalized.indexOf(".");
  if (dot >= 0) {
    const intPart = normalized.slice(0, dot);
    const frac = normalized.slice(dot + 1);
    if (intPart.length > 3) return null;
    if (frac.length > 4) return null;
    if (intPart === "100") {
      // 100 only allows zero fractional digits
      if (frac === "" || /^0{0,4}$/.test(frac)) return frac === "" ? "100." : `100.${frac}`;
      return null;
    }
    if (intPart.length > 2) return null;
    const n = Number(intPart === "" ? "0" : intPart);
    if (n > 100) return null;
    return normalized;
  }

  // Digits only — auto-place decimal after 2 digits (except exact "100")
  if (!/^\d+$/.test(normalized)) return null;
  if (normalized === "100") return "100";
  if (normalized.startsWith("100")) return null;
  if (normalized.length <= 2) {
    const n = Number(normalized);
    if (n > 100) return null;
    return normalized;
  }
  const intPart = normalized.slice(0, 2);
  const frac = normalized.slice(2, 6);
  if (normalized.length > 6) return null;
  return `${intPart}.${frac}`;
}

export default function PercentInput({
  value,
  onChange,
  step = 0.01,
}: {
  value: string;
  onChange: (next: string) => void;
  step?: number;
}) {
  const parsed = parsePercentInput(value);

  const handleChange = (raw: string) => {
    const next = normalizePercentTyping(raw);
    if (next != null) onChange(next);
  };

  return (
    <StepperInput
      value={value}
      onChange={handleChange}
      onStep={(dir) => onChange(stepPercent(value === "" ? "0" : value, dir * step))}
      minReached={parsed != null && parsed <= 0}
      maxReached={parsed != null && parsed >= 100}
      placeholder="0.00"
      inputMode="decimal"
      suffix="%"
      ariaLabel="Процент на уровне"
      onBlur={() => {
        const trimmed = value.trim().replace(/\.$/, "");
        if (!trimmed) {
          onChange("0");
          return;
        }
        const n = Number(trimmed.replace(",", "."));
        if (Number.isFinite(n)) {
          onChange(formatPercent(n));
          return;
        }
        onChange("0");
      }}
    />
  );
}
