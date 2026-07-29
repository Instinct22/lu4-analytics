interface Level {
  price: number;
  volume: number;
}

interface Props {
  buys: Level[];
  sells: Level[];
}

function formatPrice(value: number): string {
  return Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function LevelTable({
  title,
  levels,
  accent,
}: {
  title: string;
  levels: Level[];
  accent: "emerald" | "red";
}) {
  const maxVol = Math.max(...levels.map((l) => l.volume), 1);
  const color = accent === "emerald" ? "bg-emerald-500/30" : "bg-red-500/30";

  return (
    <div>
      <h4 className={`mb-3 text-xs font-semibold uppercase tracking-wider ${accent === "emerald" ? "text-emerald-400" : "text-red-400"}`}>
        {title}
      </h4>
      {!levels.length ? (
        <p className="text-sm text-zinc-500">Нет уровней</p>
      ) : (
        <div className="max-h-72 overflow-y-auto rounded-xl border border-zinc-800/80">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-zinc-950/90 text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-3 py-2 text-left">Цена</th>
                <th className="px-3 py-2 text-right">Объём</th>
              </tr>
            </thead>
            <tbody>
              {levels.map((level) => (
                <tr key={`${title}-${level.price}`} className="relative border-t border-zinc-800/40">
                  <td className="relative px-3 py-2 tabular-nums text-zinc-200">
                    <div
                      className={`absolute inset-y-0 left-0 ${color}`}
                      style={{ width: `${(level.volume / maxVol) * 100}%` }}
                    />
                    <span className="relative">{formatPrice(level.price)}</span>
                  </td>
                  <td className="relative px-3 py-2 text-right tabular-nums text-zinc-400">
                    {level.volume.toLocaleString("ru-RU")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function OrderBook({ buys, sells }: Props) {
  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-zinc-200">Стакан заявок</h3>
        <p className="mt-1 text-xs text-zinc-500">Агрегация по цене за выбранный период</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <LevelTable title="Покупки" levels={buys} accent="emerald" />
        <LevelTable title="Продажи" levels={sells} accent="red" />
      </div>
    </div>
  );
}
