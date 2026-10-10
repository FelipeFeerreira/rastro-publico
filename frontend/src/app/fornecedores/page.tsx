import Link from "next/link";
import type { Metadata } from "next";

import { EmptyState, ErrorState, Pagination } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { listSuppliers } from "@/lib/api";
import { formatDocument } from "@/lib/format";
import type { Page, SupplierSummary } from "@/lib/types";

export const metadata: Metadata = { title: "Fornecedores" };

export default async function SuppliersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; q?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  let data: Page<SupplierSummary> | null = null;
  let error: string | null = null;
  try {
    data = await listSuppliers({ page, page_size: 20, q: params.q });
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar fornecedores.";
  }

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Fornecedores</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Empresas e pessoas que celebraram contratos ou venceram itens em contratações
          públicas.
        </p>
      </header>

      <form className="mb-6 flex max-w-md gap-2" action="/fornecedores">
        <Input name="q" defaultValue={params.q ?? ""} placeholder="Buscar por nome" />
        <Button type="submit" variant="outline">
          Filtrar
        </Button>
      </form>

      {error && <ErrorState title="Não foi possível carregar os fornecedores" description={error} />}

      {data && data.items.length === 0 && (
        <EmptyState title="Nenhum fornecedor encontrado" description="Ajuste os filtros ou aguarde a sincronização." />
      )}

      {data && data.items.length > 0 && (
        <>
          <ul className="grid gap-3 sm:grid-cols-2">
            {data.items.map((supplier) => (
              <li key={supplier.id}>
                <Link href={`/fornecedores/${supplier.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="flex items-center justify-between gap-3 p-5">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{supplier.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDocument(supplier.document)}
                        </p>
                      </div>
                      <Badge variant="muted">
                        {supplier.document_type === "PF" || supplier.is_individual
                          ? "Pessoa física"
                          : "Pessoa jurídica"}
                      </Badge>
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
              basePath="/fornecedores"
              params={{ q: params.q }}
            />
          </div>
        </>
      )}
    </div>
  );
}
