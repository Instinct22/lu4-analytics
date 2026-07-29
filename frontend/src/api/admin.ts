import api from "./client";
import type { Role, User } from "./auth";

export interface AdminUser extends User {
  created_at?: string | null;
}

export interface PermissionEntry {
  permission: string;
  allowed: boolean;
  label?: string | null;
}

export interface RolePermissions {
  role: Role;
  label: string;
  permissions: PermissionEntry[];
}

export interface LoginLogItem {
  id: string;
  user_id: string | null;
  username: string;
  ip_address: string;
  logged_at: string;
}

export interface LoginLogsResponse {
  items: LoginLogItem[];
  total: number;
  page: number;
  limit: number;
}

export async function listUsers() {
  const { data } = await api.get("/admin/users");
  return data as AdminUser[];
}

export async function createUser(body: { username: string; password: string; role: Role }) {
  const { data } = await api.post("/admin/users", body);
  return data as AdminUser;
}

export async function updateUser(
  id: string,
  body: { password?: string; role?: Role; is_active?: boolean },
) {
  const { data } = await api.patch(`/admin/users/${id}`, body);
  return data as AdminUser;
}

export async function deleteUser(id: string) {
  await api.delete(`/admin/users/${id}`);
}

export async function listRolePermissions() {
  const { data } = await api.get("/admin/roles");
  return data as RolePermissions[];
}

export async function updateRolePermissions(role: Role, permissions: Record<string, boolean>) {
  const { data } = await api.put(`/admin/roles/${role}`, { permissions });
  return data as RolePermissions;
}

export async function listLoginLogs(page = 1, limit = 25) {
  const { data } = await api.get("/admin/login-logs", { params: { page, limit } });
  return data as LoginLogsResponse;
}
