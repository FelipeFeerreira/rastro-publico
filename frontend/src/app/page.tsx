import Link from "next/link";
import {
  ArrowRight,
  FileSearch,
  Landmark,
  LineChart,
  Scale,
  SearchCheck,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import { DataNotice, StatCard } from "@/components/common";
import { SearchBar } from "@/components/search/search-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getCoverage } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { Coverage } from "@/lib/types";

const EXAMPLES = [
  "Quanto minha prefeitura gastou com medicamentos?",
  "Quais empresas receberam contratos públicos na minha cidade?",
  "Quanto ganha determinado servidor público?",
  "Quanto um deputado declarou em despesas parlamentares?",
  "Existem diferenças relevantes nos preços de materiais escolares?",
];

const FEATURES = [
  {
    icon: SearchCheck,
    title: "Busca simples",
    description:
      "Pesquise por órgãos, municípios, fornecedores, contratos e itens usando linguagem comum.",
  },
  {
    icon: LineChart,
    title: "Comparação de preços",
    description:
      "Compare preços de contratações equivalentes com estatística robusta e metodologia explicada.",
  },
  {
    icon: ShieldAlert,
    title: "Investigação automatizada",
    description:
      "O motor de auditoria sinaliza possíveis anomalias e organiza evidências para verificação humana.",
  },
];

const STEPS = [
  {
    icon: FileSearch,
    title: "1. Coleta",
    description: "Conectores consomem dados abertos oficiais e os normalizam em uma base única.",
  },
  {
    icon: Landmark,
    title: "2. Organização",
    description: "Contratações, itens, fornecedores e órgãos são ligados preservando a fonte original.",
  },
  {
    icon: Scale,
    title: "3. Análise",
    description: "Regras determinísticas comparam preços e identificam padrões que merecem revisão.",
  },
  {
    icon: Sparkles,
    title: "4. Investigação",
    description: "Você reúne evidências, gera relatórios e decide os próximos passos com responsabilidade.",
  },
];

async function safeCoverage(): Promise<Coverage | null> {
  try {
    return await getCoverage();
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const coverage = await safeCoverage();

  return (
    <div>
      <section className="relative overflow-hidden border-b">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,hsl(var(--primary)/0.08),transparent)]" />
        <div className="container relative flex flex-col items-center py-20 text-center md:py-28">
          <Badge variant="secondary" className="mb-6 gap-1.5">
            <ShieldAlert className="size-3.5" />
            Plataforma independente e apartidária
          </Badge>
          <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-tight md:text-5xl">
            Para onde vai o dinheiro público?
          </h1>
          <p className="mt-5 max-w-2xl text-balance text-lg text-muted-foreground">
            Pesquise, entenda e investigue como os recursos públicos são utilizados no
            Brasil.
          </p>

          <div className="mt-8 w-full max-w-3xl">
            <SearchBar size="lg" />
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((example) => (
              <Link
                key={example}
                href={`/busca?q=${encodeURIComponent(example)}`}
                className="rounded-full border bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
              >
                {example}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="container py-14">
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="border-border/60">
              <CardHeader>
                <div className="mb-2 inline-flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <feature.icon className="size-5" />
                </div>
                <CardTitle>{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      <section className="container pb-4">
        <Link href="/campus/158364" className="group block">
          <Card className="border-primary/30 bg-primary/5 transition-colors hover:border-primary/60">
            <CardContent className="flex flex-col items-start justify-between gap-4 p-6 md:flex-row md:items-center">
              <div className="flex items-start gap-4">
                <div className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Landmark className="size-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-primary">
                    Painel em destaque
                  </p>
                  <h2 className="mt-1 text-lg font-semibold tracking-tight">
                    IFSP — Campus Salto
                  </h2>
                  <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                    Quanto o campus contratou e quanto realmente pagou, com fornecedores,
                    datas e valores. Unidade federal, em Salto/SP.
                  </p>
                </div>
              </div>
              <Button variant="default" className="shrink-0">
                Abrir painel <ArrowRight className="size-4" />
              </Button>
            </CardContent>
          </Card>
        </Link>
      </section>

      <section className="border-y bg-muted/30 py-14">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Dados disponíveis hoje</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Cobertura baseada nos registros já sincronizados nesta instalação.
            </p>
          </div>
          {coverage ? (
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Contratações" value={formatNumber(coverage.contratacoes)} icon={<Landmark className="size-5" />} />
              <StatCard label="Contratos" value={formatNumber(coverage.contratos)} icon={<FileSearch className="size-5" />} />
              <StatCard label="Fornecedores" value={formatNumber(coverage.fornecedores)} icon={<Scale className="size-5" />} />
              <StatCard
                label="Preços registrados"
                value={formatNumber(coverage.resultados_preco)}
                icon={<LineChart className="size-5" />}
              />
            </div>
          ) : (
            <div className="mt-8">
              <DataNotice>
                Não foi possível carregar as estatísticas de cobertura agora. A API pode
                estar indisponível ou ainda sem dados sincronizados.
              </DataNotice>
            </div>
          )}
          <div className="mt-6">
            <DataNotice>{coverage?.aviso ?? "Os dados provêm de fontes públicas oficiais."}</DataNotice>
          </div>
        </div>
      </section>

      <section className="container py-14">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight">Como funciona</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Do dado público bruto até uma investigação organizada e verificável.
          </p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          {STEPS.map((step) => (
            <Card key={step.title} className="border-border/60 bg-transparent shadow-none">
              <CardHeader>
                <step.icon className="size-5 text-primary" />
                <CardTitle className="text-base">{step.title}</CardTitle>
                <CardDescription>{step.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      <section className="container pb-6">
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col items-start justify-between gap-4 p-8 md:flex-row md:items-center">
            <div>
              <h2 className="text-xl font-semibold">Encontrou algo que merece atenção?</h2>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                Reúna registros, compare preços e organize um relatório de evidências.
                Anomalias não são provas — são pontos de partida para a verificação.
              </p>
            </div>
            <Button asChild size="lg">
              <Link href="/achados">
                Ver achados de auditoria <ArrowRight className="size-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
