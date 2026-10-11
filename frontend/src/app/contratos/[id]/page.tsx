import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";

import { DataNotice, SectionHeading } from "@/components/common";
import { AddToInvestigation } from "@/components/investigation/add-to-investigation";
import { ContractPlainSummary } from "@/components/plain-summary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, getContract, getContractPayments } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const STAGE_LABEL: Record<string, string> = {
  empenhado: "Empenhado (reservado)",
  liquidado: "Liquidado (conferido)",
  pago: "Pago",
  homologado: "Homologado",
  estimado: "Estimado",
};

export default async function ContractDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let contract;
  try {
    contract = await getContract(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const payments = await getContractPayments(id).catch(() => []);
  const summary = contract.payment_summary;

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/contratacoes" className="hover:text-foreground">
          Contratos
        </Link>
        <span className="mx-2">/</span>
        <span>{contract.number ?? contract.id}</span>
      </nav>

      <h1 className="text-2xl font-semibold tracking-tight">{contract.object_description}</h1>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        {contract.status && <Badge variant="secondary">{contract.status}</Badge>}
        <span>{contract.entity?.name}</span>
      </div>

      <div className="mt-6">
        <ContractPlainSummary
          data={{
            objectDescription: contract.object_description,
            contractorName: contract.entity?.name ?? null,
            contractorHref: contract.entity ? `/orgaos/${contract.entity.id}` : null,
            supplierName: contract.supplier?.name ?? null,
            supplierHref: contract.supplier ? `/fornecedores/${contract.supplier.id}` : null,
            date: contract.signed_at,
            contractedValue: contract.global_value ?? contract.initial_value,
            committedValue: summary?.empenhado ?? null,
            liquidatedValue: summary?.liquidado ?? null,
            paidValue: summary?.pago ?? 0,
          }}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <AddToInvestigation
          recordType="contract"
          recordId={contract.id}
          title={contract.object_description}
          sourceUrl={contract.source_url}
        />
        {contract.source_url && (
          <Button asChild variant="outline" size="sm">
            <a href={contract.source_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4" /> Ver registro oficial
            </a>
          </Button>
        )}
      </div>

      <section className="mt-8">
        <SectionHeading
          title="Pagamentos e execução"
          description="Estágios separados: reservado (empenhado), conferido (liquidado) e pago."
          className="mb-4"
        />
        <Card>
          <CardContent className="overflow-x-auto p-0">
            {payments.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">
                Ainda não há lançamentos de execução sincronizados para este contrato.
                Ausência de dado não significa que não houve pagamento.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data</TableHead>
                    <TableHead>Estágio</TableHead>
                    <TableHead>Descrição</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell className="text-muted-foreground">
                        {formatDate(payment.reference_date)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={payment.stage === "pago" ? "success" : "muted"}>
                          {STAGE_LABEL[payment.stage] ?? payment.stage}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-md text-sm">{payment.description ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(payment.value)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <div className="mt-3">
          <DataNotice>
            “Pago” é o dinheiro que efetivamente saiu. “Empenhado” apenas reserva o
            orçamento e “liquidado” confirma a entrega — nenhum dos dois é pagamento.
          </DataNotice>
        </div>
      </section>

      <section className="mt-8">
        <details className="group rounded-lg border bg-card">
          <summary className="cursor-pointer list-none px-5 py-4 text-sm font-medium">
            Detalhes técnicos do contrato
            <span className="ml-2 text-xs font-normal text-muted-foreground group-open:hidden">
              (mostrar)
            </span>
          </summary>
          <div className="border-t px-5 py-4">
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Número" value={contract.number} />
              <Field label="Nº PNCP" value={contract.pncp_control_number} />
              <Field label="Processo" value={contract.process_number} />
              <Field label="Assinatura" value={formatDate(contract.signed_at)} />
              <Field
                label="Vigência"
                value={`${formatDate(contract.effective_from)} — ${formatDate(contract.effective_until)}`}
              />
              <Field label="Fonte" value={contract.source?.name} />
            </dl>
          </div>
        </details>
      </section>

      <section className="mt-4">
        <details className="group rounded-lg border bg-card">
          <summary className="cursor-pointer list-none px-5 py-4 text-sm font-medium">
            Termos aditivos ({contract.amendments.length})
            <span className="ml-2 text-xs font-normal text-muted-foreground group-open:hidden">
              (mostrar)
            </span>
          </summary>
          <div className="overflow-x-auto border-t">
            {contract.amendments.length === 0 ? (
              <p className="p-5 text-sm text-muted-foreground">Nenhum aditivo registrado.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Termo</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Acréscimo</TableHead>
                    <TableHead className="text-right">Redução</TableHead>
                    <TableHead>Assinatura</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contract.amendments.map((amendment) => (
                    <TableRow key={amendment.id}>
                      <TableCell>{amendment.term_number ?? "—"}</TableCell>
                      <TableCell>{amendment.amendment_type ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(amendment.value_added)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(amendment.value_reduced)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(amendment.signed_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </details>
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm">{value || "—"}</dd>
    </div>
  );
}
