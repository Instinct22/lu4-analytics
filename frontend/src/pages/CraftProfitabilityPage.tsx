import CraftProfitability from "../components/craft/CraftProfitability";
import { PageHeader } from "../components/ui";

export default function CraftProfitabilityPage() {
  return (
    <div>
      <PageHeader title="Прибыльность крафта" />
      <CraftProfitability />
    </div>
  );
}
