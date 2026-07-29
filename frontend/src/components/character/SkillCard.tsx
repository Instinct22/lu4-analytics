import type { ClassSkillEntry } from "../../lib/characterData";
import { wikiSkillUrl } from "../../lib/characterData";
import SkillIcon from "./SkillIcon";
import WikiLink from "./WikiLink";

interface Props {
  entry: ClassSkillEntry;
  selected: boolean;
  isNewAtLevel: boolean;
  wikiBase: string;
  wrapName?: boolean;
  onClick: () => void;
}

export default function SkillCard({
  entry,
  selected,
  isNewAtLevel,
  wikiBase,
  wrapName = false,
  onClick,
}: Props) {
  const skillUrl = wikiSkillUrl(entry.skill_id, entry.name, entry.skill_level, wikiBase);

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "group relative flex flex-col items-start gap-2 rounded-xl border p-3 text-left transition-all",
        selected
          ? "border-amber-500/50 bg-amber-500/10 ring-1 ring-amber-500/30"
          : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 hover:bg-zinc-800/60",
      ].join(" ")}
    >
      <WikiLink
        href={skillUrl}
        stopPropagation
        className="absolute right-2 top-2 rounded-md bg-zinc-900/80 px-1.5 py-0.5 text-[0.6rem] text-zinc-500 opacity-0 transition-opacity hover:text-amber-400 group-hover:opacity-100"
      >
        ↗
      </WikiLink>
      <div className="flex w-full items-start gap-2">
        <SkillIcon id={entry.skill_id} size={44} />
        <div className="min-w-0 flex-1">
          <div
            className={[
              "text-sm font-medium text-zinc-100",
              wrapName ? "leading-snug" : "truncate",
            ].join(" ")}
          >
            {entry.name}
          </div>
          <div className="text-xs text-zinc-500">Lv. {entry.skill_level}</div>
        </div>
      </div>
      {isNewAtLevel && (
        <span className="rounded-md bg-amber-600/20 px-2 py-0.5 text-[0.65rem] font-semibold text-amber-300">
          +Lv.{entry.unlocked_at_level}
        </span>
      )}
    </button>
  );
}
