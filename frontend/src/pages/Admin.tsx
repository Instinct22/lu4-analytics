import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createUser,
  deleteUser,
  listLoginLogs,
  listRaidTimerLogs,
  listRolePermissions,
  listUsers,
  updateRolePermissions,
  updateUser,
  type PermissionEntry,
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

const ANALYTICS_PERMISSIONS = ["nav.dashboard", "nav.charts", "nav.statistics"] as const;

const PERMISSION_GROUPS: { id: string; label: string; permissions: readonly string[] }[] = [
  { id: "analytics", label: "Аналитика", permissions: ANALYTICS_PERMISSIONS },
];

const GROUPED_PERMISSIONS = new Set(PERMISSION_GROUPS.flatMap((g) => g.permissions));

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

function formatRaidAction(action: string) {
  return action === "clear" ? "Сброс" : "Установка";
}

export default function AdminPage() {
  const { user, refreshUser } = useAuth();
  const qc = useQueryClient();
  const isPrimaryAdmin = user?.username === "admin";
  const [tab, setTab] = useState<"users" | "roles" | "logins" | "raids">("users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [formError, setFormError] = useState("");
  const [selectedRole, setSelectedRole] = useState<Role>("user");
  const [loginPage, setLoginPage] = useState(1);
  const [raidPage, setRaidPage] = useState(1);
  const [passwordEditId, setPasswordEditId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");

  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: listUsers });
  const rolesQuery = useQuery({ queryKey: ["admin-roles"], queryFn: listRolePermissions });
  const loginLogsQuery = useQuery({
    queryKey: ["admin-login-logs", loginPage],
    queryFn: () => listLoginLogs(loginPage, LOGIN_LOGS_LIMIT),
    enabled: isPrimaryAdmin && tab === "logins",
  });
  const raidLogsQuery = useQuery({
    queryKey: ["admin-raid-timer-logs", raidPage],
    queryFn: () => listRaidTimerLogs(raidPage, LOGIN_LOGS_LIMIT),
    enabled: isPrimaryAdmin && tab === "raids",
  });

  const activeTab =
    (tab === "logins" || tab === "raids") && !isPrimaryAdmin ? "users" : tab;

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

  const permMap = useMemo(() => {
    if (!roleMatrix) return new Map<string, PermissionEntry>();
    return new Map(roleMatrix.permissions.map((p) => [p.permission, p]));
  }, [roleMatrix]);

  const standalonePermissions = useMemo(
    () => roleMatrix?.permissions.filter((p) => !GROUPED_PERMISSIONS.has(p.permission)) ?? [],
    [roleMatrix],
  );

  const applyPermissions = (updates: Record<string, boolean>) => {
    if (!roleMatrix) return;
    const next: Record<string, boolean> = {};
    for (const p of roleMatrix.permissions) {
      next[p.permission] = updates[p.permission] ?? p.allowed;
    }
    rolesMut.mutate({ role: selectedRole, permissions: next });
  };

  const togglePerm = (permission: string, allowed: boolean) => {
    applyPermissions({ [permission]: allowed });
  };

  const toggleGroup = (permissions: readonly string[]) => {
    const allAllowed = permissions.every((perm) => permMap.get(perm)?.allowed);
    const updates = Object.fromEntries(permissions.map((perm) => [perm, !allAllowed]));
    applyPermissions(updates);
  };

  const groupChecked = (permissions: readonly string[]) =>
    permissions.some((perm) => permMap.get(perm)?.allowed);

  const groupIndeterminate = (permissions: readonly string[]) => {
    const allowedCount = permissions.filter((perm) => permMap.get(perm)?.allowed).length;
    return allowedCount > 0 && allowedCount < permissions.length;
  };

  const savePassword = (userId: string) => {
    if (!newPassword.trim()) return;
    updateMut.mutate(
      { id: userId, body: { password: newPassword } },
      {
        onSuccess: () => {
          setPasswordEditId(null);
          setNewPassword("");
        },
      },
    );
  };

  if (usersQuery.isLoading || rolesQuery.isLoading) return <LoadingState />;

  const loginTotal = loginLogsQuery.data?.total ?? 0;
  const loginTotalPages = Math.max(1, Math.ceil(loginTotal / (loginLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)));
  const raidTotal = raidLogsQuery.data?.total ?? 0;
  const raidTotalPages = Math.max(1, Math.ceil(raidTotal / (raidLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)));

  return (
    <div>
      <PageHeader title="Администрирование" />
      <p className="mb-6 -mt-4 text-sm text-zinc-500">
        {isPrimaryAdmin
          ? "Пользователи, права ролей, журнал входов и обновлений таймеров рейдов"
          : "Пользователи и права ролей"}
      </p>
      <div className="mb-6 flex gap-1 rounded-xl bg-zinc-800/80 p-1 w-fit">
        {(
          [
            ["users", "Пользователи"],
            ["roles", "Права ролей"],
            ...(isPrimaryAdmin
              ? ([
                  ["logins", "Входы"],
                  ["raids", "Рейды"],
                ] as const)
              : []),
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
                        <div className="flex flex-wrap items-center gap-2">
                          {passwordEditId === u.id ? (
                            <>
                              <input
                                className="input w-36 py-1.5 text-sm"
                                type="password"
                                placeholder="Новый пароль"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                autoComplete="new-password"
                              />
                              <button
                                type="button"
                                className="text-xs text-amber-400 hover:text-amber-300 disabled:opacity-40"
                                disabled={!newPassword.trim() || updateMut.isPending}
                                onClick={() => savePassword(u.id)}
                              >
                                Сохранить
                              </button>
                              <button
                                type="button"
                                className="text-xs text-zinc-500 hover:text-zinc-300"
                                onClick={() => {
                                  setPasswordEditId(null);
                                  setNewPassword("");
                                }}
                              >
                                Отмена
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="text-xs text-zinc-400 hover:text-zinc-200"
                              onClick={() => {
                                setPasswordEditId(u.id);
                                setNewPassword("");
                              }}
                            >
                              Пароль
                            </button>
                          )}
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
                        </div>
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
          <div className="panel p-5">
            <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-zinc-500">
              Роль
            </label>
            <select
              className="input max-w-xs"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value as Role)}
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="panel p-5">
            <h3 className="mb-1 text-sm font-semibold text-zinc-200">
              Права: {roleMatrix.label}
            </h3>
            <p className="mb-4 text-xs text-zinc-500">
              Включите или отключите доступ к разделам и функциям для этой роли
            </p>
            <div className="space-y-2">
              {PERMISSION_GROUPS.map((group) => {
                const children = group.permissions
                  .map((perm) => permMap.get(perm))
                  .filter((p): p is PermissionEntry => p != null);
                if (children.length === 0) return null;

                const parentChecked = groupChecked(group.permissions);
                const parentIndeterminate = groupIndeterminate(group.permissions);

                return (
                  <div
                    key={group.id}
                    className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/40"
                  >
                    <label className="flex cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:border-zinc-700">
                      <div>
                        <p className="text-sm font-medium text-zinc-200">{group.label}</p>
                        <p className="text-[0.7rem] text-zinc-600">Раздел меню с подпунктами</p>
                      </div>
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-amber-500"
                        checked={parentChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = parentIndeterminate;
                        }}
                        disabled={rolesMut.isPending}
                        onChange={() => toggleGroup(group.permissions)}
                      />
                    </label>
                    <div className="space-y-1 border-t border-zinc-800/80 px-4 py-2">
                      {children.map((p) => (
                        <label
                          key={p.permission}
                          className="flex cursor-pointer items-center justify-between rounded-lg px-3 py-2.5 transition-colors hover:bg-zinc-800/40"
                        >
                          <div className="pl-2">
                            <p className="text-sm text-zinc-300">{p.label ?? p.permission}</p>
                            <p className="text-[0.65rem] text-zinc-600">{p.permission}</p>
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
                );
              })}

              {standalonePermissions.map((p) => (
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
      {activeTab === "raids" && isPrimaryAdmin && (
        <div className="card overflow-hidden p-0">
          <div className="border-b border-zinc-800/80 px-5 py-4">
            <h3 className="text-sm font-semibold text-zinc-200">Журнал таймеров рейдов</h3>
            <p className="mt-1 text-xs text-zinc-500">
              Кто, с какого IP и когда обновил таймер какого рейд-босса
            </p>
          </div>
          {raidLogsQuery.isLoading ? (
            <div className="p-8">
              <LoadingState />
            </div>
          ) : raidLogsQuery.isError ? (
            <p className="px-5 py-8 text-sm text-red-300">Не удалось загрузить журнал рейдов</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                      <th className="px-5 py-3 font-medium">Учётная запись</th>
                      <th className="px-5 py-3 font-medium">IP</th>
                      <th className="px-5 py-3 font-medium">Босс</th>
                      <th className="px-5 py-3 font-medium">Действие</th>
                      <th className="px-5 py-3 font-medium">Время убийства</th>
                      <th className="px-5 py-3 font-medium">Дата и время</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(raidLogsQuery.data?.items ?? []).length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-5 py-8 text-center text-zinc-500">
                          Пока нет записей об обновлениях таймеров
                        </td>
                      </tr>
                    ) : (
                      (raidLogsQuery.data?.items ?? []).map((row) => (
                        <tr key={row.id} className="border-b border-zinc-800/50">
                          <td className="px-5 py-3 font-medium text-zinc-200">{row.username}</td>
                          <td className="px-5 py-3 font-mono text-xs text-zinc-300">
                            {row.ip_address || "—"}
                          </td>
                          <td className="px-5 py-3 text-zinc-200">
                            {row.boss_name}
                            <span className="ml-1.5 text-[0.65rem] text-zinc-500">#{row.boss_external_id}</span>
                          </td>
                          <td className="px-5 py-3">
                            <span
                              className={`rounded-lg px-2 py-0.5 text-xs font-medium ${
                                row.action === "clear"
                                  ? "bg-zinc-800 text-zinc-400"
                                  : "bg-amber-950/60 text-amber-300"
                              }`}
                            >
                              {formatRaidAction(row.action)}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-zinc-300">
                            {row.killed_at ? formatLoginAt(row.killed_at) : "—"}
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
                  {raidTotal.toLocaleString("ru-RU")} записей
                  {raidLogsQuery.isFetching && " · обновление..."}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={raidPage <= 1}
                    onClick={() => setRaidPage((p) => Math.max(1, p - 1))}
                    className="btn-ghost px-2 py-1 disabled:opacity-40"
                  >
                    ←
                  </button>
                  <span>
                    {raidPage} / {raidTotalPages}
                  </span>
                  <button
                    type="button"
                    disabled={raidPage >= raidTotalPages}
                    onClick={() => setRaidPage((p) => p + 1)}
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
