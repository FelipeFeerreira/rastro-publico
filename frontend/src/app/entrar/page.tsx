"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login as loginRequest, register as registerRequest } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = React.useState<"login" | "register">("login");
  const [email, setEmail] = React.useState("");
  const [name, setName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "register") {
        await registerRequest({ email, full_name: name, password });
      }
      const token = await loginRequest({ email, password });
      localStorage.setItem("rp_token", token.access_token);
      localStorage.setItem("rp_refresh", token.refresh_token);
      router.push("/investigacoes");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível autenticar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container flex justify-center py-16">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <ShieldCheck className="size-8 text-primary" />
          <CardTitle>{mode === "login" ? "Entrar" : "Criar conta"}</CardTitle>
          <CardDescription>
            Acesse seu espaço de investigação, salve evidências e gere relatórios.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="text-sm font-medium" htmlFor="name">
                  Nome completo
                </label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
              </div>
            )}
            <div>
              <label className="text-sm font-medium" htmlFor="email">
                E-mail
              </label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor="password">
                Senha
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="size-4 animate-spin" />}
              {mode === "login" ? "Entrar" : "Criar conta e entrar"}
            </Button>
          </form>
          <button
            type="button"
            className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Não tem conta? Cadastre-se" : "Já tem conta? Entre"}
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
