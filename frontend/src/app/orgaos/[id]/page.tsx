import Link from "next/link";
import { notFound } from "next/navigation";

import { DataNotice, EmptyState, SectionHeading } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, getEntity, listEntityContracts, listEntityProcurements } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const SPHERE: Record<string, string> = {
  federal: "Federal",
  state: "Estadual",
  municipal: "Municipal",
  other: "—",
};

export default async function EntityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let entity;
  try {
    entity = await getEntity(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const [procurements, contracts] = await Promise.all([
    listEntityProcurements(id).catch(() => null),
    listEntityContracts(id).catch(() => null),
  ]);

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/orgaos" className="hover:text-foreground">
          Órgãos
        </Link>
        <span className="mx-2">/</span>
        <span>{entity.name}</span>
      </nav>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{entity.name}</h1>
        <Badge variant="secondary">{SPHERE[entity.sphere] ?? entity.sphere}</Badge>
      </div>
      {entity.cnpj && <p className="mt-2 text-sm text-muted-foreground">CNPJ {entity.cnpj}</p>}

      <div className="mt-4">
        <DataNotice>
          Dados consolidados de fontes públicas. A cobertura depende do envio de
          informações pelo próprio órgão ao portal de origem.
        </DataNotice>
      </div>

      <section className="mt-8">
        <SectionHeading title="Contratações recentes" className="mb-4" />
        {!procurements || procurements.items.length === 0 ? (
          <EmptyState title="Nenhuma contratação sincronizada" />
        ) : (
          <ul className="space-y-3">
            {procurements.items.map((item) => (
              <li key={item.id}>
                <Link href={`/contratacoes/${item.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-sm font-medium">{item.object_description}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDate(item.published_at)} · {item.modality_name}
                        </p>
                      </div>
                      <p className="font-semibold tabular-nums">
                        {formatCurrency(item.estimated_total)}
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
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
                        <p className="mt-1 text-xs text-muted-foreground">{contract.supplier?.name}</p>
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
