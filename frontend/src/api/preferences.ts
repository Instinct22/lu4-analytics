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

export async function getPreferences(): Promise<Partial<ScopePayload>> {
  const { data } = await api.get("/me/preferences");
  return data.scopes ?? {};
}

export async function putPreference<S extends PreferenceScope>(
  scope: S,
  payload: ScopePayload[S],
): Promise<ScopePayload[S]> {
  const { data } = await api.put(`/me/preferences/${scope}`, { payload });
  return data.payload ?? {};
}
