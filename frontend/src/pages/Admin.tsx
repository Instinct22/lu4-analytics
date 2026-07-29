import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createUser,
  deleteUser,
  listLoginLogs,
  listRolePermissions,
  listUsers,
  updateRolePermissions,
  updateUser,
  type RolePermissions,
} from "../api/admin";
import type { Role } from "../api/auth";
import { PageHeader, LoadingState } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "admin", label: "Админ" },
  { value: "user", label: "Пользователь" },
  { value: "driver", label: "Драйвер" },
  { value: "other", label: "Другое" },
];

const LOGIN_LOGS_LIMIT = 25;

function formatLoginAt(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AdminPage() {
  const { user, refreshUser } = useAuth();
  const qc = useQueryClient();
  const isPrimaryAdmin = user?.username === "admin";
  const [tab, setTab] = useState<"users" | "roles" | "logins">("users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [formError, setFormError] = useState("");
  const [selectedRole, setSelectedRole] = useState<Role>("user");
  const [loginPage, setLoginPage] = useState(1);

  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: listUsers });
  const rolesQuery = useQuery({ queryKey: ["admin-roles"], queryFn: listRolePermissions });
  const loginLogsQuery = useQuery({
    queryKey: ["admin-login-logs", loginPage],
    queryFn: () => listLoginLogs(loginPage, LOGIN_LOGS_LIMIT),
    enabled: isPrimaryAdmin && tab === "logins",
  });

  const activeTab = tab === "logins" && !isPrimaryAdmin ? "users" : tab;

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      setUsername("");
      setPassword("");
      setRole("user");
      setFormError("");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => setFormError("Не удалось создать пользователя"),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof updateUser>[1] }) =>
      updateUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const rolesMut = useMutation({
    mutationFn: ({ role, permissions }: { role: Role; permissions: Record<string, boolean> }) =>
      updateRolePermissions(role, permissions),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin-roles"] });
      await refreshUser();
    },
  });

  const roleMatrix: RolePermissions | undefined = useMemo(
    () => rolesQuery.data?.find((r) => r.role === selectedRole),
    [rolesQuery.data, selectedRole],
  );

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!username.trim() || !password) {
      setFormError("Укажите логин и пароль");
      return;
    }
    createMut.mutate({ username: username.trim(), password, role });
  };

  const togglePerm = (permission: string, allowed: boolean) => {
    if (!roleMatrix) return;
    const next: Record<string, boolean> = {};
    for (const p of roleMatrix.permissions) {
      next[p.permission] = p.permission === permission ? allowed : p.allowed;
    }
    rolesMut.mutate({ role: selectedRole, permissions: next });
  };

  if (usersQuery.isLoading || rolesQuery.isLoading) return <LoadingState />;

  const loginTotal = loginLogsQuery.data?.total ?? 0;
  const loginTotalPages = Math.max(1, Math.ceil(loginTotal / (loginLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)));

  return (
    <div>
      <PageHeader title="Администрирование" />
      <p className="mb-6 -mt-4 text-sm text-zinc-500">
        {isPrimaryAdmin ? "Пользователи, права ролей и журнал входов" : "Пользователи и права ролей"}
      </p>
      <div className="mb-6 flex gap-1 rounded-xl bg-zinc-800/80 p-1 w-fit">
        {(
          [
            ["users", "Пользователи"],
            ["roles", "Права ролей"],
            ...(isPrimaryAdmin ? ([["logins", "Входы"]] as const) : []),
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
              activeTab === id
                ? "bg-amber-600 text-zinc-950 shadow-sm"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            }`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "users" && (
        <div className="space-y-6">
          <form onSubmit={onCreate} className="panel space-y-4 p-5 2xl:max-w-5xl">
            <h3 className="text-sm font-semibold text-zinc-200">Новый пользователь</h3>
            <p className="text-xs text-zinc-500">Только логин и пароль — остальное настраивается ролью</p>
            {formError && (
              <p className="rounded-xl border border-red-900/50 bg-red-950/40 px-3 py-2 text-sm text-red-300">
                {formError}
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-4">
              <input
                className="input sm:col-span-1"
                placeholder="Логин"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="off"
              />
              <input
                className="input sm:col-span-1"
                type="password"
                placeholder="Пароль"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
              <select
                className="input sm:col-span-1"
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                {ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <button type="submit" className="btn-primary" disabled={createMut.isPending}>
                Создать
              </button>
            </div>
          </form>

          <div className="card overflow-hidden p-0">
            <div className="border-b border-zinc-800/80 px-5 py-4">
              <h3 className="text-sm font-semibold text-zinc-200">Список пользователей</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                    <th className="px-5 py-3 font-medium">Логин</th>
                    <th className="px-5 py-3 font-medium">Роль</th>
                    <th className="px-5 py-3 font-medium">Статус</th>
                    <th className="px-5 py-3 font-medium">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {(usersQuery.data ?? []).map((u) => (
                    <tr key={u.id} className="border-b border-zinc-800/50">
                      <td className="px-5 py-3 text-zinc-200">
                        {u.username}
                        {u.id === user?.id && (
                          <span className="ml-2 text-[0.65rem] text-amber-400">вы</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <select
                          className="input py-1.5 text-sm"
                          value={u.role}
                          onChange={(e) =>
                            updateMut.mutate({ id: u.id, body: { role: e.target.value as Role } })
                          }
                        >
                          {ROLE_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-3">
                        <button
                          type="button"
                          className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                            u.is_active !== false
                              ? "bg-emerald-950/60 text-emerald-300"
                              : "bg-zinc-800 text-zinc-500"
                          }`}
                          onClick={() =>
                            updateMut.mutate({
                              id: u.id,
                              body: { is_active: u.is_active === false },
                            })
                          }
                          disabled={u.id === user?.id}
                        >
                          {u.is_active !== false ? "Активен" : "Отключён"}
                        </button>
                      </td>
                      <td className="px-5 py-3">
                        <button
                          type="button"
                          className="text-xs text-red-400 hover:text-red-300 disabled:opacity-40"
                          disabled={u.id === user?.id || deleteMut.isPending}
                          onClick={() => {
                            if (confirm(`Удалить пользователя ${u.username}?`)) {
                              deleteMut.mutate(u.id);
                            }
                          }}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "roles" && roleMatrix && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {ROLE_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                className={`rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors ${
                  selectedRole === o.value
                    ? "border-amber-500 bg-amber-600 text-zinc-950"
                    : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-amber-500/50"
                }`}
                onClick={() => setSelectedRole(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>

          <div className="panel p-5">
            <h3 className="mb-1 text-sm font-semibold text-zinc-200">
              Права: {roleMatrix.label}
            </h3>
            <p className="mb-4 text-xs text-zinc-500">
              Включите или отключите доступ к разделам и функциям для этой роли
            </p>
            <div className="space-y-2">
              {roleMatrix.permissions.map((p) => (
                <label
                  key={p.permission}
                  className="flex cursor-pointer items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-3 transition-colors hover:border-zinc-700"
                >
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{p.label ?? p.permission}</p>
                    <p className="text-[0.7rem] text-zinc-600">{p.permission}</p>
                  </div>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-amber-500"
                    checked={p.allowed}
                    disabled={rolesMut.isPending}
                    onChange={(e) => togglePerm(p.permission, e.target.checked)}
                  />
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "logins" && isPrimaryAdmin && (
        <div className="card overflow-hidden p-0">
          <div className="border-b border-zinc-800/80 px-5 py-4">
            <h3 className="text-sm font-semibold text-zinc-200">Журнал входов</h3>
            <p className="mt-1 text-xs text-zinc-500">Кто, когда и с какого IP входил в систему</p>
          </div>
          {loginLogsQuery.isLoading ? (
            <div className="p-8">
              <LoadingState />
            </div>
          ) : loginLogsQuery.isError ? (
            <p className="px-5 py-8 text-sm text-red-300">Не удалось загрузить журнал входов</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                      <th className="px-5 py-3 font-medium">Учётная запись</th>
                      <th className="px-5 py-3 font-medium">IP</th>
                      <th className="px-5 py-3 font-medium">Дата и время</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(loginLogsQuery.data?.items ?? []).length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-5 py-8 text-center text-zinc-500">
                          Пока нет записей о входах
                        </td>
                      </tr>
                    ) : (
                      (loginLogsQuery.data?.items ?? []).map((row) => (
                        <tr key={row.id} className="border-b border-zinc-800/50">
                          <td className="px-5 py-3 font-medium text-zinc-200">{row.username}</td>
                          <td className="px-5 py-3 font-mono text-xs text-zinc-300">
                            {row.ip_address || "—"}
                          </td>
                          <td className="px-5 py-3 text-zinc-300">{formatLoginAt(row.logged_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-800/80 px-5 py-3 text-xs text-zinc-500">
                <span>
                  {loginTotal.toLocaleString("ru-RU")} записей
                  {loginLogsQuery.isFetching && " · обновление..."}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={loginPage <= 1}
                    onClick={() => setLoginPage((p) => Math.max(1, p - 1))}
                    className="btn-ghost px-2 py-1 disabled:opacity-40"
                  >
                    ←
                  </button>
                  <span>
                    {loginPage} / {loginTotalPages}
                  </span>
                  <button
                    type="button"
                    disabled={loginPage >= loginTotalPages}
                    onClick={() => setLoginPage((p) => p + 1)}
                    className="btn-ghost px-2 py-1 disabled:opacity-40"
                  >
                    →
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
