import CraftProfitability from "../components/craft/CraftProfitability";
import { PageHeader } from "../components/ui";

export default function CraftProfitabilityPage() {
  return (
    <div>
      <PageHeader title="Прибыльность крафта">
        <p className="text-sm text-zinc-500">Цены за выбранный период по данным рынка</p>
      </PageHeader>
      <CraftProfitability />
    </div>
  );
}
