import { useCallback, useRef, useState, type ReactNode } from "react";

const DEFAULT_RATIO = 50;
const MIN_RATIO = 20;
const MAX_RATIO = 80;

function readStoredRatio(storageKey: string, defaultRatio: number): number {
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw == null) return defaultRatio;
    const n = Number(raw);
    if (!Number.isFinite(n)) return defaultRatio;
    return Math.min(MAX_RATIO, Math.max(MIN_RATIO, n));
  } catch {
    return defaultRatio;
  }
}

interface Props {
  left: ReactNode;
  right: ReactNode;
  storageKey?: string;
  defaultRatio?: number;
  className?: string;
}

export default function SplitPane({
  left,
  right,
  storageKey = "lu4_craft_panel_ratio",
  defaultRatio = DEFAULT_RATIO,
  className = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() => readStoredRatio(storageKey, defaultRatio));
  const ratioRef = useRef(ratio);
  const dragging = useRef(false);

  ratioRef.current = ratio;

  const clampRatio = useCallback((value: number) => {
    return Math.min(MAX_RATIO, Math.max(MIN_RATIO, value));
  }, []);

  const saveRatio = useCallback(
    (value: number) => {
      try {
        localStorage.setItem(storageKey, String(value));
      } catch {
        // Quota or private mode.
      }
    },
    [storageKey],
  );

  const updateRatioFromPointer = useCallback(
    (clientX: number) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0) return;
      const next = clampRatio(((clientX - rect.left) / rect.width) * 100);
      ratioRef.current = next;
      setRatio(next);
    },
    [clampRatio],
  );

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    document.body.style.userSelect = "none";
    updateRatioFromPointer(e.clientX);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    updateRatioFromPointer(e.clientX);
  };

  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    dragging.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
    document.body.style.userSelect = "";
    saveRatio(ratioRef.current);
  };

  return (
    <div ref={containerRef} className={`flex min-h-0 w-full items-stretch ${className}`}>
      <div className="min-w-0 shrink-0 overflow-hidden" style={{ flexBasis: `${ratio}%` }}>
        {left}
      </div>
      <div
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(ratio)}
        aria-valuemin={MIN_RATIO}
        aria-valuemax={MAX_RATIO}
        className="group relative z-10 mx-1 w-1.5 shrink-0 cursor-col-resize touch-none"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-zinc-700/80 transition-colors group-hover:bg-amber-500/70 group-active:bg-amber-500" />
      </div>
      <div className="min-w-0 flex-1 overflow-hidden">{right}</div>
    </div>
  );
}
