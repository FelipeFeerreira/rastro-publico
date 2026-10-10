import Link from "next/link";
import type { Metadata } from "next";

import { EmptyState, ErrorState, Pagination } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { listEntities } from "@/lib/api";
import type { EntitySummary, Page } from "@/lib/types";

export const metadata: Metadata = { title: "Órgãos e entidades" };

const SPHERE: Record<string, string> = {
  federal: "Federal",
  state: "Estadual",
  municipal: "Municipal",
  other: "—",
};

export default async function EntitiesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; q?: string; uf?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  let data: Page<EntitySummary> | null = null;
  let error: string | null = null;
  try {
    data = await listEntities({ page, page_size: 20, q: params.q, uf: params.uf });
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar órgãos.";
  }

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Órgãos e entidades</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Prefeituras, secretarias, autarquias e demais entidades que realizam
          contratações públicas.
        </p>
      </header>

      <form className="mb-6 flex max-w-md gap-2" action="/orgaos">
        <Input name="q" defaultValue={params.q ?? ""} placeholder="Buscar por nome" />
        <Button type="submit" variant="outline">
          Filtrar
        </Button>
      </form>

      {error && <ErrorState title="Não foi possível carregar os órgãos" description={error} />}

      {data && data.items.length === 0 && (
        <EmptyState title="Nenhum órgão encontrado" description="Ajuste os filtros ou aguarde a sincronização." />
      )}

      {data && data.items.length > 0 && (
        <>
          <ul className="space-y-3">
            {data.items.map((entity) => (
              <li key={entity.id}>
                <Link href={`/orgaos/${entity.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
                      <div>
                        <p className="font-medium">{entity.name}</p>
                        {entity.cnpj && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            CNPJ {entity.cnpj}
                          </p>
                        )}
                      </div>
                      <Badge variant="secondary">{SPHERE[entity.sphere] ?? entity.sphere}</Badge>
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
              basePath="/orgaos"
              params={{ q: params.q, uf: params.uf }}
            />
          </div>
        </>
      )}
    </div>
  );
}
