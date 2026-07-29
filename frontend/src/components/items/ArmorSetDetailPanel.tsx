import { Link } from "react-router-dom";
import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import { formatStat, itemInfo, type CraftCatalog } from "../../lib/craftCalc";
import {
  cumulativeSetStats,
  catalogItemPath,
  formatNpcPrice,
  gearStatRows,
  setMemberCraftable,
  setMemberLabel,
  wikiItemUrl,
  type ArmorSetSummary,
} from "../../lib/itemsCatalog";

interface Props {
  catalog: CraftCatalog;
  set: ArmorSetSummary;
  onClose: () => void;
  onSelectItem: (id: number) => void;
}

export default function ArmorSetDetailPanel({ catalog, set, onClose, onSelectItem }: Props) {
  const cum = cumulativeSetStats(catalog, set.memberIds);
  const cumRows = (
    [
      ["p_atk", "Физ. атака"],
      ["m_atk", "Маг. атака"],
      ["p_def", "Физ. защита"],
      ["m_def", "Маг. защита"],
      ["shield_def", "Защита щита"],
      ["crystals", "Кристаллизация"],
    ] as const
  ).filter(([k]) => cum[k] != null);

  return (
    <div className="panel flex flex-col overflow-hidden shadow-glow">
      <div className="flex flex-wrap items-start gap-3 border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-3">
        <ItemIcon id={set.iconId} src={set.iconSrc} size={48} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-zinc-50">{set.name}</h2>
            <GradePill grade={set.grade} />
            {set.pvp && (
              <span className="rounded-lg bg-rose-500/15 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-rose-400">
                PvP
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-zinc-500">{set.memberIds.length} частей комплекта</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-3 py-1.5 text-sm text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          aria-label="Закрыть"
        >
          ✕
        </button>
      </div>

      <div className="space-y-4 p-4">
        {set.effect.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">
              Бонус комплекта
            </h3>
            <ul className="space-y-1 rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-3 py-2.5 text-sm text-zinc-200">
              {set.effect.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">Части сета</h3>
          <div className="space-y-2">
            {set.memberIds.map((id) => {
              const info = itemInfo(catalog, id);
              const known = Boolean(catalog.items[String(id)]);
              const craftable = setMemberCraftable(set, id, catalog);
              const displayName = setMemberLabel(set, id, catalog);
              const rows = known ? gearStatRows(info) : [];
              return (
                <div
                  key={id}
                  className="flex flex-wrap items-start gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-3 py-2.5"
                >
                  <button
                    type="button"
                    className="flex min-w-0 flex-1 items-start gap-3 text-left"
                    onClick={() => known && onSelectItem(id)}
                    disabled={!known}
                  >
                    <ItemIcon id={known ? id : null} size={32} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-medium text-zinc-100">{displayName}</span>
                        {known && <GradePill grade={info.grade} />}
                        {!craftable && (
                          <span className="rounded bg-zinc-700/40 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase text-zinc-400">
                            Не крафт
                          </span>
                        )}
                        {craftable && (
                          <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[0.6rem] font-bold uppercase text-emerald-400">
                            Крафт
                          </span>
                        )}
                      </div>
                      {rows.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[0.7rem] text-zinc-400">
                          {rows.map((r) => (
                            <span key={r.label}>
                              <span className="text-zinc-600">{r.label}</span>{" "}
                              <span className="tabular-nums text-zinc-200">{r.value}</span>
                            </span>
                          ))}
                          {info.npc_sell != null && (
                            <span className="tabular-nums text-amber-500/80">
                              {formatNpcPrice(info.npc_sell)}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </button>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    {known && (
                      <Link
                        to={catalogItemPath(info)}
                        className="text-[0.7rem] text-amber-400 hover:underline"
                      >
                        Вики →
                      </Link>
                    )}
                    {known && (
                      <a
                        href={wikiItemUrl(info)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[0.7rem] text-zinc-400 hover:underline"
                      >
                        Masterwork ↗
                      </a>
                    )}
                    {craftable && (
                      <Link
                        to={`/craft?id=${id}`}
                        className="text-[0.7rem] font-medium text-emerald-400 hover:underline"
                      >
                        Крафт →
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {cumRows.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">
              Суммарно (известные части)
            </h3>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {cumRows.map(([key, label]) => (
                <div
                  key={key}
                  className="rounded-xl border border-zinc-800/80 bg-zinc-900/50 px-3 py-2"
                >
                  <p className="text-[0.65rem] uppercase tracking-wide text-zinc-600">{label}</p>
                  <p className="mt-0.5 text-sm font-semibold tabular-nums text-zinc-100">
                    {formatStat(cum[key])}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {set.masterworkSetUrl && (
          <a
            href={set.masterworkSetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-sm text-amber-400 hover:underline"
          >
            Сет на Masterwork Wiki ↗
          </a>
        )}
      </div>
    </div>
  );
}
