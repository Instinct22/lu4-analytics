import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAdminCraftMonitor, updateAdminCraftMonitor } from "../../api/admin";
import { getCraftResources } from "../../api/craft";
import {
  withMasterCoin,
  type ResourceMaterial,
} from "../../lib/craftResources";

const SAVE_DEBOUNCE_MS = 400;
const SELECTION_KEY = ["admin-craft-monitor"] as const;

function ToggleSwitch({
  id,
  checked,
  onChange,
  label,
}: {
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={[
        "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950",
        checked
          ? "bg-gradient-to-r from-amber-500 to-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.35)]"
          : "bg-zinc-700/90 ring-1 ring-inset ring-zinc-600/80",
      ].join(" ")}
    >
      <span
        className={[
          "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-200 ease-out",
          checked ? "translate-x-5" : "translate-x-0",
        ].join(" ")}
      />
    </button>
  );
}

function sectionLabel(section: ResourceMaterial["section"]): string {
  if (section === "currency") return "Валюта";
  return section === "base" ? "Базовый" : "Крафт";
}

export default function CraftMonitorSettings() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const saveTimer = useRef<number | null>(null);

  const resourcesQuery = useQuery({
    queryKey: ["craft-resources"],
    queryFn: getCraftResources,
  });

  const selectionQuery = useQuery({
    queryKey: SELECTION_KEY,
    queryFn: getAdminCraftMonitor,
  });

  const saveMutation = useMutation({
    mutationFn: updateAdminCraftMonitor,
    onSuccess: (data) => {
      queryClient.setQueryData(SELECTION_KEY, data);
      void queryClient.invalidateQueries({ queryKey: ["craft-monitor"] });
      void queryClient.invalidateQueries({ queryKey: ["settings-craft-monitor"] });
    },
  });

  const selectedIds = useMemo(
    () => new Set(selectionQuery.data?.selectedIds ?? []),
    [selectionQuery.data?.selectedIds],
  );

  const materials = useMemo(
    () => withMasterCoin(resourcesQuery.data?.materials ?? []),
    [resourcesQuery.data?.materials],
  );

  const sorted = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? materials.filter(
          (m) =>
            m.name.toLowerCase().includes(q) ||
            String(m.id).includes(q) ||
            sectionLabel(m.section).toLowerCase().includes(q),
        )
      : materials;
    return [...list].sort((a, b) => {
      // Master Coin / currency first, then by name
      if (a.section === "currency" && b.section !== "currency") return -1;
      if (b.section === "currency" && a.section !== "currency") return 1;
      return a.name.localeCompare(b.name, "ru");
    });
  }, [materials, query]);

  const toggleSelected = (materialId: number, selected: boolean) => {
    const current = new Set(
      queryClient.getQueryData<{ selectedIds: number[] }>(SELECTION_KEY)?.selectedIds ?? [],
    );
    if (selected) current.add(materialId);
    else current.delete(materialId);
    const nextIds = [...current].sort((a, b) => a - b);
    queryClient.setQueryData(SELECTION_KEY, { selectedIds: nextIds });

    if (saveTimer.current != null) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      saveMutation.mutate(nextIds);
    }, SAVE_DEBOUNCE_MS);
  };

  const loading = resourcesQuery.isLoading || selectionQuery.isLoading;
  const error = resourcesQuery.isError || selectionQuery.isError;

  return (
    <section className="card space-y-4 !p-0 overflow-hidden">
      <div className="border-b border-zinc-800/80 p-5">
        <h2 className="text-base font-semibold text-zinc-100">Мониторинг крафт-ресурсов</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Выбранные ресурсы показываются на странице «Графики» · {selectedIds.size} из{" "}
          {materials.length}
          {saveMutation.isPending ? " · сохранение…" : ""}
        </p>
        <input
          className="input mt-4"
          placeholder="Поиск по названию или id…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <p className="px-5 py-8 text-sm text-zinc-500">Загрузка…</p>
      ) : error ? (
        <p className="px-5 py-8 text-sm text-red-400">Не удалось загрузить список ресурсов</p>
      ) : (
        <ul className="max-h-[min(28rem,50vh)] divide-y divide-zinc-800/70 overflow-y-auto">
          {sorted.map((material) => {
            const selected = selectedIds.has(material.id);
            const switchId = `craft-mon-${material.id}`;
            return (
              <li key={material.id}>
                <div
                  className={[
                    "flex items-center gap-3 px-4 py-2.5 transition-colors",
                    selected ? "hover:bg-zinc-800/40" : "bg-zinc-950/40 opacity-70 hover:opacity-100",
                  ].join(" ")}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => toggleSelected(material.id, !selected)}
                  >
                    <span
                      className={[
                        "block truncate text-sm font-medium",
                        selected ? "text-zinc-100" : "text-zinc-400",
                      ].join(" ")}
                    >
                      {material.name}
                    </span>
                    <span className="mt-0.5 block text-[0.7rem] text-zinc-500">
                      {sectionLabel(material.section)}
                      {material.grade ? ` · ${material.grade}` : ""} · id {material.id}
                    </span>
                  </button>
                  <ToggleSwitch
                    id={switchId}
                    checked={selected}
                    onChange={(next) => toggleSelected(material.id, next)}
                    label={`${selected ? "Убрать" : "Добавить"} ${material.name}`}
                  />
                </div>
              </li>
            );
          })}
          {sorted.length === 0 && (
            <li className="px-5 py-8 text-center text-sm text-zinc-500">Ничего не найдено</li>
          )}
        </ul>
      )}
    </section>
  );
}
