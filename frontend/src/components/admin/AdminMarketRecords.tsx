import { useState } from "react";
import AdminMarketRecordsTable from "./AdminMarketRecordsTable";
import AdminMarketStatistics from "./AdminMarketStatistics";

type DatabaseSubTab = "records" | "outliers" | "statistics";

export default function AdminMarketRecords() {
  const [subTab, setSubTab] = useState<DatabaseSubTab>("records");

  const switchSubTab = (next: DatabaseSubTab) => {
    setSubTab(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-1 rounded-xl bg-zinc-800/80 p-1 w-fit">
        {(
          [
            ["records", "База данных"],
            ["outliers", "Выбросы"],
            ["statistics", "Статистика"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              subTab === id
                ? "bg-amber-600 text-zinc-950"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            }`}
            onClick={() => switchSubTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {subTab === "statistics" && <AdminMarketStatistics />}

      {subTab === "records" && <AdminMarketRecordsTable key="records" outliersOnly={false} />}

      {subTab === "outliers" && <AdminMarketRecordsTable key="outliers" outliersOnly />}
    </div>
  );
}
