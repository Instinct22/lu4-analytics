import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { mediaUrl } from "../../api/client";
import { useNpcMaterials } from "../../hooks/useCraftResources";
import { useNpcLoot, type NpcItemLootEntry } from "../../hooks/useNpcLoot";
import { useWikiEntityByExternal } from "../../hooks/useWikiEntityByExternal";
import type { NpcLootEntry, NpcSource } from "../../lib/craftResources";
import { formatChance, npcProfileFromSource, wikiUrl } from "../../lib/craftResources";
import { itemPagePath } from "../../lib/internalNav";
import { ItemIcon } from "../craft/CraftCostBar";
import { LoadingState } from "../ui";

interface Props {
  source: NpcSource;
  materialName?: string;
  onBack: () => void;
  onMaterialClick: (id: number) => void;
}

function levelFromWikiText(text: string | null | undefined): string | null {
  const match = /Lv\.\s*(\d+)/i.exec(text ?? "");
  return match?.[1] ?? null;
}

function ResourceLootRows({
  entries,
  onMaterialClick,
}: {
  entries: NpcLootEntry[];
  onMaterialClick: (id: number) => void;
}) {
  if (entries.length === 0) {
    return <p className="text-sm italic text-zinc-500">Нет ресурсов крафта</p>;
  }
  return (
    <table className="w-full min-w-[520px] text-sm">
      <thead>
        <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
          <th className="px-3 py-2">#</th>
          <th className="px-3 py-2">Ресурс</th>
          <th className="px-3 py-2">Grade</th>
          <th className="px-3 py-2">Кол-во</th>
          <th className="px-3 py-2">Шанс</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, i) => (
          <tr key={`${entry.materialId}-${i}`} className="border-t border-zinc-800/50 even:bg-zinc-900/30">
            <td className="px-3 py-2 text-zinc-500">{i + 1}</td>
            <td className="px-3 py-2">
              <div className="flex items-center gap-2">
                <ItemIcon id={entry.materialId} size={28} />
                <button
                  type="button"
                  onClick={() => onMaterialClick(entry.materialId)}
                  className="font-medium text-sky-400 hover:underline"
                >
                  {entry.materialName}
                </button>
              </div>
            </td>
            <td className="px-3 py-2 text-zinc-400">{entry.materialGrade}</td>
            <td className="px-3 py-2 tabular-nums text-zinc-300">{entry.amount}</td>
            <td className="px-3 py-2 font-semibold tabular-nums text-sky-300">{formatChance(entry.chance)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function OtherLootRows({ entries }: { entries: NpcItemLootEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm italic text-zinc-500">Нет других предметов</p>;
  }
  return (
    <table className="w-full min-w-[520px] text-sm">
      <thead>
        <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
          <th className="px-3 py-2">#</th>
          <th className="px-3 py-2">Предмет</th>
          <th className="px-3 py-2">Grade</th>
          <th className="px-3 py-2">Кол-во</th>
          <th className="px-3 py-2">Шанс</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, i) => (
          <tr key={`${entry.item_id}-${i}`} className="border-t border-zinc-800/50 even:bg-zinc-900/30">
            <td className="px-3 py-2 text-zinc-500">{i + 1}</td>
            <td className="px-3 py-2">
              <div className="flex items-center gap-2">
                <ItemIcon id={entry.item_id} size={28} />
                <Link to={itemPagePath(entry.item_id)} className="font-medium text-sky-400 hover:underline">
                  {entry.item_name}
                </Link>
                {entry.item_url ? (
                  <a
                    href={wikiUrl(entry.item_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-amber-400/80 hover:underline"
                  >
                    wiki
                  </a>
                ) : null}
              </div>
            </td>
            <td className="px-3 py-2 text-zinc-400">{entry.item_grade || "—"}</td>
            <td className="px-3 py-2 tabular-nums text-zinc-300">{entry.amount}</td>
            <td className="px-3 py-2 font-semibold tabular-nums text-sky-300">{formatChance(entry.chance)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LootSection({
  title,
  titleColor,
  children,
}: {
  title: string;
  titleColor: string;
  children: ReactNode;
}) {
  return (
    <section className="mt-5">
      <h4 className={`text-sm font-semibold ${titleColor}`}>{title}</h4>
      <div className="mt-3 overflow-x-auto rounded-xl border border-zinc-800/80">
        <div className="p-1">{children}</div>
      </div>
    </section>
  );
}

export default function NpcDetailPanel({ source, materialName, onBack, onMaterialClick }: Props) {
  const { data, isLoading, error } = useWikiEntityByExternal("npc", source.npc_id);
  const { data: npcMaterials, isLoading: materialsLoading } = useNpcMaterials(source.npc_id);
  const { data: fullLoot, isLoading: lootLoading } = useNpcLoot(source.npc_id);

  const profile = npcMaterials?.npc_name ? npcMaterials : npcProfileFromSource(source);
  const wikiHref = profile.npc_url ? wikiUrl(profile.npc_url) : data?.url ? wikiUrl(data.url) : null;

  const isPlaceholderName = !profile.npc_name || /^NPC #\d+$/i.test(profile.npc_name);
  const displayName = isPlaceholderName && data?.display_name ? data.display_name : profile.npc_name;
  const displayLevel =
    profile.npc_level && profile.npc_level !== "?"
      ? profile.npc_level
      : levelFromWikiText(data?.content_md) || "?";

  const craftIds = new Set([
    ...profile.spoils.map((e) => e.materialId),
    ...profile.drops.map((e) => e.materialId),
  ]);
  const otherSpoils = (fullLoot?.spoils ?? []).filter((e) => !craftIds.has(e.item_id));
  const otherDrops = (fullLoot?.drops ?? []).filter((e) => !craftIds.has(e.item_id));

  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="border-b border-zinc-800/80 px-5 py-4">
        <button
          type="button"
          onClick={onBack}
          className="mb-3 flex items-center gap-1.5 text-sm text-zinc-400 transition-colors hover:text-amber-400"
        >
          <span aria-hidden>←</span>
          {materialName ? `Назад к ${materialName}` : "Назад к ресурсам"}
        </button>

        <div className="flex items-start gap-4">
          {data?.image_path && (
            <img
              src={mediaUrl(data.image_path)!}
              alt=""
              className="h-16 w-16 shrink-0 rounded-lg bg-zinc-800 object-contain"
            />
          )}
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Монстр</p>
            <h3 className="mt-1 text-xl font-semibold text-zinc-50">
              {wikiHref ? (
                <a href={wikiHref} target="_blank" rel="noreferrer" className="hover:text-amber-400">
                  {displayName}
                </a>
              ) : (
                displayName
              )}
            </h3>
            <p className="mt-1 text-sm text-zinc-400">Уровень {displayLevel}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs text-emerald-400">
                Спойл: {materialsLoading ? "…" : profile.spoils.length} ресурс.
                {!lootLoading && otherSpoils.length > 0 ? ` + ${otherSpoils.length} пр.` : ""}
              </span>
              <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs text-amber-400">
                Дроп: {materialsLoading ? "…" : profile.drops.length} ресурс.
                {!lootLoading && otherDrops.length > 0 ? ` + ${otherDrops.length} пр.` : ""}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-h-[75vh] overflow-y-auto p-5">
        {profile.locations.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Локации</p>
            <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {profile.locations.map((loc) => (
                <li key={loc.url || loc.name}>
                  {loc.url ? (
                    <a href={wikiUrl(loc.url)} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">
                      {loc.name}
                    </a>
                  ) : (
                    <span className="text-zinc-300">{loc.name}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {isLoading && <LoadingState />}
        {error && (
          <p className="mb-4 text-sm text-zinc-500">
            Статистика из вики недоступна.
            {wikiHref && (
              <>
                {" "}
                <a href={wikiHref} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">
                  Открыть на wiki
                </a>
              </>
            )}
          </p>
        )}

        {materialsLoading ? (
          <LoadingState />
        ) : (
          <>
            <LootSection title="Спойл (Sweep) — ресурсы крафта" titleColor="text-emerald-400">
              <ResourceLootRows entries={profile.spoils} onMaterialClick={onMaterialClick} />
            </LootSection>
            <LootSection title="Дроп — ресурсы крафта" titleColor="text-amber-400">
              <ResourceLootRows entries={profile.drops} onMaterialClick={onMaterialClick} />
            </LootSection>
          </>
        )}

        {lootLoading ? (
          <p className="mt-5 text-sm text-zinc-500">Загрузка остального лута…</p>
        ) : (
          <>
            {otherSpoils.length > 0 && (
              <LootSection title="Спойл — прочее" titleColor="text-emerald-300/90">
                <OtherLootRows entries={otherSpoils} />
              </LootSection>
            )}
            {otherDrops.length > 0 && (
              <LootSection title="Дроп — прочее" titleColor="text-amber-300/90">
                <OtherLootRows entries={otherDrops} />
              </LootSection>
            )}
          </>
        )}

        {(data || wikiHref) && (
          <div className="mt-6 flex flex-wrap gap-2 border-t border-zinc-800/80 pt-4">
            {data && (
              <Link
                to={`/wiki/npc/${data.id}`}
                className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-400 hover:bg-amber-500/20"
              >
                Полная статья
              </Link>
            )}
            {wikiHref && (
              <a
                href={wikiHref}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800"
              >
                masterwork.wiki
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
