import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createApiToken,
  getApiTokenScopes,
  listApiTokens,
  revokeApiToken,
  type ApiTokenItem,
  type ApiTokenScope,
} from "../../api/admin";
import { ConfirmDialog, LoadingState } from "../ui";
import { copyText } from "../../lib/copyText";

function formatAt(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const SCOPE_LABELS: Record<ApiTokenScope, string> = {
  import: "Импорт",
  market_scan: "Скан рынка",
  trading_scan: "Скан инвентаря",
  raid_life: "Статус жизни РБ",
};

export default function AdminApiTokens() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<ApiTokenScope[]>([]);
  const [expiresAt, setExpiresAt] = useState("");
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiTokenItem | null>(null);

  const tokensQuery = useQuery({
    queryKey: ["admin-api-tokens"],
    queryFn: listApiTokens,
  });

  const scopesQuery = useQuery({
    queryKey: ["admin-api-token-scopes"],
    queryFn: getApiTokenScopes,
  });

  const createMut = useMutation({
    mutationFn: createApiToken,
    onSuccess: (data) => {
      setCreatedToken(data.token);
      setCreateOpen(false);
      setName("");
      setScopes([]);
      setExpiresAt("");
      void qc.invalidateQueries({ queryKey: ["admin-api-tokens"] });
    },
  });

  const revokeMut = useMutation({
    mutationFn: revokeApiToken,
    onSuccess: () => {
      setRevokeTarget(null);
      void qc.invalidateQueries({ queryKey: ["admin-api-tokens"] });
    },
  });

  const scopeOptions = useMemo(
    () => scopesQuery.data?.items ?? [],
    [scopesQuery.data?.items],
  );

  const toggleScope = (scope: ApiTokenScope) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  };

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || scopes.length === 0) return;
    createMut.mutate({
      name: name.trim(),
      scopes,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    });
  };

  if (tokensQuery.isLoading) {
    return <LoadingState label="Загрузка API-токенов…" />;
  }

  if (tokensQuery.isError) {
    return <p className="text-sm text-red-400">Не удалось загрузить API-токены.</p>;
  }

  const items = tokensQuery.data?.items ?? [];
  const legacyConfigured = tokensQuery.data?.legacy_key_configured ?? false;

  return (
    <div className="space-y-4">
      {legacyConfigured && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Legacy-ключ из env (<code className="text-amber-100">IMPORT_API_KEY</code>) активен и даёт
          доступ ко всем scopes. Рекомендуется создать именованные токены и убрать env-ключ после
          миграции.
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-zinc-200">API-токены</h3>
          <p className="mt-1 text-xs text-zinc-500">
            Long-lived ключи для import, market scan и trading scan. Секрет показывается один раз при
            создании.
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setCreateOpen(true)}>
          Создать токен
        </button>
      </div>

      <div className="panel overflow-x-auto">
        <table className="min-w-[44rem] w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800/80 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-4 py-3 font-medium">Имя</th>
              <th className="px-4 py-3 font-medium">Префикс</th>
              <th className="px-4 py-3 font-medium">Scopes</th>
              <th className="px-4 py-3 font-medium">Создан</th>
              <th className="px-4 py-3 font-medium">Использован</th>
              <th className="px-4 py-3 font-medium">Истекает</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/70">
            {items.map((item) => (
              <tr key={item.id} className="text-zinc-300">
                <td className="px-4 py-3 font-medium text-zinc-100">{item.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-zinc-400">{item.token_prefix}…</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {item.scopes.map((scope) => (
                      <span
                        key={scope}
                        className="rounded-md bg-zinc-800/80 px-2 py-0.5 text-[0.65rem] font-medium text-zinc-300"
                      >
                        {SCOPE_LABELS[scope as ApiTokenScope] ?? scope}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-zinc-400">{formatAt(item.created_at)}</td>
                <td className="px-4 py-3 text-xs text-zinc-400">{formatAt(item.last_used_at)}</td>
                <td className="px-4 py-3 text-xs text-zinc-400">{formatAt(item.expires_at)}</td>
                <td className="px-4 py-3">
                  <span
                    className={
                      item.is_active
                        ? "text-emerald-400 text-xs font-medium"
                        : "text-zinc-500 text-xs font-medium"
                    }
                  >
                    {item.is_active ? "Активен" : "Отозван"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {item.is_active && (
                    <button
                      type="button"
                      className="text-xs text-red-400 hover:text-red-300"
                      onClick={() => setRevokeTarget(item)}
                    >
                      Отозвать
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-zinc-500">
                  Токенов пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setCreateOpen(false)}
          role="presentation"
        >
          <form
            className="panel w-full max-w-lg space-y-4 p-6"
            onClick={(e) => e.stopPropagation()}
            onSubmit={onCreate}
          >
            <h3 className="text-lg font-semibold text-zinc-100">Новый API-токен</h3>
            <label className="block space-y-1">
              <span className="text-xs text-zinc-500">Имя</span>
              <input
                className="input w-full"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Import bot prod"
                required
              />
            </label>
            <div className="space-y-2">
              <span className="text-xs text-zinc-500">Scopes</span>
              <div className="space-y-2">
                {scopeOptions.map((opt) => (
                  <label key={opt.scope} className="flex items-start gap-2 text-sm text-zinc-300">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-amber-500"
                      checked={scopes.includes(opt.scope)}
                      onChange={() => toggleScope(opt.scope)}
                    />
                    <span>
                      <span className="font-medium text-zinc-100">{SCOPE_LABELS[opt.scope]}</span>
                      <span className="mt-0.5 block text-xs text-zinc-500">{opt.label}</span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <label className="block space-y-1">
              <span className="text-xs text-zinc-500">Истекает (необязательно)</span>
              <input
                type="datetime-local"
                className="input w-full"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </label>
            {createMut.isError && (
              <p className="text-sm text-red-400">Не удалось создать токен.</p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" className="btn-ghost" onClick={() => setCreateOpen(false)}>
                Отмена
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={createMut.isPending || !name.trim() || scopes.length === 0}
              >
                Создать
              </button>
            </div>
          </form>
        </div>
      )}

      {createdToken && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setCreatedToken(null)}
          role="presentation"
        >
          <div
            className="panel w-full max-w-lg space-y-4 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-zinc-100">Токен создан</h3>
            <p className="text-sm text-amber-300">
              Скопируйте секрет сейчас — больше он не будет показан.
            </p>
            <code className="block break-all rounded-xl border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-xs text-zinc-200">
              {createdToken}
            </code>
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={() => setCreatedToken(null)}>
                Закрыть
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void copyText(createdToken)}
              >
                Скопировать
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={revokeTarget != null}
        title="Отозвать токен?"
        message={
          revokeTarget
            ? `Токен «${revokeTarget.name}» (${revokeTarget.token_prefix}…) перестанет работать.`
            : ""
        }
        confirmLabel="Отозвать"
        tone="danger"
        onCancel={() => setRevokeTarget(null)}
        onConfirm={() => revokeTarget && revokeMut.mutate(revokeTarget.id)}
      />
    </div>
  );
}
