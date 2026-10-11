import * as React from "react";
import { CalendarDays, Building2, Coins, HelpCircle, Receipt, Store, Wallet } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AnswerItem {
  icon: React.ElementType;
  question: string;
  answer: React.ReactNode;
  hint?: string;
  emphasis?: boolean;
}

export function AnswerGrid({ items }: { items: AnswerItem[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.question}
          className={cn(
            "rounded-lg border bg-card p-4",
            item.emphasis && "border-primary/40 bg-primary/5",
          )}
        >
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <item.icon className="size-3.5" />
            {item.question}
          </div>
          <p className="mt-2 text-sm font-medium">{item.answer}</p>
          {item.hint && <p className="mt-1 text-xs text-muted-foreground">{item.hint}</p>}
        </div>
      ))}
    </div>
  );
}

export interface ContractSummaryData {
  objectDescription: string;
  contractorName: string | null;
  contractorHref?: string | null;
  supplierName: string | null;
  supplierHref?: string | null;
  date: string | null;
  contractedValue: number | string | null;
  paidValue: number | string | null;
  committedValue: number | string | null;
  liquidatedValue: number | string | null;
}

export function ContractPlainSummary({ data }: { data: ContractSummaryData }) {
  return (
    <Card className="border-primary/20">
      <CardContent className="space-y-4 p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            O que foi comprado ou contratado?
          </p>
          <p className="mt-1 text-sm font-medium">{data.objectDescription}</p>
        </div>
        <AnswerGrid
          items={[
            {
              icon: Building2,
              question: "Quem contratou?",
              answer: data.contractorHref ? (
                <a href={data.contractorHref} className="text-primary hover:underline">
                  {data.contractorName ?? "Não informado"}
                </a>
              ) : (
                data.contractorName ?? "Não informado"
              ),
            },
            {
              icon: Store,
              question: "Quem recebeu o dinheiro?",
              answer: data.supplierHref ? (
                <a href={data.supplierHref} className="text-primary hover:underline">
                  {data.supplierName ?? "Não informado"}
                </a>
              ) : (
                data.supplierName ?? "Não informado"
              ),
            },
            {
              icon: CalendarDays,
              question: "Quando aconteceu?",
              answer: formatDate(data.date),
            },
            {
              icon: Receipt,
              question: "Quanto custou?",
              answer: formatCurrency(data.contractedValue),
              hint: `${data.committedValue ? formatCurrency(data.committedValue) : "—"} foi reservado (empenhado)`,
            },
            {
              icon: Wallet,
              question: "Quanto foi realmente pago?",
              answer: formatCurrency(data.paidValue),
              hint: `${data.liquidatedValue ? formatCurrency(data.liquidatedValue) : "—"} liquidado`,
              emphasis: true,
            },
          ]}
        />
        <p className="flex items-start gap-2 text-xs text-muted-foreground">
          <HelpCircle className="mt-0.5 size-3.5 shrink-0" />
          “Custo” é o valor contratado. “Pago” é o dinheiro que efetivamente saiu. Os dois
          são coisas diferentes.
        </p>
      </CardContent>
    </Card>
  );
}

export function CoinsHint() {
  return <Coins className="size-4 text-muted-foreground" />;
}
