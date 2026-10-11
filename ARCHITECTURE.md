# Arquitetura — Rastro Público

## 1. Visão geral

O Rastro Público é um **monólito modular** com fronteiras bem definidas. Evita
microserviços e complexidade prematura, mas mantém módulos desacoplados para permitir
crescimento independente.

```
┌───────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                      │
│  App Router · Server Components · Client Components · Recharts │
└───────────────────────────────┬───────────────────────────────┘
                                │ REST / JSON
┌───────────────────────────────▼───────────────────────────────┐
│                         API (FastAPI)                          │
│  /busca /contratacoes /fornecedores /orgaos /achados /assistente│
│  /investigacoes /monitoramento /admin /sources                 │
├───────────────┬───────────────┬──────────────┬────────────────┤
│  Connectors   │   Services    │   Analysis   │   AI (opcional)│
│  PNCP, ...    │ ingestão      │ preços,      │ provider       │
│               │ normalização  │ regras,      │ abstraction    │
│               │ busca         │ achados      │ RAG + guardas  │
├───────────────┴───────────────┴──────────────┴────────────────┤
│                  SQLAlchemy ORM + Alembic                      │
└───────────────────────────────┬───────────────────────────────┘
                                │
                       ┌────────▼────────┐     ┌──────────────┐
                       │   PostgreSQL    │     │    Redis     │
                       │  (FTS pt-BR)    │     │ rate limit / │
                       │                 │     │ Celery       │
                       └─────────────────┘     └──────────────┘
```

## 2. Fronteiras de módulos (backend)

| Módulo | Responsabilidade | Depende de |
|--------|------------------|------------|
| `core` | configuração, logging, segurança, rate limit | — |
| `db` | engine, sessão, base declarativa | `core` |
| `models` | schema ORM normalizado | `db` |
| `schemas` | contratos de entrada/saída (Pydantic) | `models` (enums) |
| `connectors` | clientes HTTP resilientes de fontes públicas | `core` |
| `services/normalization` | padronização de texto, números, domínios | `models` |
| `services/ingestion` | orquestra conector → normalização → banco | `connectors`, `models` |
| `services/search` | busca unificada (FTS/LIKE) e autocomplete | `models` |
| `services/analysis` | cálculo de preço, referência, regras, achados | `models` |
| `services/ai` | abstração de provedor e assistente fundamentado | `services/search` |
| `services/reporting` | relatórios de evidências (JSON + PDF) | `models` |
| `api/v1` | camada HTTP, validação, autenticação | services |

Regra: **a camada de apresentação não contém regra de negócio** e o cálculo financeiro
vive exclusivamente em `services/analysis`.

## 3. Modelo de dados (PostgreSQL)

26 tabelas normalizadas. Principais grupos:

### Proveniência e coleta
- `data_sources` — catálogo de fontes oficiais (URL, licença, cobertura, requisitos).
- `collection_runs` — cada execução de sincronização com contadores e log de erros.

### Território e órgãos
- `states`, `municipalities`, `government_entities` — chave natural: UF, código IBGE,
  CNPJ.

### Contratações
- `procurements` — contratação publicada (chave única `pncp_control_number`).
- `procurement_items` — itens com quantidade, unidade, preços estimados e
  `category_key` (chave de comparabilidade).
- `procurement_results` — resultados homologados por item, com fornecedor e preço
  unitário.
- `contracts`, `contract_amendments`, `payments`.

### Fornecedores e pessoas
- `suppliers` — CNPJ/CPF normalizado; dados de PF mascarados na exibição.
- `public_people`, `public_positions`, `remunerations` — dados de agentes públicos
  quando disponíveis.

### Auditoria
- `audit_rules` — regras determinísticas versionadas e parametrizadas.
- `audit_findings` — achados reproduzíveis com métricas, evidências, metodologia,
  limitações, confiança e histórico de revisão.
- `price_references` — estatísticas de referência por categoria/período.

### Investigação e governança
- `investigations`, `investigation_evidence`, `documents`.
- `monitoring_subscriptions`, `notifications`.
- `users`, `user_roles`, `audit_logs`.

### Índices
- Únicos: `pncp_control_number`, `cnpj`, `document`, `ibge_code`, `code`.
- GIN full-text: `to_tsvector('portuguese', search_text)` em contratações, itens,
  contratos, fornecedores, órgãos, municípios e pessoas.
- GIN trigram (`pg_trgm`) em nomes, para autocomplete tolerante a erros.
- Compostos para consultas por órgão/ano, município/ano, estágio/data.

## 4. Conector PNCP

Documentação verificada em outubro de 2026:

- Consulta: `https://pncp.gov.br/api/consulta` (`/v3/api-docs`)
- Ingestão: `https://pncp.gov.br/api/pncp` (`/v3/api-docs`)

Pontos importantes observados na API real:
- `codigoModalidadeContratacao` é **obrigatório** nas consultas por publicação; a
  sincronização itera sobre as 13 modalidades da Lei 14.133/2021.
- `tamanhoPagina` deve ser **≥ 10**.
- Resposta paginada com `totalRegistros`, `totalPaginas`, `paginasRestantes`.
- Itens: `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`.
- Resultados: `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{item}/resultados`.
- O endpoint de itens é lento; a ingestão de itens é opcional e incremental.

`BaseConnector` fornece: timeout, retries com backoff exponencial, respeito a
`Retry-After`, limitação de taxa e paginação padronizada. Falhas por registro são
toleradas (`begin_nested`) sem interromper a execução completa.

### Conector Comprasnet Contratos (federal, por UASG)

`connectors/comprasnet.py` reutiliza `BaseConnector` e importa contratos de uma
**unidade gestora (UASG)** específica:

- `GET /api/contrato/ug/{uasg}` (ativos) e `/api/contrato/inativo/ug/{uasg}` (inativos).
- A **unidade gestora** (`contratante.orgao.unidade_gestora.codigo`) é a chave confiável;
  o código do órgão pai e o campo `unidade_compra` **não** isolam o campus.
- Cada registro é validado contra a UASG solicitada; divergências são rejeitadas
  (proteção contra atribuir contratos de outros campi).
- Proveniência: `contracts.source_system`, `external_id`, `uasg`, `organization_code`,
  `contract_type`, `accumulated_value`; a URL original (`/api/contrato/id/{id}`) é
  preservada em `source_url`.
- Identidade do campus: `government_entities.uasg` (entidade federal própria, distinta do
  CNPJ institucional compartilhado).

Isso mantém despesas **federais** (IFSP) separadas das **municipais**, filtráveis por
`uasg`, `source_system` e `organization_code` em `/contratos`.

### Execução financeira e remuneração

- **Pagamentos:** `GET /api/contrato/{id}/empenhos` e `/faturas` alimentam a tabela
  `payments` com um lançamento por estágio (`empenhado`, `liquidado`, `pago`),
  idempotente por `(contract_id, external_id)`. Valor contratado e valor pago são
  campos e somas distintos.
- **Remuneração:** `connectors/transparencia.py` consulta o Portal da Transparência
  (header `chave-api-dados`, obrigatório). A lotação (campus/UORG) é resolvida no
  detalhe do servidor; o código do órgão não identifica o campus. Sem a chave, o
  serviço registra a ausência de credencial e não importa nada.

## 5. Motor de análise

### Preço unitário
`preço = total ÷ quantidade`, sempre com validação de quantidade (> 0), unidade de
medida e consistência do valor. Itens inválidos são excluídos das comparações.

### Comparabilidade
Itens são agrupados por `category_key` (código de catálogo oficial quando presente;
heurística textual transparente caso contrário) e unidade canônica, dentro de uma
janela temporal. Amostras com menos de 5 registros **não são conclusivas**.

### Estatística robusta
Mediana, intervalo interquartil (IQR) e escore z modificado (MAD), resistentes a
valores extremos.

### Regras iniciais
- `unit_price_outlier` — preço unitário muito acima do padrão comparável.
- `total_above_estimate` — valor homologado acima do estimado.
- `quantity_inconsistent` — quantidade muito distante do padrão.
- `supplier_concentration` — concentração relevante em um fornecedor.
- `large_contract_amendment` — aditivo de grande proporção.

Cada achado é **reproduzível**: registra métricas calculadas, registros de origem,
metodologia, limitações, nível de confiança e histórico de revisão.

## 6. Assistente de IA

- Abstração `AIProvider` (OpenAI-compatível ou *disabled*). A plataforma funciona sem
  IA.
- **A IA nunca calcula valores.** Perguntas financeiras disparam consultas
  determinísticas; a IA apenas redige a explicação a partir dos fatos calculados.
- Proteção contra **prompt injection**: conteúdo de documentos é tratado como dado e
  instruções embutidas são desconsideradas.
- Respostas substantivas exigem referências às fontes.
- Credenciais permanecem exclusivamente no servidor.

## 7. Segurança e governança

- Autenticação JWT (access + refresh), senha com bcrypt.
- Rate limiting por IP/escopo com Redis e fallback em memória.
- Validação de entrada via Pydantic; ORM parametrizado (sem SQL concatenado).
- CORS restrito por configuração.
- `audit_logs` para ações sensíveis e `request_id` em todas as respostas.
- LGPD: coleta e exibição mínimas; dados de PF mascarados; finalidade de interesse
  público; fluxo de correção via fonte oficial.

## 8. Resiliência e desempenho

- Consultas paginadas com índices dedicados.
- A aplicação **não depende** de APIs governamentais em tempo de requisição: usa a
  base local normalizada e exibe o timestamp da última sincronização.
- Ingestão tolerante a falhas parciais, com commits em lotes e registro em
  `collection_runs`.
- FTS nativo do PostgreSQL com ranking (`ts_rank`) e fallback para ambientes de teste.

## 9. Decisões e alternativas

| Decisão | Justificativa |
|---------|---------------|
| Monólito modular | Menor complexidade operacional; fronteiras claras para evoluir |
| PostgreSQL FTS nativo | Suficiente no início; evita dependência de motor externo |
| Redis/Celery opcionais | Só onde truly necessário; app funciona sem eles |
| Categoria heurística + catálogo | Comparabilidade sem depender de dados ausentes |
| SQLite em testes | Rapidez e isolamento sem subir Postgres no CI |
