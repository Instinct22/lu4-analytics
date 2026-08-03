import { ReactNode } from "react";

export function StatCard({
  title,
  value,
  subtitle,
  highlight = false,
  fullValue,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  highlight?: boolean;
  /** Exact value for tooltip when `value` is compacted. */
  fullValue?: string;
}) {
  const text = String(value);
  const long = text.length >= 10;
  return (
    <div
      className={[
        "card group transition-colors",
        highlight
          ? "border-amber-500/40 bg-amber-500/10 ring-1 ring-amber-500/25 hover:border-amber-400/50 hover:bg-amber-500/15"
          : "hover:border-zinc-700/80 hover:bg-zinc-900/80",
      ].join(" ")}
    >
      <p
        className={[
          "text-xs font-medium uppercase tracking-wider",
          highlight ? "text-amber-400/90" : "text-zinc-500",
        ].join(" ")}
      >
        {title}
      </p>
      <p
        title={fullValue ?? (typeof value === "string" ? value : undefined)}
        className={[
          "mt-2 font-semibold tabular-nums tracking-tight break-all leading-tight",
          highlight ? "text-amber-50" : "text-zinc-50",
          long ? "text-lg sm:text-xl" : "text-2xl sm:text-3xl",
        ].join(" ")}
      >
        {value}
      </p>
      {subtitle && (
        <p className={["mt-1.5 text-xs", highlight ? "text-amber-500/70" : "text-zinc-600"].join(" ")}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-amber-500" />
      <p className="mt-4 text-sm text-zinc-500">Загрузка...</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-900/50 bg-red-950/30 px-6 py-12 text-center">
      <p className="text-sm text-red-300">{message}</p>
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 border-b border-zinc-800/80 pb-4 sm:mb-8 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:pb-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-zinc-50 sm:text-2xl">{title}</h2>
        <div className="mt-1 h-0.5 w-12 rounded-full bg-gradient-to-r from-amber-500 to-amber-600/0" />
      </div>
      {children}
    </div>
  );
}

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Подтвердить",
  cancelLabel = "Отмена",
  tone = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  const confirmClass =
    tone === "danger"
      ? "rounded-xl border border-red-800/60 bg-red-900/80 px-4 py-2 text-sm font-semibold text-red-100 transition hover:bg-red-800"
      : "btn-primary";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onCancel}
      role="presentation"
    >
      <div
        className="panel w-full max-w-md space-y-4 p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-dialog-title" className="text-lg font-semibold text-zinc-100">
          {title}
        </h3>
        <p className="text-sm text-zinc-400">{message}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className={confirmClass} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
