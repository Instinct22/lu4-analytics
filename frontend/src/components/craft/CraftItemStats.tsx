import { formatStat, isArmorItem, isWeaponItem, itemInfo, type CraftCatalog } from "../../lib/craftCalc";

interface Props {
  catalog: CraftCatalog;
  id: number;
  compact?: boolean;
}

const cellClass = (compact?: boolean) =>
  compact
    ? "whitespace-nowrap text-[0.65rem] tabular-nums text-zinc-500"
    : "whitespace-nowrap text-xs tabular-nums text-zinc-400";

export function CraftWeaponStatCells({
  catalog,
  id,
  compact,
}: Props) {
  const stats = itemInfo(catalog, id).stats;
  const cls = cellClass(compact);
  return (
    <>
      <td className={cls}>{formatStat(stats?.p_atk)}</td>
      <td className={cls}>{formatStat(stats?.m_atk)}</td>
      <td className={cls}>{formatStat(stats?.crystals)}</td>
    </>
  );
}

export function CraftArmorStatCells({
  catalog,
  id,
  compact,
}: Props) {
  const stats = itemInfo(catalog, id).stats;
  const cls = cellClass(compact);
  return (
    <>
      <td className={cls}>{formatStat(stats?.p_def)}</td>
      <td className={cls}>{formatStat(stats?.m_def)}</td>
      <td className={cls}>{formatStat(stats?.shield_def)}</td>
    </>
  );
}

export function CraftItemStatsPanel({ catalog, id }: Props) {
  const info = itemInfo(catalog, id);
  const stats = info.stats;
  if (!stats) return null;

  const rows: { label: string; value: string }[] = [];
  if (isWeaponItem(info)) {
    if (stats.p_atk != null) rows.push({ label: "Физ. атака", value: formatStat(stats.p_atk) });
    if (stats.m_atk != null) rows.push({ label: "Маг. атака", value: formatStat(stats.m_atk) });
    if (stats.crystals != null) rows.push({ label: "Кристализация", value: formatStat(stats.crystals) });
  } else if (isArmorItem(info)) {
    if (stats.p_def != null) rows.push({ label: "Физ. защита", value: formatStat(stats.p_def) });
    if (stats.m_def != null) rows.push({ label: "Маг. защита", value: formatStat(stats.m_def) });
    if (stats.shield_def != null) rows.push({ label: "Защита щита", value: formatStat(stats.shield_def) });
  }

  if (rows.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
      {rows.map((row) => (
        <span key={row.label} className="text-zinc-400">
          <span className="text-zinc-500">{row.label}:</span>{" "}
          <span className="font-medium tabular-nums text-zinc-200">{row.value}</span>
        </span>
      ))}
    </div>
  );
}

export function CraftItemDescription({ catalog, id }: Props) {
  const description = itemInfo(catalog, id).description;
  if (!description) return null;
  return (
    <div className="mt-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
      <h4 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-zinc-500">Описание</h4>
      <p className="text-sm leading-relaxed text-zinc-300">{description}</p>
    </div>
  );
}
