"use client";

import * as React from "react";
import Link from "next/link";
import { Bell, Loader2, Plus } from "lucide-react";

import { DataNotice, EmptyState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { API_BASE_URL } from "@/lib/api";

interface Subscription {
  id: number;
  kind: string;
  label: string;
  target_reference: string;
  channel: string;
  is_active: boolean;
}

interface Notification {
  id: number;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

const KINDS = [
  { value: "municipality", label: "Município (código IBGE)" },
  { value: "supplier", label: "Fornecedor (documento)" },
  { value: "government_entity", label: "Órgão (CNPJ)" },
  { value: "keyword", label: "Palavra-chave" },
];

export default function MonitoringPage() {
  const [token, setToken] = React.useState<string | null>(null);
  const [subscriptions, setSubscriptions] = React.useState<Subscription[]>([]);
  const [notifications, setNotifications] = React.useState<Notification[]>([]);
  const [kind, setKind] = React.useState("municipality");
  const [target, setTarget] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const authHeaders = (authToken: string) => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${authToken}`,
  });

  const load = React.useCallback(async (authToken: string) => {
    const [subs, notes] = await Promise.all([
      fetch(`${API_BASE_URL}/monitoramento/assinaturas`, {
        headers: authHeaders(authToken),
      }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${API_BASE_URL}/monitoramento/notificacoes`, {
        headers: authHeaders(authToken),
      }).then((r) => (r.ok ? r.json() : [])),
    ]);
    setSubscriptions(subs);
    setNotifications(notes);
  }, []);

  React.useEffect(() => {
    const stored = localStorage.getItem("rp_token");
    setToken(stored);
    if (stored) load(stored);
  }, [load]);

  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || !target.trim() || !label.trim()) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE_URL}/monitoramento/assinaturas`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ kind, target_reference: target.trim(), label: label.trim() }),
      });
      setTarget("");
      setLabel("");
      await load(token);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="container py-16">
        <EmptyState
          title="Entre para configurar alertas"
          description="Crie uma conta para acompanhar municípios, fornecedores e palavras-chave."
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
        <h1 className="text-3xl font-semibold tracking-tight">Monitoramento e alertas</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Acompanhe entidades e termos de interesse. Você receberá notificações na
          plataforma quando houver novidades relevantes.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Nova assinatura</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={create} className="space-y-3">
                <Select value={kind} onChange={(event) => setKind(event.target.value)}>
                  {KINDS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
                <Input
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                  placeholder="Identificador (ex.: 3509502, CNPJ ou termo)"
                />
                <Input
                  value={label}
                  onChange={(event) => setLabel(event.target.value)}
                  placeholder="Rótulo amigável"
                />
                <Button type="submit" disabled={loading}>
                  {loading ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
                  Assinar
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Assinaturas ativas</CardTitle>
            </CardHeader>
            <CardContent>
              {subscriptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhuma assinatura configurada.</p>
              ) : (
                <ul className="divide-y">
                  {subscriptions.map((subscription) => (
                    <li key={subscription.id} className="flex items-center justify-between py-2 text-sm">
                      <div>
                        <p className="font-medium">{subscription.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {subscription.kind} · {subscription.target_reference}
                        </p>
                      </div>
                      <Bell className="size-4 text-muted-foreground" />
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
              <CardTitle className="text-base">Notificações</CardTitle>
            </CardHeader>
            <CardContent>
              {notifications.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhuma notificação.</p>
              ) : (
                <ul className="divide-y">
                  {notifications.map((notification) => (
                    <li key={notification.id} className="py-2">
                      <p className="text-sm font-medium">{notification.title}</p>
                      <p className="text-sm text-muted-foreground">{notification.body}</p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <div className="mt-4">
            <DataNotice>
              As notificações dependem de tarefas de verificação periódica. Em instalações
              sem agendador configurado, elas podem não ser geradas automaticamente.
            </DataNotice>
          </div>
        </div>
      </div>
    </div>
  );
}
