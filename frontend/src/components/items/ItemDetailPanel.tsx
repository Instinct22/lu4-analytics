import { Link } from "react-router-dom";
import DualCraftSection from "./DualCraftSection";
import ItemEncyclopediaPanel from "./ItemEncyclopediaPanel";
import { LoadingState } from "../ui";
import { useItemDetail } from "../../hooks/useItemEncyclopedia";
import {
  findSetsForItem,
  itemCraftable,
  type ArmorSetSummary,
  type GearItem,
} from "../../lib/itemsCatalog";
import type { CraftCatalog } from "../../lib/craftCalc";
import type { DualsCatalog } from "../../lib/dualsCatalog";
import { DUAL_TYPE_LABELS } from "../../lib/dualsCatalog";
import type { ReturnLink } from "../../lib/internalNav";

interface Props {
  catalog: CraftCatalog;
  dualsCatalog?: DualsCatalog | null;
  item: GearItem;
  sets: ArmorSetSummary[];
  onClose: () => void;
  onOpenSet: (setId: string) => void;
  returnLink?: ReturnLink | null;
  returnPath?: string | null;
}

export default function ItemDetailPanel({
  catalog,
  dualsCatalog,
  item,
  sets,
  onClose,
  onOpenSet,
  returnLink,
  returnPath,
}: Props) {
  const { data: entry, isLoading, isError } = useItemDetail(item.id);
  const craftable = !item.isDual && itemCraftable(catalog, item.id);
  const itemSets = findSetsForItem(sets, item.id);

  if (isLoading) return <LoadingState />;
  if (isError || !entry) {
    return (
      <div className="panel p-6 text-sm text-zinc-500">
        Не удалось загрузить данные предмета.{" "}
        <button type="button" onClick={onClose} className="text-amber-400 hover:underline">
          Закрыть
        </button>
      </div>
    );
  }

  const headerExtra = (
    <>
      {item.isDual && item.dualType && (
        <span className="mt-1 inline-block rounded-lg bg-zinc-800 px-2 py-0.5 text-[0.65rem] font-semibold uppercase text-zinc-400">
          {DUAL_TYPE_LABELS[item.dualType]}
        </span>
      )}
      {craftable && (
        <Link to={`/craft?id=${item.id}`} className="ml-2 text-xs font-medium text-emerald-400 hover:underline">
          Калькулятор крафта →
        </Link>
      )}
      {item.isDual && dualsCatalog && (
        <div className="mt-3">
          <DualCraftSection catalog={dualsCatalog} productId={item.id} />
        </div>
      )}
    </>
  );

  return (
    <ItemEncyclopediaPanel
      entry={{ ...entry, craft: entry.craft ?? { craftable, variants: [] } }}
      onClose={onClose}
      craftLink={craftable ? `/craft?id=${item.id}` : null}
      setLinks={itemSets.map((s) => ({ name: s.name, onClick: () => onOpenSet(s.id) }))}
      headerExtra={headerExtra}
      returnLink={returnLink}
      returnPath={returnPath}
    />
  );
}
