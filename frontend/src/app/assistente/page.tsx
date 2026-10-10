"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BookOpen, Loader2, Send, Sparkles } from "lucide-react";

import { DataNotice } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { askAssistant } from "@/lib/api";
import type { AssistantAnswer } from "@/lib/types";

const SUGGESTIONS = [
  "O que é valor homologado?",
  "O que significa SRP?",
  "Como funciona uma dispensa de licitação?",
  "O que é um termo aditivo?",
];

function AssistantContent() {
  const searchParams = useSearchParams();
  const [question, setQuestion] = React.useState(searchParams.get("q") ?? "");
  const [answer, setAnswer] = React.useState<AssistantAnswer | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const ask = async (value?: string) => {
    const text = (value ?? question).trim();
    if (!text) return;
    setQuestion(text);
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await askAssistant(text));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível responder agora.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-3xl py-10">
      <div className="text-center">
        <div className="mx-auto inline-flex size-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Sparkles className="size-5" />
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight">Assistente de pesquisa</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Faça perguntas sobre gastos, contratos e terminologia. Os valores financeiros são
          calculados de forma determinística a partir dos dados oficiais — nunca pela IA.
        </p>
      </div>

      <form
        className="mt-8 space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          ask();
        }}
      >
        <Textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ex.: Quanto a prefeitura de Campinas gastou com computadores em 2026?"
          rows={3}
        />
        <div className="flex items-center justify-between">
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.slice(0, 2).map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => ask(suggestion)}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <Button type="submit" disabled={loading || !question.trim()}>
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            Perguntar
          </Button>
        </div>
      </form>

      {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

      {answer && (
        <Card className="mt-6 animate-fade-in">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Resposta</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={answer.grounded ? "success" : "muted"}>
                {answer.grounded ? "Fundamentada em dados" : "Sem dados suficientes"}
              </Badge>
              {answer.provider !== "disabled" && <Badge variant="secondary">IA: {answer.provider}</Badge>}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed">{answer.answer}</p>

            {answer.computed && (
              <div className="rounded-md border bg-muted/30 p-3 text-sm">
                <p className="mb-2 font-medium">Cálculo determinístico</p>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs text-muted-foreground">
                  {JSON.stringify(answer.computed, null, 2)}
                </pre>
              </div>
            )}

            {answer.citations.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium">Fontes e referências</p>
                <ul className="space-y-1 text-sm">
                  {answer.citations.map((citation, index) => (
                    <li key={index}>
                      {citation.url ? (
                        <Link href={citation.url} className="text-primary hover:underline">
                          {citation.title ?? citation.url}
                        </Link>
                      ) : (
                        String(citation.title ?? citation.term ?? "referência")
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {answer.limitations.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                {answer.limitations.map((limitation, index) => (
                  <li key={index}>{limitation}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <div className="mt-6">
        <DataNotice>
          <span className="inline-flex items-center gap-1">
            <BookOpen className="size-3.5" /> As respostas citam fontes públicas. Confira
            sempre o registro original antes de tirar conclusões.
          </span>
        </DataNotice>
      </div>
    </div>
  );
}

export default function AssistantPage() {
  return (
    <React.Suspense fallback={<div className="container py-16 text-sm text-muted-foreground">Carregando…</div>}>
      <AssistantContent />
    </React.Suspense>
  );
}
