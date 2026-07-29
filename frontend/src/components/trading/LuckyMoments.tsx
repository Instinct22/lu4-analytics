interface Event {
  type: string;
  severity: string;
  title: string;
  description: string;
  recorded_at: string;
  price: number | null;
  quantity: number | null;
  side: string | null;
  seller_name: string | null;
}

interface Props {
  events: Event[];
}

const TYPE_ICONS: Record<string, string> = {
  price_drop: "↓",
  price_surge: "↑",
  cheap_deal: "★",
  volume_spike: "▮",
  activity_spike: "⚡",
  arbitrage: "⇄",
};

const SEVERITY_STYLES: Record<string, string> = {
  high: "border-red-500/30 bg-red-500/10",
  medium: "border-amber-500/30 bg-amber-500/10",
  low: "border-zinc-700/80 bg-zinc-900/60",
};

export default function LuckyMoments({ events }: Props) {
  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-zinc-200">«Лаки» моменты</h3>
        <p className="mt-1 text-xs text-zinc-500">Выгодные ситуации, рассчитанные на backend</p>
      </div>

      {!events.length ? (
        <p className="text-sm text-zinc-500">Событий не найдено за период</p>
      ) : (
        <ul className="max-h-80 space-y-2 overflow-y-auto">
          {events.map((event, idx) => (
            <li
              key={`${event.type}-${event.recorded_at}-${idx}`}
              className={`rounded-xl border px-4 py-3 ${SEVERITY_STYLES[event.severity] ?? SEVERITY_STYLES.low}`}
            >
              <div className="flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-950/60 text-sm">
                  {TYPE_ICONS[event.type] ?? "•"}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium text-zinc-100">{event.title}</p>
                    <time className="text-xs tabular-nums text-zinc-500">
                      {new Date(event.recorded_at).toLocaleString("ru-RU")}
                    </time>
                  </div>
                  <p className="mt-1 text-sm text-zinc-400">{event.description}</p>
                  {(event.seller_name || event.price != null) && (
                    <p className="mt-1 text-xs text-zinc-500">
                      {event.seller_name && <span>{event.seller_name} · </span>}
                      {event.price != null && (
                        <span>{Number(event.price).toLocaleString("ru-RU")}</span>
                      )}
                      {event.quantity != null && <span> · {event.quantity} шт.</span>}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
