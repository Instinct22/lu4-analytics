export type RaidBossDropItem = {
  name: string;
  grade: string | null;
  amount: string | null;
  chance: string | null;
  icon?: string | null;
  itemId?: number | null;
};

export type RaidBossDropGroup = {
  groupChance: string | null;
  items: RaidBossDropItem[];
};

export type RaidBossSkill = {
  name: string;
  level: number | null;
  desc: string | null;
};

export type RaidBossStats = {
  hp: string | null;
  mp: string | null;
  pAtk: string | null;
  mAtk: string | null;
  pDef: string | null;
  mDef: string | null;
  accuracy: string | null;
  evasion: string | null;
  exp: string | null;
  sp: string | null;
  atkAttr: string | null;
  defAttr: string | null;
};

export type RaidBoss = {
  id: number;
  name: string;
  level: number | null;
  x: number;
  y: number;
  image: string | null;
  wikiUrl: string;
  location: string | null;
  respawn: string | null;
  /** Respawn window precomputed by the backend; falls back to parsing `respawn`. */
  respawnMinSec?: number | null;
  respawnMaxSec?: number | null;
  stats: RaidBossStats;
  lore: string | null;
  howToReach?: string | null;
  skills: RaidBossSkill[];
  drops: RaidBossDropGroup[];
};

export type RaidBossesPayload = {
  source: { map: string; wikiPost: string };
  map: { width: number; height: number; image: string; flag: string };
  bosses: RaidBoss[];
};
