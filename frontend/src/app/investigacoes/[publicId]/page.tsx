"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download, FileText, Loader2, Plus } from "lucide-react";

import { EmptyState } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API_BASE_URL, getInvestigation, addEvidence } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Investigation } from "@/lib/types";

export default function InvestigationDetailPage({
  params,
}: {
  params: Promise<{ publicId: string }>;
}) {
  const { publicId } = React.use(params);
  const router = useRouter();
  const [token, setToken] = React.useState<string | null>(null);
  const [investigation, setInvestigation] = React.useState<Investigation | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [note, setNote] = React.useState("");
  const [noteTitle, setNoteTitle] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  const reload = React.useCallback(
    async (authToken: string) => {
      try {
        setInvestigation(await getInvestigation(authToken, publicId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Não foi possível carregar a investigação.");
      }
    },
    [publicId],
  );

  React.useEffect(() => {
    const stored = localStorage.getItem("rp_token");
    setToken(stored);
    if (!stored) {
      router.push("/entrar");
      return;
    }
    reload(stored);
  }, [reload, router]);

  const addNote = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || !noteTitle.trim()) return;
    setSaving(true);
    try {
      await addEvidence(token, publicId, {
        kind: "note",
        title: noteTitle.trim(),
        note: note.trim() || null,
      });
      setNote("");
      setNoteTitle("");
      await reload(token);
    } finally {
      setSaving(false);
    }
  };

  const downloadPdf = async () => {
    if (!token) return;
    const response = await fetch(`${API_BASE_URL}/investigacoes/${publicId}/relatorio.pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `relatorio-${publicId}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="container py-16">
        <EmptyState title="Investigação indisponível" description={error} />
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="container flex items-center gap-2 py-16 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Carregando…
      </div>
    );
  }

  return (
    <div className="container py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/investigacoes" className="hover:text-foreground">
          Investigações
        </Link>
        <span className="mx-2">/</span>
        <span>{investigation.public_id}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{investigation.title}</h1>
          {investigation.description && (
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              {investigation.description}
            </p>
          )}
          <Badge variant="secondary" className="mt-3">
            {investigation.status}
          </Badge>
        </div>
        <Button variant="outline" onClick={downloadPdf}>
          <Download className="size-4" /> Exportar PDF
        </Button>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="size-4 text-primary" /> Evidências
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(investigation.evidence_items ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Nenhuma evidência ainda. Salve registros a partir das páginas de
                  contratações, contratos, achados ou adicione anotações.
                </p>
              ) : (
                <ul className="divide-y">
                  {(investigation.evidence_items ?? []).map((evidence) => (
                    <li key={evidence.id} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium">{evidence.title}</p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant="muted">{evidence.kind}</Badge>
                            {evidence.source_url && (
                              <a
                                href={evidence.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline"
                              >
                                fonte
                              </a>
                            )}
                            <span>{formatDateTime(evidence.created_at)}</span>
                          </div>
                          {evidence.note && (
                            <p className="mt-1 text-sm text-muted-foreground">{evidence.note}</p>
                          )}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Adicionar anotação</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={addNote} className="space-y-3">
                <Input
                  value={noteTitle}
                  onChange={(event) => setNoteTitle(event.target.value)}
                  placeholder="Título da anotação"
                />
                <Textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Observações, hipóteses, referências…"
                  rows={4}
                />
                <Button type="submit" size="sm" disabled={saving || !noteTitle.trim()}>
                  {saving ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
                  Adicionar
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardContent className="p-5 text-xs text-muted-foreground">
              O relatório em PDF reúne registros citados, fontes, metodologia, limitações
              e orientações para encaminhamento a órgãos de controle (ex.: Fala.BR e
              Tribunais de Contas).
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
