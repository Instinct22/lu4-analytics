import { MarketVariants } from "../../api/market";

export interface VariantSelection {
  soulCrystal: string | null;
  rarity: string | null;
  armorClass: string | null;
  sealed: string | null;
  enchantLevel: number | "clean" | null;
}

interface Props {
  variants?: MarketVariants;
  value: VariantSelection;
  onChange: (value: VariantSelection) => void;
}

const selectClass =
  "rounded-lg border border-zinc-700/80 bg-zinc-900/60 px-2 py-1.5 text-sm text-zinc-200 focus:border-amber-500/50 focus:outline-none";

const ARMOR_CLASS_LABELS: Record<string, string> = {
  heavy: "Heavy Armor",
  light: "Light Armor",
  magic: "Robe",
};

/** Slice a base item's chart/tables by variant attributes. */
export default function VariantFilter({ variants, value, onChange }: Props) {
  const souls = variants?.soul_crystals ?? [];
  const rarities = variants?.rarities ?? [];
  const armorClasses = variants?.armor_classes ?? [];
  const enchants = variants?.enchant_levels ?? [];
  const hasSealed = Boolean(variants?.has_sealed);

  if (
    souls.length === 0 &&
    rarities.length === 0 &&
    armorClasses.length === 0 &&
    enchants.length === 0 &&
    !hasSealed
  ) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {rarities.length > 0 && (
        <label className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="uppercase tracking-wider">Редкость</span>
          <select
            className={selectClass}
            value={value.rarity ?? ""}
            onChange={(e) => onChange({ ...value, rarity: e.target.value || null })}
          >
            <option value="">Все</option>
            <option value="clean">Обычная</option>
            {rarities.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
      )}
      {souls.length > 0 && (
        <label className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="uppercase tracking-wider">СА</span>
          <select
            className={selectClass}
            value={value.soulCrystal ?? ""}
            onChange={(e) =>
              onChange({ ...value, soulCrystal: e.target.value || null })
            }
          >
            <option value="">Все</option>
            <option value="clean">Без СА</option>
            {souls.map((sa) => (
              <option key={sa} value={sa}>
                {sa}
              </option>
            ))}
          </select>
        </label>
      )}
      {armorClasses.length > 0 && (
        <label className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="uppercase tracking-wider">Класс</span>
          <select
            className={selectClass}
            value={value.armorClass ?? ""}
            onChange={(e) => onChange({ ...value, armorClass: e.target.value || null })}
          >
            <option value="">Все</option>
            <option value="clean">Без класса</option>
            {armorClasses.map((cls) => (
              <option key={cls} value={cls}>
                {ARMOR_CLASS_LABELS[cls] ?? cls}
              </option>
            ))}
          </select>
        </label>
      )}
      {hasSealed && (
        <label className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="uppercase tracking-wider">Печать</span>
          <select
            className={selectClass}
            value={value.sealed ?? ""}
            onChange={(e) => onChange({ ...value, sealed: e.target.value || null })}
          >
            <option value="">Все</option>
            <option value="true">Запечатано</option>
            <option value="false">Распечатано</option>
          </select>
        </label>
      )}
      {enchants.length > 0 && (
        <label className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className="uppercase tracking-wider">Заточка</span>
          <select
            className={selectClass}
            value={
              value.enchantLevel === "clean"
                ? "clean"
                : value.enchantLevel != null
                  ? String(value.enchantLevel)
                  : ""
            }
            onChange={(e) => {
              const raw = e.target.value;
              onChange({
                ...value,
                enchantLevel: !raw ? null : raw === "clean" ? "clean" : Number(raw),
              });
            }}
          >
            <option value="">Любая</option>
            <option value="clean">Нет</option>
            {enchants.map((level) => (
              <option key={level} value={level}>
                +{level}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
