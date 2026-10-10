import Link from "next/link";
import type { Metadata } from "next";
import { Info } from "lucide-react";

import { EmptyState, ErrorState, Pagination } from "@/components/common";
import { FindingCard } from "@/components/finding-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { listFindings } from "@/lib/api";
import type { Finding, Page } from "@/lib/types";

export const metadata: Metadata = { title: "Achados de auditoria" };

const SEVERITIES = [
  { value: "", label: "Todos" },
  { value: "relevante", label: "Relevantes" },
  { value: "atencao", label: "Atenção" },
  { value: "info", label: "Informativos" },
];

export default async function FindingsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; severity?: string; status?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  let data: (Page<Finding> & { aviso?: string }) | null = null;
  let error: string | null = null;
  try {
    data = await listFindings({ page, page_size: 20, severity: params.severity, status: params.status });
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar achados.";
  }

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Achados de auditoria</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Indicadores gerados automaticamente a partir de dados públicos. Servem para
          orientar a verificação humana — não são provas de irregularidade nem
          acusações.
        </p>
      </header>

      <Alert variant="info" className="mb-6">
        <Info />
        <AlertDescription>
          {data?.aviso ??
            "Anomalias estatísticas não constituem conclusão de irregularidade. Sempre confira os registros originais."}
        </AlertDescription>
      </Alert>

      <div className="mb-6 flex flex-wrap gap-2">
        {SEVERITIES.map((severity) => (
          <Link key={severity.label} href={`/achados${severity.value ? `?severity=${severity.value}` : ""}`}>
            <Badge variant={params.severity === severity.value || (!params.severity && !severity.value) ? "default" : "muted"}>
              {severity.label}
            </Badge>
          </Link>
        ))}
      </div>

      {error && <ErrorState title="Não foi possível carregar os achados" description={error} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="Nenhum achado no momento"
          description="Execute o motor de auditoria após sincronizar contratações com itens e resultados homologados."
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="space-y-3">
            {data.items.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
          <div className="mt-6">
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              basePath="/achados"
              params={{ severity: params.severity, status: params.status }}
            />
          </div>
        </>
      )}
    </div>
  );
}
