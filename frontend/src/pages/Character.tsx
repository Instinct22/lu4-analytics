import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import ClassSkillPanel from "../components/character/ClassSkillPanel";
import ClassTree from "../components/character/ClassTree";
import RaceTabs from "../components/character/RaceTabs";
import SkillDetailPanel from "../components/character/SkillDetailPanel";
import WikiLink from "../components/character/WikiLink";
import { ErrorState, LoadingState, PageHeader } from "../components/ui";
import {
  useCharacterClass,
  useCharacterRaces,
  useCharacterSkill,
} from "../hooks/useCharacterData";
import {
  classUnlockEntry,
  defaultLevelForClass,
  findRaceById,
  wikiClassesUrl,
  type ClassSkillEntry,
} from "../lib/characterData";

function parseIntParam(raw: string | null): number | null {
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export default function CharacterPage() {
  const { data: racesData, isLoading, error } = useCharacterRaces();
  const [searchParams, setSearchParams] = useSearchParams();

  const raceId = searchParams.get("race") ?? racesData?.races[0]?.id ?? "human";
  const classId = parseIntParam(searchParams.get("class"));
  const level = parseIntParam(searchParams.get("level"));
  const skillId = parseIntParam(searchParams.get("skill"));
  const skillLv = parseIntParam(searchParams.get("skillLv"));

  const { data: classData } = useCharacterClass(classId);
  const { data: skill } = useCharacterSkill(skillId);

  const race = racesData ? findRaceById(racesData.races, raceId) : undefined;

  const resolvedLevel = useMemo(() => {
    if (!classData) return null;
    if (level != null && classData.levels.includes(level)) return level;
    return defaultLevelForClass(classData);
  }, [classData, level]);

  const resolvedSkillLv = useMemo(() => {
    if (!skill) return null;
    const keys = Object.keys(skill.levels).map(Number).sort((a, b) => a - b);
    if (skillLv != null && skill.levels[String(skillLv)]) return skillLv;
    const unlock = classData && skillId != null ? classUnlockEntry(classData, skillId) : undefined;
    if (unlock && skill.levels[String(unlock.skill_level)]) return unlock.skill_level;
    return keys[keys.length - 1] ?? 1;
  }, [skill, skillLv, classData, skillId]);

  const unlockEntry = useMemo(() => {
    if (!classData || skillId == null) return null;
    return classUnlockEntry(classData, skillId) ?? null;
  }, [classData, skillId]);

  const patchParams = useCallback(
    (patch: Record<string, string | null>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            if (v == null) next.delete(k);
            else next.set(k, v);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const selectRace = (id: string) => {
    patchParams({ race: id, class: null, level: null, skill: null, skillLv: null });
  };

  // Level is resolved once the class payload arrives, so it starts empty.
  const selectClass = (id: number) => {
    patchParams({ class: String(id), level: null, skill: null, skillLv: null });
  };

  const selectLevel = (lv: number) => {
    patchParams({ level: String(lv) });
  };

  const selectSkill = (entry: ClassSkillEntry) => {
    patchParams({
      skill: String(entry.skill_id),
      skillLv: String(entry.skill_level),
    });
  };

  const selectSkillLevel = (lv: number) => {
    patchParams({ skillLv: String(lv) });
  };

  const closeSkill = () => {
    patchParams({ skill: null, skillLv: null });
  };

  if (isLoading) return <LoadingState />;
  if (error || !racesData || racesData.races.length === 0) {
    return (
      <ErrorState message="Данные персонажей не загружены. Запустите build_character_data.py и import_datasets.py" />
    );
  }

  const activeRace = race ?? racesData.races[0]!;
  const wikiBase = racesData.wiki_base;

  return (
    <div className="min-h-full">
      <PageHeader title="Персонаж">
        <p className="text-sm text-zinc-500">
          Расы, классы и умения Lu4 ·{" "}
          <WikiLink href={wikiClassesUrl(wikiBase)} className="text-sm text-amber-400">
            Все классы на Wiki ↗
          </WikiLink>
        </p>
      </PageHeader>

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <div
          className={[
            "shrink-0 space-y-4 transition-all",
            classData ? "xl:w-[20rem] 2xl:w-[24rem]" : "w-full xl:max-w-md",
          ].join(" ")}
        >
          <RaceTabs races={racesData.races} selectedId={activeRace.id} onSelect={selectRace} />
          <div className="panel list-scroll p-4">
            <ClassTree
              branches={activeRace.branches}
              selectedId={classId}
              onSelect={selectClass}
              wikiBase={wikiBase}
            />
          </div>
        </div>

        {classData && resolvedLevel != null ? (
          <>
            <div className="min-w-0 flex-1">
              <ClassSkillPanel
                classData={classData}
                level={resolvedLevel}
                selectedSkillId={skillId}
                wikiBase={wikiBase}
                onLevelChange={selectLevel}
                onSkillSelect={selectSkill}
              />
            </div>

            {skill && resolvedSkillLv != null && (
              <div className="min-w-0 xl:w-[22rem] 2xl:w-[26rem]">
                <SkillDetailPanel
                  skill={skill}
                  skillLevel={resolvedSkillLv}
                  classData={classData}
                  unlockEntry={unlockEntry}
                  races={racesData.races}
                  wikiBase={wikiBase}
                  onLevelChange={selectSkillLevel}
                  onClose={closeSkill}
                />
              </div>
            )}
          </>
        ) : (
          <div className="panel hidden flex-1 items-center justify-center border-dashed p-12 xl:flex">
            <div className="max-w-sm text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/80 ring-1 ring-zinc-700/80">
                <span className="text-2xl text-amber-500">⚔</span>
              </div>
              <p className="text-lg font-medium text-zinc-300">Выберите класс</p>
              <p className="mt-2 text-sm text-zinc-500">
                Дерево слева показывает путь профессий от базового класса до финальной
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
