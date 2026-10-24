# Rastro Público

> **English summary** - *Where does public money go?* An independent, non-partisan
> open-source platform for searching and investigating Brazilian public spending:
> natural-language search, procurement dashboards, price comparison across
> equivalent purchases, and a deterministic audit engine that flags anomalies for
> **human review**, never as proof of wrongdoing. Data comes from official public
> sources (PNCP, Comprasnet, TCE-SP) and keeps a link to the original record.
> Next.js + FastAPI + PostgreSQL, runnable with Docker Compose.
>
> Menu, documentation and UI are in Brazilian Portuguese.

**Para onde vai o dinheiro público?**

Plataforma independente, apartidária e de código aberto para **pesquisar, entender e
investigar** os gastos públicos brasileiros. Combina busca em linguagem natural,
dashboards de contratações, comparação de preços e um motor de auditoria determinístico
que sinaliza possíveis anomalias para **verificação humana** — nunca como prova de
irregularidade.

> ⚠️ O Rastro Público **não é um serviço oficial do governo**. Todos os dados são
> provenientes de fontes públicas oficiais e preservam o vínculo com o registro
> original.

---

| | |
|:--|:--|
| **Live demo** | [rastro-publico.vercel.app](https://rastro-publico.vercel.app) |
| **Screenshots** | Pending — no screenshots yet |
| **Stack** | FastAPI · Python · Next.js · TypeScript · PostgreSQL · Docker Compose |
| **License** | MIT — [LICENSE](LICENSE) |

## Sumário

- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack](#stack)
- [Início rápido com Docker](#início-rápido-com-docker)
- [Desenvolvimento local](#desenvolvimento-local)
- [Ingestão de dados reais](#ingestão-de-dados-reais)
- [Testes](#testes)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Princípios](#princípios)
- [Documentação](#documentação)

---

## Visão geral

O Rastro Público oferece duas experiências integradas:

1. **Busca simples** — qualquer cidadão pesquisa gastos, contratos, fornecedores, órgãos
   e itens usando linguagem natural, com autocomplete, filtros e agrupamento de
   resultados.
2. **Investigação automatizada** — o sistema compara preços de contratações equivalentes,
   detecta anomalias estatísticas de forma explicável e organiza evidências para
   relatórios cidadãos.

A primeira integração real é o **Portal Nacional de Contratações Públicas (PNCP)**,
cobrindo contratações sob a Lei 14.133/2021 de União, estados e municípios.

### Painel municipal

Há um painel de despesas municipais em `/municipios/3545209/despesas`
(**Salto/SP**), com fonte TCE-SP: quanto a Prefeitura, a Câmara e o SAAE
**realmente pagaram**, além de empenhado, liquidado e anulado (sempre separados,
nunca somados entre si), com filtros por ano, mês, instituição, fornecedor e
estágio. O **pago** é a métrica principal. Cobertura parcial é exibida
explicitamente (ex.: 2026: jan–ago). Despesa municipal é mantida separada da
despesa federal do IFSP Campus Salto.

### Painel de campus

Há um painel dedicado por unidade gestora (UASG) em `/campus/{uasg}` — por exemplo
`/campus/158364` (**IFSP Campus Salto**). Ele reúne, em linguagem simples: o que foi
contratado, fornecedores, período, valores e quanto foi **realmente pago**, com filtros
por data, fornecedor e valor. Despesa **federal** (IFSP) é mantida separada da despesa
**municipal** de Salto. Acessível pela página inicial e pelos resultados de busca.

## Arquitetura

Monólito modular com fronteiras claras:

```
frontend/  Next.js (App Router, TypeScript, Tailwind, shadcn/ui, Recharts)
backend/   FastAPI + SQLAlchemy + Alembic + Pydantic
  ├── connectors/   conectores de dados públicos (PNCP, ...)
  ├── services/     ingestão, normalização, busca, análise, IA, relatórios
  ├── models/       schema PostgreSQL normalizado
  └── api/          endpoints REST versionados
postgres/  banco relacional com full-text search
redis/     cache de rate-limit e tarefas assíncronas (opcional)
```

Detalhes em [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Stack

| Camada     | Tecnologia |
|------------|------------|
| Frontend   | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Lucide, Recharts |
| Backend    | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Banco      | PostgreSQL 16 (full-text search com `portuguese`) |
| Async      | Redis + Celery (opcional) |
| Infra      | Docker, Docker Compose, GitHub Actions |
| Testes     | pytest, respx, Vitest, Testing Library, Playwright |

## Início rápido com Docker

```bash
cp .env.example .env
# edite .env se necessário (portas, segredos)
docker compose up -d --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000/api/v1
- Documentação da API (Swagger): http://localhost:8000/api/docs

Sincronize uma pequena amostra de dados reais do PNCP:

```bash
docker compose exec api python -m app.cli seed
docker compose exec api python -m app.cli ingest pncp \
  --data-inicial 2026-01-05 --data-final 2026-01-05 \
  --modalidades 6 --max-paginas 1
```

## Desenvolvimento local

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
cp .env.example .env.local   # ajuste NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
```

## Ingestão de dados reais

O conector do PNCP implementa paginação, rate limiting, retries com backoff
exponencial e deduplicação por número de controle PNCP.

```bash
# Contratações por período e modalidade (códigos da Lei 14.133/2021)
python -m app.cli ingest pncp --data-inicial 2026-01-01 --data-final 2026-01-31 \
  --uf SP --modalidades 6,5 --max-paginas 5

# Incluir itens e resultados homologados (mais lento na fonte)
python -m app.cli ingest pncp --data-inicial 2026-01-05 --data-final 2026-01-05 \
  --com-itens --max-paginas 1

# Contratos (PNCP)
python -m app.cli contracts --data-inicial 2026-01-01 --data-final 2026-01-31

# Contratos federais do Comprasnet por unidade gestora (UASG)
# Ex.: IFSP Campus Salto — UASG 158364, Salto/SP (IBGE 3545209)
python -m app.cli comprasnet --uasg 158364 \
  --municipio 3545209 --nome-municipio Salto --uf SP

# Execução financeira (empenhado/liquidado/pago) dos contratos de uma UASG
python -m app.cli comprasnet-pagamentos --uasg 158364

# Despesas municipais (eventos) do TCE-SP — ex.: Salto/SP
python -m app.cli tce-sp-despesas --municipio salto --ibge 3545209 --uf SP \
  --nome-municipio Salto --ano 2025 --mes-inicio 1 --mes-fim 12

# Enriquecimento: histórico, função/atividade e link do detalhe oficial
# (CSV do conjunto de dados do TCE-SP; correspondência 1:1, idempotente)
python -m app.cli tce-sp-detalhes --municipio salto --ibge 3545209 --ano 2025 --max 100

# Remuneração de servidores federais (exige TRANSPARENCIA_API_KEY)
python -m app.cli transparencia-servidores --orgao 26439 --mes 202501 \
  --campus "IFSP - CAMPUS SALTO"

# Executar motor de auditoria
python -m app.cli audit --limit 200
```

> **Pagamentos:** os estágios são mantidos separados — “empenhado” reserva,
> “liquidado” confere e “pago” efetiva. Valor contratado nunca é exibido como pago.
> **Salários:** só são exibidos quando publicados oficialmente; sem a credencial do
> Portal da Transparência, a plataforma informa explicitamente a indisponibilidade.

> A importação do Comprasnet é idempotente (reimportar atualiza, não duplica) e
> valida a UASG de cada registro, evitando atribuir contratos de outros campi.

> A coleta é **incremental**: registros já existentes são atualizados, não duplicados.
> Cada execução gera um `collection_run` com contadores e log de erros.

## Testes

```bash
# Backend
cd backend && python -m pytest -q        # 37 testes
ruff check app tests

# Frontend
cd frontend && npm run test              # Vitest
npm run typecheck && npm run lint
npm run test:e2e                         # Playwright (requer a stack no ar)
```

## Estrutura do projeto

```
politica/
├── ARCHITECTURE.md          # decisões arquiteturais e modelo de dados
├── ROADMAP.md               # marcos e status
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── core/            # config, logging, segurança, rate limit
│   │   ├── db/              # engine, sessão, base declarativa
│   │   ├── models/          # 26 tabelas normalizadas
│   │   ├── schemas/         # contratos Pydantic
│   │   ├── connectors/      # PNCP e infraestrutura de conectores
│   │   ├── services/        # ingestão, normalização, busca, análise, IA
│   │   ├── api/v1/          # endpoints REST
│   │   ├── cli.py           # seed, ingest, audit, stats
│   │   └── main.py
│   ├── alembic/             # migrações
│   └── tests/               # pytest
└── frontend/
    └── src/
        ├── app/             # rotas (App Router)
        ├── components/      # UI, layout, busca, gráficos, investigação
        └── lib/             # api, tipos, formatação
```

## Princípios

1. **Nunca inventar dados.** Valores de produção vêm exclusivamente de fontes oficiais.
2. **Rastreabilidade total.** Todo número aponta para o registro e a fonte originais.
3. **Estágios financeiros distintos.** Estimado ≠ homologado ≠ empenhado ≠ pago.
4. **Anomalia não é acusação.** A plataforma sinaliza; quem conclui são os órgãos
   competentes e o cidadão.
5. **A IA não calcula valores.** Cálculo é determinístico; a IA explica e organiza.
6. **Neutralidade política.** Nenhum ranking de corrupção ou veredito automático.

## Documentação

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — arquitetura, modelo de dados e conector PNCP
- [`ROADMAP.md`](./ROADMAP.md) — marcos e checklist
- [`docs/API.md`](./docs/API.md) — referência da API
- [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) — implantação e operação
- [`docs/DATA_SOURCES.md`](./docs/DATA_SOURCES.md) — fontes e requisitos

## O que eu faria a seguir

- Adicionar CI no GitHub Actions rodando a suíte de backend e o build do frontend, com badge no README.
- Ampliar os conectores de ingestão e documentar a cobertura por fonte no ROADMAP.
- Capturar telas do painel municipal e do motor de auditoria para o topo do README.

## Licença e uso responsável

Código sob licença MIT — ver [LICENSE](LICENSE).

Plataforma de interesse público. Ao reutilizar os dados, cite a fonte oficial e o
Rastro Público. Não apresente achados automáticos como prova de irregularidade.
