"use client";

import * as React from "react";
import Link from "next/link";
import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { API_BASE_URL } from "@/lib/api";

const STATUSES = [
  { value: "aguardando_verificacao", label: "Aguardando verificação" },
  { value: "em_analise", label: "Em análise" },
  { value: "documentado", label: "Documentado" },
  { value: "encerrado_apos_analise", label: "Encerrado após análise" },
  { value: "sem_irregularidade", label: "Sem irregularidade" },
];

export function FindingReview({ publicId, currentStatus }: { publicId: string; currentStatus: string }) {
  const [token, setToken] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState(currentStatus);
  const [state, setState] = React.useState<"idle" | "saving" | "done" | "error" | "unauth">("idle");

  React.useEffect(() => setToken(localStorage.getItem("rp_token")), []);

  if (!token) {
    return (
      <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
        <Link href="/entrar" className="text-primary hover:underline">
          Entre
        </Link>{" "}
        para registrar a revisão deste achado.
      </div>
    );
  }

  const submit = async () => {
    setState("saving");
    try {
      const response = await fetch(`${API_BASE_URL}/achados/${publicId}/revisao`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      if (response.status === 401) {
        setState("unauth");
        return;
      }
      if (!response.ok) throw new Error();
      setState("done");
    } catch {
      setState("error");
    }
  };

  return (
    <div className="space-y-3 rounded-md border p-4">
      <p className="text-sm font-medium">Registrar revisão</p>
      <Select value={status} onChange={(event) => setStatus(event.target.value)}>
        {STATUSES.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={submit} disabled={state === "saving"}>
          {state === "saving" ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
          Salvar revisão
        </Button>
        {state === "done" && <span className="text-sm text-success">Revisão registrada.</span>}
        {state === "error" && <span className="text-sm text-destructive">Falha ao salvar.</span>}
        {state === "unauth" && <span className="text-sm text-destructive">Sessão expirada.</span>}
      </div>
    </div>
  );
}
