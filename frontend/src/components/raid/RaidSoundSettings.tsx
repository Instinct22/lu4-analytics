import { useEffect, useRef, useState } from "react";
import { RAID_SOUND_CATALOG } from "../../lib/raidSoundCatalog";
import { isSoundPreviewPlaying, stopSoundPreview } from "../../lib/raidTimerSounds";

type Props = {
  enabled: boolean;
  soonSoundId: string;
  windowSoundId: string;
  onToggleEnabled: () => void;
  onSoonChange: (id: string) => void;
  onWindowChange: (id: string) => void;
  onPreview: (id: string) => void;
};

function SoundRow({
  label,
  description,
  value,
  onChange,
  onPreview,
}: {
  label: string;
  description: string;
  value: string;
  onChange: (id: string) => void;
  onPreview: (id: string) => void;
}) {
  const [playing, setPlaying] = useState(() => isSoundPreviewPlaying(value));

  useEffect(() => {
    const tick = () => setPlaying(isSoundPreviewPlaying(value));
    const id = window.setInterval(tick, 200);
    return () => window.clearInterval(id);
  }, [value]);

  return (
    <div className="space-y-1.5">
      <div>
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        <p className="text-xs text-zinc-500">{description}</p>
      </div>
      <div className="flex items-center gap-2">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input min-w-0 flex-1 truncate text-sm"
          title={RAID_SOUND_CATALOG.find((s) => s.id === value)?.label ?? value}
        >
          {RAID_SOUND_CATALOG.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => onPreview(value)}
          aria-label={playing ? "Остановить прослушивание" : "Прослушать выбранный звук"}
          title={playing ? "Остановить" : "Прослушать"}
          className={[
            "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-sm transition-colors",
            playing
              ? "border-amber-500/50 bg-amber-500/15 text-amber-300"
              : "border-zinc-700/80 bg-zinc-900/60 text-zinc-300 hover:border-zinc-600 hover:text-zinc-100",
          ].join(" ")}
        >
          {playing ? "■" : "▶"}
        </button>
      </div>
    </div>
  );
}

export default function RaidSoundSettings({
  enabled,
  soonSoundId,
  windowSoundId,
  onToggleEnabled,
  onSoonChange,
  onWindowChange,
  onPreview,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      stopSoundPreview();
      return;
    }
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        stopSoundPreview();
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        stopSoundPreview();
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={`relative ${open ? "z-50" : "z-10"}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={
          enabled
            ? "Звук включён. Нажмите, чтобы настроить мелодии."
            : "Звук выключен. Нажмите, чтобы настроить и включить."
        }
        className={[
          "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
          enabled
            ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:border-amber-400/60 hover:bg-amber-500/15"
            : "border-zinc-700/80 bg-zinc-900/60 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200",
        ].join(" ")}
      >
        <span aria-hidden>{enabled ? "🔊" : "🔇"}</span>
        <span>{enabled ? "Звук: вкл" : "Звук: выкл"}</span>
        <span aria-hidden className="text-xs text-zinc-500">
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Настройки звука таймеров"
          className="absolute right-0 top-full z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-zinc-700/80 bg-zinc-950/95 p-4 shadow-xl backdrop-blur-sm"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-zinc-100">Звук таймеров</p>
              <p className="text-xs text-zinc-500">Мелодии при переходе фаз респа</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={enabled}
              onClick={onToggleEnabled}
              className={[
                "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200",
                enabled
                  ? "bg-gradient-to-r from-amber-500 to-amber-400"
                  : "bg-zinc-700/90 ring-1 ring-inset ring-zinc-600/80",
              ].join(" ")}
            >
              <span
                className={[
                  "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-200",
                  enabled ? "translate-x-5" : "translate-x-0",
                ].join(" ")}
              />
            </button>
          </div>

          <div className="space-y-4">
            <SoundRow
              label="За 30 мин (Скоро)"
              description="Когда таймер переходит в «Скоро»"
              value={soonSoundId}
              onChange={onSoonChange}
              onPreview={onPreview}
            />
            <SoundRow
              label="Окно респа"
              description="Когда «Скоро» сменяется на окно респа"
              value={windowSoundId}
              onChange={onWindowChange}
              onPreview={onPreview}
            />
          </div>
        </div>
      )}
    </div>
  );
}
