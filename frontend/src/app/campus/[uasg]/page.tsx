import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  Banknote,
  CalendarDays,
  ExternalLink,
  Landmark,
  Lock,
  Receipt,
  Store,
  Users,
} from "lucide-react";

import { CampusFinancialCards } from "@/components/campus-summary";
import { DataNotice, EmptyState, Pagination, StatCard } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, getCampus, listContracts, listSalarySources } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import type { CampusDashboard } from "@/lib/types";

interface SearchParams {
  page?: string;
  q?: string;
  supplier_name?: string;
  date_from?: string;
  date_to?: string;
  min_value?: string;
  max_value?: string;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ uasg: string }>;
}): Promise<Metadata> {
  const { uasg } = await params;
  try {
    const campus = await getCampus(uasg);
    return { title: `${campus.entity.name} — contratos e pagamentos` };
  } catch {
    return { title: "Painel do campus" };
  }
}

export default async function CampusPage({
  params,
  searchParams,
}: {
  params: Promise<{ uasg: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { uasg } = await params;
  const filters = await searchParams;
  const page = Number(filters.page ?? "1") || 1;

  let campus: CampusDashboard | null = null;
  try {
    campus = await getCampus(uasg);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    return (
      <div className="container py-16">
        <EmptyState
          title="Não foi possível carregar o painel"
          description="O serviço de dados pode estar temporariamente indisponível. Tente novamente."
        />
      </div>
    );
  }

  const [contracts, salarySources] = await Promise.all([
    listContracts({
      uasg,
      page,
      page_size: 15,
      q: filters.q,
      supplier_name: filters.supplier_name,
      date_from: filters.date_from,
      date_to: filters.date_to,
      min_value: filters.min_value,
      max_value: filters.max_value,
    }).catch(() => null),
    listSalarySources().catch(() => []),
  ]);

  const fin = campus.financials;
  const salaryCredentialMissing = salarySources.some(
    (s) => s.code === "transparencia" && !s.credentials_present,
  );

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/" className="hover:text-foreground">
          Início
        </Link>
        <span className="mx-2">/</span>
        <span>{campus.entity.name}</span>
      </nav>

      {/* Cabeçalho */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight">{campus.entity.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {campus.is_federal ? (
              <Badge variant="default">Instituição federal</Badge>
            ) : (
              <Badge variant="secondary">Unidade pública</Badge>
            )}
            <Badge variant="muted">UASG {campus.uasg}</Badge>
            {campus.municipality_name && (
              <span>
                {campus.municipality_name}
                {campus.uf ? `/${campus.uf}` : ""}
              </span>
            )}
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Tudo o que este campus contratou e pagou, a partir de dados oficiais. Valores
            “contratado” e “pago” são diferentes: contratar não é pagar.
          </p>
        </div>
        {campus.source && (
          <Button asChild variant="outline" size="sm">
            <a href={campus.source.homepage_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4" /> Fonte oficial
            </a>
          </Button>
        )}
      </div>

      {/* Resumo financeiro */}
      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Resumo financeiro</h2>
        <CampusFinancialCards values={fin} />
        <div className="mt-3">
          <DataNotice>
            Os quatro valores <strong>não são a mesma coisa</strong>. Um contrato pode
            estar assinado (contratado) sem nenhum pagamento ainda.
          </DataNotice>
        </div>
      </section>

      {/* Totais */}
      <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Contratos"
          value={formatNumber(campus.totals.contracts)}
          icon={<Landmark className="size-5" />}
        />
        <StatCard
          label="Fornecedores"
          value={formatNumber(campus.totals.suppliers)}
          icon={<Store className="size-5" />}
        />
        <StatCard
          label="Período"
          value={`${formatDate(campus.totals.first_contract_date)} — ${formatDate(campus.totals.last_contract_date)}`}
          icon={<CalendarDays className="size-5" />}
        />
        <StatCard
          label="Última atualização"
          value={formatDate(campus.totals.last_collection_at)}
          hint="Coleta dos dados oficiais"
          icon={<Receipt className="size-5" />}
        />
      </section>

      {/* Salários */}
      <section className="mt-8">
        <Card>
          <CardContent className="flex flex-wrap items-start justify-between gap-4 p-5">
            <div className="max-w-2xl">
              <h2 className="flex items-center gap-2 font-semibold">
                <Users className="size-4 text-primary" /> Funcionários e salários
              </h2>
              {salaryCredentialMissing ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  A remuneração de servidores federais vem do Portal da Transparência, que
                  exige uma chave oficial. <strong>Sem essa chave, nenhum valor é exibido</strong>{" "}
                  — não usamos estimativas.
                </p>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Consulte a remuneração mensal dos servidores deste campus na busca de
                  salários.
                </p>
              )}
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href={`/salarios?uasg=${campus.uasg}`}>
                {salaryCredentialMissing ? (
                  <>
                    <Lock className="size-4" /> Ver disponibilidade
                  </>
                ) : (
                  <>Ver salários</>
                )}
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Separação federal x municipal */}
      <section className="mt-4">
        <DataNotice>
          Este painel é da unidade <strong>federal</strong> (IFSP). A Prefeitura de Salto é
          uma instituição <strong>municipal</strong>, com orçamento e portal próprios — um
          conjunto de dados separado.{" "}
          <Link href="/municipios/3545209" className="text-primary underline">
            Ver o município de Salto
          </Link>
          .
        </DataNotice>
      </section>

      {/* Lista de contratos */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold tracking-tight">Contratos e serviços</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Filtre por data, fornecedor ou valor.
        </p>

        <form className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-6" action={`/campus/${uasg}`}>
          <Input name="q" defaultValue={filters.q ?? ""} placeholder="O que foi comprado" />
          <Input
            name="supplier_name"
            defaultValue={filters.supplier_name ?? ""}
            placeholder="Fornecedor"
          />
          <Input type="date" name="date_from" defaultValue={filters.date_from ?? ""} aria-label="De" />
          <Input type="date" name="date_to" defaultValue={filters.date_to ?? ""} aria-label="Até" />
          <Input name="min_value" defaultValue={filters.min_value ?? ""} placeholder="Valor mín." inputMode="decimal" />
          <Button type="submit" variant="outline">
            Filtrar
          </Button>
        </form>

        <div className="mt-4 space-y-3">
          {!contracts || contracts.items.length === 0 ? (
            <EmptyState
              title="Nenhum contrato para este filtro"
              description="Ajuste a data, o fornecedor ou o valor. A base pode não cobrir todo o período histórico."
            />
          ) : (
            contracts.items.map((contract) => (
              <Link key={contract.id} href={`/contratos/${contract.id}`}>
                <Card className="transition-colors hover:border-primary/40">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-sm font-medium">
                          {contract.object_description}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          {contract.supplier && (
                            <span className="inline-flex items-center gap-1">
                              <Store className="size-3.5" />
                              {contract.supplier.name}
                            </span>
                          )}
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays className="size-3.5" />
                            {formatDate(contract.signed_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-6 text-right">
                        <div>
                          <p className="text-xs text-muted-foreground">Contratado</p>
                          <p className="text-sm font-semibold tabular-nums">
                            {formatCurrency(contract.global_value ?? contract.initial_value)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Pago</p>
                          <p className="text-sm font-semibold tabular-nums text-primary">
                            {contract.paid_value != null ? formatCurrency(contract.paid_value) : "—"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))
          )}
        </div>

        {contracts && contracts.items.length > 0 && (
          <div className="mt-6">
            <Pagination
              page={contracts.page}
              pages={contracts.pages}
              total={contracts.total}
              basePath={`/campus/${uasg}`}
              params={{
                q: filters.q,
                supplier_name: filters.supplier_name,
                date_from: filters.date_from,
                date_to: filters.date_to,
                min_value: filters.min_value,
                max_value: filters.max_value,
              }}
            />
          </div>
        )}
      </section>

      {/* Detalhes técnicos (expansível) */}
      <section className="mt-8">
        <details className="group rounded-lg border bg-card">
          <summary className="cursor-pointer list-none px-5 py-4 text-sm font-medium">
            Detalhes técnicos e metodologia
            <span className="ml-2 text-xs font-normal text-muted-foreground group-open:hidden">
              (mostrar)
            </span>
          </summary>
          <div className="space-y-3 border-t px-5 py-4 text-sm text-muted-foreground">
            <p>
              Fonte: {campus.source?.name ?? "Comprasnet Contratos"} —{" "}
              {campus.source?.homepage_url && (
                <a
                  href={campus.source.homepage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline"
                >
                  acessar
                </a>
              )}
            </p>
            <p>
              Filtro por unidade gestora (UASG) {campus.uasg}. O código do órgão IFSP
              (26439) não isola o campus; usamos a UASG validada.
            </p>
            <p>
              Cada lançamento financeiro tem um identificador único (contrato + evento),
              evitando somar o mesmo pagamento duas vezes. Os estágios vêm dos empenhos
              oficiais.
            </p>
            <ul className="list-disc space-y-1 pl-5">
              {campus.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
            <p className="inline-flex items-center gap-1">
              <Banknote className="size-3.5" /> Eventos financeiros registrados:{" "}
              {formatNumber(fin.payment_events)}
            </p>
          </div>
        </details>
      </section>
    </div>
  );
}
