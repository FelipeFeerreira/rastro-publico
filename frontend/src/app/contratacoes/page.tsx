import Link from "next/link";
import type { Metadata } from "next";

import { DataNotice, EmptyState, ErrorState, Pagination } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { listProcurements } from "@/lib/api";
import { formatCurrency, formatDate, modalityLabel } from "@/lib/format";
import type { Page, ProcurementSummary } from "@/lib/types";

export const metadata: Metadata = { title: "Contratações públicas" };

interface SearchParams {
  page?: string;
  year?: string;
  uf?: string;
  modality?: string;
}

export default async function ProcurementsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  let data: Page<ProcurementSummary> | null = null;
  let error: string | null = null;

  try {
    data = await listProcurements({
      page,
      page_size: 20,
      year: params.year,
      uf: params.uf,
      modality: params.modality,
    });
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar contratações.";
  }

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Contratações públicas</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Editais, avisos, dispensas e demais contratações publicadas no Portal
          Nacional de Contratações Públicas (PNCP).
        </p>
      </header>

      {error && <ErrorState title="Não foi possível carregar as contratações" description={error} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="Nenhuma contratação encontrada"
          description="Ainda não há dados sincronizados para este recorte. Execute a ingestão ou ajuste os filtros."
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <ul className="space-y-3">
            {data.items.map((item) => (
              <li key={item.id}>
                <Link href={`/contratacoes/${item.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="line-clamp-2 text-sm font-medium">
                            {item.object_description}
                          </p>
                          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                            <span>{item.entity?.name ?? "Órgão não informado"}</span>
                            {item.municipality && (
                              <span>
                                {item.municipality.name}
                                {item.municipality.uf ? `/${item.municipality.uf}` : ""}
                              </span>
                            )}
                            <span>{formatDate(item.published_at)}</span>
                            <Badge variant="secondary">{modalityLabel(item.modality)}</Badge>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold tabular-nums">
                            {formatCurrency(item.estimated_total)}
                          </p>
                          <p className="text-xs text-muted-foreground">valor estimado</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>

          <div className="mt-6">
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              basePath="/contratacoes"
              params={{ year: params.year, uf: params.uf, modality: params.modality }}
            />
          </div>
          <div className="mt-4">
            <DataNotice>
              “Valor estimado” é a previsão orçamentária, não o valor contratado nem o
              pago. Veja os resultados homologados na página de cada contratação.
            </DataNotice>
          </div>
        </>
      )}
    </div>
  );
}
