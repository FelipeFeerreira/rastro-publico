"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderSearch, Loader2, Plus } from "lucide-react";

import { EmptyState } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createInvestigation, listInvestigations } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Investigation } from "@/lib/types";

export default function InvestigationsPage() {
  const router = useRouter();
  const [token, setToken] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<Investigation[]>([]);
  const [title, setTitle] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [creating, setCreating] = React.useState(false);

  React.useEffect(() => {
    const stored = localStorage.getItem("rp_token");
    setToken(stored);
    if (!stored) {
      setLoading(false);
      return;
    }
    listInvestigations(stored)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || !title.trim()) return;
    setCreating(true);
    try {
      const created = await createInvestigation(token, { title: title.trim() });
      router.push(`/investigacoes/${created.public_id}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="container py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight">Minhas investigações</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Organize registros, evidências e relatórios. Suas investigações são privadas por
          padrão.
        </p>
      </header>

      {!token && !loading && (
        <EmptyState
          title="Entre para acessar seu espaço de investigação"
          description="Crie uma conta gratuita para salvar registros e gerar relatórios de evidências."
          action={
            <Button asChild>
              <Link href="/entrar">Entrar</Link>
            </Button>
          }
        />
      )}

      {token && (
        <>
          <Card className="mb-6">
            <CardContent className="p-5">
              <form onSubmit={create} className="flex flex-wrap gap-2">
                <Input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Nova investigação (ex.: Preços de medicamentos em Campinas)"
                  className="min-w-[240px] flex-1"
                />
                <Button type="submit" disabled={creating || !title.trim()}>
                  {creating ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
                  Criar
                </Button>
              </form>
            </CardContent>
          </Card>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Carregando…
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              title="Nenhuma investigação ainda"
              description="Crie a primeira e comece a salvar registros públicos como evidência."
            />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {items.map((item) => (
                <li key={item.id}>
                  <Link href={`/investigacoes/${item.public_id}`}>
                    <Card className="transition-colors hover:border-primary/40">
                      <CardContent className="p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{item.title}</p>
                            {item.description && (
                              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                                {item.description}
                              </p>
                            )}
                          </div>
                          <FolderSearch className="size-4 text-muted-foreground" />
                        </div>
                        <div className="mt-3 flex items-center gap-2">
                          <Badge variant="secondary">{item.status}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(item.created_at)}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
