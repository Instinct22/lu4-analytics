import type { Race } from "../../lib/characterData";

interface Props {
  races: Race[];
  selectedId: string;
  onSelect: (raceId: string) => void;
}

export default function RaceTabs({ races, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {races.map((race) => {
        const active = race.id === selectedId;
        return (
          <button
            key={race.id}
            type="button"
            onClick={() => onSelect(race.id)}
            className={[
              "rounded-xl px-4 py-2 text-sm font-medium transition-all",
              active
                ? "bg-amber-600 text-zinc-950 shadow-glow ring-1 ring-amber-500/40"
                : "bg-zinc-800/80 text-zinc-400 ring-1 ring-zinc-700/60 hover:bg-zinc-800 hover:text-zinc-200",
            ].join(" ")}
          >
            {race.name}
          </button>
        );
      })}
    </div>
  );
}
