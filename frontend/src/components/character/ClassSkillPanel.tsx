import { useMemo } from "react";
import type { ClassData, ClassSkillEntry } from "../../lib/characterData";
import { skillsUpToLevel, wikiClassUrl } from "../../lib/characterData";
import { ClassPortrait } from "./ClassIcon";
import SkillCard from "./SkillCard";
import WikiLink from "./WikiLink";

interface Props {
  classData: ClassData;
  level: number;
  selectedSkillId: number | null;
  wikiBase: string;
  onLevelChange: (level: number) => void;
  onSkillSelect: (entry: ClassSkillEntry) => void;
}

export default function ClassSkillPanel({
  classData,
  level,
  selectedSkillId,
  wikiBase,
  onLevelChange,
  onSkillSelect,
}: Props) {
  const skills = useMemo(() => skillsUpToLevel(classData, level), [classData, level]);

  const newAtLevel = useMemo(() => {
    const set = new Set<number>();
    for (const e of classData.skills_by_level[String(level)] ?? []) {
      set.add(e.skill_id);
    }
    return set;
  }, [classData, level]);

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <ClassPortrait id={classData.id} className="h-32 w-24 shrink-0" />
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-semibold text-zinc-50">
            <WikiLink
              href={wikiClassUrl(classData.slug, level, wikiBase)}
              className="text-zinc-50 hover:text-amber-300"
            >
              {classData.name}
            </WikiLink>
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Умения, доступные на {level} уровне · всего {skills.length}
          </p>
          <WikiLink
            href={wikiClassUrl(classData.slug, level, wikiBase)}
            className="mt-1 inline-block text-xs text-amber-400"
          >
            Класс на Wiki ↗
          </WikiLink>
        </div>
      </div>

      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Уровень персонажа
        </div>
        <div className="flex gap-1 overflow-x-auto pb-1">
          {classData.levels.map((lv) => (
            <button
              key={lv}
              type="button"
              onClick={() => onLevelChange(lv)}
              className={[
                "shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                lv === level
                  ? "bg-amber-600 text-zinc-950"
                  : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200",
              ].join(" ")}
            >
              {lv}
            </button>
          ))}
        </div>
      </div>

      {skills.length === 0 ? (
        <p className="text-sm text-zinc-500">На этом уровне нет новых умений.</p>
      ) : (
        <div
          className={[
            "grid gap-3 transition-all",
            selectedSkillId != null
              ? "grid-cols-2 2xl:grid-cols-3"
              : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6 min-[2200px]:grid-cols-7",
          ].join(" ")}
        >
          {skills.map((entry) => (
            <SkillCard
              key={`${entry.skill_id}-${entry.skill_level}`}
              entry={entry}
              selected={selectedSkillId === entry.skill_id}
              isNewAtLevel={newAtLevel.has(entry.skill_id)}
              wikiBase={wikiBase}
              wrapName={selectedSkillId != null}
              onClick={() => onSkillSelect(entry)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
