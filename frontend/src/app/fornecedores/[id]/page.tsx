import Link from "next/link";
import { notFound } from "next/navigation";
import { FileText, ScrollText } from "lucide-react";

import { DataNotice, EmptyState, SectionHeading, StatCard } from "@/components/common";
import { FindingCard } from "@/components/finding-card";
import { AddToInvestigation } from "@/components/investigation/add-to-investigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, getSupplier, getSupplierFindings, listSupplierContracts } from "@/lib/api";
import { formatCurrency, formatDate, formatDocument, formatNumber } from "@/lib/format";

export default async function SupplierDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let supplier;
  try {
    supplier = await getSupplier(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const [contracts, findings] = await Promise.all([
    listSupplierContracts(id).catch(() => null),
    getSupplierFindings(id).catch(() => []),
  ]);

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/fornecedores" className="hover:text-foreground">
          Fornecedores
        </Link>
        <span className="mx-2">/</span>
        <span>{supplier.name}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{supplier.name}</h1>
          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <span>{formatDocument(supplier.document)}</span>
            <Badge variant="muted">
              {supplier.is_individual ? "Pessoa física" : "Pessoa jurídica"}
            </Badge>
          </div>
        </div>
        <AddToInvestigation recordType="procurement" recordId={supplier.id} title={supplier.name} />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Contratos" value={formatNumber(supplier.contract_count ?? 0)} icon={<ScrollText className="size-5" />} />
        <StatCard
          label="Valor total contratado"
          value={formatCurrency(supplier.total_contract_value ?? 0)}
        />
        <StatCard
          label="Contratações com itens vencidos"
          value={formatNumber(supplier.procurement_count ?? 0)}
          icon={<FileText className="size-5" />}
        />
      </div>

      <div className="mt-4">
        <DataNotice>
          Valores contratados (globais) não equivalem a pagamentos efetivados. Consulte
          cada contrato e a execução orçamentária na fonte original.
        </DataNotice>
      </div>

      <section className="mt-8">
        <SectionHeading title="Achados de auditoria" description="Indicadores automáticos associados a este fornecedor." className="mb-4" />
        {findings.length === 0 ? (
          <EmptyState title="Nenhum achado associado" description="Não foram identificados indicadores automáticos para este fornecedor." />
        ) : (
          <div className="space-y-3">
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <SectionHeading title="Contratos" className="mb-4" />
        {!contracts || contracts.items.length === 0 ? (
          <EmptyState title="Nenhum contrato sincronizado" />
        ) : (
          <ul className="space-y-3">
            {contracts.items.map((contract) => (
              <li key={contract.id}>
                <Link href={`/contratos/${contract.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-sm font-medium">{contract.object_description}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {contract.entity?.name} · {formatDate(contract.signed_at)}
                        </p>
                      </div>
                      <p className="font-semibold tabular-nums">
                        {formatCurrency(contract.global_value)}
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
