import type { Metadata } from "next";
import { CheckCircle2, Clock, ExternalLink, PauseCircle, XCircle } from "lucide-react";

import { DataNotice } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listSources } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Source } from "@/lib/types";

export const metadata: Metadata = { title: "Fontes de dados" };

const STATUS: Record<string, { label: string; variant: "success" | "warning" | "destructive" | "muted"; icon: React.ElementType }> = {
  active: { label: "Ativa", variant: "success", icon: CheckCircle2 },
  degraded: { label: "Degradada", variant: "warning", icon: Clock },
  unavailable: { label: "Indisponível", variant: "destructive", icon: XCircle },
  maintenance: { label: "Em preparação", variant: "muted", icon: PauseCircle },
};

export default async function SourcesPage() {
  let sources: Source[] = [];
  let error = false;
  try {
    sources = await listSources();
  } catch {
    error = true;
  }

  return (
    <div className="container max-w-4xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Fontes de dados</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        O Rastro Público consome apenas dados abertos oficiais. Cada registro exibido na
        plataforma mantém o vínculo com a fonte original e o momento da coleta.
      </p>

      {error && (
        <div className="mt-6">
          <DataNotice>
            Não foi possível carregar o catálogo de fontes agora. Verifique se a API está
            disponível.
          </DataNotice>
        </div>
      )}

      <div className="mt-8 space-y-4">
        {sources.map((source) => {
          const status = STATUS[source.status] ?? STATUS.active;
          const Icon = status.icon;
          return (
            <Card key={source.id}>
              <CardHeader className="flex-row items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-base">{source.name}</CardTitle>
                  {source.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
                  )}
                </div>
                <Badge variant={status.variant} className="gap-1 whitespace-nowrap">
                  <Icon className="size-3.5" /> {status.label}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {source.coverage_description && (
                  <p className="text-muted-foreground">
                    <span className="font-medium text-foreground">Cobertura:</span>{" "}
                    {source.coverage_description}
                  </p>
                )}
                <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span>
                    Autenticação: {source.requires_authentication ? "necessária" : "não exigida"}
                  </span>
                  <span>Licença: {source.license_name ?? "não informada"}</span>
                  <span>Última coleta: {formatDateTime(source.last_success_at)}</span>
                </div>
                <div className="flex flex-wrap gap-3 pt-1">
                  <a
                    href={source.homepage_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    <ExternalLink className="size-3.5" /> Portal oficial
                  </a>
                  {source.api_documentation_url && (
                    <a
                      href={source.api_documentation_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      <ExternalLink className="size-3.5" /> Documentação da API
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
