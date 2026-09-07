import { useEffect, useRef, useState, type MouseEvent } from "react";
import CraftMonitorSettingsPanel from "../settings/CraftMonitorSettingsPanel";

interface Props {
  stopPropagation?: boolean;
}

export default function CraftMonitorSettingsPopover({ stopPropagation = false }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const guardClick = (event: MouseEvent) => {
    if (stopPropagation) event.stopPropagation();
  };

  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div
      ref={rootRef}
      className={`relative shrink-0 ${open ? "z-50" : "z-10"}`}
      onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
    >
      <button
        type="button"
        onClick={(e) => {
          guardClick(e);
          setOpen((v) => !v);
        }}
        aria-expanded={open}
        aria-haspopup="dialog"
        title="Настроить список крафт-ресурсов на мониторинге"
        className={[
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors",
          open
            ? "border-amber-500/50 bg-amber-500/15 text-amber-200"
            : "border-zinc-700/80 bg-zinc-900/80 text-zinc-400 hover:border-zinc-600 hover:bg-zinc-800/80 hover:text-zinc-200",
        ].join(" ")}
      >
        <svg
          aria-hidden
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-3.5 w-3.5 shrink-0 opacity-80"
        >
          <path
            fillRule="evenodd"
            d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.925 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.212l-1.278 1.278a6.993 6.993 0 010 3.85l1.278 1.278a1 1 0 01.205 1.212l-1.18 2.044a1 1 0 01-1.186.447l-1.598-.54a6.993 6.993 0 01-1.925 1.115l-.331 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.925-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.212l1.278-1.278a6.993 6.993 0 010-3.85L2.98 6.98a1 1 0 01-.205-1.212l1.18-2.044a1 1 0 011.186-.447l1.598.54A6.993 6.993 0 017.509 3.66l.331-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
            clipRule="evenodd"
          />
        </svg>
        <span>Настройка</span>
        <span aria-hidden className="text-[0.65rem] text-zinc-500">
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open ? (
        <div
          role="dialog"
          aria-label="Настройка мониторинга крафт-ресурсов"
          className="absolute right-0 top-full z-50 mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-zinc-700/80 bg-zinc-950/95 p-4 shadow-xl backdrop-blur-sm"
          onClick={guardClick}
        >
          <CraftMonitorSettingsPanel listMaxHeight="max-h-[min(22rem,45vh)]" />
        </div>
      ) : null}
    </div>
  );
}
