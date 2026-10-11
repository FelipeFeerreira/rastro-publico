import Link from "next/link";
import { notFound } from "next/navigation";

import { DataNotice, EmptyState, SectionHeading, StatCard } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, getMunicipality, listProcurements } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

export default async function MunicipalityPage({ params }: { params: Promise<{ ibge: string }> }) {
  const { ibge } = await params;
  let municipality;
  try {
    municipality = await getMunicipality(ibge);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const procurements = await listProcurements({ municipality_ibge: ibge, page_size: 10 }).catch(
    () => null,
  );

  return (
    <div className="container py-10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            {municipality.name}
            {municipality.uf ? `/${municipality.uf}` : ""}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Código IBGE {municipality.ibge_code}
            {municipality.state_name ? ` · ${municipality.state_name}` : ""}
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/municipios/${municipality.ibge_code}/despesas`}>
            Ver despesas públicas (Prefeitura, Câmara, SAAE)
          </Link>
        </Button>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <StatCard label="Contratações" value={formatNumber(municipality.procurement_count)} />
        <StatCard label="Valor estimado somado" value={formatCurrency(municipality.estimated_total)} />
      </div>

      <div className="mt-4">
        <DataNotice>
          A cobertura municipal depende do envio de dados pelos órgãos ao PNCP e aos
          portais de transparência. Alguns entes podem não estar integralmente
          representados.
        </DataNotice>
      </div>

      <section className="mt-8">
        <SectionHeading title="Contratações no município" className="mb-4" />
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
                          {item.entity?.name} · {formatDate(item.published_at)}
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
    </div>
  );
}
