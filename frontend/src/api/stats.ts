import api from "./client";

export async function getDashboard() {
  const { data } = await api.get("/statistics/dashboard");
  return data;
}

export async function getUnmatched() {
  const { data } = await api.get("/statistics/unmatched");
  return data;
}

export async function searchEntities(q: string) {
  const { data } = await api.get("/search", { params: { q } });
  return data;
}