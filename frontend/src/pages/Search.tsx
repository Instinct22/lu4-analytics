import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { searchEntities } from "../api/stats";
import { ItemIcon } from "../components/craft/CraftCostBar";
import { PageHeader, LoadingState } from "../components/ui";

type SearchItem = {
  id: string;
  display_name: string;
  entity_type: string;
  external_id?: number | null;
};

type SearchGroup = {
  entity_type: string;
  total: number;
  items: SearchItem[];
};

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => searchEntities(submitted),
    enabled: submitted.length >= 2,
  });

  return (
    <div>
      <PageHeader title="Поиск">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(q);
          }}
          className="flex w-full gap-2 sm:w-auto"
        >
          <input
            className="input sm:w-80 lg:w-96"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск..."
          />
          <button type="submit" className="btn-primary shrink-0">
            Найти
          </button>
        </form>
      </PageHeader>

      {isLoading && <LoadingState />}
      {data && (
        <div className="grid items-start gap-4 lg:grid-cols-2 2xl:grid-cols-3 min-[2200px]:grid-cols-4">
          {data.groups.map((group: SearchGroup) => (
            <div key={group.entity_type} className="card">
              <h3 className="mb-3 text-sm font-semibold capitalize text-zinc-200">
                {group.entity_type}{" "}
                <span className="font-normal text-zinc-500">({group.total})</span>
              </h3>
              <ul className="space-y-1.5">
                {group.items.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={`/wiki/${item.entity_type}/${item.id}`}
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800/50 hover:text-amber-300"
                    >
                      {item.entity_type === "item" && item.external_id != null && (
                        <ItemIcon id={item.external_id} size={24} />
                      )}
                      {item.display_name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
