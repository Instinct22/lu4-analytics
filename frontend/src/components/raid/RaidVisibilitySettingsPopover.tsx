import { useEffect, useRef, useState, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import type { RaidBoss } from "../../lib/raidBosses";
import RaidVisibilitySettingsPanel from "./RaidVisibilitySettingsPanel";

interface Props {
  bosses: RaidBoss[];
  hiddenIds: Set<number>;
  onToggle: (bossId: number, visible: boolean) => void;
  saving?: boolean;
}

type PanelPos = {
  top: number;
  right: number;
};

function computePanelPos(button: HTMLButtonElement): PanelPos {
  const rect = button.getBoundingClientRect();
  return {
    top: rect.bottom + 8,
    right: Math.max(8, window.innerWidth - rect.right),
  };
}

export default function RaidVisibilitySettingsPopover({
  bosses,
  hiddenIds,
  onToggle,
  saving = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [panelPos, setPanelPos] = useState<PanelPos>({ top: 0, right: 0 });
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const guardClick = (event: MouseEvent) => {
    event.stopPropagation();
  };

  const updatePanelPos = () => {
    if (!buttonRef.current) return;
    setPanelPos(computePanelPos(buttonRef.current));
  };

  useEffect(() => {
    if (!open) return;
    updatePanelPos();
    const onLayout = () => updatePanelPos();
    window.addEventListener("resize", onLayout);
    window.addEventListener("scroll", onLayout, true);
    return () => {
      window.removeEventListener("resize", onLayout);
      window.removeEventListener("scroll", onLayout, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (document.getElementById("raid-visibility-popover")?.contains(target)) return;
      setOpen(false);
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

  const panel =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            id="raid-visibility-popover"
            role="dialog"
            aria-label="Список рейд-боссов"
            className="fixed z-[200] w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-zinc-700/80 bg-zinc-950/95 p-4 shadow-xl backdrop-blur-sm"
            style={{ top: panelPos.top, right: panelPos.right }}
            onClick={guardClick}
            onMouseDown={guardClick}
          >
            <RaidVisibilitySettingsPanel
              bosses={bosses}
              hiddenIds={hiddenIds}
              onToggle={onToggle}
              saving={saving}
            />
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <div ref={rootRef} className="relative inline-flex">
        <button
          ref={buttonRef}
          type="button"
          onClick={(e) => {
            guardClick(e);
            setOpen((v) => {
              const next = !v;
              if (next && buttonRef.current) {
                setPanelPos(computePanelPos(buttonRef.current));
              }
              return next;
            });
          }}
          aria-expanded={open}
          aria-haspopup="dialog"
          title="Настроить видимость рейд-боссов в общем списке"
          className={[
            "inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-[0.7rem] font-semibold transition-colors",
            open
              ? "border-amber-500/50 bg-amber-500/15 text-amber-200"
              : "border-transparent bg-transparent text-amber-400/80 hover:border-zinc-700/80 hover:bg-zinc-900/60 hover:text-amber-300",
          ].join(" ")}
        >
          <span>Список РБ</span>
          <span aria-hidden className="text-[0.6rem] text-zinc-500">
            {open ? "▴" : "▾"}
          </span>
        </button>
      </div>
      {panel}
    </>
  );
}
