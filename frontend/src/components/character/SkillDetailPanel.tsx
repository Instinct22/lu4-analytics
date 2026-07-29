import { useMemo } from "react";
import { ItemIcon } from "../craft/CraftCostBar";
import type { ClassData, ClassSkillEntry, Race, SkillData } from "../../lib/characterData";
import {
  classUnlockEntry,
  findClassNodeByName,
  formatSp,
  skillLevelRange,
  wikiClassesUrl,
  wikiClassUrl,
  wikiItemUrl,
  wikiSkillUrl,
} from "../../lib/characterData";
import SkillIcon from "./SkillIcon";
import WikiLink from "./WikiLink";

interface Props {
  skill: SkillData;
  skillLevel: number;
  classData: ClassData | null;
  unlockEntry: ClassSkillEntry | null;
  races: Race[];
  wikiBase: string;
  onLevelChange: (level: number) => void;
  onClose: () => void;
}

const STAT_LABELS: Record<string, string> = {
  Consumes: "Мана",
  "Reuse Time": "Перезарядка",
  "Cast Range": "Дальность",
  "Can be used on Olympiad": "Олимпиада",
  Attribute: "Стихия",
  Trait: "Тип",
};

export default function SkillDetailPanel({
  skill,
  skillLevel,
  classData,
  unlockEntry,
  races,
  wikiBase,
  onLevelChange,
  onClose,
}: Props) {
  const skillWikiUrl = wikiSkillUrl(skill.id, skill.name, skillLevel, wikiBase);
  const levels = useMemo(() => skillLevelRange(skill), [skill]);
  const levelData = skill.levels[String(skillLevel)];
  const resolvedUnlock = unlockEntry ?? (classData ? classUnlockEntry(classData, skill.id) : undefined);

  const minLv = levels[0] ?? 1;
  const maxLv = levels[levels.length - 1] ?? 1;

  return (
    <div className="panel flex flex-col gap-4 p-4 xl:sticky xl:top-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <SkillIcon id={skill.id} size={56} />
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-zinc-50">
              <WikiLink href={skillWikiUrl} className="text-zinc-50 hover:text-amber-300">
                {skill.name}
              </WikiLink>
            </h3>
            {skill.type && <p className="text-sm text-zinc-500">{skill.type}</p>}
            <WikiLink href={skillWikiUrl} className="mt-1 inline-block text-xs text-amber-400">
              Wiki Lu4 ↗
            </WikiLink>
          </div>
        </div>
        <button type="button" className="btn-ghost shrink-0 text-xs" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="flex items-center justify-center gap-3 rounded-xl bg-zinc-900/60 py-3">
        <button
          type="button"
          className="btn-ghost px-3 py-1 disabled:opacity-30"
          disabled={skillLevel <= minLv}
          onClick={() => onLevelChange(skillLevel - 1)}
          aria-label="Предыдущий уровень"
        >
          ◀
        </button>
        <span className="min-w-[5rem] text-center text-sm font-semibold text-amber-300">
          Lv. {skillLevel}
        </span>
        <button
          type="button"
          className="btn-ghost px-3 py-1 disabled:opacity-30"
          disabled={skillLevel >= maxLv}
          onClick={() => onLevelChange(skillLevel + 1)}
          aria-label="Следующий уровень"
        >
          ▶
        </button>
      </div>

      {levelData?.description && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Описание</div>
          <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-300">{levelData.description}</p>
        </div>
      )}

      {levelData?.stats && Object.keys(levelData.stats).length > 0 && (
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Характеристики</div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(levelData.stats)
              .filter(([k]) => k !== "Available For")
              .map(([key, value]) => (
                <div key={key} className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
                  <div className="text-[0.65rem] uppercase tracking-wide text-zinc-500">
                    {STAT_LABELS[key] ?? key}
                  </div>
                  <div className="text-sm font-medium text-zinc-200">{value}</div>
                </div>
              ))}
          </div>
        </div>
      )}

      {resolvedUnlock && (
        <div className="rounded-xl border border-amber-900/30 bg-amber-950/20 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-200/70">
            Требования для изучения
          </div>
          <div className="space-y-2 text-sm">
            {resolvedUnlock.unlocked_at_level != null && (
              <div className="text-zinc-400">
                Уровень класса:{" "}
                {classData ? (
                  <WikiLink
                    href={wikiClassUrl(classData.slug, resolvedUnlock.unlocked_at_level, wikiBase)}
                    className="font-medium text-sky-400 hover:underline"
                  >
                    Lv. {resolvedUnlock.unlocked_at_level}
                  </WikiLink>
                ) : (
                  <span className="font-medium text-zinc-200">Lv. {resolvedUnlock.unlocked_at_level}</span>
                )}
              </div>
            )}
            {resolvedUnlock.sp != null && (
              <div className="flex items-center gap-2 text-zinc-400">
                <span>SP:</span>
                <span className="font-medium text-amber-300">{formatSp(resolvedUnlock.sp)}</span>
              </div>
            )}
            {resolvedUnlock.spellbook && (
              <div className="flex items-center gap-2">
                <ItemIcon id={resolvedUnlock.spellbook.id} size={28} />
                <div>
                  <WikiLink
                    href={wikiItemUrl(resolvedUnlock.spellbook.id, resolvedUnlock.spellbook.name, wikiBase)}
                    className="font-medium text-sky-400 hover:underline"
                  >
                    {resolvedUnlock.spellbook.name}
                  </WikiLink>
                  {resolvedUnlock.spellbook.grade && (
                    <div className="text-xs text-zinc-500">{resolvedUnlock.spellbook.grade}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {skill.available_for.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Доступно для</div>
          <div className="flex flex-wrap gap-2">
            {skill.available_for.map((a) => {
              const cls = findClassNodeByName(races, a.class_name);
              const href = cls
                ? wikiClassUrl(cls.slug, a.level, wikiBase)
                : wikiClassesUrl(wikiBase);
              return (
                <WikiLink
                  key={`${a.class_name}-${a.level}`}
                  href={href}
                  className="rounded-lg bg-zinc-800 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-700 hover:text-amber-300"
                >
                  {a.class_name} Lv.{a.level}
                </WikiLink>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
