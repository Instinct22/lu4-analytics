import { ReactNode } from "react";

export function StatCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="card group transition-colors hover:border-zinc-700/80 hover:bg-zinc-900/80">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{title}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-zinc-50">{value}</p>
      {subtitle && <p className="mt-1.5 text-xs text-zinc-600">{subtitle}</p>}
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
