import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCustomRole,
  createUser,
  deleteCustomRole,
  deleteUser,
  getPublicRoles,
  listCustomRoles,
  listLoginLogs,
  listRaidTimerLogs,
  listRolePermissions,
  listUserCreationLogs,
  listUsers,
  quickCreateUser,
  updatePublicRoles,
  updateRolePermissions,
  updateUser,
  type PermissionEntry,
  type RolePermissions,
} from "../api/admin";
import type { Role } from "../api/auth";
import { PageHeader, LoadingState } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

const FALLBACK_PERMISSION_GROUPS = [
  {
    id: "analytics",
    label: "Аналитика",
    permissions: ["nav.dashboard", "nav.charts", "nav.statistics"],
  },
  {
    id: "raid",
    label: "Рейд-боссы",
    permissions: [
      "nav.raid_bosses",
      "feature.raid_timers_view",
      "feature.raid_route",
      "feature.raid_timers_write",
      "feature.raid_visibility",
      "feature.level_unrestricted",
    ],
  },
  {
    id: "craft",
    label: "Крафт",
    permissions: [
      "nav.craft",
      "feature.craft_prices",
      "feature.craft_bulk",
      "feature.craft_warehouse",
    ],
  },
  {
    id: "administration",
    label: "Администрирование",
    permissions: ["nav.admin", "admin.users_quick_create", "admin.roles_manage", "admin.logs_view", "admin.level_preset", "admin.level_restriction"],
  },
] as const;

const BUILTIN_ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "admin", label: "Админ" },
  { value: "user", label: "Пользователь" },
  { value: "driver", label: "Драйвер" },
  { value: "other", label: "Другое" },
];

const LOGIN_LOGS_LIMIT = 25;

const PRESET_ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "user", label: "Пользователь" },
  { value: "driver", label: "Драйвер" },
  { value: "other", label: "Другое" },
  { value: "admin", label: "Админ" },
];

/** Permission cannot be enabled unless its prerequisite is enabled. */
const PERMISSION_REQUIRES: Record<string, string> = {
  "feature.raid_timers_write": "feature.raid_timers_view",
  "feature.raid_visibility": "nav.raid_bosses",
};

function applyPermissionRules(draft: Record<string, boolean>): Record<string, boolean> {
  const next = { ...draft };
  for (const [perm, required] of Object.entries(PERMISSION_REQUIRES)) {
    if (next[perm] && !next[required]) {
      next[required] = true;
    }
  }
  for (const [perm, required] of Object.entries(PERMISSION_REQUIRES)) {
    if (!next[required]) {
      next[perm] = false;
    }
  }
  return next;
}

function isPermissionDisabled(permission: string, draft: Record<string, boolean>): boolean {
  const required = PERMISSION_REQUIRES[permission];
  return Boolean(required && !draft[required]);
}

type AdminTab = "users" | "roles" | "publicRoles" | "customRoles" | "logs";
type LogSubTab = "logins" | "raids" | "creations";

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
  const { user, refreshUser, hasPermission, isSuperadmin } = useAuth();
  const qc = useQueryClient();
  const canManageRoles = hasPermission("admin.roles_manage");
  const canViewLogs = hasPermission("admin.logs_view");
  const canQuickCreate = hasPermission("admin.users_quick_create");
  const [tab, setTab] = useState<AdminTab>("users");
  const [logSubTab, setLogSubTab] = useState<LogSubTab>("logins");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [formError, setFormError] = useState("");
  const [selectedRole, setSelectedRole] = useState<Role>("user");
  const [loginPage, setLoginPage] = useState(1);
  const [raidPage, setRaidPage] = useState(1);
  const [creationPage, setCreationPage] = useState(1);
  const [passwordEditId, setPasswordEditId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [quickCreateOpen, setQuickCreateOpen] = useState(false);
  const [quickCreateResult, setQuickCreateResult] = useState<{
    username: string;
    password: string;
  } | null>(null);
  const [publicRolesDraft, setPublicRolesDraft] = useState<Role[]>([]);
  const [customRoleLabel, setCustomRoleLabel] = useState("");
  const [customRolePreset, setCustomRolePreset] = useState<Role>("user");
  const [customRoleError, setCustomRoleError] = useState("");
  const [permDraft, setPermDraft] = useState<Record<string, boolean>>({});
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [permSaveMessage, setPermSaveMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: listUsers });
  const rolesQuery = useQuery({
    queryKey: ["admin-roles"],
    queryFn: listRolePermissions,
    enabled: canManageRoles,
  });
  const publicRolesQuery = useQuery({
    queryKey: ["admin-public-roles"],
    queryFn: getPublicRoles,
    enabled: isSuperadmin,
  });
  const customRolesQuery = useQuery({
    queryKey: ["admin-custom-roles"],
    queryFn: listCustomRoles,
    enabled: isSuperadmin,
  });
  const loginLogsQuery = useQuery({
    queryKey: ["admin-login-logs", loginPage],
    queryFn: () => listLoginLogs(loginPage, LOGIN_LOGS_LIMIT),
    enabled: canViewLogs && tab === "logs" && logSubTab === "logins",
  });
  const raidLogsQuery = useQuery({
    queryKey: ["admin-raid-timer-logs", raidPage],
    queryFn: () => listRaidTimerLogs(raidPage, LOGIN_LOGS_LIMIT),
    enabled: canViewLogs && tab === "logs" && logSubTab === "raids",
  });
  const creationLogsQuery = useQuery({
    queryKey: ["admin-user-creation-logs", creationPage],
    queryFn: () => listUserCreationLogs(creationPage, LOGIN_LOGS_LIMIT),
    enabled: canViewLogs && tab === "logs" && logSubTab === "creations",
  });

  const allRoleOptions = useMemo(() => {
    const custom =
      customRolesQuery.data?.items.map((r) => ({ value: r.key as Role, label: r.label })) ?? [];
    return [...BUILTIN_ROLE_OPTIONS, ...custom];
  }, [customRolesQuery.data?.items]);

  const roleOptions = useMemo(() => {
    if (isSuperadmin) return allRoleOptions;
    const roles = publicRolesQuery.data?.roles ?? ["user", "driver", "other"];
    return allRoleOptions.filter((o) => roles.includes(o.value));
  }, [isSuperadmin, publicRolesQuery.data?.roles, allRoleOptions]);

  const matrixRoleOptions = useMemo(
    () =>
      rolesQuery.data?.map((r) => ({ value: r.role as Role, label: r.label })) ??
      BUILTIN_ROLE_OPTIONS.filter((o) => o.value !== "superadmin"),
    [rolesQuery.data],
  );

  const permissionGroups = FALLBACK_PERMISSION_GROUPS;

  const groupedPermissions = useMemo(
    () => new Set(permissionGroups.flatMap((g) => g.permissions)),
    [permissionGroups],
  );

  const activeTab = useMemo(() => {
    if ((tab === "roles" || tab === "publicRoles" || tab === "customRoles") && !isSuperadmin) {
      return canManageRoles && tab === "roles" ? "roles" : "users";
    }
    if (tab === "logs" && !canViewLogs) return "users";
    if (tab === "roles" && !canManageRoles) return "users";
    return tab;
  }, [tab, isSuperadmin, canManageRoles, canViewLogs]);

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

  const quickCreateMut = useMutation({
    mutationFn: (r: Role) => quickCreateUser(r),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const publicRolesMut = useMutation({
    mutationFn: updatePublicRoles,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-public-roles"] }),
  });

  const customRoleCreateMut = useMutation({
    mutationFn: createCustomRole,
    onSuccess: () => {
      setCustomRoleLabel("");
      setCustomRolePreset("user");
      setCustomRoleError("");
      qc.invalidateQueries({ queryKey: ["admin-custom-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-public-roles"] });
    },
    onError: () => setCustomRoleError("Не удалось создать роль"),
  });

  const customRoleDeleteMut = useMutation({
    mutationFn: deleteCustomRole,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-custom-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-public-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const roleMatrix: RolePermissions | undefined = useMemo(
    () => rolesQuery.data?.find((r) => r.role === selectedRole),
    [rolesQuery.data, selectedRole],
  );

  useEffect(() => {
    if (!roleMatrix) {
      setPermDraft({});
      return;
    }
    const draft: Record<string, boolean> = {};
    for (const p of roleMatrix.permissions) {
      draft[p.permission] = p.allowed;
    }
    setPermDraft(applyPermissionRules(draft));
    setPermSaveMessage(null);
  }, [roleMatrix, selectedRole]);

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!username.trim() || !password) {
      setFormError("Укажите логин и пароль");
      return;
    }
    createMut.mutate({ username: username.trim(), password, role });
  };

  const permDirty = useMemo(() => {
    if (!roleMatrix) return false;
    return roleMatrix.permissions.some((p) => permDraft[p.permission] !== p.allowed);
  }, [roleMatrix, permDraft]);

  const standalonePermissions = useMemo(() => {
    if (!roleMatrix) return [];
    return roleMatrix.permissions
      .filter((p) => !groupedPermissions.has(p.permission))
      .map((p) => ({ ...p, allowed: permDraft[p.permission] ?? p.allowed }));
  }, [roleMatrix, groupedPermissions, permDraft]);

  const togglePerm = (permission: string, allowed: boolean) => {
    if (allowed && isPermissionDisabled(permission, permDraft)) return;
    setPermDraft((prev) => applyPermissionRules({ ...prev, [permission]: allowed }));
    setPermSaveMessage(null);
  };

  const toggleGroup = (permissions: readonly string[]) => {
    const allAllowed = permissions.every((perm) => permDraft[perm]);
    const updates = Object.fromEntries(permissions.map((perm) => [perm, !allAllowed]));
    setPermDraft((prev) => applyPermissionRules({ ...prev, ...updates }));
    setPermSaveMessage(null);
  };

  const toggleGroupExpanded = (groupId: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  const savePermissions = () => {
    if (!roleMatrix || !permDirty) return;
    rolesMut.mutate(
      { role: selectedRole, permissions: applyPermissionRules(permDraft) },
      {
        onSuccess: () => {
          setPermSaveMessage({ type: "success", text: "Права успешно сохранены" });
        },
        onError: () => {
          setPermSaveMessage({ type: "error", text: "Не удалось сохранить права" });
        },
      },
    );
  };

  const groupChecked = (permissions: readonly string[]) =>
    permissions.some((perm) => permDraft[perm]);

  const groupIndeterminate = (permissions: readonly string[]) => {
    const allowedCount = permissions.filter((perm) => permDraft[perm]).length;
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

  if (usersQuery.isLoading || (canManageRoles && rolesQuery.isLoading)) return <LoadingState />;

  const creationTotal = creationLogsQuery.data?.total ?? 0;
  const creationTotalPages = Math.max(
    1,
    Math.ceil(creationTotal / (creationLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)),
  );

  const copyCredentials = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
    }
  };

  const tabButtons: { id: AdminTab; label: string; show: boolean }[] = [
    { id: "users", label: "Пользователи", show: true },
    { id: "roles", label: "Права ролей", show: canManageRoles },
    { id: "publicRoles", label: "Публичные роли", show: isSuperadmin },
    { id: "customRoles", label: "Создание ролей", show: isSuperadmin },
    { id: "logs", label: "Журналы", show: canViewLogs },
  ];
  const loginTotal = loginLogsQuery.data?.total ?? 0;
  const loginTotalPages = Math.max(1, Math.ceil(loginTotal / (loginLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)));
  const raidTotal = raidLogsQuery.data?.total ?? 0;
  const raidTotalPages = Math.max(1, Math.ceil(raidTotal / (raidLogsQuery.data?.limit ?? LOGIN_LOGS_LIMIT)));

  return (
    <div>
      <PageHeader title="Администрирование" />
      <p className="mb-6 -mt-4 text-sm text-zinc-500">
        {isSuperadmin
          ? "Полное управление пользователями, правами, настройками и журналами"
          : canManageRoles
            ? "Пользователи и права ролей"
            : "Управление созданными пользователями"}
      </p>
      <div className="mb-6 flex flex-wrap gap-1 rounded-xl bg-zinc-800/80 p-1 w-fit">
        {tabButtons
          .filter((t) => t.show)
          .map(({ id, label }) => (
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
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-zinc-200">Новый пользователь</h3>
              {canQuickCreate && (
                <button
                  type="button"
                  className="btn-ghost text-xs text-amber-400"
                  onClick={() => {
                    setQuickCreateResult(null);
                    quickCreateMut.mutate(role, {
                      onSuccess: (data) => {
                        setQuickCreateOpen(true);
                        setQuickCreateResult({ username: data.username, password: data.password });
                      },
                    });
                  }}
                  disabled={quickCreateMut.isPending}
                >
                  Быстрое создание
                </button>
              )}
            </div>
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
                {roleOptions.map((o) => (
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
                          {roleOptions.map((o) => (
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
              {matrixRoleOptions.map((o) => (
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
              {permissionGroups.map((group) => {
                const children = group.permissions
                  .map((perm) => {
                    const meta = roleMatrix.permissions.find((p) => p.permission === perm);
                    if (!meta) return null;
                    return { ...meta, allowed: permDraft[perm] ?? meta.allowed };
                  })
                  .filter((p): p is PermissionEntry => p != null);
                if (children.length === 0) return null;

                const parentChecked = groupChecked(group.permissions);
                const parentIndeterminate = groupIndeterminate(group.permissions);
                const expanded = expandedGroups[group.id] ?? false;

                return (
                  <div
                    key={group.id}
                    className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/40"
                  >
                    <div className="flex items-center justify-between px-4 py-3 transition-colors hover:border-zinc-700">
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        onClick={() => toggleGroupExpanded(group.id)}
                      >
                        <span
                          className={`inline-block text-xs text-zinc-500 transition-transform ${expanded ? "rotate-90" : ""}`}
                          aria-hidden
                        >
                          ▶
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-zinc-200">{group.label}</p>
                          <p className="text-[0.7rem] text-zinc-600">
                            {expanded ? "Скрыть права раздела" : "Показать права раздела"}
                          </p>
                        </div>
                      </button>
                      <input
                        type="checkbox"
                        className="ml-3 h-4 w-4 shrink-0 accent-amber-500"
                        checked={parentChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = parentIndeterminate;
                        }}
                        onChange={() => toggleGroup(group.permissions)}
                      />
                    </div>
                    {expanded && (
                      <div className="space-y-1 border-t border-zinc-800/80 px-4 py-2">
                        {children.map((p) => {
                          const disabled = isPermissionDisabled(p.permission, permDraft);
                          const requiredPerm = PERMISSION_REQUIRES[p.permission];
                          const requiredLabel = requiredPerm
                            ? roleMatrix.permissions.find((x) => x.permission === requiredPerm)?.label
                            : null;
                          return (
                          <label
                            key={p.permission}
                            className={`flex items-center justify-between rounded-lg px-3 py-2.5 transition-colors ${
                              disabled
                                ? "cursor-not-allowed opacity-50"
                                : "cursor-pointer hover:bg-zinc-800/40"
                            }`}
                            title={
                              disabled && requiredLabel
                                ? `Сначала включите «${requiredLabel}»`
                                : undefined
                            }
                          >
                            <div className="pl-2">
                              <p className="text-sm text-zinc-300">{p.label ?? p.permission}</p>
                              <p className="text-[0.65rem] text-zinc-600">{p.permission}</p>
                              {disabled && requiredLabel && (
                                <p className="text-[0.65rem] text-zinc-500">
                                  Требуется: {requiredLabel}
                                </p>
                              )}
                            </div>
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-amber-500 disabled:cursor-not-allowed"
                              checked={p.allowed}
                              disabled={disabled}
                              onChange={(e) => togglePerm(p.permission, e.target.checked)}
                            />
                          </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {standalonePermissions.map((p) => {
                const disabled = isPermissionDisabled(p.permission, permDraft);
                const requiredPerm = PERMISSION_REQUIRES[p.permission];
                const requiredLabel = requiredPerm
                  ? roleMatrix.permissions.find((x) => x.permission === requiredPerm)?.label
                  : null;
                return (
                <label
                  key={p.permission}
                  className={`flex items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-3 transition-colors ${
                    disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:border-zinc-700"
                  }`}
                  title={
                    disabled && requiredLabel ? `Сначала включите «${requiredLabel}»` : undefined
                  }
                >
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{p.label ?? p.permission}</p>
                    <p className="text-[0.7rem] text-zinc-600">{p.permission}</p>
                    {disabled && requiredLabel && (
                      <p className="text-[0.65rem] text-zinc-500">Требуется: {requiredLabel}</p>
                    )}
                  </div>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-amber-500 disabled:cursor-not-allowed"
                    checked={p.allowed}
                    disabled={disabled}
                    onChange={(e) => togglePerm(p.permission, e.target.checked)}
                  />
                </label>
                );
              })}
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-zinc-800/80 pt-4">
              <button
                type="button"
                className="btn-primary"
                disabled={!permDirty || rolesMut.isPending}
                onClick={savePermissions}
              >
                {rolesMut.isPending ? "Сохранение…" : "Сохранить права"}
              </button>
              {permDirty && !rolesMut.isPending && (
                <span className="text-xs text-amber-400">Есть несохранённые изменения</span>
              )}
              {permSaveMessage && (
                <span
                  className={`text-sm ${permSaveMessage.type === "success" ? "text-emerald-400" : "text-red-300"}`}
                >
                  {permSaveMessage.text}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "logs" && canViewLogs && (
        <div className="space-y-4">
          <div className="flex gap-1 rounded-xl bg-zinc-800/80 p-1 w-fit">
            {(
              [
                ["logins", "Входы"],
                ["raids", "Рейды"],
                ["creations", "Создание пользователей"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                  logSubTab === id
                    ? "bg-amber-600 text-zinc-950"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
                onClick={() => setLogSubTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {logSubTab === "logins" && (
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

          {logSubTab === "raids" && (
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

          {logSubTab === "creations" && (
            <div className="card overflow-hidden p-0">
              <div className="border-b border-zinc-800/80 px-5 py-4">
                <h3 className="text-sm font-semibold text-zinc-200">Создание пользователей</h3>
                <p className="mt-1 text-xs text-zinc-500">Кто создал учётную запись, роль и IP</p>
              </div>
              {creationLogsQuery.isLoading ? (
                <div className="p-8">
                  <LoadingState />
                </div>
              ) : creationLogsQuery.isError ? (
                <p className="px-5 py-8 text-sm text-red-300">Не удалось загрузить журнал</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                          <th className="px-5 py-3 font-medium">Создал</th>
                          <th className="px-5 py-3 font-medium">Пользователь</th>
                          <th className="px-5 py-3 font-medium">Роль</th>
                          <th className="px-5 py-3 font-medium">IP</th>
                          <th className="px-5 py-3 font-medium">Дата</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(creationLogsQuery.data?.items ?? []).map((row) => (
                          <tr key={row.id} className="border-b border-zinc-800/50">
                            <td className="px-5 py-3 text-zinc-200">{row.creator_username}</td>
                            <td className="px-5 py-3 text-zinc-200">{row.created_username}</td>
                            <td className="px-5 py-3 text-zinc-400">{row.role}</td>
                            <td className="px-5 py-3 font-mono text-xs text-zinc-300">
                              {row.ip_address || "—"}
                            </td>
                            <td className="px-5 py-3 text-zinc-300">{formatLoginAt(row.logged_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="flex items-center justify-between border-t border-zinc-800/80 px-5 py-3 text-xs text-zinc-500">
                    <span>{creationTotal.toLocaleString("ru-RU")} записей</span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={creationPage <= 1}
                        onClick={() => setCreationPage((p) => Math.max(1, p - 1))}
                        className="btn-ghost px-2 py-1 disabled:opacity-40"
                      >
                        ←
                      </button>
                      <span>
                        {creationPage} / {creationTotalPages}
                      </span>
                      <button
                        type="button"
                        disabled={creationPage >= creationTotalPages}
                        onClick={() => setCreationPage((p) => p + 1)}
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
      )}

      {activeTab === "publicRoles" && isSuperadmin && (
        <div className="panel max-w-lg space-y-4 p-5">
          <h3 className="text-sm font-semibold text-zinc-200">Публичные роли для админов</h3>
          <p className="text-xs text-zinc-500">
            Админы могут создавать пользователей только с этими ролями
          </p>
          <div className="space-y-2">
            {allRoleOptions.filter((o) => o.value !== "admin" && o.value !== "superadmin").map(
              (o) => {
                const draft =
                  publicRolesDraft.length > 0
                    ? publicRolesDraft
                    : (publicRolesQuery.data?.roles ?? ["user", "driver", "other"]);
                const checked = draft.includes(o.value);
                return (
                  <label
                    key={o.value}
                    className="flex cursor-pointer items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-3"
                  >
                    <span className="text-sm text-zinc-200">{o.label}</span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-amber-500"
                      checked={checked}
                      onChange={() => {
                        const base =
                          publicRolesDraft.length > 0
                            ? publicRolesDraft
                            : (publicRolesQuery.data?.roles ?? ["user", "driver", "other"]);
                        setPublicRolesDraft(
                          checked ? base.filter((r) => r !== o.value) : [...base, o.value],
                        );
                      }}
                    />
                  </label>
                );
              },
            )}
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={publicRolesMut.isPending}
            onClick={() => {
              const roles =
                publicRolesDraft.length > 0
                  ? publicRolesDraft
                  : (publicRolesQuery.data?.roles ?? ["user", "driver", "other"]);
              publicRolesMut.mutate(roles);
            }}
          >
            Сохранить
          </button>
        </div>
      )}

      {activeTab === "customRoles" && isSuperadmin && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            className="panel space-y-4 p-5"
            onSubmit={(e) => {
              e.preventDefault();
              setCustomRoleError("");
              if (!customRoleLabel.trim()) {
                setCustomRoleError("Укажите название роли");
                return;
              }
              customRoleCreateMut.mutate({
                label: customRoleLabel.trim(),
                preset_role: customRolePreset,
              });
            }}
          >
            <h3 className="text-sm font-semibold text-zinc-200">Новая роль</h3>
            <p className="text-xs text-zinc-500">
              Укажите название и выберите пресет прав из существующих ролей
            </p>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Название</label>
              <input
                className="input w-full"
                value={customRoleLabel}
                onChange={(e) => setCustomRoleLabel(e.target.value)}
                placeholder="Например: Модератор"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-500">Пресет прав</label>
              <select
                className="input w-full"
                value={customRolePreset}
                onChange={(e) => setCustomRolePreset(e.target.value as Role)}
              >
                {PRESET_ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            {customRoleError && <p className="text-sm text-red-300">{customRoleError}</p>}
            <button type="submit" className="btn-primary" disabled={customRoleCreateMut.isPending}>
              Сохранить роль
            </button>
          </form>

          <div className="panel space-y-4 p-5">
            <h3 className="text-sm font-semibold text-zinc-200">Созданные роли</h3>
            {(customRolesQuery.data?.items ?? []).length === 0 ? (
              <p className="text-sm text-zinc-500">Пока нет пользовательских ролей</p>
            ) : (
              <ul className="space-y-2">
                {(customRolesQuery.data?.items ?? []).map((role) => (
                  <li
                    key={role.key}
                    className="flex items-center justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-zinc-200">{role.label}</p>
                      <p className="text-xs text-zinc-500">{role.key}</p>
                    </div>
                    <button
                      type="button"
                      className="text-xs text-red-400 hover:text-red-300"
                      disabled={customRoleDeleteMut.isPending}
                      onClick={() => {
                        if (window.confirm(`Удалить роль «${role.label}»?`)) {
                          customRoleDeleteMut.mutate(role.key);
                        }
                      }}
                    >
                      Удалить
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {quickCreateOpen && quickCreateResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="panel w-full max-w-md space-y-4 p-6">
            <h3 className="text-lg font-semibold text-zinc-100">Учётная запись создана</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between gap-2 rounded-lg bg-zinc-900/60 px-3 py-2">
                <span className="text-zinc-400">Логин</span>
                <span className="font-mono text-zinc-100">{quickCreateResult.username}</span>
                <button
                  type="button"
                  className="text-xs text-amber-400"
                  onClick={() => copyCredentials(quickCreateResult.username)}
                >
                  Копировать
                </button>
              </div>
              <div className="flex items-center justify-between gap-2 rounded-lg bg-zinc-900/60 px-3 py-2">
                <span className="text-zinc-400">Пароль</span>
                <span className="font-mono text-zinc-100">{quickCreateResult.password}</span>
                <button
                  type="button"
                  className="text-xs text-amber-400"
                  onClick={() => copyCredentials(quickCreateResult.password)}
                >
                  Копировать
                </button>
              </div>
            </div>
            <button
              type="button"
              className="btn-primary w-full"
              onClick={() => {
                setQuickCreateOpen(false);
                setQuickCreateResult(null);
              }}
            >
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
