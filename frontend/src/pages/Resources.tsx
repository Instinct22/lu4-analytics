import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import NpcDetailPanel from "../components/resources/NpcDetailPanel";
import ResourceDetail from "../components/resources/ResourceDetail";
import ResourcePicker from "../components/resources/ResourcePicker";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useCraftResources, useMaterialSources, useNpcMaterials } from "../hooks/useCraftResources";
import type { NpcLootProfile, NpcSource } from "../lib/craftResources";
import { findResource, npcLevelBounds } from "../lib/craftResources";
import { isSafeReturnPath, returnLinkFromParam } from "../lib/internalNav";

function parseIdParam(raw: string | null): number | null {
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) ? id : null;
}

function sourceFromNpcId(npcId: number, profile?: NpcLootProfile | null): NpcSource {
  if (profile?.npc_name) {
    return {
      npc_id: profile.npc_id,
      npc_url: profile.npc_url,
      npc_name: profile.npc_name,
      npc_level: profile.npc_level,
      amount: "",
      chance: "",
      chance_val: 0,
      locations: profile.locations,
    };
  }
  return {
    npc_id: npcId,
    npc_url: "",
    npc_name: `NPC #${npcId}`,
    npc_level: "?",
    amount: "",
    chance: "",
    chance_val: 0,
    locations: [],
  };
}

export default function ResourcesPage() {
  const navigate = useNavigate();
  const { data: payload, isLoading, error } = useCraftResources();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedNpc, setSelectedNpc] = useState<NpcSource | null>(null);
  const [minLevel, setMinLevel] = useState<number | null>(null);
  const [maxLevel, setMaxLevel] = useState<number | null>(null);

  const selectedId = useMemo(() => parseIdParam(searchParams.get("id")), [searchParams]);
  const npcParam = useMemo(() => parseIdParam(searchParams.get("npc")), [searchParams]);
  const returnPath = searchParams.get("from");
  const returnLink = useMemo(() => returnLinkFromParam(returnPath), [returnPath]);

  const withFrom = (params: Record<string, string>) => {
    if (isSafeReturnPath(returnPath)) params.from = returnPath;
    return params;
  };

  const levelBounds = useMemo(() => (payload ? npcLevelBounds(payload) : { min: 1, max: 80 }), [payload]);
  const { data: sources, isLoading: sourcesLoading } = useMaterialSources(selectedId);
  const { data: npcFromUrl } = useNpcMaterials(npcParam);

  useEffect(() => {
    if (!payload) return;
    setMinLevel((prev) => (prev == null ? levelBounds.min : Math.max(levelBounds.min, Math.min(prev, levelBounds.max))));
    setMaxLevel((prev) => (prev == null ? levelBounds.max : Math.max(levelBounds.min, Math.min(prev, levelBounds.max))));
  }, [payload, levelBounds.min, levelBounds.max]);

  useEffect(() => {
    if (npcParam == null) {
      setSelectedNpc(null);
      return;
    }
    setSelectedNpc(sourceFromNpcId(npcParam, npcFromUrl ?? null));
  }, [npcParam, npcFromUrl]);

  const selectMaterial = (id: number) => {
    setSearchParams(withFrom({ id: String(id) }), { replace: true });
  };

  const selectNpc = (source: NpcSource) => {
    const next = withFrom({ npc: String(source.npc_id) });
    if (selectedId != null) next.id = String(selectedId);
    setSelectedNpc(source);
    setSearchParams(next, { replace: true });
  };

  const closeMaterial = () => {
    if (returnLink) {
      navigate(returnLink.href);
      return;
    }
    setSearchParams({}, { replace: true });
  };

  const backFromNpc = () => {
    if (selectedId != null) {
      setSearchParams(withFrom({ id: String(selectedId) }), { replace: true });
      return;
    }
    if (returnLink) {
      navigate(returnLink.href);
      return;
    }
    setSearchParams({}, { replace: true });
  };

  if (isLoading) return <LoadingState />;
  if (error || !payload) {
    return (
      <ErrorState message="Данные ресурсов не загружены. Запустите import_datasets.py items_encyclopedia" />
    );
  }

  const selectedEntry = selectedId != null ? findResource(payload, selectedId) : undefined;
  const resolvedMin = minLevel ?? levelBounds.min;
  const resolvedMax = maxLevel ?? levelBounds.max;
  const showNpc = selectedNpc != null && npcParam != null;

  return (
    <div className="min-h-full">
      <PageHeader title="Ресурсы">
        <p className="text-sm text-zinc-500">
          Материалы крафта · спойл и дроп с мобов · {levelBounds.min}–{levelBounds.max} lvl · без рейд-боссов
        </p>
      </PageHeader>

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <div
          className={`shrink-0 transition-all ${
            selectedEntry || showNpc ? "xl:w-[24rem] 2xl:w-[28rem]" : "w-full"
          }`}
        >
          <ResourcePicker
            payload={payload}
            selectedId={selectedId}
            onSelect={selectMaterial}
            compact={!!selectedEntry || showNpc}
          />
        </div>

        {showNpc ? (
          <div className="min-w-0 flex-1">
            <NpcDetailPanel
              source={selectedNpc}
              materialName={selectedEntry?.material.name}
              onBack={backFromNpc}
              onMaterialClick={selectMaterial}
              returnLink={returnLink}
              returnPath={returnPath}
            />
          </div>
        ) : selectedEntry ? (
          <div className="min-w-0 flex-1">
            <ResourceDetail
              entry={selectedEntry}
              sources={sources}
              sourcesLoading={sourcesLoading}
              minLevel={resolvedMin}
              maxLevel={resolvedMax}
              levelBounds={levelBounds}
              onMinLevelChange={setMinLevel}
              onMaxLevelChange={setMaxLevel}
              onNpcSelect={selectNpc}
              onClose={closeMaterial}
              returnLink={returnLink}
            />
          </div>
        ) : (
          <div className="panel hidden flex-1 items-center justify-center border-dashed p-12 xl:flex">
            <div className="max-w-sm text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/80 ring-1 ring-zinc-700/80">
                <span className="text-2xl text-emerald-500">◆</span>
              </div>
              <p className="text-lg font-medium text-zinc-300">Выберите ресурс</p>
              <p className="mt-2 text-sm text-zinc-500">
                Слева — материалы крафта. Справа появятся мобы, с которых они спойлятся и выбиваются.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
