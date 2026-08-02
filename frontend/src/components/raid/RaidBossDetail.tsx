import { useEffect, useState } from "react";
import type { RaidBoss } from "../../lib/raidBosses";
import { bossRespawn, formatHm, maskTimeInput } from "../../lib/raidTimers";
import type { TimerSnapshot } from "../../lib/raidTimers";
import { dropIconUrl, raidBossImageUrl } from "../../lib/raidTimers";
import { ItemIcon } from "../craft/CraftCostBar";
import { ConfirmDialog } from "../ui";

function Stat({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="rounded-xl bg-zinc-950/50 px-3 py-2 ring-1 ring-zinc-800/80">
      <p className="text-[0.65rem] uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium tabular-nums text-zinc-100">{value}</p>
    </div>
  );
}

function DropIcon({ itemId, icon, name }: { itemId?: number | null; icon?: string | null; name: string }) {
  const remote = dropIconUrl(icon);
  if (remote) {
    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80">
        <img
          src={remote}
          alt={name}
          width={28}
          height={28}
          className="h-full w-full object-contain"
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>
    );
  }
  if (itemId != null) {
    return <ItemIcon id={itemId} size={28} />;
  }
  return <div className="h-7 w-7 shrink-0 rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80" />;
}

type Props = {
  boss: RaidBoss;
  timer: TimerSnapshot | null;
  canWrite: boolean;
  canViewRoute?: boolean;
  onClose: () => void;
  onStart: (hhmm: string) => boolean;
  onAuto: () => boolean;
  onClear: () => void;
};

export default function RaidBossDetail({
  boss,
  timer,
  canWrite,
  canViewRoute = true,
  onClose,
  onStart,
  onAuto,
  onClear,
}: Props) {
  const s = boss.stats;
  const respawn = bossRespawn(boss);
  const [timeInput, setTimeInput] = useState(() => formatHm(new Date()));
  const [inputError, setInputError] = useState("");
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);

  useEffect(() => {
    setTimeInput(formatHm(new Date()));
    setInputError("");
  }, [boss.id]);

  const handleStart = () => {
    const ok = onStart(timeInput);
    setInputError(ok ? "" : "Введите время в формате HH:MM");
  };

  const bossImage = raidBossImageUrl(boss.image);

  return (
    <>
    <div className="panel flex h-full min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-zinc-800/80 p-4">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-1 gap-3">
            {bossImage ? (
              <img
                src={bossImage}
                alt={boss.name}
                className="h-20 w-20 shrink-0 rounded-xl object-cover ring-1 ring-zinc-700/80"
                loading="lazy"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-zinc-800/80 text-zinc-500 ring-1 ring-zinc-700/80">
                RB
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-lg font-semibold text-zinc-50">{boss.name}</h3>
              <p className="mt-1 text-sm text-amber-400/90">
                Raid Boss · Lv. {boss.level ?? "?"}
              </p>
              {boss.location && <p className="mt-1 text-xs text-zinc-500">{boss.location}</p>}
              {boss.respawn && (
                <p className="mt-2 inline-flex rounded-lg bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-300 ring-1 ring-amber-500/20">
                  Респаун: {boss.respawn}
                </p>
              )}
            </div>
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

        <div className="rounded-xl bg-zinc-950/50 p-3 ring-1 ring-zinc-800/80">
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-[0.65rem] font-medium uppercase tracking-wider text-zinc-500">Таймер</p>
            {timer && (
              <span className={`font-mono text-sm font-semibold tabular-nums ${timer.colorClass}`}>
                {timer.display}
              </span>
            )}
          </div>
          {respawn && !canWrite && (
            <p className="text-xs text-zinc-500">
              Таймеры общие для сервера. Нет прав на их изменение.
            </p>
          )}
          {respawn && canWrite ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                className="input w-24 !py-1.5 text-center font-mono text-sm"
                value={timeInput}
                onChange={(e) => {
                  setTimeInput(maskTimeInput(e.target.value));
                  setInputError("");
                }}
                onKeyDown={(e) => {
                  const allowed = [
                    "Backspace",
                    "Delete",
                    "Tab",
                    "ArrowLeft",
                    "ArrowRight",
                    "Home",
                    "End",
                    "Enter",
                  ];
                  if (allowed.includes(e.key) || e.ctrlKey || e.metaKey) {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleStart();
                    }
                    return;
                  }
                  if (!/^\d$/.test(e.key)) e.preventDefault();
                }}
                placeholder="HH:MM"
                inputMode="numeric"
                autoComplete="off"
                maxLength={5}
                aria-label="Время килла HH:MM"
              />
              <button type="button" className="btn-primary !px-3 !py-1.5 text-xs" onClick={handleStart}>
                Старт
              </button>
              <button
                type="button"
                className="btn-ghost !px-3 !py-1.5 text-xs"
                onClick={() => {
                  onAuto();
                  setTimeInput(formatHm(new Date()));
                  setInputError("");
                }}
                title="Записать текущее время и начать отсчёт от мин. респа"
              >
                Авто
              </button>
              {timer && (
                <button
                  type="button"
                  className="btn-ghost !px-3 !py-1.5 text-xs text-zinc-400"
                  onClick={() => setClearConfirmOpen(true)}
                  title="Сбросить общий таймер этого босса"
                >
                  Сброс
                </button>
              )}
            </div>
          ) : null}
          {!respawn && (
            <p className="text-xs text-zinc-500">Для этого босса респаун фиксированный — таймер недоступен.</p>
          )}
          {inputError && <p className="mt-1.5 text-xs text-red-400">{inputError}</p>}
          {respawn && (
            <p className="mt-2 text-[0.7rem] text-zinc-600">
              Окно: {(respawn.minMs / 3_600_000).toFixed(0)}–{(respawn.maxMs / 3_600_000).toFixed(0)} ч после килла
            </p>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain p-4">
        <section>
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Характеристики</h4>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <Stat label="HP" value={s.hp} />
            <Stat label="MP" value={s.mp} />
            <Stat label="P. Atk" value={s.pAtk} />
            <Stat label="M. Atk" value={s.mAtk} />
            <Stat label="P. Def" value={s.pDef} />
            <Stat label="M. Def" value={s.mDef} />
            <Stat label="Accuracy" value={s.accuracy} />
            <Stat label="Evasion" value={s.evasion} />
            <Stat label="Exp" value={s.exp} />
            <Stat label="SP" value={s.sp} />
          </div>
          {(s.atkAttr || s.defAttr) && (
            <div className="mt-2 space-y-1 text-xs text-zinc-400">
              {s.atkAttr && <p>Атака: {s.atkAttr}</p>}
              {s.defAttr && <p>Защита: {s.defAttr}</p>}
            </div>
          )}
        </section>

        {canViewRoute && boss.howToReach && (
          <section className="rounded-xl bg-amber-500/10 p-3 ring-1 ring-amber-500/25">
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-amber-400">
              Как добраться
            </h4>
            <p className="text-sm leading-relaxed text-amber-100/90">{boss.howToReach}</p>
          </section>
        )}

        {boss.lore && (
          <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Описание</h4>
            <p className="text-sm leading-relaxed text-zinc-300">{boss.lore}</p>
          </section>
        )}

        {boss.skills.length > 0 && (
          <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Навыки</h4>
            <ul className="space-y-2">
              {boss.skills.map((sk, i) => (
                <li key={`${sk.name}-${i}`} className="rounded-xl bg-zinc-950/40 px-3 py-2 ring-1 ring-zinc-800/70">
                  <p className="text-sm font-medium text-zinc-200">
                    {sk.name}
                    {sk.level != null ? <span className="ml-1 text-zinc-500">Lv. {sk.level}</span> : null}
                  </p>
                  {sk.desc && <p className="mt-1 text-xs leading-relaxed text-zinc-500">{sk.desc}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}

        {boss.drops.length > 0 && (
          <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Дроп</h4>
            <div className="space-y-3">
              {boss.drops.map((group, gi) => (
                <div key={gi} className="overflow-hidden rounded-xl ring-1 ring-zinc-800/80">
                  <div className="bg-zinc-900/80 px-3 py-1.5 text-[0.7rem] text-zinc-500">
                    Группа · шанс {group.groupChance ?? "—"}
                  </div>
                  <ul className="divide-y divide-zinc-800/60">
                    {group.items.map((it, ii) => (
                      <li key={`${it.name}-${ii}`} className="flex items-center gap-2.5 px-3 py-1.5">
                        <DropIcon itemId={it.itemId} icon={it.icon} name={it.name ?? ""} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-zinc-200">
                            {it.name}
                            {it.grade && (
                              <span className="ml-1.5 text-[0.65rem] text-zinc-500">{it.grade}</span>
                            )}
                          </p>
                        </div>
                        <span className="shrink-0 tabular-nums text-xs text-zinc-400">{it.amount ?? "—"}</span>
                        <span className="w-16 shrink-0 text-right tabular-nums text-xs text-amber-400/90">
                          {it.chance?.replace(/(\.\d*?[1-9])0+%/, "$1%").replace(/\.0+%/, "%") ?? "—"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      <div className="shrink-0 border-t border-zinc-800/80 p-3">
        <a
          href={boss.wikiUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary block w-full text-center text-xs"
        >
          Masterwork Wiki
        </a>
      </div>
    </div>

    <ConfirmDialog
      open={clearConfirmOpen}
      title="Сброс таймера"
      message={`Сбросить таймер «${boss.name}»?`}
      confirmLabel="Сбросить"
      tone="danger"
      onConfirm={() => {
        onClear();
        setClearConfirmOpen(false);
      }}
      onCancel={() => setClearConfirmOpen(false)}
    />
    </>
  );
}
