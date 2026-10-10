import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacidade e LGPD" };

export default function PrivacyPage() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Privacidade e LGPD</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Como tratamos dados pessoais em conformidade com a Lei Geral de Proteção de Dados
        (Lei 13.709/2018) e com o interesse público na transparência.
      </p>
      <div className="prose-rp mt-8">
        <h2>Base legal e finalidade</h2>
        <p>
          O tratamento de dados tem finalidade de transparência pública e controle social,
          com base no exercício de funções públicas e no legítimo interesse público,
          observados os princípios da necessidade e da finalidade.
        </p>

        <h2>Dados de agentes públicos</h2>
        <p>
          Apresentamos dados de agentes públicos apenas quando legalmente disponíveis em
          portais oficiais e estritamente no exercício da função pública. Documentos são
          exibidos de forma mascarada quando necessário.
        </p>

        <h2>Dados de usuários</h2>
        <p>
          Contas armazenam e-mail, nome e senha com hash seguro. Investigações são privadas
          por padrão e não são exibidas publicamente.
        </p>

        <h2>Direitos do titular</h2>
        <p>
          Você pode solicitar correção de informações imprecisas, acesso e informações sobre
          o tratamento. Nos casos em que o dado provém de fonte oficial, a correção deve ser
          buscada prioritariamente junto ao órgão responsável pela publicação original.
        </p>

        <h2>Correção de dados</h2>
        <p>
          Rastreabilidade e origem permitem identificar e corrigir inconsistências. Quando a
          fonte oficial corrige um registro, a atualização é propagada na próxima
          sincronização.
        </p>
      </div>
    </div>
  );
}
