import api from "./client";

export type Role = "admin" | "user" | "driver" | "other";

export interface User {
  id: string;
  username: string;
  role: Role;
  permissions: string[];
  email?: string | null;
  is_active?: boolean;
}

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  return data as { access_token: string; refresh_token: string };
}

export async function fetchMe() {
  const { data } = await api.get("/auth/me");
  return data as User;
}
