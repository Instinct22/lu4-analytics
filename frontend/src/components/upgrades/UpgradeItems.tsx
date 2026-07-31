import { Link, useLocation } from "react-router-dom";
import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import { currentReturnPath, itemPagePath } from "../../lib/internalNav";
import {
  upgradeItem,
  weaponStatLine,
  type UpgradeItem,
  type WeaponUpgradesCatalog,
} from "../../lib/weaponUpgrades";

export function UpgradeItemChip({
  catalog,
  id,
}: {
  catalog: WeaponUpgradesCatalog;
  id: number;
}) {
  const location = useLocation();
  const from = currentReturnPath(location);
  const item = upgradeItem(catalog, id);
  const stats = weaponStatLine(item);

  if (!item) {
    return <span className="text-zinc-500">#{id}</span>;
  }

  return (
    <Link
      to={itemPagePath(id, from)}
      className="inline-flex min-w-0 items-center gap-2 rounded-lg bg-zinc-900/60 px-2 py-1 ring-1 ring-zinc-800/80 transition-colors hover:ring-amber-500/30"
      title={[item.name, stats].filter(Boolean).join(" · ")}
    >
      <ItemIcon id={id} size={24} />
      <span className="min-w-0">
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="truncate text-sm font-medium text-zinc-100">{item.name}</span>
          {item.grade ? <GradePill grade={item.grade} /> : null}
        </span>
        {stats ? <span className="block text-[0.65rem] tabular-nums text-zinc-500">{stats}</span> : null}
      </span>
    </Link>
  );
}

export function UpgradeItemStack({
  catalog,
  ids,
}: {
  catalog: WeaponUpgradesCatalog;
  ids: number[];
}) {
  if (ids.length === 0) return <span className="text-zinc-600">—</span>;
  return (
    <div className="flex flex-col gap-1.5">
      {ids.map((id) => (
        <UpgradeItemChip key={id} catalog={catalog} id={id} />
      ))}
    </div>
  );
}

export function UpgradeInfoBanner({ catalog }: { catalog: WeaponUpgradesCatalog }) {
  const location = useLocation();
  const from = currentReturnPath(location);
  const { info } = catalog;

  return (
    <div className="card mb-5 space-y-3 text-sm text-zinc-300">
      <p>
        <span className="font-semibold text-zinc-100">Как:</span> {info.how}
      </p>
      <p>
        <span className="font-semibold text-zinc-100">Где (NG/D):</span> {info.where}
      </p>
      <p>
        <span className="font-semibold text-zinc-100">NG → D:</span> {info.ng_to_d_where} + купон{" "}
        {catalog.ng_to_d ? (
          <Link
            to={itemPagePath(catalog.ng_to_d.coupon_id, from)}
            className="text-amber-400 hover:underline"
          >
            {catalog.ng_to_d.coupon_name}
          </Link>
        ) : (
          "Weapon Upgrade Coupon"
        )}{" "}
        (за 1-ю профессию)
      </p>
      <ul className="list-disc space-y-1 pl-5 text-zinc-400">
        <li>{info.ng_rule}</li>
        <li>{info.d_rule}</li>
        <li>{info.tax_note}</li>
      </ul>
      {catalog.source_url ? (
        <p className="text-xs text-zinc-500">
          Источник:{" "}
          <a href={catalog.source_url} target="_blank" rel="noreferrer" className="text-amber-500/80 hover:underline">
            Ng/D Equipment upgrade (wiki)
          </a>
        </p>
      ) : null}
    </div>
  );
}

export function itemLabel(catalog: WeaponUpgradesCatalog, id: number): string {
  return upgradeItem(catalog, id)?.name ?? `#${id}`;
}

export type { UpgradeItem };
