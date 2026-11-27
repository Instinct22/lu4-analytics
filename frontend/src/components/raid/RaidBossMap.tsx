import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RaidBoss, RaidBossesPayload } from "../../lib/raidBosses";
import type { TimerSnapshot } from "../../lib/raidTimers";

type Props = {
  payload: RaidBossesPayload;
  bosses: RaidBoss[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  timers: Map<number, TimerSnapshot>;
};

const MIN_SCALE = 0.35;
const MAX_SCALE = 3.5;
const FLAG_SIZE = 28;

export default function RaidBossMap({ payload, bosses, selectedId, onSelect, timers }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.55);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  const { width, height, image, flag } = payload.map;

  const fitMap = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const pad = 24;
    const sx = (el.clientWidth - pad * 2) / width;
    const sy = (el.clientHeight - pad * 2) / height;
    const next = Math.min(Math.max(Math.min(sx, sy), MIN_SCALE), 1.2);
    setScale(next);
    setOffset({
      x: (el.clientWidth - width * next) / 2,
      y: (el.clientHeight - height * next) / 2,
    });
  }, [width, height]);

  const didFitRef = useRef(false);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    if (!didFitRef.current) {
      fitMap();
      didFitRef.current = true;
    }

    let prevW = el.clientWidth;
    let prevH = el.clientHeight;

    if (typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(() => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      const dw = w - prevW;
      const dh = h - prevH;
      if (dw === 0 && dh === 0) return;
      setOffset((o) => ({ x: o.x + dw / 2, y: o.y + dh / 2 }));
      prevW = w;
      prevH = h;
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fitMap]);

  useEffect(() => {
    if (selectedId == null) return;
    const boss = bosses.find((b) => b.id === selectedId) ?? payload.bosses.find((b) => b.id === selectedId);
    const el = viewportRef.current;
    if (!boss || boss.x == null || boss.y == null || !el) return;
    setOffset({
      x: el.clientWidth / 2 - boss.x * scale,
      y: el.clientHeight / 2 - boss.y * scale,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when selection changes
  }, [selectedId]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const el = viewportRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const delta = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale * delta));
    const wx = (mx - offset.x) / scale;
    const wy = (my - offset.y) / scale;
    setScale(next);
    setOffset({ x: mx - wx * next, y: my - wy * next });
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    setOffset({
      x: drag.current.ox + (e.clientX - drag.current.x),
      y: drag.current.oy + (e.clientY - drag.current.y),
    });
  };

  const endDrag = () => {
    drag.current = null;
    setDragging(false);
  };

  const markers = useMemo(() => bosses.flatMap((boss) =>
    boss.spawnPoints?.length
      ? boss.spawnPoints.map((point) => ({ ...boss, x: point.mapX, y: point.mapY }))
      : boss.x != null && boss.y != null ? [{ ...boss, x: boss.x, y: boss.y }] : []
  ), [bosses]);

  const overlays = useMemo(() => {
    return markers
      .map((boss) => {
        const timer = timers.get(boss.id);
        const active = boss.id === selectedId;
        if (!timer && !active) return null;
        const sx = Math.round(offset.x + boss.x * scale);
        const sy = Math.round(offset.y + boss.y * scale);
        const flagH = Math.round(FLAG_SIZE * scale);
        return { boss, timer, active, sx, sy, flagH };
      })
      .filter((v): v is NonNullable<typeof v> => v != null);
  }, [markers, timers, selectedId, offset.x, offset.y, scale]);

  return (
    <div className="relative flex h-full min-h-[28rem] flex-col overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-950 shadow-panel">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800/80 px-3 py-2">
        <p className="text-[0.7rem] uppercase tracking-wider text-zinc-500">Карта мира</p>
        <div className="flex items-center gap-1.5">
          <button type="button" className="btn-ghost px-2.5 py-1 text-xs" onClick={() => setScale((s) => Math.min(MAX_SCALE, s * 1.2))}>
            +
          </button>
          <button type="button" className="btn-ghost px-2.5 py-1 text-xs" onClick={() => setScale((s) => Math.max(MIN_SCALE, s / 1.2))}>
            −
          </button>
          <button type="button" className="btn-ghost px-2.5 py-1 text-xs" onClick={fitMap}>
            Сброс
          </button>
        </div>
      </div>

      <div
        ref={viewportRef}
        className={`relative flex-1 touch-none overflow-hidden bg-[#0a0a0b] ${dragging ? "cursor-grabbing" : "cursor-grab"}`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <div
          className="absolute origin-top-left will-change-transform"
          style={{
            width,
            height,
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
          }}
        >
          <img
            src={image}
            alt="Карта Lu4"
            width={width}
            height={height}
            draggable={false}
            className="pointer-events-none block select-none"
          />
          {markers.map((boss) => {
            const active = boss.id === selectedId;
            return (
              <button
                key={`${boss.id}-${boss.x}-${boss.y}`}
                type="button"
                title={`${boss.name} · Lv. ${boss.level ?? "?"}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(boss.id);
                }}
                onPointerDown={(e) => e.stopPropagation()}
                className={[
                  "absolute -translate-x-1/2 -translate-y-full transition-transform duration-150",
                  active ? "z-20 scale-125" : "z-10 hover:scale-110",
                ].join(" ")}
                style={{ left: boss.x, top: boss.y }}
              >
                <img
                  src={flag}
                  alt=""
                  width={FLAG_SIZE}
                  height={FLAG_SIZE}
                  className={[
                    "drop-shadow-[0_2px_6px_rgba(0,0,0,0.85)]",
                    active ? "brightness-125" : "opacity-90",
                  ].join(" ")}
                  draggable={false}
                />
              </button>
            );
          })}
        </div>

        {/* Screen-space labels — not inside map scale, so text stays sharp */}
        <div className="pointer-events-none absolute inset-0 z-30 overflow-hidden">
          {overlays.map(({ boss, timer, active, sx, sy, flagH }) => (
            <div key={`label-${boss.id}-${boss.x}-${boss.y}`}>
              {timer && (
                <span
                  className={`absolute whitespace-nowrap rounded bg-zinc-950/95 px-1.5 py-0.5 font-mono text-[11px] font-semibold tabular-nums leading-none shadow-sm ring-1 ring-zinc-700/80 ${timer.colorClass}`}
                  style={{
                    left: sx,
                    top: sy - flagH - 2,
                    transform: "translate(-50%, -100%)",
                  }}
                >
                  {timer.display}
                </span>
              )}
              {active && (
                <span
                  className="absolute whitespace-nowrap rounded-md bg-zinc-950/95 px-1.5 py-0.5 text-[0.65rem] font-medium text-amber-300 ring-1 ring-amber-500/40"
                  style={{
                    left: sx,
                    top: sy + 4,
                    transform: "translateX(-50%)",
                  }}
                >
                  {boss.name}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
