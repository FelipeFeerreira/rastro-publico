# Roadmap — Rastro Público

Marcos incrementais. O objetivo é sempre manter um fluxo ponta a ponta funcional:

```
dado oficial → ingestão → PostgreSQL → API → interface de busca → resultado com fonte
```

Status: ✅ Concluído · 🟡 Parcial · ⬜ Planejado

---

## Milestone 1 — Fundação ✅

- [x] Estrutura completa do projeto (monorepo `frontend/` + `backend/`).
- [x] Configuração de frontend (Next.js 15, TS, Tailwind, shadcn/ui, Recharts).
- [x] Configuração de backend (FastAPI, SQLAlchemy, Alembic, Pydantic).
- [x] Docker Compose (Postgres, Redis, API, worker opcional, web).
- [x] Sistema de design (tema claro/escuro, tipografia, componentes acessíveis).
- [x] Página inicial com busca proeminente e buscas de exemplo.
- [x] Navegação principal e rodapé institucional.
- [x] `.env.example` e documentação de setup.
- [x] Testes básicos de backend e frontend.

**Critérios de aceite atendidos:** `docker compose up` sobe a stack; homepage renderiza
com busca funcional; API responde `/api/v1/health`; `pytest` e `vitest` verdes.

## Milestone 2 — Dados governamentais reais 🟡

- [x] Conector do PNCP (publicações, itens, resultados, contratos).
- [x] Ingestão com paginação, rate limiting, retries com backoff e dedup.
- [x] Persistência normalizada com preservação da fonte original.
- [x] Registro de sincronização (`collection_runs`) e status por fonte.
- [x] Tratamento de falhas parciais e indisponibilidade da fonte.
- [x] Ingestão de itens/resultados homologados (opcional, incremental).
- [x] Busca funcional sobre dados reais.
- [ ] Agendador de sincronização contínua em produção (cron/Celery beat).

## Milestone 3 — Busca e painéis públicos ✅

- [x] Busca unificada (contratações, contratos, fornecedores, órgãos, municípios,
      itens) com FTS em português e ranking.
- [x] Autocomplete com sugestões por tipo.
- [x] Filtros e paginação.
- [x] Páginas de detalhe de contratação (itens, resultados, gráfico, estágios).
- [x] Perfis de fornecedor com agregados e achados.
- [x] Visões de órgão e município.
- [x] Gráficos e explicações de dados.
- [x] Responsividade mobile-first e componentes acessíveis.

## Milestone 4 — Auditoria automatizada ✅

- [x] Cálculo determinístico de preço unitário com validação.
- [x] Normalização de itens e chave de comparabilidade.
- [x] Construção de conjuntos de compras comparáveis.
- [x] Regras iniciais de detecção (5 regras) e persistência de achados reproduzíveis.
- [x] Endpoint de comparação de preços sob demanda.
- [x] Testes de cálculo e de casos de falso positivo (amostra pequena).

## Milestone 5 — IA e evidências 🟡

- [x] Abstração de provedor de IA configurável (OpenAI-compatível / desativado).
- [x] Perguntas em linguagem natural com cálculo determinístico no backend.
- [x] Glossário de termos de contratações.
- [x] Proteção contra prompt injection e exigência de referências.
- [x] Espaço de investigação privado (casos, evidências, anotações).
- [x] Exportação de relatório de evidências em PDF.
- [ ] RAG sobre documentos oficiais completos (PDFs de editais/contratos).
- [ ] Sugestão automatizada de próximos passos de investigação.

## Milestone 6 — Expansão de transparência 🟡

- [x] Catálogo de fontes futuras (Portal da Transparência, Câmara) com status.
- [x] **Conector Comprasnet Contratos** (federal, por UASG) com importação idempotente e
      piloto real do IFSP Campus Salto (UASG 158364): 253 contratos.
- [x] **Execução financeira real** (empenhado/liquidado/pago) do IFSP Salto:
      1.233 lançamentos de empenho; estágios separados, sem contagem dupla.
- [x] **Painel do campus** `/campus/{uasg}` (ex.: IFSP Salto) com totais, resumo
      financeiro, filtros por data/fornecedor/valor e seção de salários.
- [x] **Busca de remuneração** (interface + API + ingestão) com verificação de campus
      por UORG; **integração bloqueada** sem `TRANSPARENCIA_API_KEY`.
- [ ] Conector do Portal da Transparência efetivamente ativo (requer chave de API).
- [ ] Despesas parlamentares (Câmara dos Deputados).
- [ ] Conectores estaduais e municipais extensíveis.

## Milestone 7 — Monitoramento e produção ⬜

- [x] Assinaturas de monitoramento e notificações (base).
- [x] Ferramentas administrativas (estatísticas, ingestão, auditoria).
- [x] Índices de desempenho e cache.
- [x] Verificações de segurança (JWT, rate limit, CORS, validação).
- [x] Testes automatizados (37 backend, 11 frontend, smoke e2e).
- [x] Documentação de implantação.
- [ ] Envio real de notificações por e-mail.
- [ ] Observabilidade (métricas, tracing) e alertas operacionais.
- [ ] Paginação por cursor em datasets muito grandes.

---

## Próximos passos concretos

1. **Agendamento de ingestão** (`celery beat` ou cron) para sincronizações contínuas.
2. **Conector do Portal da Transparência** para execução financeira (empenho,
   liquidação, pagamento), exigindo `TRANSPARENCIA_API_KEY`.
3. **RAG de documentos** com extração de texto de PDFs oficiais e indexação.
4. **Notificações por e-mail** e resumos periódicos de monitoramento.
5. **Observabilidade** e *runbooks* de operação em produção.
