import Link from "next/link";
import type { Metadata } from "next";
import {
  Building2,
  FileText,
  Landmark,
  MapPin,
  Package,
  ScrollText,
  SearchX,
} from "lucide-react";

import { DataNotice, EmptyState, ErrorState, Pagination } from "@/components/common";
import { SearchBar } from "@/components/search/search-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { search } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { SearchGroup, SearchHit, SearchResponse } from "@/lib/types";

export const metadata: Metadata = { title: "Resultados da busca" };

const GROUP_ICON: Record<string, React.ElementType> = {
  procurement: FileText,
  contract: ScrollText,
  supplier: Landmark,
  entity: Building2,
  municipality: MapPin,
  item: Package,
};

interface SearchParams {
  q?: string;
  types?: string;
  page?: string;
  year?: string;
  uf?: string;
}

function ResultRow({ hit }: { hit: SearchHit }) {
  const Icon = GROUP_ICON[hit.type] ?? FileText;
  const href = hit.url ?? "/busca";
  return (
    <li className="border-b last:border-0">
      <Link href={href} className="flex gap-3 px-1 py-3 transition-colors hover:bg-muted/40">
        <span className="mt-0.5 text-muted-foreground">
          <Icon className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 text-sm font-medium">{hit.title}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {hit.subtitle && <span>{hit.subtitle}</span>}
            {hit.location && <span>{hit.location}</span>}
            {hit.date && <span>{formatDate(hit.date)}</span>}
            {hit.value && <span className="font-medium text-foreground">{hit.value}</span>}
          </div>
        </div>
      </Link>
    </li>
  );
}

function GroupSection({ group }: { group: SearchGroup }) {
  return (
    <section className="rounded-lg border bg-card">
      <div className="flex items-center justify-between border-b px-5 py-3">
        <h2 className="text-sm font-semibold">{group.label}</h2>
        <Badge variant="muted">{group.total}</Badge>
      </div>
      <ul className="px-4">
        {group.items.map((hit) => (
          <ResultRow key={`${hit.type}-${hit.id}`} hit={hit} />
        ))}
      </ul>
    </section>
  );
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const query = (params.q ?? "").trim();
  const page = Number(params.page ?? "1") || 1;

  let result: SearchResponse | null = null;
  let error: string | null = null;

  if (query) {
    try {
      result = await search({
        q: query,
        types: params.types,
        page,
        page_size: 8,
        year: params.year ? Number(params.year) : undefined,
        uf: params.uf,
      });
    } catch (err) {
      error = err instanceof Error ? err.message : "Erro ao buscar.";
    }
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <div className="container py-10">
      <div className="mx-auto max-w-3xl">
        <SearchBar defaultValue={query} autoFocus={!query} />
      </div>

      <div className="mx-auto mt-4 flex max-w-3xl flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Painéis de destaque:</span>
        <Link
          href="/municipios/3545209/despesas"
          className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
        >
          Salto — Despesas municipais (quem recebeu e quanto)
        </Link>
        <Link
          href="/campus/158364"
          className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
        >
          IFSP — Campus Salto (contratos e pagamentos)
        </Link>
      </div>

      <div className="mx-auto mt-8 max-w-4xl">
        {!query && (
          <EmptyState
            title="O que você quer investigar?"
            description="Digite um órgão, município, fornecedor, contrato, item ou uma pergunta em linguagem natural."
          />
        )}

        {query && error && <ErrorState title="Não foi possível concluir a busca" description={error} />}

        {query && result && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                {result.total} resultados para <span className="font-medium text-foreground">{query}</span>{" "}
                <span className="text-xs">({result.took_ms} ms)</span>
              </p>
              <Button asChild variant="outline" size="sm">
                <Link href={`/assistente?q=${encodeURIComponent(query)}`}>
                  Perguntar ao assistente
                </Link>
              </Button>
            </div>

            {result.groups.length === 0 ? (
              <div className="flex flex-col items-center rounded-lg border border-dashed py-16 text-center">
                <SearchX className="size-8 text-muted-foreground" />
                <h3 className="mt-3 font-medium">Nenhum registro encontrado</h3>
                <p className="mt-1 max-w-md text-sm text-muted-foreground">
                  A base local pode ainda não cobrir esse recorte. Tente termos mais
                  gerais, outra grafia ou verifique a página de cobertura de fontes.
                </p>
                <Button asChild variant="link" className="mt-2">
                  <Link href="/fontes">Ver fontes e cobertura</Link>
                </Button>
              </div>
            ) : (
              result.groups.map((group) => <GroupSection key={group.type} group={group} />)
            )}

            <DataNotice>
              Resultados são registros públicos. Valores estimados e homologados são
              estágios distintos e não representam, por si sós, pagamentos realizados.
            </DataNotice>

            <Pagination
              page={page}
              pages={totalPages}
              total={result.total}
              basePath="/busca"
              params={{ q: query, types: params.types, year: params.year, uf: params.uf }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
