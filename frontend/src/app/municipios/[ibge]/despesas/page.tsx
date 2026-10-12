import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { AlertTriangle, CalendarClock, ExternalLink, Info, Store } from "lucide-react";

import { DataNotice, EmptyState, Pagination, StatCard } from "@/components/common";
import {
  InstitutionBreakdown,
  MunicipalFinancialCards,
  PurposeText,
  describeCoverage,
} from "@/components/municipal-summary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  ApiError,
  getMunicipalSummary,
  getMunicipality,
  listMunicipalExpenses,
  listMunicipalInstitutions,
} from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

interface SearchParams {
  page?: string;
  ano?: string;
  mes?: string;
  entity_id?: string;
  stage?: string;
  supplier_name?: string;
}

const STAGE_LABEL: Record<string, string> = {
  empenhado: "Empenhado (reservado)",
  liquidado: "Liquidado (conferido)",
  pago: "Pago (registrado)",
  anulacao: "Anulado (cancelado)",
  reforco: "Reforço",
};

const MONTHS = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ ibge: string }>;
}): Promise<Metadata> {
  const { ibge } = await params;
  try {
    const muni = await getMunicipality(ibge);
    return { title: `Despesas públicas de ${muni.name}` };
  } catch {
    return { title: "Despesas municipais" };
  }
}

export default async function MunicipalExpensesPage({
  params,
  searchParams,
}: {
  params: Promise<{ ibge: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { ibge } = await params;
  const filters = await searchParams;
  const page = Number(filters.page ?? "1") || 1;
  const ano = filters.ano ? Number(filters.ano) : undefined;
  const mes = filters.mes ? Number(filters.mes) : undefined;
  const entityId = filters.entity_id ? Number(filters.entity_id) : undefined;

  let municipality;
  try {
    municipality = await getMunicipality(ibge);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    return (
      <div className="container py-16">
        <EmptyState
          title="Não foi possível carregar o painel"
          description="O serviço de dados pode estar indisponível. Tente novamente."
        />
      </div>
    );
  }

  const [summary, institutions, expenses] = await Promise.all([
    getMunicipalSummary({ municipio_ibge: ibge }).catch(() => null),
    listMunicipalInstitutions({ municipio_ibge: ibge }).catch(() => []),
    listMunicipalExpenses({
      municipio_ibge: ibge,
      page,
      page_size: 20,
      ano,
      mes,
      entity_id: entityId,
      stage: filters.stage,
      supplier_name: filters.supplier_name,
    }).catch(() => null),
  ]);

  const coverage = describeCoverage(summary?.coverage ?? null);
  const years = summary?.coverage ? Object.keys(summary.coverage.months_by_year).sort() : [];

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/" className="hover:text-foreground">
          Início
        </Link>
        <span className="mx-2">/</span>
        <Link href={`/municipios/${ibge}`} className="hover:text-foreground">
          {municipality.name}
        </Link>
        <span className="mx-2">/</span>
        <span>Despesas públicas</span>
      </nav>

      {/* Cabeçalho */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight">
            Despesas públicas de {municipality.name}
            {municipality.uf ? `/${municipality.uf}` : ""}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="secondary">Municipal</Badge>
            <Badge variant="muted">IBGE {ibge}</Badge>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Para onde foi o dinheiro público deste município. <strong>Pago</strong> é o
            dinheiro que efetivamente saiu. “Empenhado” apenas reserva e “liquidado”
            confere — não são pagamentos.
          </p>
        </div>
      </div>

      {!summary && (
        <div className="mt-8">
          <EmptyState
            title="Sem dados de despesas para este município"
            description="Ainda não há registros municipais importados para o código IBGE informado."
          />
        </div>
      )}

      {summary && (
        <>
          {/* Métrica principal: pago */}
          <section className="mt-8">
            <h2 className="mb-3 text-lg font-semibold tracking-tight">Resumo financeiro</h2>
            <MunicipalFinancialCards totals={summary} />
            <div className="mt-3">
              <DataNotice>
                Os quatro valores <strong>não podem ser somados entre si</strong>. Cada um
                é um estágio diferente da mesma despesa. O valor pago é o que realmente saiu.
              </DataNotice>
            </div>
          </section>

          {/* Totais e cobertura */}
          <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label="Eventos de despesa"
              value={formatNumber(summary.records)}
              hint="Cada evento é um lançamento — não é o número de compras"
              icon={<Info className="size-5" />}
            />
            <StatCard
              label="Período coberto"
              value={coverage ? coverage.period : "—"}
              icon={<CalendarClock className="size-5" />}
            />
            <StatCard
              label="Última atualização"
              value={formatDate(summary.coverage?.last_collected_at)}
              hint="Coleta dos dados oficiais"
              icon={<Store className="size-5" />}
            />
          </section>

          {coverage?.hasPartial && (
            <section className="mt-4">
              <div className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                <div>
                  <p className="font-medium">Cobertura parcial de alguns anos</p>
                  <p className="mt-1 text-muted-foreground">
                    {coverage.perYear
                      .filter((y) => y.partial)
                      .map((y) => `${y.year}: ${y.label} (parcial)`)
                      .join(" · ")}
                    . O ano ainda não está completo na fonte oficial — os meses ausentes
                    não foram publicados.
                  </p>
                </div>
              </div>
            </section>
          )}

          {/* Por instituição */}
          <section className="mt-8">
            <h2 className="text-lg font-semibold tracking-tight">Gastos por instituição</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Prefeitura, Câmara Municipal e SAAE separados. O valor em destaque é o pago.
            </p>
            <div className="mt-4">
              <InstitutionBreakdown items={institutions} />
            </div>
          </section>

          {/* Explorador */}
          <section className="mt-10">
            <h2 className="text-lg font-semibold tracking-tight">Explorador de despesas</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Quem recebeu, quando e quanto. Filtre por ano, mês, instituição, fornecedor e
              estágio.
            </p>

            <form
              className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5"
              action={`/municipios/${ibge}/despesas`}
            >
              <Select name="ano" defaultValue={filters.ano ?? ""} aria-label="Ano">
                <option value="">Todos os anos</option>
                {years.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </Select>
              <Select name="mes" defaultValue={filters.mes ?? ""} aria-label="Mês">
                <option value="">Todos os meses</option>
                {MONTHS.map((name, index) => (
                  <option key={name} value={index + 1}>
                    {name}
                  </option>
                ))}
              </Select>
              <Select name="entity_id" defaultValue={filters.entity_id ?? ""} aria-label="Instituição">
                <option value="">Todas as instituições</option>
                {institutions.map((inst) => (
                  <option key={inst.entity_id ?? "na"} value={inst.entity_id ?? ""}>
                    {inst.entity_name ?? "Não informada"}
                  </option>
                ))}
              </Select>
              <Select name="stage" defaultValue={filters.stage ?? ""} aria-label="Estágio">
                <option value="">Todos os estágios</option>
                <option value="pago">Pago</option>
                <option value="liquidado">Liquidado</option>
                <option value="empenhado">Empenhado</option>
                <option value="anulacao">Anulado</option>
              </Select>
              <Input
                name="supplier_name"
                defaultValue={filters.supplier_name ?? ""}
                placeholder="Fornecedor"
              />
              <Button type="submit" variant="outline" className="lg:col-span-5 lg:justify-self-start">
                Filtrar
              </Button>
            </form>

            <div className="mt-4 space-y-2">
              {!expenses || expenses.items.length === 0 ? (
                <EmptyState
                  title="Nenhum lançamento para este filtro"
                  description="Ajuste o período, a instituição, o fornecedor ou o estágio."
                />
              ) : (
                expenses.items.map((expense) => {
                  const officialUrl = expense.detail_url ?? expense.source_url;
                  const hasDetails =
                    expense.history ||
                    expense.expense_element ||
                    expense.government_subfunction ||
                    expense.funding_source;
                  return (
                    <Card key={expense.id}>
                      <CardContent className="p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium">
                              <PurposeText purpose={expense.activity_description} />
                            </p>
                            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                              <span>{expense.entity_name ?? "Instituição não informada"}</span>
                              <span className="inline-flex items-center gap-1">
                                <Store className="size-3.5" />
                                {expense.supplier_name ?? "Fornecedor não informado"}
                              </span>
                              <span className="inline-flex items-center gap-1">
                                <CalendarClock className="size-3.5" />
                                {formatDate(expense.event_date)}
                              </span>
                              {expense.government_function && (
                                <Badge variant="muted">{expense.government_function}</Badge>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-base font-semibold tabular-nums">
                              {formatCurrency(expense.value)}
                            </span>
                            <Badge variant={expense.stage === "pago" ? "success" : "muted"}>
                              {STAGE_LABEL[expense.stage] ?? expense.stage}
                            </Badge>
                            {officialUrl && (
                              <a
                                href={officialUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                              >
                                <ExternalLink className="size-3" /> ver detalhe oficial
                              </a>
                            )}
                          </div>
                        </div>

                        {hasDetails && (
                          <details className="mt-3 border-t pt-2 text-xs text-muted-foreground">
                            <summary className="cursor-pointer list-none">
                              Detalhes oficiais (texto original)
                            </summary>
                            <dl className="mt-2 space-y-1">
                              {expense.history && (
                                <div>
                                  <dt className="inline font-medium text-foreground">Histórico: </dt>
                                  <dd className="inline">{expense.history}</dd>
                                </div>
                              )}
                              {expense.government_subfunction && (
                                <div>
                                  <dt className="inline font-medium text-foreground">Subfunção: </dt>
                                  <dd className="inline">{expense.government_subfunction}</dd>
                                </div>
                              )}
                              {expense.expense_element && (
                                <div>
                                  <dt className="inline font-medium text-foreground">Categoria (elemento): </dt>
                                  <dd className="inline">{expense.expense_element}</dd>
                                </div>
                              )}
                              {expense.funding_source && (
                                <div>
                                  <dt className="inline font-medium text-foreground">Fonte do recurso: </dt>
                                  <dd className="inline">{expense.funding_source}</dd>
                                </div>
                              )}
                            </dl>
                          </details>
                        )}
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>

            {expenses && expenses.items.length > 0 && (
              <div className="mt-6">
                <Pagination
                  page={expenses.page}
                  pages={expenses.pages}
                  total={expenses.total}
                  basePath={`/municipios/${ibge}/despesas`}
                  params={{
                    ano: filters.ano,
                    mes: filters.mes,
                    entity_id: filters.entity_id,
                    stage: filters.stage,
                    supplier_name: filters.supplier_name,
                  }}
                />
              </div>
            )}
          </section>
        </>
      )}

      {/* Separação federal x municipal */}
      <section className="mt-8">
        <DataNotice>
          Esta é a despesa <strong>municipal</strong> (fonte TCE-SP). É um conjunto
          separado dos gastos <strong>federais</strong> do IFSP Campus Salto, que tem
          orçamento próprio.{" "}
          <Link href="/campus/158364" className="text-primary underline">
            Ver os gastos federais do IFSP em Salto
          </Link>
          .
        </DataNotice>
      </section>

      {/* Detalhes técnicos */}
      <section className="mt-4">
        <details className="group rounded-lg border bg-card">
          <summary className="cursor-pointer list-none px-5 py-4 text-sm font-medium">
            Detalhes técnicos e metodologia
            <span className="ml-2 text-xs font-normal text-muted-foreground group-open:hidden">
              (mostrar)
            </span>
          </summary>
          <div className="space-y-3 border-t px-5 py-4 text-sm text-muted-foreground">
            <p>Fonte: TCE-SP — Portal da Transparência Municipal (eventos de despesa).</p>
            <p>
              Estágios: <strong>Empenhado</strong> = dinheiro reservado;{" "}
              <strong>Liquidado</strong> = despesa conferida; <strong>Pago</strong> =
              pagamento registrado; <strong>Anulado</strong> = valor cancelado. Nunca
              somamos estágios diferentes.
            </p>
            <p>
              Cada linha é um <strong>evento</strong> de despesa (não um contrato, nem uma
              compra). A fonte não informa a descrição do que foi comprado.
            </p>
            <p>
              Não exibimos CPF de pessoas físicas. Mostramos apenas o nome publicado pela
              fonte.
            </p>
            <p>
              Não classificamos preços como caros ou normais sem dados comparáveis
              confiáveis.
            </p>
          </div>
        </details>
      </section>
    </div>
  );
}
