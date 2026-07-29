import { useMemo, useState } from "react";
import type { CraftResourcesPayload, ResourceEntry } from "../../lib/craftResources";
import { allResources, npcLevelBounds } from "../../lib/craftResources";
import { ItemIcon } from "../craft/CraftCostBar";

interface Props {
  payload: CraftResourcesPayload;
  selectedId: number | null;
  onSelect: (id: number) => void;
  compact?: boolean;
}

function hasFarmSources(entry: ResourceEntry): boolean {
  return entry.material.spoil_count > 0 || entry.material.drop_count > 0;
}

function ResourceChip({
  entry,
  selected,
  onSelect,
}: {
  entry: ResourceEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  const { material } = entry;
  const chipClass = selected
    ? "border-amber-500/80 bg-amber-500/10 ring-2 ring-amber-500/20"
    : "border-zinc-800/80 bg-zinc-900/50 hover:border-amber-500/40 hover:bg-zinc-800/50";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex w-full items-start gap-2.5 rounded-xl border px-3 py-2 text-left transition-all ${chipClass}`}
    >
      <ItemIcon id={material.id} size={36} />
      <span className="min-w-0 flex-1">
        <span className="text-sm font-medium text-zinc-100">{material.name}</span>
        <span className="mt-0.5 flex flex-wrap gap-2 text-[0.65rem] text-zinc-500">
          <span>{material.grade}</span>
          <span className="text-emerald-400/80">S{material.spoil_count}</span>
          <span className="text-amber-400/80">D{material.drop_count}</span>
        </span>
      </span>
    </button>
  );
}

export default function ResourcePicker({ payload, selectedId, onSelect, compact }: Props) {
  const [search, setSearch] = useState("");
  const levels = useMemo(() => npcLevelBounds(payload), [payload]);

  const entries = useMemo(
    () => allResources(payload).filter(hasFarmSources),
    [payload],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return entries;
    return entries.filter(
      (e) => e.material.name.toLowerCase().includes(q) || String(e.material.id).includes(q),
    );
  }, [entries, search]);

  const baseEntries = filtered.filter((e) => e.section === "base");
  const craftEntries = filtered.filter((e) => e.section === "craft");

  return (
    <div className={`panel ${compact ? "p-3" : "p-4"}`}>
      {!compact && (
        <div className="mb-4">
          <h2 className="text-xl font-bold text-zinc-50">Ресурсы крафта</h2>
          <p className="text-sm text-zinc-500">
            {entries.length} материалов · спойл и дроп · монстры {levels.min}–{levels.max} lvl
          </p>
        </div>
      )}

      <input
        type="search"
        placeholder="Поиск ресурса..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="input mb-3"
      />

      <div className="list-scroll space-y-4 pr-1">
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Фарм / спойл ({baseEntries.length})
          </h3>
          <div className="space-y-1.5">
            {baseEntries.map((entry) => (
              <ResourceChip
                key={entry.material.id}
                entry={entry}
                selected={selectedId === entry.material.id}
                onSelect={() => onSelect(entry.material.id)}
              />
            ))}
          </div>
        </section>

        {craftEntries.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-violet-400/80">
              Крафтовые материалы ({craftEntries.length})
            </h3>
            <div className="space-y-1.5">
              {craftEntries.map((entry) => (
                <ResourceChip
                  key={entry.material.id}
                  entry={entry}
                  selected={selectedId === entry.material.id}
                  onSelect={() => onSelect(entry.material.id)}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
