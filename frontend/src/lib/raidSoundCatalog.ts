export type RaidSoundEntry = {
  id: string;
  url: string;
  label: string;
};

export const DEFAULT_SOON_SOUND_ID = "pesik-pesik-av-av-av";
export const DEFAULT_WINDOW_SOUND_ID = "okhaeshechki-dattebaeshechki-poanimeshimsia";

const FILE_NAMES = [
  "415-i-ia-baza-otvette.mp3",
  "anime-ahh.mp3",
  "diadia-sasha_2a6g2tE.mp3",
  "dlia-zdorovia-alkasha-chekushka.mp3",
  "ia-potianu-tebia-za.mp3",
  "ia-shcha-tvoei-materi-eb-lo-razobiu.mp3",
  "kogda-mne-bylo-12-let.mp3",
  "mezhdu-nami-khammam.mp3",
  "miau-miau-miau-miau.mp3",
  "novosti.mp3",
  "okhaeshechki-dattebaeshechki-poanimeshimsia.mp3",
  "ozhidanie.mp3",
  "pesik-pesik-av-av-av.mp3",
  "pitstsa-4-syna.mp3",
  "pora-vstavat-khoziain-anime-devochka.mp3",
  "rzhd-pribytie-poezda.mp3",
  "s-t-a-l-k-e-r_GEuPZxH.mp3",
  "smeshariki-pogonia.mp3",
  "soundpad.mp3",
  "taksi.mp3",
  "tuturu_1.mp3",
  "yara-yara-phonk.mp3",
  "za-gorami-gde-e.mp3",
] as const;

function labelFromFileName(fileName: string): string {
  const base = fileName.replace(/\.mp3$/i, "");
  return base.replace(/[-_]+/g, " ");
}

function entryFromFileName(fileName: string): RaidSoundEntry {
  const id = fileName.replace(/\.mp3$/i, "");
  return {
    id,
    url: `/sound/${fileName}`,
    label: labelFromFileName(fileName),
  };
}

export const RAID_SOUND_CATALOG: RaidSoundEntry[] = FILE_NAMES.map(entryFromFileName).sort((a, b) =>
  a.label.localeCompare(b.label, "ru"),
);

const catalogById = new Map(RAID_SOUND_CATALOG.map((entry) => [entry.id, entry]));

export function getRaidSoundById(id: string | null | undefined): RaidSoundEntry | null {
  if (!id) return null;
  return catalogById.get(id) ?? null;
}

export function getRaidSoundUrl(id: string | null | undefined, fallbackId: string): string {
  return getRaidSoundById(id)?.url ?? getRaidSoundById(fallbackId)!.url;
}
