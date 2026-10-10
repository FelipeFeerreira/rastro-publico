import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";

import { DataNotice, FindingStatusBadge, SectionHeading, SeverityBadge } from "@/components/common";
import { AddToInvestigation } from "@/components/investigation/add-to-investigation";
import { FindingReview } from "@/components/investigation/finding-review";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, getFinding } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";

export default async function FindingDetailPage({
  params,
}: {
  params: Promise<{ publicId: string }>;
}) {
  const { publicId } = await params;
  let finding;
  try {
    finding = await getFinding(publicId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const metrics = finding.metrics ?? {};

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/achados" className="hover:text-foreground">
          Achados
        </Link>
        <span className="mx-2">/</span>
        <span>{finding.public_id}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <FindingStatusBadge status={finding.status} />
            {finding.rule_code && (
              <span className="font-mono text-xs text-muted-foreground">{finding.rule_code}</span>
            )}
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">{finding.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{finding.summary}</p>
        </div>
        <AddToInvestigation
          recordType="finding"
          recordId={finding.public_id}
          title={finding.title}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {finding.explanation && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Análise</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <p>{finding.explanation}</p>
                {finding.methodology && (
                  <p>
                    <span className="font-medium text-foreground">Metodologia:</span>{" "}
                    {finding.methodology}
                  </p>
                )}
                {finding.limitations && (
                  <p>
                    <span className="font-medium text-foreground">Limitações:</span>{" "}
                    {finding.limitations}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {finding.source_records && finding.source_records.length > 0 && (
            <section>
              <SectionHeading title="Registros de origem" className="mb-3" />
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Registro</TableHead>
                        <TableHead>Detalhe</TableHead>
                        <TableHead>Fonte</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {finding.source_records.slice(0, 20).map((record, index) => {
                        const rec = record as Record<string, unknown>;
                        const url = (rec.source_url as string) || (rec.url as string);
                        return (
                          <TableRow key={index}>
                            <TableCell className="font-mono text-xs">
                              {(rec.pncp_control_number as string) || (rec.pncp as string) || "—"}
                            </TableCell>
                            <TableCell className="text-sm">
                              {(rec.supplier as string) ||
                                (rec.unit_price as number)?.toString() ||
                                "—"}
                            </TableCell>
                            <TableCell>
                              {url ? (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-primary hover:underline"
                                >
                                  <ExternalLink className="size-3.5" /> abrir
                                </a>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </section>
          )}

          <section>
            <SectionHeading title="Histórico de revisão" className="mb-3" />
            <Card>
              <CardContent className="space-y-3 p-5 text-sm">
                {(finding.review_history ?? []).length === 0 ? (
                  <p className="text-muted-foreground">Sem revisões registradas.</p>
                ) : (
                  (finding.review_history ?? []).map((entry, index) => {
                    const item = entry as Record<string, unknown>;
                    return (
                      <div key={index} className="flex items-center justify-between gap-3 border-b pb-2 last:border-0">
                        <span>{String(item.status ?? "")}</span>
                        <span className="text-xs text-muted-foreground">
                          {String(item.by ?? "")} · {formatDateTime(String(item.at ?? ""))}
                        </span>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>
          </section>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Métricas do cálculo</CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(metrics).length === 0 ? (
                <p className="text-sm text-muted-foreground">Sem métricas.</p>
              ) : (
                <dl className="space-y-2 text-sm">
                  {Object.entries(metrics).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between gap-3">
                      <dt className="text-muted-foreground">{key}</dt>
                      <dd className="font-mono tabular-nums">
                        {value === null || value === undefined ? "—" : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Confiança e qualidade</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                Confiança do indicador:{" "}
                <span className="font-medium text-foreground">
                  {finding.confidence != null ? `${Math.round(finding.confidence * 100)}%` : "—"}
                </span>
              </p>
              <p>Identificado em {formatDate(finding.created_at)}.</p>
            </CardContent>
          </Card>

          <FindingReview publicId={finding.public_id} currentStatus={finding.status} />

          <Button asChild variant="link" className="px-0">
            <Link href="/metodologia">Como o motor de auditoria funciona</Link>
          </Button>
        </div>
      </div>

      <div className="mt-8">
        <DataNotice>
          Este achado é um indicador automático e reproduzível a partir dos registros de
          origem. Não constitui acusação, laudo pericial ou conclusão de órgão de
          controle.
        </DataNotice>
      </div>
    </div>
  );
}
