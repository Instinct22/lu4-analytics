import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { mediaUrl } from "../../api/client";
import { useNpcMaterials } from "../../hooks/useCraftResources";
import { useNpcLoot, type NpcItemLootEntry } from "../../hooks/useNpcLoot";
import { useWikiEntityByExternal } from "../../hooks/useWikiEntityByExternal";
import type { NpcLootEntry, NpcSource } from "../../lib/craftResources";
import { formatChance, npcProfileFromSource, wikiUrl } from "../../lib/craftResources";
import { itemPagePath, wikiPagePath, type ReturnLink } from "../../lib/internalNav";
import { ItemIcon } from "../craft/CraftCostBar";
import { LoadingState } from "../ui";

interface Props {
  source: NpcSource;
  materialName?: string;
  onBack: () => void;
  onMaterialClick: (id: number) => void;
  returnLink?: ReturnLink | null;
  returnPath?: string | null;
}

function levelFromWikiText(text: string | null | undefined): string | null {
  const match = /Lv\.\s*(\d+)/i.exec(text ?? "");
  return match?.[1] ?? null;
}

const LOOT_CELL = "px-3 py-2";

interface NpcLootTableRow {
  id: number;
  name: string;
  grade: string;
  amount: string;
  chance: string;
  itemUrl?: string;
  onNameClick?: () => void;
  nameHref?: string;
}

function NpcLootTable({
  rows,
  nameColumn,
  emptyMessage,
}: {
  rows: NpcLootTableRow[];
  nameColumn: string;
  emptyMessage: string;
}) {
  if (rows.length === 0) {
    return <p className={`${LOOT_CELL} text-sm italic text-zinc-500`}>{emptyMessage}</p>;
  }

  return (
    <table className="w-full min-w-[560px] table-fixed text-sm">
      <colgroup>
        <col className="w-10" />
        <col />
        <col className="w-[4.5rem]" />
        <col className="w-[5.5rem]" />
        <col className="w-[5.5rem]" />
        <col className="w-12" />
      </colgroup>
      <thead>
        <tr className="border-b border-zinc-800/80 bg-zinc-900/80 text-left text-xs uppercase tracking-wider text-zinc-500">
          <th className={LOOT_CELL}>#</th>
          <th className={LOOT_CELL}>{nameColumn}</th>
          <th className={LOOT_CELL}>Grade</th>
          <th className={LOOT_CELL}>Кол-во</th>
          <th className={`${LOOT_CELL} text-right`}>Шанс</th>
          <th className={`${LOOT_CELL} text-center`}>Wiki</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => {
          const wikiHref = row.itemUrl ? wikiUrl(row.itemUrl) : null;
          return (
            <tr key={`${row.id}-${i}`} className="border-t border-zinc-800/50 even:bg-zinc-900/30">
              <td className={`${LOOT_CELL} text-zinc-500`}>{i + 1}</td>
              <td className={LOOT_CELL}>
                <div className="flex min-w-0 items-center gap-2">
                  <ItemIcon id={row.id} size={28} />
                  {row.onNameClick ? (
                    <button
                      type="button"
                      onClick={row.onNameClick}
                      className="min-w-0 truncate text-left font-medium text-sky-400 hover:underline"
                    >
                      {row.name}
                    </button>
                  ) : row.nameHref ? (
                    <Link
                      to={row.nameHref}
                      className="min-w-0 truncate font-medium text-sky-400 hover:underline"
                    >
                      {row.name}
                    </Link>
                  ) : (
                    <span className="min-w-0 truncate font-medium text-zinc-200">{row.name}</span>
                  )}
                </div>
              </td>
              <td className={`${LOOT_CELL} text-zinc-400`}>{row.grade || "—"}</td>
              <td className={`${LOOT_CELL} tabular-nums text-zinc-300`}>{row.amount}</td>
              <td className={`${LOOT_CELL} text-right font-semibold tabular-nums text-sky-300`}>
                {formatChance(row.chance)}
              </td>
              <td className={`${LOOT_CELL} text-center`}>
                {wikiHref ? (
                  <a href={wikiHref} target="_blank" rel="noreferrer" className="text-amber-400 hover:underline">
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
  );
}

function resourceLootRows(entries: NpcLootEntry[], onMaterialClick: (id: number) => void): NpcLootTableRow[] {
  return entries.map((entry) => ({
    id: entry.materialId,
    name: entry.materialName,
    grade: entry.materialGrade,
    amount: entry.amount,
    chance: entry.chance,
    itemUrl: entry.materialUrl,
    onNameClick: () => onMaterialClick(entry.materialId),
  }));
}

function otherLootRows(entries: NpcItemLootEntry[], returnPath?: string | null): NpcLootTableRow[] {
  return entries.map((entry) => ({
    id: entry.item_id,
    name: entry.item_name,
    grade: entry.item_grade,
    amount: entry.amount,
    chance: entry.chance,
    itemUrl: entry.item_url,
    nameHref: itemPagePath(entry.item_id, returnPath),
  }));
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
      <div className="mt-3 overflow-x-auto rounded-xl border border-zinc-800/80">{children}</div>
    </section>
  );
}

export default function NpcDetailPanel({
  source,
  materialName,
  onBack,
  onMaterialClick,
  returnLink,
  returnPath,
}: Props) {
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

  const backLabel = materialName
    ? `Назад к ${materialName}`
    : returnLink?.label ?? "Назад к ресурсам";

  return (
    <div className="panel flex flex-col overflow-hidden">
      <div className="border-b border-zinc-800/80 px-5 py-4">
        <button
          type="button"
          onClick={onBack}
          className="mb-3 flex items-center gap-1.5 text-sm text-zinc-400 transition-colors hover:text-amber-400"
        >
          <span aria-hidden>←</span>
          {backLabel}
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
              <NpcLootTable
                rows={resourceLootRows(profile.spoils, onMaterialClick)}
                nameColumn="Ресурс"
                emptyMessage="Нет ресурсов крафта"
              />
            </LootSection>
            <LootSection title="Дроп — ресурсы крафта" titleColor="text-amber-400">
              <NpcLootTable
                rows={resourceLootRows(profile.drops, onMaterialClick)}
                nameColumn="Ресурс"
                emptyMessage="Нет ресурсов крафта"
              />
            </LootSection>
          </>
        )}

        {lootLoading ? (
          <p className="mt-5 text-sm text-zinc-500">Загрузка остального лута…</p>
        ) : (
          <>
            {otherSpoils.length > 0 && (
              <LootSection title="Спойл — прочее" titleColor="text-emerald-300/90">
                <NpcLootTable
                  rows={otherLootRows(otherSpoils, returnPath)}
                  nameColumn="Предмет"
                  emptyMessage="Нет других предметов"
                />
              </LootSection>
            )}
            {otherDrops.length > 0 && (
              <LootSection title="Дроп — прочее" titleColor="text-amber-300/90">
                <NpcLootTable
                  rows={otherLootRows(otherDrops, returnPath)}
                  nameColumn="Предмет"
                  emptyMessage="Нет других предметов"
                />
              </LootSection>
            )}
          </>
        )}

        {(data || wikiHref) && (
          <div className="mt-6 flex flex-wrap gap-2 border-t border-zinc-800/80 pt-4">
            {data && (
              <Link
                to={wikiPagePath("npc", data.id, returnPath)}
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
