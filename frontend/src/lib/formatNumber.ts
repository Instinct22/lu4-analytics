/** Compact RU formatting for large market numbers that overflow stat cards. */
export function formatCompactNumber(value: number | null | undefined, maxFractionDigits = 2): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";

  if (abs >= 1_000_000_000) {
    return `${sign}${(abs / 1_000_000_000).toLocaleString("ru-RU", {
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    })} млрд`;
  }
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toLocaleString("ru-RU", {
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    })} млн`;
  }
  if (abs >= 100_000) {
    return `${sign}${(abs / 1_000).toLocaleString("ru-RU", {
      maximumFractionDigits: 1,
      minimumFractionDigits: 0,
    })} тыс`;
  }
  return n.toLocaleString("ru-RU", { maximumFractionDigits: maxFractionDigits });
}

/** Full number with space grouping: 1 000, 10 000, 1 500 000. */
export function formatFullNumber(value: number | null | undefined, maxFractionDigits = 2): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  const nearest = Math.round(n);
  const isInt = Math.abs(n - nearest) < 1e-9;
  return n
    .toLocaleString("ru-RU", {
      maximumFractionDigits: isInt ? 0 : maxFractionDigits,
      minimumFractionDigits: 0,
      useGrouping: true,
    })
    .replace(/\u00A0/g, " ")
    .replace(/\u202F/g, " ");
}

/** Human duration from minutes (e.g. 90 → "1 ч 30 мин"). */
export function formatDurationMinutes(minutes: number | null | undefined): string {
  if (minutes == null || !Number.isFinite(minutes) || minutes < 0) return "—";
  if (minutes === 0) return "0 мин";
  if (minutes < 1) {
    const sec = Math.max(1, Math.round(minutes * 60));
    return `${formatFullNumber(sec)} сек`;
  }
  const total = Math.round(minutes);
  if (total < 60) return `${formatFullNumber(total)} мин`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (m === 0) return `${formatFullNumber(h)} ч`;
  return `${formatFullNumber(h)} ч ${formatFullNumber(m)} мин`;
}

/** Digits only from a possibly grouped input ("2 500 000" → "2500000"). */
export function parseGroupedInt(raw: string): string {
  return raw.replace(/\D/g, "");
}

/** Group integer digits with spaces: 2500000 → "2 500 000". */
export function formatGroupedInt(raw: string | number): string {
  const digits = String(raw).replace(/\D/g, "");
  if (!digits) return "";
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}
