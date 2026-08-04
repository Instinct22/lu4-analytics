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

export interface PermissionGroup {
  id: string;
  label: string;
  permissions: string[];
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

export interface RaidTimerLogItem {
  id: string;
  user_id: string | null;
  username: string;
  ip_address: string;
  boss_external_id: number;
  boss_name: string;
  action: "set" | "clear";
  killed_at: string | null;
  logged_at: string;
}

export interface RaidTimerLogsResponse {
  items: RaidTimerLogItem[];
  total: number;
  page: number;
  limit: number;
}

export interface UserCreationLogItem {
  id: string;
  creator_id: string | null;
  creator_username: string;
  created_user_id: string | null;
  created_username: string;
  role: string;
  ip_address: string;
  logged_at: string;
}

export interface UserCreationLogsResponse {
  items: UserCreationLogItem[];
  total: number;
  page: number;
  limit: number;
}

export interface QuickCreateResult {
  username: string;
  password: string;
  user: AdminUser;
}

export async function listUsers() {
  const { data } = await api.get("/admin/users");
  return data as AdminUser[];
}

export async function createUser(body: { username: string; password: string; role: Role }) {
  const { data } = await api.post("/admin/users", body);
  return data as AdminUser;
}

export async function quickCreateUser(role: Role) {
  const { data } = await api.post("/admin/users/quick-create", { role });
  return data as QuickCreateResult;
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

export interface CustomRoleItem {
  key: string;
  label: string;
}

export async function listCustomRoles() {
  const { data } = await api.get("/admin/custom-roles");
  return data as { items: CustomRoleItem[] };
}

export async function createCustomRole(body: {
  label: string;
  preset_role: string;
  key?: string;
}) {
  const { data } = await api.post("/admin/custom-roles", body);
  return data as CustomRoleItem;
}

export async function deleteCustomRole(key: string) {
  await api.delete(`/admin/custom-roles/${encodeURIComponent(key)}`);
}

export async function listRolePermissions() {
  const { data } = await api.get("/admin/roles");
  return data as RolePermissions[];
}

export async function updateRolePermissions(role: string, permissions: Record<string, boolean>) {
  const { data } = await api.put(`/admin/roles/${role}`, { permissions });
  return data as RolePermissions;
}

export async function getPublicRoles() {
  const { data } = await api.get("/admin/settings/public-roles");
  return data as { roles: Role[] };
}

export async function updatePublicRoles(roles: Role[]) {
  const { data } = await api.put("/admin/settings/public-roles", { roles });
  return data as { roles: Role[] };
}

export async function getPermissionGroups() {
  const { data } = await api.get("/admin/settings/permission-groups");
  return data as { groups: PermissionGroup[] };
}

export async function updatePermissionGroups(groups: PermissionGroup[]) {
  const { data } = await api.put("/admin/settings/permission-groups", { groups });
  return data as { groups: PermissionGroup[] };
}

export async function getAdminLevelRestriction() {
  const { data } = await api.get("/admin/settings/level-restriction");
  return data as { min: number; max: number };
}

export async function updateAdminLevelRestriction(body: { min: number; max: number }) {
  const { data } = await api.put("/admin/settings/level-restriction", body);
  return data as { min: number; max: number };
}

export async function getAdminLevelPreset() {
  const { data } = await api.get("/admin/settings/level-preset");
  return data as { min: number; max: number };
}

export async function updateAdminLevelPreset(body: { min: number; max: number }) {
  const { data } = await api.put("/admin/settings/level-preset", body);
  return data as { min: number; max: number };
}

export async function getAdminCraftMonitor() {
  const { data } = await api.get("/admin/settings/craft-monitor");
  return data as { selectedIds: number[] };
}

export async function updateAdminCraftMonitor(selectedIds: number[]) {
  const { data } = await api.put("/admin/settings/craft-monitor", { selectedIds });
  return data as { selectedIds: number[] };
}

export async function listLoginLogs(page = 1, limit = 25) {
  const { data } = await api.get("/admin/login-logs", { params: { page, limit } });
  return data as LoginLogsResponse;
}

export async function listRaidTimerLogs(page = 1, limit = 25) {
  const { data } = await api.get("/admin/raid-timer-logs", { params: { page, limit } });
  return data as RaidTimerLogsResponse;
}

export async function listUserCreationLogs(page = 1, limit = 25) {
  const { data } = await api.get("/admin/user-creation-logs", { params: { page, limit } });
  return data as UserCreationLogsResponse;
}

export interface MarketRecordAdminItem {
  id: string;
  entity_id: string | null;
  item_name: string | null;
  product_name_raw: string;
  seller_name: string;
  price: number | string;
  currency: string;
  side: string | null;
  quantity: number | null;
  recorded_at: string;
}

export interface MarketRecordsResponse {
  items: MarketRecordAdminItem[];
  total: number;
  page: number;
  limit: number;
}

export interface MarketRecordsFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
  product?: string;
  seller?: string;
  price?: string;
  currency?: string;
  side?: string;
  quantity?: string;
}

export interface MarketRecordUpdateItem {
  id: string;
  product_name_raw: string;
  seller_name: string;
  price: number;
  currency: string;
  side: string | null;
  quantity: number | null;
  recorded_at: string;
}

export async function listMarketRecords(
  page = 1,
  limit = 50,
  filters: MarketRecordsFilters = {},
) {
  const params: Record<string, string | number> = { page, limit };
  for (const [key, value] of Object.entries(filters)) {
    if (value != null && String(value).trim() !== "") {
      params[key] = String(value).trim();
    }
  }
  const { data } = await api.get("/admin/market-records", { params });
  return data as MarketRecordsResponse;
}

export async function deleteMarketRecord(id: string) {
  await api.delete(`/admin/market-records/${id}`);
}

export async function bulkUpdateMarketRecords(items: MarketRecordUpdateItem[]) {
  const { data } = await api.patch("/admin/market-records/bulk", { items });
  return data as { updated: number };
}

export async function bulkDeleteMarketRecords(ids: string[]) {
  const { data } = await api.post("/admin/market-records/bulk-delete", { ids });
  return data as { deleted: number };
}
