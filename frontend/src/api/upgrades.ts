import type { WeaponUpgradesCatalog } from "../lib/weaponUpgrades";
import api from "./client";

export async function getWeaponUpgradesCatalog(): Promise<WeaponUpgradesCatalog> {
  const { data } = await api.get<WeaponUpgradesCatalog>("/upgrades/catalog");
  return data;
}
