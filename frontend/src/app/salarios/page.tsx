import Link from "next/link";
import type { Metadata } from "next";
import { AlertTriangle, BadgeInfo, Building2, CalendarClock } from "lucide-react";

import { DataNotice, EmptyState, ErrorState, Pagination } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { listSalarySources, listServidores } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { Page, Person, SalarySource } from "@/lib/types";

export const metadata: Metadata = { title: "Salários de servidores públicos" };

const MONTHS = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

function referenceLabel(year: number | null, month: number | null): string {
  if (!year || !month) return "mês não informado";
  return `${MONTHS[month - 1] ?? month}/${year}`;
}

export default async function SalariesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; uasg?: string; page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  let data: Page<Person> | null = null;
  let sources: SalarySource[] = [];
  let error: string | null = null;
  try {
    [data, sources] = await Promise.all([
      listServidores({ page, page_size: 20, q: params.q, uasg: params.uasg }),
      listSalarySources().catch(() => []),
    ]);
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar servidores.";
  }

  const credentialMissing = sources.some(
    (s) => s.code === "transparencia" && !s.credentials_present,
  );

  return (
    <div className="container py-10">
      <header className="mb-6 max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight">Salários de servidores públicos</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Consulte a remuneração mensal de servidores, quando publicada oficialmente. Os
          valores são os registrados pelos órgãos — nunca estimados pela plataforma.
        </p>
      </header>

      <form className="mb-6 flex max-w-md gap-2" action="/salarios">
        <Input name="q" defaultValue={params.q ?? ""} placeholder="Buscar por nome" />
        <Input name="uasg" defaultValue={params.uasg ?? ""} placeholder="UASG (ex.: 158364)" />
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>

      {credentialMissing && (
        <Card className="mb-6 border-warning/40 bg-warning/5">
          <CardContent className="flex items-start gap-3 p-5 text-sm">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
            <div>
              <p className="font-medium">Dados federais de remuneração ainda não disponíveis</p>
              <p className="mt-1 text-muted-foreground">
                A remuneração de servidores federais (como o IFSP) vem do Portal da
                Transparência, que exige uma chave de API gratuita
                (<code>TRANSPARENCIA_API_KEY</code>). Sem essa credencial, nenhum valor é
                exibido — não usamos estimativas.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {error && <ErrorState title="Não foi possível carregar os servidores" description={error} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="Nenhum servidor encontrado"
          description="Ou não há dados de remuneração importados para este recorte, ou a credencial oficial ainda não foi configurada. Veja as fontes abaixo."
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <ul className="grid gap-3 sm:grid-cols-2">
            {data.items.map((person) => (
              <li key={person.id}>
                <Link href={`/salarios/${person.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="p-5">
                      <p className="font-medium">{person.name}</p>
                      {person.role_title && (
                        <p className="mt-1 text-sm text-muted-foreground">{person.role_title}</p>
                      )}
                      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        {person.entity_name && (
                          <span className="inline-flex items-center gap-1">
                            <Building2 className="size-3.5" />
                            {person.entity_name}
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1">
                          <CalendarClock className="size-3.5" />
                          {referenceLabel(person.latest_reference_year, person.latest_reference_month)}
                        </span>
                      </div>
                      {person.latest_gross != null && (
                        <p className="mt-3 text-sm">
                          <span className="font-semibold tabular-nums">
                            {formatCurrency(person.latest_gross)}
                          </span>{" "}
                          <span className="text-muted-foreground">bruto</span>
                          {person.latest_net != null && (
                            <>
                              {" · "}
                              <span className="font-semibold tabular-nums">
                                {formatCurrency(person.latest_net)}
                              </span>{" "}
                              <span className="text-muted-foreground">líquido</span>
                            </>
                          )}
                        </p>
                      )}
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
              basePath="/salarios"
              params={{ q: params.q, uasg: params.uasg }}
            />
          </div>
        </>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-semibold tracking-tight">Fontes de dados de remuneração</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Transparência sobre o que está disponível e o que está bloqueado.
        </p>
        <div className="mt-4 space-y-3">
          {sources.map((source) => (
            <Card key={source.code}>
              <CardContent className="flex items-start justify-between gap-4 p-5">
                <div>
                  <p className="text-sm font-medium">{source.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{source.note}</p>
                </div>
                <Badge variant={source.credentials_present ? "success" : "warning"}>
                  {source.status.replace(/_/g, " ")}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
        <DataNotice>
          <span className="inline-flex items-center gap-1">
            <BadgeInfo className="size-3.5" /> Nunca confundimos a tabela de cargos com a
            remuneração individual do mês. Cada valor tem mês de referência e fonte oficial.
          </span>
        </DataNotice>
      </section>
    </div>
  );
}
