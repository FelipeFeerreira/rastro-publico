import { Ban, CheckCircle2, PiggyBank, Wallet } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/format";
import type {
  MunicipalCoverage,
  MunicipalExpenseTotals,
  MunicipalInstitutionTotals,
} from "@/lib/types";

const MONTHS_SHORT = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
];

export interface CoverageDescription {
  period: string;
  perYear: Array<{ year: string; label: string; partial: boolean }>;
  hasPartial: boolean;
}

/** Descreve, em linguagem simples, o período coberto e os anos parciais. */
export function describeCoverage(coverage: MunicipalCoverage | null): CoverageDescription | null {
  if (!coverage || !coverage.first_date) return null;

  const fmt = (iso: string | null) => {
    if (!iso) return "—";
    const [y, m, d] = iso.slice(0, 10).split("-");
    return `${d}/${m}/${y}`;
  };

  const perYear = Object.entries(coverage.months_by_year).map(([year, months]) => {
    const sorted = [...months].sort((a, b) => a - b);
    const first = MONTHS_SHORT[(sorted[0] ?? 1) - 1];
    const last = MONTHS_SHORT[(sorted[sorted.length - 1] ?? 1) - 1];
    const partial = coverage.partial_years.includes(Number(year));
    return {
      year,
      label: sorted.length === 1 ? first : `${first}–${last}`,
      partial,
    };
  });

  return {
    period: `${fmt(coverage.first_date)} a ${fmt(coverage.last_date)}`,
    perYear,
    hasPartial: perYear.some((y) => y.partial),
  };
}

const STAGES = [
  {
    key: "pago" as const,
    title: "Pago",
    explanation: "Pagamento registrado.",
    icon: Wallet,
    primary: true,
  },
  {
    key: "empenhado" as const,
    title: "Empenhado",
    explanation: "Dinheiro reservado para uma despesa.",
    icon: PiggyBank,
    primary: false,
  },
  {
    key: "liquidado" as const,
    title: "Liquidado",
    explanation: "Despesa conferida pela administração.",
    icon: CheckCircle2,
    primary: false,
  },
  {
    key: "anulacao" as const,
    title: "Anulado",
    explanation: "Valor cancelado.",
    icon: Ban,
    primary: false,
  },
];

export function MunicipalFinancialCards({ totals }: { totals: MunicipalExpenseTotals }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {STAGES.map((stage) => {
        const Icon = stage.icon;
        return (
          <Card
            key={stage.key}
            className={stage.primary ? "border-primary/40 bg-primary/5" : undefined}
          >
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Icon className="size-3.5" />
                {stage.title}
              </div>
              <p
                data-testid={`municipal-${stage.key}`}
                className={`mt-2 font-semibold tabular-nums ${stage.primary ? "text-2xl" : "text-xl"}`}
              >
                {formatCurrency(totals[stage.key])}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{stage.explanation}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export function InstitutionBreakdown({ items }: { items: MunicipalInstitutionTotals[] }) {
  if (items.length === 0) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <Card key={item.entity_id ?? item.entity_name ?? "sem-instituicao"}>
          <CardContent className="p-5">
            <p className="text-sm font-medium">{item.entity_name ?? "Instituição não informada"}</p>
            <p className="mt-2 text-xl font-semibold tabular-nums text-primary">
              {formatCurrency(item.pago)}
            </p>
            <p className="text-xs text-muted-foreground">pago</p>
            <div className="mt-3 space-y-0.5 text-xs text-muted-foreground">
              <p>Empenhado: {formatCurrency(item.empenhado)}</p>
              <p>Liquidado: {formatCurrency(item.liquidado)}</p>
              <p>Anulado: {formatCurrency(item.anulacao)}</p>
              <p className="pt-1">Eventos: {item.records}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

const DESCRIPTION_FALLBACK = "Descrição não informada pela fonte";

/** Mostra a descrição da despesa ou o aviso explícito de ausência. */
export function ExpenseDescription({ description }: { description: string | null }) {
  if (!description || !description.trim()) {
    return <span className="text-muted-foreground italic">{DESCRIPTION_FALLBACK}</span>;
  }
  return <span>{description}</span>;
}

export { DESCRIPTION_FALLBACK };
