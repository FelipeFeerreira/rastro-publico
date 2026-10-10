"use client";

import * as React from "react";
import Link from "next/link";
import { Loader2, PlayCircle, RefreshCw } from "lucide-react";

import { DataNotice, EmptyState, StatCard } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE_URL } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";

interface Stats {
  contratacoes: number;
  itens: number;
  contratos: number;
  fornecedores: number;
  orgaos: number;
  municipios: number;
  achados: number;
  fontes: number;
  execucoes: number;
}

interface Run {
  id: number;
  scope: string | null;
  status: string;
  started_at: string;
  records_inserted: number;
  records_updated: number;
  error_count: number;
  message: string | null;
}

export default function AdminPanel() {
  const [token, setToken] = React.useState<string | null>(null);
  const [authorized, setAuthorized] = React.useState<boolean | null>(null);
  const [stats, setStats] = React.useState<Stats | null>(null);
  const [runs, setRuns] = React.useState<Run[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");

  const headers = React.useCallback(
    (authToken: string) => ({ "Content-Type": "application/json", Authorization: `Bearer ${authToken}` }),
    [],
  );

  const load = React.useCallback(
    async (authToken: string) => {
      const [meRes, statsRes, runsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/auth/eu`, { headers: headers(authToken) }),
        fetch(`${API_BASE_URL}/admin/estatisticas`, { headers: headers(authToken) }),
        fetch(`${API_BASE_URL}/admin/execucoes`, { headers: headers(authToken) }),
      ]);
      if (!meRes.ok) {
        setAuthorized(false);
        return;
      }
      const me = await meRes.json();
      if (me.role !== "admin") {
        setAuthorized(false);
        return;
      }
      setAuthorized(true);
      setStats(statsRes.ok ? await statsRes.json() : null);
      setRuns(runsRes.ok ? await runsRes.json() : []);
    },
    [headers],
  );

  React.useEffect(() => {
    const stored = localStorage.getItem("rp_token");
    setToken(stored);
    if (stored) load(stored);
    else setAuthorized(false);
  }, [load]);

  const triggerIngest = async () => {
    if (!token || !start || !end) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/ingestao/pncp`, {
        method: "POST",
        headers: headers(token),
        body: JSON.stringify({ start, end, with_items: false, max_pages_per_modality: 1 }),
      });
      const body = await response.json();
      setMessage(response.ok ? body.message : body.detail ?? "Falha ao agendar.");
      setTimeout(() => token && load(token), 3000);
    } finally {
      setBusy(false);
    }
  };

  const runAudit = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/auditoria/executar?limit=200`, {
        method: "POST",
        headers: headers(token),
      });
      const body = await response.json();
      setMessage(response.ok ? `${body.message} (${body.achados} achados)` : body.detail);
      if (token) load(token);
    } finally {
      setBusy(false);
    }
  };

  if (authorized === false) {
    return (
      <div className="container py-16">
        <EmptyState
          title="Acesso restrito"
          description="Esta área é exclusiva para administradores. Entre com uma conta autorizada."
          action={
            <Button asChild>
              <Link href="/entrar">Entrar</Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Painel administrativo</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Estatísticas da base local, ingestão de dados e execução do motor de auditoria.
        </p>
      </header>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard label="Contratações" value={formatNumber(stats.contratacoes)} />
          <StatCard label="Itens/resultados" value={formatNumber(stats.itens)} />
          <StatCard label="Contratos" value={formatNumber(stats.contratos)} />
          <StatCard label="Fornecedores" value={formatNumber(stats.fornecedores)} />
          <StatCard label="Achados" value={formatNumber(stats.achados)} />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ingestão PNCP</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
              <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <Button onClick={triggerIngest} disabled={busy || !start || !end}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
              Agendar ingestão
            </Button>
            <DataNotice>
              A ingestão roda em segundo plano. Datas em formato ISO. Intervalos amplos
              podem levar vários minutos.
            </DataNotice>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Motor de auditoria</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button onClick={runAudit} disabled={busy}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <PlayCircle className="size-4" />}
              Executar varredura
            </Button>
            <DataNotice>
              A varredura analisa itens comparáveis e gera achados. Regras conservadoras
              evitam falsos positivos quando há poucos dados.
            </DataNotice>
            {message && <p className="text-sm text-muted-foreground">{message}</p>}
          </CardContent>
        </Card>
      </div>

      <section className="mt-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Execuções recentes</CardTitle>
          </CardHeader>
          <CardContent>
            {runs.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma execução registrada.</p>
            ) : (
              <ul className="divide-y">
                {runs.map((run) => (
                  <li key={run.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <p className="font-mono text-xs">{run.scope}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(run.started_at)} · {run.records_inserted} novos ·{" "}
                        {run.records_updated} atualizados · {run.error_count} erros
                      </p>
                    </div>
                    <Badge variant={run.status === "success" ? "success" : run.status === "failed" ? "destructive" : "warning"}>
                      {run.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
