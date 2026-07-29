import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { GradePill, ItemIcon } from "../craft/CraftCostBar";
import {
  dualItemInfo,
  dualVariants,
  isDualMaterialWeapon,
  type DualsCatalog,
} from "../../lib/dualsCatalog";

interface Props {
  catalog: DualsCatalog;
  productId: number;
}

function mergeDirectMaterials(materials: { id: number; amount: number }[]) {
  const order: number[] = [];
  const byId = new Map<number, number>();
  for (const mat of materials) {
    if (!byId.has(mat.id)) order.push(mat.id);
    byId.set(mat.id, (byId.get(mat.id) ?? 0) + mat.amount);
  }
  return order.map((id) => ({ id, amount: byId.get(id)! }));
}

export default function DualCraftSection({ catalog, productId }: Props) {
  const navigate = useNavigate();
  const variant = dualVariants(catalog, productId)[0];
  const materials = useMemo(
    () => mergeDirectMaterials(variant?.direct ?? []),
    [variant?.direct],
  );

  const onMaterialClick = (id: number) => {
    if (!isDualMaterialWeapon(catalog, id)) return;
    navigate(`/craft?id=${id}`);
  };

  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">Создание у Pushkin</h3>
      <p className="mb-2 text-xs text-zinc-500">
        {variant?.npc ?? "Pushkin"} ·{" "}
        {variant?.source === "inferred"
          ? "состав по названию"
          : variant?.source === "pushkin"
            ? "рецепт кузнеца"
            : "создание"}
      </p>
      {(variant?.sa || dualItemInfo(catalog, productId).description) && (
        <div className="mb-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3">
          <h4 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-zinc-500">SA / эффект</h4>
          <p className="text-sm leading-relaxed text-zinc-300">
            {variant?.sa || dualItemInfo(catalog, productId).description}
          </p>
        </div>
      )}
      {materials.length === 0 ? (
        <p className="text-sm text-zinc-500">Состав создания не найден</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-zinc-800/80">
          <table className="min-w-full text-sm">
            <thead className="border-b border-zinc-800/80 bg-zinc-900/60">
              <tr>
                <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Материал
                </th>
                <th className="px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Грейд
                </th>
                <th className="px-3 py-2 text-right text-[0.65rem] font-semibold uppercase tracking-wide text-zinc-500">
                  Кол-во
                </th>
              </tr>
            </thead>
            <tbody>
              {materials.map((mat) => {
                const info = dualItemInfo(catalog, mat.id);
                const weapon = isDualMaterialWeapon(catalog, mat.id);
                return (
                  <tr
                    key={mat.id}
                    onClick={() => onMaterialClick(mat.id)}
                    className={`border-b border-zinc-800/50 last:border-b-0 ${
                      weapon ? "cursor-pointer transition-colors hover:bg-amber-500/10" : ""
                    }`}
                    title={weapon ? "Открыть крафт оружия" : undefined}
                  >
                    <td className="px-3 py-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <ItemIcon id={mat.id} size={24} />
                        <div className="min-w-0">
                          <span
                            className={`truncate font-medium ${weapon ? "text-amber-300" : "text-zinc-100"}`}
                          >
                            {info.name}
                          </span>
                          {weapon && <p className="text-[0.65rem] text-zinc-500">Крафт →</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <GradePill grade={info.grade} />
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-zinc-200">
                      ×{mat.amount.toLocaleString("ru-RU")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {materials.some((m) => isDualMaterialWeapon(catalog, m.id)) && (
        <p className="mt-2 text-xs text-zinc-500">
          Нажмите на оружие в списке, чтобы открыть его страницу крафта
        </p>
      )}
    </div>
  );
}
