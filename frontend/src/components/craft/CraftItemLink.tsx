import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useCraftResources } from "../../hooks/useCraftResources";
import type { CraftCatalog } from "../../lib/craftCalc";
import { farmResourceIds } from "../../lib/craftResources";
import { itemPagePath, resourcePagePath } from "../../lib/internalNav";

interface Props {
  id: number;
  name: string;
  catalog: CraftCatalog;
  className?: string;
}

export default function CraftItemLink({ id, name, catalog, className }: Props) {
  const { hasPermission } = useAuth();
  const canOpenResources = hasPermission("nav.resources");
  const { data: resourcesPayload } = useCraftResources({
    enabled: canOpenResources && catalog.farmMaterialIds == null,
  });
  const farmSet = useMemo(() => {
    if (catalog.farmMaterialIds) return new Set(catalog.farmMaterialIds);
    if (resourcesPayload) return farmResourceIds(resourcesPayload);
    return new Set<number>();
  }, [catalog.farmMaterialIds, resourcesPayload]);

  const hasResourceLink = canOpenResources && farmSet.has(id);
  const to = hasResourceLink ? resourcePagePath(id) : itemPagePath(id);
  const title = hasResourceLink
    ? "Спойл и дроп на вкладке «Ресурсы»"
    : "Энциклопедия предметов";

  return (
    <Link
      to={to}
      title={title}
      className={
        className ??
        "break-words font-semibold text-zinc-100 hover:text-amber-400 hover:underline"
      }
    >
      {name}
    </Link>
  );
}
