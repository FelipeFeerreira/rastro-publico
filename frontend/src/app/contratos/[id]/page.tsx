import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";

import { DataNotice, SectionHeading } from "@/components/common";
import { AddToInvestigation } from "@/components/investigation/add-to-investigation";
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
import { ApiError, getContract } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export default async function ContractDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let contract;
  try {
    contract = await getContract(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/contratacoes" className="hover:text-foreground">
          Contratos
        </Link>
        <span className="mx-2">/</span>
        <span>{contract.number ?? contract.pncp_control_number ?? contract.id}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-semibold tracking-tight">{contract.object_description}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {contract.entity && (
              <Link href={`/orgaos/${contract.entity.id}`} className="hover:text-foreground">
                {contract.entity.name}
              </Link>
            )}
            {contract.status && <Badge variant="secondary">{contract.status}</Badge>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AddToInvestigation
            recordType="contract"
            recordId={contract.id}
            title={contract.object_description}
            sourceUrl={contract.source_url}
          />
          {contract.source_url && (
            <Button asChild variant="outline" size="sm">
              <a href={contract.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="size-4" /> Registro original
              </a>
            </Button>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Valor global</p>
            <p className="mt-1 text-xl font-semibold tabular-nums">
              {formatCurrency(contract.global_value)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Fornecedor</p>
            <p className="mt-1 text-sm font-medium">
              {contract.supplier ? (
                <Link href={`/fornecedores/${contract.supplier.id}`} className="text-primary hover:underline">
                  {contract.supplier.name}
                </Link>
              ) : (
                "—"
              )}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Vigência</p>
            <p className="mt-1 text-sm">
              {formatDate(contract.effective_from)} — {formatDate(contract.effective_until)}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4">
        <DataNotice>
          O valor global do contrato não representa pagamento. A execução financeira
          (empenho, liquidação, pagamento) é acompanhada em outros sistemas oficiais.
        </DataNotice>
      </div>

      <section className="mt-8">
        <SectionHeading title="Termos aditivos" className="mb-4" />
        <Card>
          <CardContent className="overflow-x-auto p-0">
            {contract.amendments.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">Nenhum aditivo registrado.</p>
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
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
