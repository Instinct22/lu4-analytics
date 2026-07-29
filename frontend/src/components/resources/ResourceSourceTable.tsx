import type { NpcSource } from "../../lib/craftResources";
import { formatChance, wikiUrl } from "../../lib/craftResources";

interface Props {
  sources: NpcSource[];
  kind: "spoil" | "drop";
  onNpcClick: (source: NpcSource) => void;
}

function LocationCell({ source }: { source: NpcSource }) {
  const locations = source.locations ?? [];
  if (locations.length === 0) {
    return <span className="text-zinc-500">не указана</span>;
  }
  return (
    <ul className="flex flex-col gap-0.5">
      {locations.map((loc) => (
        <li key={loc.url || loc.name}>
          {loc.url ? (
            <a
              href={wikiUrl(loc.url)}
              target="_blank"
              rel="noreferrer"
              className="text-sky-400 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {loc.name}
            </a>
          ) : (
            <span className="text-zinc-300">{loc.name}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function ResourceSourceTable({ sources, kind, onNpcClick }: Props) {
  const title = kind === "spoil" ? "Спойл (Sweep)" : "Дроп";
  const titleColor = kind === "spoil" ? "text-emerald-400" : "text-amber-400";

  return (
    <section className="mt-5">
      <div className="flex items-baseline gap-2">
        <h4 className={`text-sm font-semibold ${titleColor}`}>{title}</h4>
        <span className="text-xs text-zinc-500">{sources.length} мобов</span>
      </div>

      {sources.length === 0 ? (
        <p className="mt-2 text-sm italic text-zinc-500">Нет источников в выбранном диапазоне уровней</p>
      ) : (
        <div className="mt-3 overflow-x-auto rounded-xl border border-zinc-800/80">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Монстр</th>
                <th className="px-3 py-2">Ур.</th>
                <th className="min-w-[160px] px-3 py-2">Локация</th>
                <th className="px-3 py-2">Кол-во</th>
                <th className="px-3 py-2">Шанс</th>
                <th className="px-3 py-2">Wiki</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((src, i) => {
                const href = src.npc_url ? wikiUrl(src.npc_url) : null;
                return (
                  <tr key={`${src.npc_id}-${src.amount}-${src.chance}-${i}`} className="border-t border-zinc-800/50 even:bg-zinc-900/30">
                    <td className="px-3 py-2 text-zinc-500">{i + 1}</td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => onNpcClick(src)}
                        className="text-left font-medium text-sky-400 hover:underline"
                      >
                        {src.npc_name}
                      </button>
                    </td>
                    <td className="px-3 py-2 tabular-nums text-zinc-300">{src.npc_level}</td>
                    <td className="min-w-[160px] px-3 py-2 text-zinc-400">
                      <LocationCell source={src} />
                    </td>
                    <td className="px-3 py-2 tabular-nums text-zinc-300">{src.amount}</td>
                    <td className="px-3 py-2 font-semibold tabular-nums text-sky-300">{formatChance(src.chance)}</td>
                    <td className="px-3 py-2">
                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          className="text-amber-400 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          ↗
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
