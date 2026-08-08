import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTradingCharacter,
  createTradingSnapshot,
  deleteTradingCharacter,
  getTradingSnapshot,
  listTradingCharacters,
  listTradingSnapshots,
  syncTradingWarehouse,
  type CharacterKind,
  type TradingCharacter,
} from "../api/trading";
import CharacterCard, {
  characterFromSnapshot,
} from "../components/trading-inventory/CharacterCard";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { usePreference } from "../hooks/usePreferences";

function formatSnapshotLabel(iso: string, label: string | null) {
  const d = new Date(iso);
  const when = Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
  return label ? `${when} — ${label}` : when;
}

function Section({
  title,
  kind,
  characters,
  canWrite,
  readOnly,
  showMain,
  canSyncWarehouse,
  onSaved,
  onDelete,
  onCreated,
  onMainChanged,
  onSyncWarehouse,
  syncPending,
  syncError,
  syncHint,
}: {
  title: string;
  kind: CharacterKind;
  characters: TradingCharacter[];
  canWrite: boolean;
  readOnly: boolean;
  showMain?: boolean;
  canSyncWarehouse?: boolean;
  onSaved?: (c: TradingCharacter) => void;
  onDelete?: (id: string) => Promise<void>;
  onCreated?: () => void;
  onMainChanged?: () => void;
  onSyncWarehouse?: () => void;
  syncPending?: boolean;
  syncError?: string;
  syncHint?: string;
}) {
  const [nick, setNick] = useState("");
  const [error, setError] = useState("");
  const createMut = useMutation({
    mutationFn: () => createTradingCharacter({ kind, nick: nick.trim() }),
    onSuccess: () => {
      setNick("");
      setError("");
      onCreated?.();
    },
    onError: () => setError("Не удалось создать персонажа"),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!nick.trim()) {
      setError("Введите ник");
      return;
    }
    createMut.mutate();
  };

  const hasMain = characters.some((c) => c.is_main);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
          <p className="text-xs text-zinc-500">
            {kind === "bank" ? "Накопления и ресурсы" : "Торговцы с личным инвентарём"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {kind === "bank" && canSyncWarehouse && !readOnly ? (
            <button
              type="button"
              className="btn-ghost"
              disabled={syncPending || !hasMain}
              title={
                hasMain
                  ? "Заменить склад предметами, аденой и MC из Main"
                  : "Сначала отметьте Main у персонажа банка"
              }
              onClick={onSyncWarehouse}
            >
              {syncPending ? "Синхронизация…" : "Синхронизировать со складом"}
            </button>
          ) : null}
          {canWrite && !readOnly ? (
            <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
              <input
                className="input w-44"
                placeholder="Ник"
                value={nick}
                onChange={(e) => setNick(e.target.value)}
              />
              <button type="submit" className="btn-primary" disabled={createMut.isPending}>
                Добавить
              </button>
            </form>
          ) : null}
        </div>
      </div>
      {kind === "bank" && syncError ? <p className="text-sm text-rose-400">{syncError}</p> : null}
      {kind === "bank" && syncHint ? <p className="text-sm text-emerald-400">{syncHint}</p> : null}
      {error ? <p className="text-sm text-rose-400">{error}</p> : null}
      {characters.length === 0 ? (
        <div className="card text-sm text-zinc-500">Пока нет персонажей</div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {characters.map((character) => (
            <CharacterCard
              key={character.id}
              character={character}
              canWrite={canWrite}
              readOnly={readOnly}
              showMain={Boolean(showMain)}
              onSaved={onSaved}
              onDeleteRequest={onDelete}
              onMainChanged={onMainChanged}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default function TradingPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("feature.trading_write");
  const canWarehouse = hasPermission("feature.craft_warehouse");
  const canSyncWarehouse = canWrite && canWarehouse;
  const qc = useQueryClient();
  const [, , replaceOwned] = usePreference("craft_owned");
  const [snapshotId, setSnapshotId] = useState<string>("");
  const [syncError, setSyncError] = useState("");
  const [syncHint, setSyncHint] = useState("");

  const charactersQuery = useQuery({
    queryKey: ["trading-characters"],
    queryFn: listTradingCharacters,
  });

  const snapshotsQuery = useQuery({
    queryKey: ["trading-snapshots"],
    queryFn: listTradingSnapshots,
  });

  const snapshotQuery = useQuery({
    queryKey: ["trading-snapshot", snapshotId],
    queryFn: () => getTradingSnapshot(snapshotId),
    enabled: Boolean(snapshotId),
  });

  const snapshotMut = useMutation({
    mutationFn: () => createTradingSnapshot(),
    onSuccess: async (snap) => {
      await qc.invalidateQueries({ queryKey: ["trading-snapshots"] });
      setSnapshotId(snap.id);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteTradingCharacter,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-characters"] }),
  });

  const syncMut = useMutation({
    mutationFn: () => syncTradingWarehouse("to_warehouse"),
    onSuccess: async (result) => {
      setSyncError("");
      setSyncHint(
        `Склад обновлён из ${result.character_nick}: ${result.item_count} поз., ` +
          `${Math.round(Number(result.adena) || 0)} а, ${Math.round(Number(result.master_coin) || 0)} MC`,
      );
      await replaceOwned(result.warehouse ?? {});
    },
    onError: (err: unknown) => {
      setSyncHint("");
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setSyncError(
        typeof detail === "string" ? detail : "Не удалось синхронизировать со складом",
      );
    },
  });

  const viewingSnapshot = Boolean(snapshotId);
  const liveCharacters = charactersQuery.data?.characters ?? [];

  const characters: TradingCharacter[] = useMemo(() => {
    if (!viewingSnapshot) return liveCharacters;
    const rows = snapshotQuery.data?.payload?.characters ?? [];
    return rows.map((row, idx) => characterFromSnapshot(row, idx));
  }, [viewingSnapshot, liveCharacters, snapshotQuery.data]);

  const banks = characters.filter((c) => c.kind === "bank");
  const merchants = characters.filter((c) => c.kind === "merchant");

  const refreshCharacters = () => {
    void qc.invalidateQueries({ queryKey: ["trading-characters"] });
  };

  if (charactersQuery.isLoading) return <LoadingState />;
  if (charactersQuery.isError) {
    return <ErrorState message="Не удалось загрузить персонажей торговли" />;
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Торговля">
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-zinc-400">
            <span className="shrink-0">Снимок</span>
            <select
              className="input w-56"
              value={snapshotId}
              onChange={(e) => setSnapshotId(e.target.value)}
            >
              <option value="">Текущее</option>
              {(snapshotsQuery.data?.snapshots ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {formatSnapshotLabel(s.created_at, s.label)}
                </option>
              ))}
            </select>
          </label>
          {canWrite ? (
            <button
              type="button"
              className="btn-primary"
              disabled={snapshotMut.isPending || viewingSnapshot}
              title={viewingSnapshot ? "Вернитесь к текущему состоянию" : undefined}
              onClick={() => snapshotMut.mutate()}
            >
              {snapshotMut.isPending ? "Снимок…" : "Сделать снимок"}
            </button>
          ) : null}
        </div>
      </PageHeader>

      {viewingSnapshot ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Просмотр снимка
          {snapshotQuery.data
            ? ` от ${formatSnapshotLabel(snapshotQuery.data.created_at, snapshotQuery.data.label)}`
            : "…"}
          . Данные только для чтения.
          <button
            type="button"
            className="ml-3 text-amber-200 underline hover:text-white"
            onClick={() => setSnapshotId("")}
          >
            К текущему
          </button>
        </div>
      ) : null}

      {viewingSnapshot && snapshotQuery.isLoading ? <LoadingState /> : null}
      {viewingSnapshot && snapshotQuery.isError ? (
        <ErrorState message="Не удалось загрузить снимок" />
      ) : null}

      {!(viewingSnapshot && (snapshotQuery.isLoading || snapshotQuery.isError)) ? (
        <>
          <Section
            title="Банк"
            kind="bank"
            characters={banks}
            canWrite={canWrite}
            readOnly={viewingSnapshot}
            showMain={canSyncWarehouse && !viewingSnapshot}
            canSyncWarehouse={canSyncWarehouse && !viewingSnapshot}
            onSaved={refreshCharacters}
            onCreated={refreshCharacters}
            onMainChanged={refreshCharacters}
            onSyncWarehouse={() => {
              if (
                !window.confirm(
                  "Заменить весь склад предметами, аденой и Master Coin из Main? Старый склад будет удалён.",
                )
              ) {
                return;
              }
              setSyncError("");
              setSyncHint("");
              syncMut.mutate();
            }}
            syncPending={syncMut.isPending}
            syncError={syncError}
            syncHint={syncHint}
            onDelete={async (id) => {
              await deleteMut.mutateAsync(id);
            }}
          />
          <Section
            title="Торговцы"
            kind="merchant"
            characters={merchants}
            canWrite={canWrite}
            readOnly={viewingSnapshot}
            onSaved={refreshCharacters}
            onCreated={refreshCharacters}
            onDelete={async (id) => {
              await deleteMut.mutateAsync(id);
            }}
          />
        </>
      ) : null}
    </div>
  );
}
