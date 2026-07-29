import { useEffect, useState } from "react";
import { mediaUrl } from "../../api/client";

const ICON_VERSION = "3";

interface Props {
  id: number;
  size?: number;
  className?: string;
}

function skillSources(id: number): string[] {
  const local = mediaUrl(`images/wiki/skills/skill${id}.png?v=${ICON_VERSION}`);
  return local ? [local] : [];
}

export default function SkillIcon({ id, size = 40, className = "" }: Props) {
  const sources = skillSources(id);
  const [index, setIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setIndex(0);
    setFailed(false);
  }, [id]);

  const src = sources[index];

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-900 ring-1 ring-zinc-700/80 ${className}`}
      style={{ width: size, height: size }}
    >
      {!failed && src ? (
        <img
          key={`${id}-${index}`}
          src={src}
          alt=""
          width={size}
          height={size}
          className="h-full w-full object-contain p-0.5"
          onError={() => {
            if (index + 1 < sources.length) {
              setIndex(index + 1);
            } else {
              setFailed(true);
            }
          }}
        />
      ) : (
        <span className="text-[0.65rem] font-bold text-amber-500/80">S</span>
      )}
    </div>
  );
}
