# Implantação e operação — Rastro Público

## 1. Requisitos

- Docker + Docker Compose, ou
- Node.js 22+, Python 3.11+, PostgreSQL 16, Redis 7.

## 2. Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste. As principais:

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | Conexão PostgreSQL (`postgresql+psycopg://...`) |
| `SECRET_KEY` | Chave de assinatura JWT — **obrigatória** em produção |
| `CORS_ORIGINS` | Origens permitidas do frontend |
| `PNCP_BASE_URL` | Base da API de consulta do PNCP |
| `AI_PROVIDER` | `disabled`, `openai` ou `local` (opcional) |
| `AI_API_KEY` | Chave do provedor de IA (somente servidor) |
| `NEXT_PUBLIC_API_BASE_URL` | URL pública da API usada pelo frontend |

Gere um segredo forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. Docker Compose (recomendado)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.cli seed
```

Serviços: `postgres`, `redis`, `api` (roda migrações e sobe o Uvicorn), `web`
(Next.js) e `worker` (Celery, perfil `async`, opcional).

## 4. Migrações

```bash
cd backend
alembic upgrade head                     # aplica
alembic revision --autogenerate -m "..." # cria nova
```

A primeira migração cria o schema e extensões/índices de busca (`pg_trgm`, GIN FTS).

## 5. Ingestão e agendamento

- Manual: `python -m app.cli ingest pncp --data-inicial ... --data-final ...`
- Administração: `POST /admin/ingestao/pncp` (segundo plano do FastAPI).
- Produção: agende via `celery beat`, cron ou Kubernetes CronJob. Recomenda-se
  ingerir janelas diárias e uma janela móvel de atualização para captar alterações.

### Boas práticas de coleta

- Respeite os limites das fontes (o conector já aplica rate limiting e backoff).
- A ingestão de itens é mais lenta; faça-a de forma incremental e fora do pico.
- Acompanhe `collection_runs.error_count` e o `status` de cada `data_source`.

## 6. Banco de dados

- PostgreSQL 16, com `pg_trgm` habilitado pela migração.
- Backup: `pg_dump` periódico; retenção conforme política de dados.
- Índices GIN de FTS e trigram já criados; `VACUUM`/`ANALYZE` regulares
  recomendados após grandes ingestões.

## 7. Armazenamento de documentos (opcional)

Configure `S3_*` para armazenar PDFs de editais/contratos. A tabela `documents`
guarda `storage_key`, `checksum` e metadados; o conteúdo permanece em bucket
S3-compatível.

## 8. Segurança em produção

- `SECRET_KEY` forte e rotacionável; `DEBUG=false`; `ENVIRONMENT=production`.
- `CORS_ORIGINS` restrito ao domínio do frontend.
- Terminação TLS em proxy reverso (Nginx/Traefik/Caddy) ou balanceador gerenciado.
- Redis privado, sem exposição pública.
- Credenciais de IA e de APIs governamentais apenas no servidor.
- Logs estruturados em JSON; correlacione por `x-request-id`.
- Execute atrás de WAF/rate limiting de borda, se possível.

## 9. Observabilidade

- Health check: `GET /api/v1/health`.
- Cabeçalhos `x-request-id` e `x-process-time-ms` em todas as respostas.
- Recomenda-se coletar métricas (Prometheus) e traces em uma evolução futura.

## 10. Checklist de go-live

- [ ] `SECRET_KEY` e demais segredos definidos.
- [ ] Migrações aplicadas e `app.cli seed` executado.
- [ ] Ingestão inicial concluída e verificada (`/meta/coverage`).
- [ ] CORS restrito e TLS ativo.
- [ ] Backup do banco configurado.
- [ ] Agendador de ingestão e de auditoria ativos.
- [ ] Monitoramento de `collection_runs` e erros.
