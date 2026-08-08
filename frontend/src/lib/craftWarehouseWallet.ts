/** Wallet fields stored alongside item quantities in craft_owned. */
export const WAREHOUSE_ADENA_KEY = "adena";
export const WAREHOUSE_MASTER_COIN_KEY = "master_coin";

export function warehouseAdena(owned: Record<string, number>): number {
  return Math.max(0, Math.floor(Number(owned[WAREHOUSE_ADENA_KEY]) || 0));
}

export function warehouseMasterCoin(owned: Record<string, number>): number {
  return Math.max(0, Math.floor(Number(owned[WAREHOUSE_MASTER_COIN_KEY]) || 0));
}

export function setWarehouseWallet(
  owned: Record<string, number>,
  adena: number,
  masterCoin: number,
): Record<string, number> {
  const next = { ...owned };
  const a = Math.max(0, Math.floor(adena));
  const m = Math.max(0, Math.floor(masterCoin));
  if (a > 0) next[WAREHOUSE_ADENA_KEY] = a;
  else delete next[WAREHOUSE_ADENA_KEY];
  if (m > 0) next[WAREHOUSE_MASTER_COIN_KEY] = m;
  else delete next[WAREHOUSE_MASTER_COIN_KEY];
  return next;
}
