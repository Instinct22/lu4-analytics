import { Link } from "react-router-dom";
import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import {
  OTHER_SUB_LABELS,
  restrictionLabels,
  statRows,
} from "../../lib/itemEncyclopedia";
import type { ItemEncyclopediaEntry, ItemSourceRow, ItemEnchantRow } from "../../api/items";
import { characterSkillPath, itemPagePath, type ReturnLink } from "../../lib/internalNav";
import { masterworkItemUrl } from "../../lib/itemEncyclopedia";
import { useItemSources } from "../../hooks/useItemEncyclopedia";
import { LoadingState } from "../ui";

interface Props {
  entry: ItemEncyclopediaEntry;
  onClose: () => void;
  craftLink?: string | null;
  setLinks?: Array<{ name: string; onClick: () => void }>;
  headerExtra?: React.ReactNode;
  returnLink?: ReturnLink | null;
  returnPath?: string | null;
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="mb-3 border-b border-zinc-800/80 pb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h3>
      {children}
    </section>
  );
}

function SourceTable({
  title,
  rows,
}: {
  title: string;
  rows: ItemSourceRow[];
}) {
  if (!rows.length) return null;
  return (
    <div>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h4>
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-900/80 text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-3 py-2">NPC</th>
              <th className="px-3 py-2">Уровень</th>
              <th className="px-3 py-2">Кол-во</th>
              <th className="px-3 py-2 text-right">Шанс</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={`${row.npc_id}-${i}`} className="border-t border-zinc-800/80">
                <td className="px-3 py-2">
                  {row.npc_id ? (
                    <Link to={`/resources?npc=${row.npc_id}`} className="text-amber-400 hover:underline">
                      {row.npc_name}
                    </Link>
                  ) : (
                    row.npc_name
                  )}
                </td>
                <td className="px-3 py-2 text-zinc-400">{row.npc_level_raw || row.npc_level || "—"}</td>
                <td className="px-3 py-2 text-zinc-300">{row.amount}</td>
                <td className="px-3 py-2 text-right text-zinc-300">{row.chance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const SOUL_CRYSTAL_MARKER = "<Available Soul Crystals>";

function displayEffects(entry: ItemEncyclopediaEntry): string | null {
  const raw = entry.effects || entry.description || "";
  if (!raw) return null;
  if (entry.item_modifiers?.soul_crystals?.length) {
    const cleaned = raw.replace(new RegExp(`${SOUL_CRYSTAL_MARKER}[^<]*`, "i"), "").trim();
    return cleaned || null;
  }
  return raw;
}

const VARIANT_ORIGIN_LABELS: Record<string, string> = {
  unseal_variant: "Результат распечатки предмета",
  unsealed_variant: "Результат распечатки предмета",
  weapon_sa_variant: "Вариант с кристаллом души предмета",
  duplicate_variant: "Вариант редкости предмета",
  variant: "Вариант предмета",
};

const ARMOR_CLASS_LABELS: Record<string, string> = {
  heavy: "Тяжёлая броня",
  light: "Лёгкая броня",
  magic: "Роба",
};

interface UnsealRow {
  id: number;
  name: string;
  hint: string | null;
}

function unsealRows(entry: ItemEncyclopediaEntry): UnsealRow[] {
  const rows = (entry.unseal_variants ?? []).map((v) => ({
    id: v.id,
    name: v.name || `#${v.id}`,
    hint: v.label || (v.armor_class ? ARMOR_CLASS_LABELS[v.armor_class] ?? v.armor_class : null),
  }));
  if (rows.length) return rows;

  if (!entry.name.startsWith("Sealed ")) return [];
  return (entry.sealed_group?.variants ?? [])
    .filter((v) => !v.name.startsWith("Sealed "))
    .map((v) => ({
      id: v.id,
      name: v.name,
      hint: v.armor_type ? ARMOR_CLASS_LABELS[v.armor_type] ?? v.armor_type : null,
    }));
}

export default function ItemEncyclopediaPanel({
  entry,
  onClose,
  craftLink,
  setLinks,
  headerExtra,
  returnLink,
  returnPath,
}: Props) {
  const hasSources =
    (entry.drops?.length ?? 0) > 0 ||
    (entry.spoils?.length ?? 0) > 0 ||
    Boolean(entry.has_drop) ||
    Boolean(entry.has_spoil);

  const needFetchSources =
    hasSources &&
    (entry.drops == null || entry.spoils == null) &&
    (Boolean(entry.has_drop) || Boolean(entry.has_spoil));

  const showCraft = Boolean(entry.craft?.craftable && craftLink);
  const showSet = Boolean(entry.set || entry.set_name || setLinks?.length);
  const showEnchant = (entry.enchant?.length ?? 0) > 0;
  const showLinks = Boolean(entry.sealed_group);
  const { data: fetchedSources, isLoading: sourcesLoading } = useItemSources(
    entry.id,
    needFetchSources,
  );
  const drops = entry.drops ?? fetchedSources?.drops ?? [];
  const spoils = entry.spoils ?? fetchedSources?.spoils ?? [];

  const rows = statRows(entry);
  const restrictions = entry.restrictions ?? {};
  const rLabels = restrictionLabels();

  const itemSkills =
    (entry.links as { item_skills?: Array<{ name: string; id?: number }> } | undefined)?.item_skills ?? [];

  const masterwork = entry.masterwork as
    | {
        baseId?: number;
        baseName?: string;
        rareName?: string;
        bonus?: { raw?: string; atoms?: Array<{ stat: string; op: string; value: number; unit?: string }> };
      }
    | undefined;

  const modifiers = entry.item_modifiers;
  const effectsText = displayEffects(entry);
  const unsealVariants = unsealRows(entry);

  return (
    <div className="panel flex flex-col overflow-hidden shadow-glow">
      {returnLink ? (
        <div className="border-b border-zinc-800/80 bg-zinc-900/40 px-4 py-2">
          <Link
            to={returnLink.href}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-400 transition-colors hover:text-amber-300"
          >
            ← {returnLink.label}
          </Link>
        </div>
      ) : null}
      <div className="flex flex-wrap items-start gap-3 border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-3">
        <ItemIcon id={entry.id} size={48} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-zinc-50">{entry.name}</h2>
            <GradePill grade={entry.grade} />
            {entry.craft?.craftable && (
              <span className="rounded-lg bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-emerald-400">
                Крафт
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-zinc-500">{entry.type}</p>
          {entry.other_subcategory && (
            <p className="text-xs text-zinc-600">
              {OTHER_SUB_LABELS[entry.other_subcategory] || entry.other_subcategory}
            </p>
          )}
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs">
            <Link
              to={itemPagePath(entry.id, returnPath)}
              className="font-medium text-amber-400 hover:underline"
            >
              Локальная вики →
            </Link>
            <a
              href={masterworkItemUrl(entry)}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-amber-400 hover:underline"
            >
              Masterwork Wiki ↗
            </a>
          </div>
          {headerExtra}
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

      <div className="max-h-[70vh] space-y-6 overflow-y-auto p-4">
        <DetailSection title="Характеристики">
          <div className="space-y-4">
            {entry.variant_of != null && (
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-800/40 px-3 py-2.5 text-sm">
                <p className="text-zinc-400">
                  {VARIANT_ORIGIN_LABELS[entry.exclude_reason ?? ""] ?? "Вариант предмета"}:{" "}
                  <Link
                    to={itemPagePath(entry.variant_of, returnPath)}
                    className="font-medium text-amber-400 hover:underline"
                  >
                    ← вернуться к основному предмету
                  </Link>
                </p>
              </div>
            )}
            {effectsText && (
              <div>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Эффекты</h4>
                <p className="text-sm leading-relaxed text-zinc-300">{effectsText}</p>
              </div>
            )}
            {unsealVariants.length > 0 && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2.5">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-400">
                  Распечатка
                </h4>
                <p className="mb-2 text-sm text-zinc-400">
                  У кузнеца предмет можно распечатать. Возможные варианты:
                </p>
                <ul className="space-y-1.5 text-sm">
                  {unsealVariants.map((v) => (
                    <li key={v.id}>
                      <Link to={itemPagePath(v.id, returnPath)} className="font-medium text-amber-400 hover:underline">
                        {v.name}
                      </Link>
                      {v.hint && <span className="ml-2 text-xs text-zinc-500">{v.hint}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {modifiers?.soul_crystals && modifiers.soul_crystals.length > 0 && (
              <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-3 py-2.5">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-400">
                  Кристаллы души (CA)
                </h4>
                <ul className="space-y-2 text-sm text-zinc-300">
                  {modifiers.soul_crystals.map((sc) => (
                    <li key={`${sc.name}-${sc.id ?? sc.full_name ?? ""}`} className="leading-relaxed">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-medium text-zinc-100">{sc.name}</span>
                        {sc.pvp && (
                          <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase text-rose-300">
                            PvP
                          </span>
                        )}
                        {"weapon_sa" in sc && sc.weapon_sa && (
                          <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase text-indigo-300">
                            SA
                          </span>
                        )}
                      </div>
                      {sc.effect && <p className="mt-0.5 text-zinc-400">{sc.effect}</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(modifiers?.rarity?.length ?? 0) > 0 && (
              <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-violet-400">
                  Редкость
                </h4>
                <ul className="space-y-2 text-sm">
                  {modifiers!.rarity!.map((r) => (
                    <li key={`${r.name}-${r.id ?? r.full_name ?? ""}`}>
                      <p className="font-medium text-zinc-100">
                        {r.name}
                        {r.sa && <span className="text-zinc-400"> + {r.sa}</span>}
                        {r.pvp && (
                          <span className="ml-1 rounded bg-rose-500/15 px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase text-rose-300">
                            PvP
                          </span>
                        )}
                      </p>
                      {r.effect && <p className="text-zinc-400">{r.effect}</p>}
                      {r.sa_effect && <p className="text-zinc-500">CA: {r.sa_effect}</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {modifiers?.pvp?.available && (
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2.5">
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-rose-400">PvP</h4>
                <p className="text-sm text-zinc-300">
                  Доступен PvP-вариант
                  {modifiers.pvp.full_name ? `: ${modifiers.pvp.full_name}` : ""}
                </p>
                {modifiers.pvp.notes && (
                  <p className="mt-1 text-sm text-zinc-400">{modifiers.pvp.notes}</p>
                )}
              </div>
            )}
            {masterwork && !modifiers?.rarity?.length && (
              <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-violet-400">Masterwork</h4>
                {masterwork.rareName && (
                  <p className="text-sm font-medium text-zinc-200">{masterwork.rareName}</p>
                )}
                {masterwork.baseId != null && (
                  <Link
                    to={itemPagePath(masterwork.baseId, returnPath)}
                    className="text-xs text-amber-400 hover:underline"
                  >
                    База: {masterwork.baseName || `#${masterwork.baseId}`} →
                  </Link>
                )}
                {masterwork.bonus?.raw && (
                  <p className="mt-1 text-sm text-zinc-400">{masterwork.bonus.raw}</p>
                )}
              </div>
            )}
            {rows.length > 0 && (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                {rows.map((r) => (
                  <div key={r.label}>
                    <dt className="text-[0.65rem] uppercase tracking-wide text-zinc-600">{r.label}</dt>
                    <dd className="text-sm font-medium text-zinc-200">{r.value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {Object.keys(restrictions).length > 0 && (
              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Ограничения</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(restrictions).map(([key, val]) => (
                    <span
                      key={key}
                      className={`rounded-lg px-2 py-1 text-xs ${
                        val ? "bg-emerald-500/10 text-emerald-400" : "bg-zinc-800 text-zinc-500 line-through"
                      }`}
                    >
                      {rLabels[key] || key}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {itemSkills.map((skill) => (
              <div key={skill.id ?? skill.name}>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Item Skill</h4>
                {skill.id ? (
                  <Link
                    to={characterSkillPath(skill.id)}
                    className="text-sm text-amber-400 hover:underline"
                  >
                    {skill.name}
                  </Link>
                ) : (
                  <span className="text-sm text-zinc-300">{skill.name}</span>
                )}
              </div>
            ))}
          </div>
        </DetailSection>

        {hasSources && (
          <DetailSection title="Источники">
            <div className="space-y-4">
              {sourcesLoading && drops.length === 0 && spoils.length === 0 ? (
                <LoadingState />
              ) : (
                <>
                  <SourceTable title="Дроп" rows={drops} />
                  <SourceTable title="Спойл" rows={spoils} />
                </>
              )}
            </div>
          </DetailSection>
        )}

        {showCraft && craftLink && (
          <DetailSection title="Крафт">
            <Link
              to={craftLink}
              className="inline-flex rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-zinc-950"
            >
              Открыть калькулятор крафта →
            </Link>
          </DetailSection>
        )}

        {showSet && (
          <DetailSection title="Сет">
            <div className="space-y-2">
              {setLinks?.length ? (
                <div className="space-y-1">
                  {setLinks.length > 1 && (
                    <p className="text-xs text-zinc-500">
                      Часть используется в нескольких комплектах:
                    </p>
                  )}
                  {setLinks.map((link) => (
                    <button
                      key={link.name}
                      type="button"
                      onClick={link.onClick}
                      className="block text-sm font-medium text-amber-400 hover:underline"
                    >
                      {link.name}
                    </button>
                  ))}
                </div>
              ) : (
                entry.set_name && <p className="text-sm text-zinc-300">{entry.set_name}</p>
              )}
              {entry.set && typeof entry.set === "object" && "effect" in entry.set && (
                <ul className="list-inside list-disc text-sm text-zinc-400">
                  {((entry.set as { effect?: string[] }).effect ?? []).map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          </DetailSection>
        )}

        {showEnchant && (
          <DetailSection title="Заточка">
            <div className="overflow-x-auto rounded-lg border border-zinc-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-zinc-900/80 text-xs uppercase text-zinc-500">
                  <tr>
                    <th className="px-3 py-2">+</th>
                    <th className="px-3 py-2">Кристаллы</th>
                    <th className="px-3 py-2">Fail</th>
                    <th className="px-3 py-2">Статы</th>
                  </tr>
                </thead>
                <tbody>
                  {(entry.enchant ?? []).map((row: ItemEnchantRow) => (
                    <tr key={row.level} className="border-t border-zinc-800/80">
                      <td className="px-3 py-2">+{row.level}</td>
                      <td className="px-3 py-2">{row.crystals ?? "—"}</td>
                      <td className="px-3 py-2">{row.fail_crystals ?? "—"}</td>
                      <td className="px-3 py-2 text-zinc-400">
                        {Object.entries(row)
                          .filter(([k]) => !["level", "crystals", "fail_crystals"].includes(k))
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ") || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DetailSection>
        )}

        {showLinks && entry.sealed_group && (
          <DetailSection title="Связи">
            <div className="space-y-3 text-sm">
              <p className="text-zinc-400">Sealed ID: {entry.sealed_group.sealed_id}</p>
              {entry.sealed_group.variants.map((v: { id: number; name: string; armor_type?: string | null }) => (
                <Link key={v.id} to={`/items?id=${v.id}`} className="block text-amber-400 hover:underline">
                  {v.name} {v.armor_type ? `(${v.armor_type})` : ""}
                </Link>
              ))}
            </div>
          </DetailSection>
        )}
      </div>
    </div>
  );
}
