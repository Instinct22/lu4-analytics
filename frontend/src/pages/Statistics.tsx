import { useQuery } from "@tanstack/react-query";
import { getDashboard, getUnmatched } from "../api/stats";
import { PageHeader, StatCard, LoadingState } from "../components/ui";

export default function Statistics() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const { data: unmatched } = useQuery({
    queryKey: ["unmatched"],
    queryFn: getUnmatched,
  });

  if (isLoading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Статистика" />
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <StatCard title="Записей цен" value={dashboard?.total_market_records ?? 0} />
        <StatCard title="Импортов" value={dashboard?.total_imports ?? 0} />
        <StatCard title="Без сопоставления" value={dashboard?.unmatched_records ?? 0} />
      </div>
      <div className="card overflow-hidden p-0">
        <div className="border-b border-zinc-800/80 px-5 py-4">
          <h3 className="text-sm font-semibold text-zinc-200">Несопоставленные импорты</h3>
        </div>
        {!unmatched?.length ? (
          <p className="px-5 py-8 text-sm text-zinc-500">Все записи сопоставлены</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800/80 bg-zinc-900/40 text-left text-xs uppercase tracking-wider text-zinc-500">
                  <th className="px-5 py-3 font-medium">Название</th>
                  <th className="px-5 py-3 font-medium">Цена</th>
                  <th className="px-5 py-3 font-medium">Дата</th>
                </tr>
              </thead>
              <tbody>
                {unmatched.map((r: { id: string; product_name: string; price: number; recorded_at: string }) => (
                  <tr key={r.id} className="border-t border-zinc-800/60 transition-colors hover:bg-zinc-800/30">
                    <td className="px-5 py-3 text-zinc-300">{r.product_name}</td>
                    <td className="px-5 py-3 tabular-nums text-amber-400">{r.price}</td>
                    <td className="px-5 py-3 tabular-nums text-zinc-500">
                      {new Date(r.recorded_at).toLocaleString("ru-RU")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
