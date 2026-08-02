import { useMemo, useState } from "react";
import type { RaidBoss } from "../../lib/raidBosses";
import { raidBossImageUrl } from "../../lib/raidTimers";

type Props = {
  bosses: RaidBoss[];
  /** Boss ids currently hidden from the main list. */
  hiddenIds: Set<number>;
  onToggle: (bossId: number, visible: boolean) => void;
  onClose: () => void;
  saving?: boolean;
};

function ToggleSwitch({
  id,
  checked,
  onChange,
  label,
}: {
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={[
        "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950",
        checked
          ? "bg-gradient-to-r from-amber-500 to-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.35)]"
          : "bg-zinc-700/90 ring-1 ring-inset ring-zinc-600/80",
      ].join(" ")}
    >
      <span
        className={[
          "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-200 ease-out",
          checked ? "translate-x-5" : "translate-x-0",
        ].join(" ")}
      />
    </button>
  );
}

export default function RaidVisibilitySettings({
  bosses,
  hiddenIds,
  onToggle,
  onClose,
  saving = false,
}: Props) {
  const [query, setQuery] = useState("");

  const sorted = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? bosses.filter(
          (b) =>
            b.name.toLowerCase().includes(q) ||
            (b.location?.toLowerCase().includes(q) ?? false),
        )
      : bosses;
    return [...list].sort((a, b) => {
      const la = a.level ?? 0;
      const lb = b.level ?? 0;
      if (la !== lb) return la - lb;
      return a.name.localeCompare(b.name, "ru");
    });
  }, [bosses, query]);

  const visibleCount = bosses.length - hiddenIds.size;

  return (
    <div className="panel flex h-full min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-zinc-800/80 p-4">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-zinc-50">Список рейд-боссов</h3>
            <p className="mt-1 text-sm text-zinc-500">
              Включённые боссы видны всем · {visibleCount} из {bosses.length}
              {saving ? " · сохранение…" : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-ghost shrink-0 px-2.5 py-1 text-xs text-zinc-400"
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>
        <input
          className="input"
          placeholder="Поиск по имени или локации…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <ul className="min-h-0 flex-1 divide-y divide-zinc-800/70 overflow-y-auto">
        {sorted.map((boss) => {
          const visible = !hiddenIds.has(boss.id);
          const image = raidBossImageUrl(boss.image);
          const switchId = `raid-vis-${boss.id}`;
          return (
            <li key={boss.id}>
              <div
                className={[
                  "flex items-center gap-3 px-3 py-2.5 transition-colors",
                  visible ? "hover:bg-zinc-800/40" : "bg-zinc-950/40 opacity-70 hover:opacity-100",
                ].join(" ")}
              >
                {image ? (
                  <img
                    src={image}
                    alt=""
                    className="h-10 w-10 shrink-0 rounded-lg object-cover ring-1 ring-zinc-700/80"
                    loading="lazy"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-800/80 text-[0.65rem] text-zinc-500 ring-1 ring-zinc-700/80">
                    RB
                  </div>
                )}
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => onToggle(boss.id, !visible)}
                >
                  <span
                    className={[
                      "block truncate text-sm font-medium",
                      visible ? "text-zinc-100" : "text-zinc-400",
                    ].join(" ")}
                  >
                    {boss.name}
                  </span>
                  <span className="mt-0.5 block text-[0.7rem] text-zinc-500">
                    Lv. {boss.level ?? "?"}
                    {boss.location ? ` · ${boss.location}` : ""}
                  </span>
                </button>
                <ToggleSwitch
                  id={switchId}
                  checked={visible}
                  onChange={(next) => onToggle(boss.id, next)}
                  label={`${visible ? "Скрыть" : "Показать"} ${boss.name}`}
                />
              </div>
            </li>
          );
        })}
        {sorted.length === 0 && (
          <li className="px-4 py-8 text-center text-sm text-zinc-500">Ничего не найдено</li>
        )}
      </ul>
    </div>
  );
}
