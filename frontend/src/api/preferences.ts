import api from "./client";

export type PreferenceScope = "craft_owned" | "craft_prices" | "craft_variants" | "craft_cart";

export type PreferenceMap = Record<string, number>;

export type CraftCartLine = { qty: number; variant?: number };

export type CraftCartPayload = Record<string, CraftCartLine>;

export type ScopePayload = {
  craft_owned: PreferenceMap;
  craft_prices: PreferenceMap;
  craft_variants: PreferenceMap;
  craft_cart: CraftCartPayload;
};

export type PreferenceResponse<S extends PreferenceScope = PreferenceScope> = {
  scope: S;
  payload: ScopePayload[S];
  updated_at: string | null;
};

export type PreferencesListResponse = {
  scopes: Partial<ScopePayload>;
  updated_at: Partial<Record<PreferenceScope, string>>;
};

export async function getPreferences(): Promise<PreferencesListResponse> {
  const { data } = await api.get("/me/preferences");
  return {
    scopes: data.scopes ?? {},
    updated_at: data.updated_at ?? {},
  };
}

export async function putPreference<S extends PreferenceScope>(
  scope: S,
  payload: ScopePayload[S],
): Promise<PreferenceResponse<S>> {
  const { data } = await api.put(`/me/preferences/${scope}`, { payload });
  return data;
}

export async function patchPreference<S extends PreferenceScope>(
  scope: S,
  patch: Partial<ScopePayload[S]>,
): Promise<PreferenceResponse<S>> {
  const { data } = await api.patch(`/me/preferences/${scope}`, { patch });
  return data;
}
