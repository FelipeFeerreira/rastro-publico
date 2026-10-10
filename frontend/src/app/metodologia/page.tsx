import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Metodologia" };

export default function MethodologyPage() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Metodologia</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Transparência sobre como os dados são coletados, normalizados, calculados e
        apresentados.
      </p>

      <div className="prose-rp mt-8">
        <h2>1. Coleta e proviniência</h2>
        <p>
          Os dados são obtidos de APIs e dados abertos oficiais, principalmente o{" "}
          <Link href="/fontes">Portal Nacional de Contratações Públicas (PNCP)</Link>. Cada
          registro preserva o identificador de origem (ex.: número de controle PNCP),
          a URL do registro original e o timestamp de coleta.
        </p>

        <h2>2. Estágios financeiros</h2>
        <p>
          A plataforma distingue rigorosamente os estágios da despesa pública:
        </p>
        <ul>
          <li>
            <strong>Estimado:</strong> valor previsto pela Administração antes da disputa.
          </li>
          <li>
            <strong>Homologado:</strong> valor adjudicado/contratado após a disputa.
          </li>
          <li>
            <strong>Empenhado, liquidado e pago:</strong> estágios da execução financeira,
            acompanhados quando a fonte disponibiliza tais dados.
          </li>
        </ul>
        <p>
          Um contrato publicado <strong>não</strong> é tratado como pagamento. Uma
          contratação estimada não é tratada como despesa realizada.
        </p>

        <h2>3. Cálculo de preço unitário</h2>
        <p>
          O preço unitário é calculado como <code>valor total ÷ quantidade</code>, sempre
          após validação de quantidade, unidade de medida e consistência do valor. Itens
          com dados inválidos não entram nas comparações.
        </p>

        <h2>4. Comparação de preços</h2>
        <p>
          Comparamos itens suficientemente equivalentes, agrupados por categoria e unidade
          de medida. Usamos estatística robusta: mediana, intervalo interquartil (IQR) e
          escore z modificado (MAD). Conjuntos com menos de cinco registros comparáveis não
          são considerados conclusivos.
        </p>

        <h2>5. Motor de auditoria</h2>
        <p>
          As regras são determinísticas e explicáveis. Cada achado registra as métricas
          calculadas, os registros de origem, a metodologia, as limitações e as referências
          de evidência, permitindo reprodução completa.
        </p>

        <h2>6. Papel da inteligência artificial</h2>
        <p>
          A IA é opcional e nunca é a fonte de verdade de valores. Todo cálculo financeiro é
          executado por lógica determinística no servidor. Respostas substantivas do
          assistente exigem referências às fontes.
        </p>

        <h2>7. O que a plataforma não faz</h2>
        <ul>
          <li>Não emite conclusões de irregularidade ou corrupção.</li>
          <li>Não ranqueia pessoas ou instituições como “suspeitas”.</li>
          <li>Não substitui a análise de órgãos de controle competentes.</li>
        </ul>

        <p className="mt-6">
          Veja também as <Link href="/limitacoes">limitações</Link> e a{" "}
          <Link href="/privacidade">política de privacidade</Link>.
        </p>
      </div>
    </div>
  );
}
