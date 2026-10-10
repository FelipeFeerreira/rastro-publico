import * as React from "react";
import Link from "next/link";
import { AlertTriangle, ChevronLeft, ChevronRight, Inbox, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SectionHeading({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-3", className)}>
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {icon && <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>}
      </CardContent>
    </Card>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
      <Inbox className="size-8 text-muted-foreground" />
      <h3 className="mt-3 font-medium">{title}</h3>
      {description && (
        <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 py-12 text-center">
      <AlertTriangle className="size-7 text-destructive" />
      <h3 className="mt-3 font-medium">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  basePath,
  params,
}: {
  page: number;
  pages: number;
  total: number;
  basePath: string;
  params: Record<string, string | number | undefined>;
}) {
  const buildHref = (target: number) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    search.set("page", String(target));
    return `${basePath}?${search.toString()}`;
  };

  if (pages <= 1) {
    return (
      <p className="text-sm text-muted-foreground">
        {total} {total === 1 ? "registro" : "registros"}
      </p>
    );
  }

  return (
    <div className="flex items-center justify-between gap-4">
      <p className="text-sm text-muted-foreground">
        Página {page} de {pages} · {total} registros
      </p>
      <div className="flex items-center gap-2">
        <Button asChild variant="outline" size="sm" disabled={page <= 1}>
          <Link
            href={buildHref(Math.max(1, page - 1))}
            aria-disabled={page <= 1}
            className={page <= 1 ? "pointer-events-none opacity-50" : ""}
          >
            <ChevronLeft className="size-4" /> Anterior
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm" disabled={page >= pages}>
          <Link
            href={buildHref(Math.min(pages, page + 1))}
            aria-disabled={page >= pages}
            className={page >= pages ? "pointer-events-none opacity-50" : ""}
          >
            Próxima <ChevronRight className="size-4" />
          </Link>
        </Button>
      </div>
    </div>
  );
}

export function DataNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
      <Info className="mt-0.5 size-3.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

const SEVERITY: Record<string, { label: string; variant: "warning" | "destructive" | "muted" }> = {
  relevante: { label: "Relevante", variant: "destructive" },
  atencao: { label: "Atenção", variant: "warning" },
  info: { label: "Informativo", variant: "muted" },
};

export function SeverityBadge({ severity }: { severity: string }) {
  const config = SEVERITY[severity] ?? SEVERITY.info;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

const STATUS_LABEL: Record<string, string> = {
  identificado: "Identificado automaticamente",
  aguardando_verificacao: "Aguardando verificação",
  em_analise: "Em análise",
  documentado: "Documentado",
  encerrado_apos_analise: "Encerrado após análise",
  sem_irregularidade: "Sem irregularidade",
};

export function FindingStatusBadge({ status }: { status: string }) {
  return <Badge variant="secondary">{STATUS_LABEL[status] ?? status}</Badge>;
}
