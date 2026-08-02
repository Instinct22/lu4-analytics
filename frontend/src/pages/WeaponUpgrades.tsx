import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getWeaponUpgradesCatalog } from "../api/upgrades";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { UpgradeInfoBanner, UpgradeItemChip, UpgradeItemStack } from "../components/upgrades/UpgradeItems";
import {
  availableGradesForKind,
  categoriesForTab,
  formatAdena,
  KIND_LABELS,
  UPGRADE_KINDS,
  UPGRADE_TABS,
  upgradeItem,
  upgradesForCategory,
  weaponStatDelta,
  type UpgradeKind,
  type UpgradeTab,
  type WeaponUpgradesCatalog,
} from "../lib/weaponUpgrades";

function tabClass(active: boolean) {
  return [
    "flex-1 rounded-lg px-2 py-2 text-xs font-semibold transition-colors sm:text-sm",
    active ? "bg-amber-600 text-zinc-950 shadow-sm" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200",
  ].join(" ");
}

function GradeUpgradesPanel({
  catalog,
  grade,
  kind,
  searchHint,
}: {
  catalog: WeaponUpgradesCatalog;
  grade: "NG" | "D";
  kind: UpgradeKind;
  searchHint: string;
}) {
  const categories = useMemo(() => categoriesForTab(catalog, grade, kind), [catalog, grade, kind]);
  const [category, setCategory] = useState(categories[0]?.id ?? "");
  const [search, setSearch] = useState("");

  const activeCategory = categories.find((c) => c.id === category) ?? categories[0];
  const rows = useMemo(() => {
    if (!activeCategory) return [];
    return upgradesForCategory(catalog, grade, activeCategory.id, kind);
  }, [catalog, grade, activeCategory, kind]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => {
      const names = [...row.from_ids, ...row.to_ids].map((id) => {
        const item = catalog.items[String(id)];
        return item?.name?.toLowerCase() ?? "";
      });
      return names.some((n) => n.includes(q));
    });
  }, [rows, search, catalog.items]);

  if (categories.length === 0) {
    return <p className="text-sm text-zinc-500">Нет данных по этому грейду.</p>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
      <div className="panel p-3">
        <p className="mb-2 text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">Категория</p>
        <div className="flex flex-col gap-1">
          {categories.map((cat) => (
            <button
              key={`${cat.kind}:${cat.id}`}
              type="button"
              onClick={() => setCategory(cat.id)}
              className={[
                "rounded-lg px-3 py-2 text-left text-sm transition-colors",
                activeCategory?.id === cat.id
                  ? "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/25"
                  : "text-zinc-400 hover:bg-zinc-800/80 hover:text-zinc-200",
              ].join(" ")}
            >
              <span className="block font-medium">{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="panel p-4">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-zinc-50">{activeCategory?.label}</h3>
            <p className="text-sm text-zinc-500">
              {grade} · {KIND_LABELS[activeCategory?.kind ?? ""] ?? activeCategory?.kind} · {filtered.length}{" "}
              апгрейдов
            </p>
          </div>
          <input
            type="search"
            placeholder={`Поиск ${searchHint}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input max-w-xs"
          />
        </div>

        <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
          <table className="min-w-full text-sm">
            <thead className="border-b border-zinc-800/80 bg-zinc-900/60">
              <tr>
                <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Отдаёте
                </th>
                <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Стоимость
                </th>
                <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Получаете
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {filtered.map((row, idx) => {
                const fromItem = upgradeItem(catalog, row.from_ids[0]);
                const toItem = upgradeItem(catalog, row.to_ids[0]);
                const delta = weaponStatDelta(fromItem, toItem);
                return (
                <tr key={`${row.category}-${idx}`} className="align-top hover:bg-zinc-900/40">
                  <td className="px-3 py-3">
                    <UpgradeItemStack catalog={catalog} ids={row.from_ids} />
                  </td>
                  <td className="px-3 py-3">
                    <span className="whitespace-nowrap font-semibold tabular-nums text-amber-300">
                      {formatAdena(row.cost_adena)} Adena
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <UpgradeItemStack catalog={catalog} ids={row.to_ids} />
                    {delta ? (
                      <p className="mt-1.5 text-xs font-semibold tabular-nums text-emerald-400">{delta}</p>
                    ) : null}
                  </td>
                </tr>
              );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function NgToDPanel({ catalog }: { catalog: WeaponUpgradesCatalog }) {
  const exchange = catalog.ng_to_d;
  if (!exchange) {
    return <p className="text-sm text-zinc-500">Данные обмена NG → D не загружены.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 px-4 py-3 text-sm text-amber-100/90">
        <p>
          Лучшее NG-оружие можно обменять на базовое D-оружие у{" "}
          <span className="font-semibold text-amber-200">{exchange.npc}</span> с купоном{" "}
          <UpgradeItemChip catalog={catalog} id={exchange.coupon_id} /> (награда за{" "}
          {exchange.profession === "1st Profession" ? "1-ю профессию" : exchange.profession}).
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
        <table className="min-w-full text-sm">
          <thead className="border-b border-zinc-800/80 bg-zinc-900/60">
            <tr>
              <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                NG (топ)
              </th>
              <th className="px-3 py-2 text-center text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                →
              </th>
              <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                D (базовое)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {exchange.pairs.map((pair) => {
              const fromItem = upgradeItem(catalog, pair.from_id);
              const toItem = upgradeItem(catalog, pair.to_id);
              const delta = weaponStatDelta(fromItem, toItem);
              return (
              <tr key={`${pair.from_id}-${pair.to_id}`} className="hover:bg-zinc-900/40">
                <td className="px-3 py-3">
                  <UpgradeItemChip catalog={catalog} id={pair.from_id} />
                </td>
                <td className="px-3 py-3 text-center text-zinc-600">
                  →
                  {delta ? (
                    <p className="mt-1 text-xs font-semibold tabular-nums text-emerald-400">{delta}</p>
                  ) : null}
                </td>
                <td className="px-3 py-3">
                  <UpgradeItemChip catalog={catalog} id={pair.to_id} />
                </td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const KIND_SEARCH_HINTS: Record<UpgradeKind, string> = {
  physical: "оружия",
  magic: "маг. оружия",
  armor: "брони",
  jewelry: "бижутерии",
};

function kindButtonClass(active: boolean) {
  return [
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors",
    active
      ? "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30"
      : "text-zinc-400 hover:bg-zinc-800/80 hover:text-zinc-200",
  ].join(" ");
}

export default function WeaponUpgradesPage() {
  const [kind, setKind] = useState<UpgradeKind>("physical");
  const [tab, setTab] = useState<UpgradeTab>("NG");

  const { data: catalog, isLoading, isError } = useQuery({
    queryKey: ["upgrades", "catalog"],
    queryFn: getWeaponUpgradesCatalog,
    staleTime: 1000 * 60 * 60,
  });

  const grades = useMemo(
    () => (catalog ? availableGradesForKind(catalog, kind) : []),
    [catalog, kind],
  );

  const hasExchange = kind === "physical" && !!catalog?.ng_to_d?.pairs.length;

  const tabs = useMemo<{ id: UpgradeTab; label: string }[]>(() => {
    const list = UPGRADE_TABS.filter(
      (t) => (t.id === "NG_TO_D" ? hasExchange : grades.includes(t.id as "NG" | "D")),
    );
    return list;
  }, [grades, hasExchange]);

  // Keep the active grade tab valid whenever the type filter changes.
  useEffect(() => {
    if (tabs.length && !tabs.some((t) => t.id === tab)) {
      setTab(tabs[0].id);
    }
  }, [tabs, tab]);

  const stats = useMemo(() => {
    if (!catalog) return null;
    const rows = catalog.upgrades.filter((u) => u.kind === kind);
    const ng = rows.filter((u) => u.grade === "NG").length;
    const d = rows.filter((u) => u.grade === "D").length;
    return { ng, d, pairs: hasExchange ? (catalog.ng_to_d?.pairs.length ?? 0) : 0 };
  }, [catalog, kind, hasExchange]);

  if (isLoading) return <LoadingState />;
  if (isError || !catalog) {
    return (
      <ErrorState message="Каталог апгрейдов не загружен. Запустите build_weapon_upgrades.py и import_datasets.py weapon_upgrades" />
    );
  }

  const searchHint = KIND_SEARCH_HINTS[kind];

  return (
    <div className="min-h-full">
      <PageHeader title="Апгрейд снаряжения NG / D">
        {stats ? (
          <p className="text-sm text-zinc-500">
            {KIND_LABELS[kind]}: {stats.ng} NG · {stats.d} D
            {stats.pairs > 0 ? ` · ${stats.pairs} обменов NG→D` : ""}
          </p>
        ) : null}
      </PageHeader>

      <UpgradeInfoBanner catalog={catalog} />

      <div className="mb-4 flex flex-wrap gap-1 rounded-xl bg-zinc-900/60 p-1 ring-1 ring-zinc-800/80">
        {UPGRADE_KINDS.map((k) => (
          <button
            key={k.id}
            type="button"
            className={kindButtonClass(kind === k.id)}
            onClick={() => setKind(k.id)}
          >
            <span aria-hidden>{k.icon}</span>
            {k.label}
          </button>
        ))}
      </div>

      {tabs.length > 1 ? (
        <div className="mb-4 flex gap-1 rounded-xl bg-zinc-800/80 p-1">
          {tabs.map((t) => (
            <button key={t.id} type="button" className={tabClass(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      ) : null}

      {tab === "NG" && grades.includes("NG") ? (
        <GradeUpgradesPanel catalog={catalog} grade="NG" kind={kind} searchHint={searchHint} />
      ) : null}
      {tab === "D" && grades.includes("D") ? (
        <GradeUpgradesPanel catalog={catalog} grade="D" kind={kind} searchHint={searchHint} />
      ) : null}
      {tab === "NG_TO_D" && hasExchange ? <NgToDPanel catalog={catalog} /> : null}
    </div>
  );
}
