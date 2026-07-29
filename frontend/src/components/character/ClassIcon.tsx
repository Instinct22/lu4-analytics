import { useEffect, useState } from "react";
import { mediaUrl } from "../../api/client";

const ICON_VERSION = "3";

interface Props {
  id: number;
  size?: number;
  className?: string;
}

function classIconSources(id: number): string[] {
  const icon = mediaUrl(`images/wiki/class_icon_${id}.png?v=${ICON_VERSION}`);
  return icon ? [icon] : [];
}

function classPortraitSources(id: number): string[] {
  const sources: string[] = [];
  const portrait = mediaUrl(`images/wiki/classes/${id}.png?v=${ICON_VERSION}`);
  const icon = mediaUrl(`images/wiki/class_icon_${id}.png?v=${ICON_VERSION}`);
  if (portrait) sources.push(portrait);
  if (icon) sources.push(icon);
  return sources;
}

export default function ClassIcon({ id, size = 40, className = "" }: Props) {
  const sources = classIconSources(id);
  const [index, setIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setIndex(0);
    setFailed(false);
  }, [id]);

  const src = sources[index];

  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-800 ring-1 ring-zinc-700/80 ${className}`}
      style={{ width: size, height: size }}
    >
      {!failed && src ? (
        <img
          key={`${id}-${index}`}
          src={src}
          alt=""
          width={size}
          height={size}
          className="h-full w-full object-cover"
          onError={() => {
            if (index + 1 < sources.length) {
              setIndex(index + 1);
            } else {
              setFailed(true);
            }
          }}
        />
      ) : (
        <span className="text-[0.65rem] font-bold text-zinc-500">C</span>
      )}
    </div>
  );
}

export function ClassPortrait({ id, className = "" }: { id: number; className?: string }) {
  const sources = classPortraitSources(id);
  const [index, setIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setIndex(0);
    setFailed(false);
  }, [id]);

  const src = sources[index];

  return (
    <div className={`overflow-hidden rounded-xl bg-zinc-800 ring-1 ring-zinc-700/80 ${className}`}>
      {!failed && src ? (
        <img
          key={`${id}-${index}`}
          src={src}
          alt=""
          className="h-full w-full object-cover"
          onError={() => {
            if (index + 1 < sources.length) {
              setIndex(index + 1);
            } else {
              setFailed(true);
            }
          }}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-zinc-600">?</div>
      )}
    </div>
  );
}
