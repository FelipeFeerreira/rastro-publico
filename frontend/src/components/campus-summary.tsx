import { PiggyBank, Receipt, Scale, Wallet } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/format";

export interface FinancialValues {
  contracted: number | string;
  committed: number | string;
  liquidated: number | string;
  paid: number | string;
  payment_events?: number;
}

export const FINANCIAL_STAGES = [
  {
    key: "contracted" as const,
    title: "Contratado",
    hint: "Valor total dos contratos assinados.",
    icon: Receipt,
    emphasize: false,
  },
  {
    key: "committed" as const,
    title: "Empenhado",
    hint: "Orçamento reservado (ainda não é pagamento).",
    icon: PiggyBank,
    emphasize: false,
  },
  {
    key: "liquidated" as const,
    title: "Liquidado",
    hint: "Entrega ou serviço conferido.",
    icon: Scale,
    emphasize: false,
  },
  {
    key: "paid" as const,
    title: "Pago",
    hint: "Dinheiro que efetivamente saiu.",
    icon: Wallet,
    emphasize: true,
  },
];

export function CampusFinancialCards({ values }: { values: FinancialValues }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {FINANCIAL_STAGES.map((stage) => {
        const Icon = stage.icon;
        return (
          <Card
            key={stage.key}
            className={stage.emphasize ? "border-primary/40 bg-primary/5" : undefined}
          >
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Icon className="size-3.5" />
                {stage.title}
              </div>
              <p
                data-testid={`financial-${stage.key}`}
                className="mt-2 text-2xl font-semibold tabular-nums"
              >
                {formatCurrency(values[stage.key])}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{stage.hint}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
