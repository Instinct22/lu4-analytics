import api from "./client";

export type PreferenceScope = "craft_owned" | "craft_prices" | "craft_variants";

export type PreferenceMap = Record<string, number>;

export async function getPreferences(): Promise<Partial<Record<PreferenceScope, PreferenceMap>>> {
  const { data } = await api.get("/me/preferences");
  return data.scopes ?? {};
}

export async function putPreference(
  scope: PreferenceScope,
  payload: PreferenceMap,
): Promise<PreferenceMap> {
  const { data } = await api.put(`/me/preferences/${scope}`, { payload });
  return data.payload ?? {};
}
