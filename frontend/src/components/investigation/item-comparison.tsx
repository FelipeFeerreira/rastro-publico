"use client";

import * as React from "react";
import { AlertTriangle, BarChart3, Loader2, Scale } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { comparePrices } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { ComparisonResponse, ProcurementItem } from "@/lib/types";

const CLASSIFICATION_STYLE: Record<string, string> = {
  dentro_da_faixa: "border-success/40 bg-success/10 text-success",
  acima_da_referencia: "border-warning/50 bg-warning/10 text-warning",
  sem_dados: "border-border bg-muted/40 text-muted-foreground",
};

export function ItemComparison({ items }: { items: ProcurementItem[] }) {
  const [selected, setSelected] = React.useState<ProcurementItem | null>(null);
  const [result, setResult] = React.useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const runComparison = async (item: ProcurementItem) => {
    setSelected(item);
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const data = await comparePrices({ item_id: item.id });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível comparar agora.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="size-4 text-primary" /> Itens da contratação
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">Nº</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead className="text-right">Qtd.</TableHead>
                  <TableHead className="text-right">Unit. estimado</TableHead>
                  <TableHead className="text-right">Total estimado</TableHead>
                  <TableHead className="text-right">Comparar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-muted-foreground">{item.item_number}</TableCell>
                    <TableCell className="max-w-md">
                      <p className="line-clamp-3 text-sm">{item.description}</p>
                      {item.unit && (
                        <span className="mt-1 inline-block text-xs text-muted-foreground">
                          {item.unit}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(item.quantity)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(item.unit_price_estimated)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(item.total_estimated)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" variant="outline" onClick={() => runComparison(item)}>
                        <Scale className="size-3.5" /> Analisar
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {selected && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-base">Comparação de preços comparáveis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Item {selected.item_number}: {selected.description}
            </p>

            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Calculando referência estatística…
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}

            {result?.classification && (
              <div
                className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
                  CLASSIFICATION_STYLE[result.classification.status] ?? CLASSIFICATION_STYLE.sem_dados
                }`}
              >
                <AlertTriangle className="mt-0.5 size-4" />
                <div>
                  <p className="font-medium">{result.classification.label}</p>
                  <p className="mt-1 text-foreground/80">{result.classification.explanation}</p>
                </div>
              </div>
            )}

            {result && !result.classification && !result.conclusive && (
              <div className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
                <AlertTriangle className="mt-0.5 size-4 text-warning" />
                <p>
                  Amostra insuficiente ({result.sample_size} registros comparáveis). Não é
                  possível concluir sobre o preço deste item com segurança estatística.
                </p>
              </div>
            )}

            {result && result.conclusive && (
              <div className="grid gap-4 sm:grid-cols-4">
                <Metric label="Amostra" value={formatNumber(result.distribution.count)} />
                <Metric label="Mediana" value={formatCurrency(result.distribution.median)} />
                <Metric label="P25" value={formatCurrency(result.distribution.p25)} />
                <Metric label="P75" value={formatCurrency(result.distribution.p75)} />
                <div className="sm:col-span-4">
                  <Badge variant="muted">{result.unit ?? "unidade não informada"}</Badge>
                </div>
              </div>
            )}

            {result && (
              <div className="space-y-2 rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                <p>
                  <span className="font-medium text-foreground">Metodologia:</span>{" "}
                  {result.methodology}
                </p>
                <p>
                  <span className="font-medium text-foreground">Limitações:</span>{" "}
                  {result.limitations}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold tabular-nums">{value}</p>
    </div>
  );
}
