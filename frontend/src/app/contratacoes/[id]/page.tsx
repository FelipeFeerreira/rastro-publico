import Link from "next/link";
import { notFound } from "next/navigation";
import { Building2, CalendarDays, Coins, ExternalLink, MapPin, Scale } from "lucide-react";

import { DataNotice, ErrorState, SectionHeading } from "@/components/common";
import { PriceBars } from "@/components/charts/price-bars";
import { AddToInvestigation } from "@/components/investigation/add-to-investigation";
import { AnswerGrid } from "@/components/plain-summary";
import { ItemComparison } from "@/components/investigation/item-comparison";
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
import { ApiError, getProcurement } from "@/lib/api";
import { formatCurrency, formatDate, formatDateTime, modalityLabel } from "@/lib/format";
import type { ProcurementDetail } from "@/lib/types";

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm">{value ?? "—"}</dd>
    </div>
  );
}

export default async function ProcurementDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let procurement: ProcurementDetail | null = null;
  let errorStatus = 0;

  try {
    procurement = await getProcurement(id);
  } catch (err) {
    if (err instanceof ApiError) errorStatus = err.status;
  }

  if (errorStatus === 404) notFound();
  if (!procurement) {
    return (
      <div className="container py-16">
        <ErrorState
          title="Não foi possível carregar a contratação"
          description="O serviço de dados pode estar indisponível."
        />
      </div>
    );
  }

  const chartData = procurement.items
    .filter((item) => (item.total_estimated ?? 0) > 0)
    .sort((a, b) => (b.total_estimated ?? 0) - (a.total_estimated ?? 0))
    .slice(0, 8)
    .map((item) => ({ label: `#${item.item_number}`, value: item.total_estimated ?? 0 }));

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/contratacoes" className="hover:text-foreground">
          Contratações
        </Link>
        <span className="mx-2">/</span>
        <span>{procurement.pncp_control_number}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-semibold tracking-tight">{procurement.object_description}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {procurement.entity && (
              <Link href={`/orgaos/${procurement.entity.id}`} className="hover:text-foreground">
                {procurement.entity.name}
              </Link>
            )}
            {procurement.municipality && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" />
                {procurement.municipality.name}
                {procurement.municipality.uf ? `/${procurement.municipality.uf}` : ""}
              </span>
            )}
            <Badge variant="secondary">{modalityLabel(procurement.modality)}</Badge>
            {procurement.status_name && <Badge variant="muted">{procurement.status_name}</Badge>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddToInvestigation
            recordType="procurement"
            recordId={procurement.id}
            title={procurement.object_description}
            sourceUrl={procurement.source_url}
          />
          {procurement.source_url && (
            <Button asChild variant="outline" size="sm">
              <a href={procurement.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="size-4" /> Registro original
              </a>
            </Button>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-primary/20 bg-primary/5 p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          O que foi comprado ou contratado?
        </p>
        <p className="mt-1 text-sm font-medium">{procurement.object_description}</p>
        <div className="mt-4">
          <AnswerGrid
            items={[
              {
                icon: Building2,
                question: "Quem contratou?",
                answer: procurement.entity?.name ?? "Não informado",
              },
              {
                icon: MapPin,
                question: "Onde?",
                answer: procurement.municipality
                  ? `${procurement.municipality.name}${procurement.municipality.uf ? `/${procurement.municipality.uf}` : ""}`
                  : "Não informado",
              },
              {
                icon: CalendarDays,
                question: "Quando?",
                answer: formatDate(procurement.published_at),
              },
              {
                icon: Coins,
                question: "Quanto custou?",
                answer: formatCurrency(procurement.estimated_total),
                hint: `Homologado: ${formatCurrency(procurement.approved_total)}`,
              },
            ]}
          />
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Valor estimado</p>
            <p className="mt-1 text-xl font-semibold tabular-nums">
              {formatCurrency(procurement.estimated_total)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Valor homologado
            </p>
            <p className="mt-1 text-xl font-semibold tabular-nums">
              {formatCurrency(procurement.approved_total)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Itens</p>
            <p className="mt-1 text-xl font-semibold tabular-nums">{procurement.items.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4">
        <DataNotice>
          Estágios distintos: valor <strong>estimado</strong> (previsão),{" "}
          <strong>homologado</strong> (contratado/adjudicado), <strong>empenhado</strong>,{" "}
          <strong>liquidado</strong> e <strong>pago</strong>. Uma contratação publicada não
          é pagamento.
        </DataNotice>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Detalhes</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Meta label="Nº PNCP" value={procurement.pncp_control_number} />
              <Meta label="Nº da compra" value={procurement.number} />
              <Meta label="Processo" value={procurement.process_number} />
              <Meta label="Modo de disputa" value={procurement.dispute_mode_name} />
              <Meta label="Registro de preços" value={procurement.is_price_registry ? "Sim" : "Não"} />
              <Meta
                label="Emenda parlamentar"
                value={
                  procurement.is_parliamentary_amendment === null
                    ? "Não informado"
                    : procurement.is_parliamentary_amendment
                      ? "Sim"
                      : "Não"
                }
              />
              <Meta label="Publicação" value={formatDate(procurement.published_at)} />
              <Meta label="Abertura de propostas" value={formatDateTime(procurement.proposal_open_at)} />
              <Meta label="Encerramento" value={formatDateTime(procurement.proposal_close_at)} />
              <Meta label="Coleta local" value={formatDateTime(procurement.collected_at)} />
              <Meta label="Atualização na fonte" value={formatDateTime(procurement.source_updated_at)} />
              {procurement.source && <Meta label="Fonte" value={procurement.source.name} />}
            </dl>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Scale className="size-4 text-primary" /> Maiores itens por valor estimado
            </CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <PriceBars data={chartData} />
            ) : (
              <p className="text-sm text-muted-foreground">Sem itens com valor informado.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <section className="mt-8">
        <SectionHeading
          title="Itens e análise de preços"
          description="Compare o preço unitário de cada item com contratações equivalentes."
          className="mb-4"
        />
        {procurement.items.length > 0 ? (
          <ItemComparison items={procurement.items} />
        ) : (
          <DataNotice>
            Esta contratação ainda não teve itens sincronizados. Execute a ingestão com a
            opção de itens para habilitar a comparação de preços.
          </DataNotice>
        )}
      </section>

      <section className="mt-8">
        <SectionHeading
          title="Resultados homologados"
          description="Fornecedores vencedores e preços por item."
          className="mb-4"
        />
        <Card>
          <CardContent className="overflow-x-auto p-0">
            {procurement.results.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Fornecedor</TableHead>
                    <TableHead className="text-right">Unit. homologado</TableHead>
                    <TableHead className="text-right">Qtd.</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead>Data</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {procurement.results.map((result) => {
                    const item = procurement!.items.find((i) => i.id === result.item_id);
                    return (
                      <TableRow key={result.id}>
                        <TableCell>#{item?.item_number ?? "—"}</TableCell>
                        <TableCell>
                          {result.supplier_id ? (
                            <Link
                              href={`/fornecedores/${result.supplier_id}`}
                              className="text-primary hover:underline"
                            >
                              {result.supplier_name}
                            </Link>
                          ) : (
                            result.supplier_name ?? "—"
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatCurrency(result.unit_price)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {result.quantity ?? "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatCurrency(result.total_price)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(result.result_date)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <p className="p-6 text-sm text-muted-foreground">
                Nenhum resultado homologado sincronizado para esta contratação.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
