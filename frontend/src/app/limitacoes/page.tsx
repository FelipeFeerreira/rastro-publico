import type { Metadata } from "next";

export const metadata: Metadata = { title: "Limitações" };

export default function LimitationsPage() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Limitações</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Reconhecer os limites da análise é parte essencial de uma plataforma de
        transparência responsável.
      </p>
      <div className="prose-rp mt-8">
        <h2>Cobertura e completude</h2>
        <p>
          A completude dos dados depende do envio das informações pelos próprios órgãos às
          fontes oficiais. Alguns entes podem não estar integralmente representados, e a
          cobertura geográfica ou temporal pode variar.
        </p>

        <h2>Atualização</h2>
        <p>
          Os dados são sincronizados periodicamente e podem estar desatualizados em relação
          à fonte. O timestamp da última coleta é exibido quando disponível.
        </p>

        <h2>Comparabilidade de preços</h2>
        <p>
          Descrições de itens variam entre órgãos. Especificações técnicas, frete, prazos,
          garantias e demais condições contratuais nem sempre são capturados. A comparação é
          uma aproximação, não um laudo.
        </p>

        <h2>Anomalias são indicadores</h2>
        <p>
          Achados automáticos apontam padrões que merecem verificação. Podem ter explicações
          legítimas — demanda sazonal, especificidades do objeto, monopólios, emergências ou
          restrições de mercado. Nunca constituem prova de irregularidade.
        </p>

        <h2>Dados pessoais</h2>
        <p>
          Dados de agentes públicos são apresentados apenas no exercício da função pública,
          quando legalmente disponíveis. A plataforma não expõe informações privadas
          desnecessárias.
        </p>
      </div>
    </div>
  );
}
