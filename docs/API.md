# Referência da API — Rastro Público

Base: `http://localhost:8000/api/v1`. Documentação interativa (Swagger) em
`/api/docs` e Redoc em `/api/redoc`.

Autenticação: `Authorization: Bearer <access_token>` nos endpoints que exigem login.

Todos os erros seguem o formato:

```json
{ "detail": "mensagem em português" }
```

---

## Sistema

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Estado do serviço |
| GET | `/meta/coverage` | Contagens e aviso de cobertura |

## Fontes de dados

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/sources` | Catálogo de fontes oficiais |
| GET | `/sources/{code}` | Detalhe de uma fonte |
| GET | `/sources/{code}/runs` | Histórico de sincronizações |

## Busca

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/search?q=&types=&page=&page_size=&uf=&year=&modality=&min_value=&max_value=` | Busca unificada |
| GET | `/search/suggest?q=` | Autocomplete |

`types` aceita lista separada por vírgula: `procurement,contract,supplier,entity,municipality,item`.

## Contratações e contratos

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/contratacoes?page=&page_size=&uf=&municipality_ibge=&entity_id=&year=&modality=` | Lista paginada |
| GET | `/contratacoes/{id}` | Detalhe com itens e resultados |
| GET | `/contratos?page=&page_size=&uf=&entity_id=&supplier_id=&supplier_name=&year=&uasg=&source_system=&organization_code=&q=&date_from=&date_to=&min_value=&max_value=&order=` | Lista paginada (cada item traz `paid_value`) |
| GET | `/contratos/{id}` | Detalhe com aditivos e `payment_summary` |

## Fornecedores

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/fornecedores?q=&document=&page=` | Lista |
| GET | `/fornecedores/{id}` | Detalhe com agregados |
| GET | `/fornecedores/{id}/contratos` | Contratos do fornecedor |
| GET | `/fornecedores/{id}/achados` | Achados associados |

## Órgãos e territórios

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/orgaos?q=&uf=&sphere=&page=` | Lista de órgãos |
| GET | `/orgaos/{id}` | Detalhe |
| GET | `/orgaos/{id}/contratacoes` | Contratações do órgão |
| GET | `/orgaos/{id}/contratos` | Contratos do órgão |
| GET | `/campus/{uasg}` | Painel agregado do campus (totais + resumo financeiro) |
| GET | `/estados` | Unidades da Federação |
| GET | `/municipios?q=&uf=&page=` | Municípios |
| GET | `/municipios/{ibge_code}` | Detalhe com totais |

## Análise e auditoria

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/achados?status=&severity=&rule_code=&entity_id=&procurement_id=&page=` | Lista de achados |
| GET | `/achados/{public_id}` | Detalhe do achado |
| PATCH | `/achados/{public_id}/revisao` 🔒 | Registrar revisão (status + nota) |
| POST | `/analise/comparacao` | Comparar preços por item ou categoria |

Exemplo de comparação:

```json
POST /analise/comparacao
{
  "item_id": 123,
  "window_months": 18
}
```

Resposta: distribuição (mediana, P25, P75, IQR), tamanho da amostra, metodologia,
limitações e registros comparáveis. Inclui `classification` em linguagem simples
(`dentro_da_faixa`, `acima_da_referencia`, `sem_dados`) e `compared_value`.

Status de revisão válidos: `aguardando_verificacao`, `em_analise`, `documentado`,
`encerrado_apos_analise`, `sem_irregularidade`.

## Pagamentos (execução financeira)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/pagamentos?uasg=&entity_id=&supplier_id=&stage=&year=&page=` | Lançamentos por estágio |
| GET | `/contratos/{id}/pagamentos` | Lançamentos de um contrato |

`stage` ∈ `empenhado` \| `liquidado` \| `pago`. O detalhe do contrato
(`/contratos/{id}`) inclui `payment_summary` com os totais **por estágio** —
estágios nunca são somados como se fossem o mesmo.

Os lançamentos vêm dos **empenhos** do Comprasnet. As **faturas** não são persistidas
como pagamento: elas documentam a liquidação já agregada no empenho e somá-las contaria
o mesmo dinheiro duas vezes.

## Servidores e remuneração

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/servidores?q=&uasg=&entity_id=&year=&page=` | Busca de servidores |
| GET | `/servidores/{id}` | Detalhe com remunerações por mês |
| GET | `/salarios/fontes` | Disponibilidade das fontes de remuneração |

A busca usa `PublicPerson`/`Remuneration`. Valores só aparecem quando publicados
oficialmente; a ausência é explícita.

## Assistente

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/assistente/perguntar` | Pergunta em linguagem natural |
| GET | `/assistente/glossario` | Glossário completo |
| GET | `/assistente/glossario/{termo}` | Definição de um termo |
| GET | `/assistente/sugestoes?q=` | Sugestões |

Resposta inclui `grounded`, `computed` (cálculo determinístico), `citations` e
`limitations`.

## Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/registrar` | Cria conta |
| POST | `/auth/login` | Retorna access + refresh token |
| POST | `/auth/renovar` | Renova tokens |
| GET | `/auth/eu` 🔒 | Perfil atual |

## Investigações

Todas exigem autenticação.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/investigacoes` | Lista as investigações do usuário |
| POST | `/investigacoes` | Cria investigação |
| GET | `/investigacoes/{public_id}` | Detalhe com evidências |
| PATCH | `/investigacoes/{public_id}` | Atualiza metadados/status |
| DELETE | `/investigacoes/{public_id}` | Remove |
| POST | `/investigacoes/{public_id}/evidencias` | Adiciona evidência |
| DELETE | `/investigacoes/{public_id}/evidencias/{id}` | Remove evidência |
| GET | `/investigacoes/{public_id}/relatorio` | Relatório (JSON) |
| GET | `/investigacoes/{public_id}/relatorio.pdf` | Relatório (PDF) |

## Monitoramento

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/monitoramento/assinaturas` 🔒 | Lista assinaturas |
| POST | `/monitoramento/assinaturas` 🔒 | Cria assinatura |
| DELETE | `/monitoramento/assinaturas/{id}` 🔒 | Remove assinatura |
| GET | `/monitoramento/notificacoes` 🔒 | Lista notificações |
| PATCH | `/monitoramento/notificacoes/{id}/ler` 🔒 | Marca como lida |

## Administração (`role = admin`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/estatisticas` | Contagens da base |
| GET | `/admin/execucoes` | Últimas sincronizações |
| POST | `/admin/ingestao/pncp` | Agenda ingestão em segundo plano |
| POST | `/admin/auditoria/executar?limit=` | Executa varredura de auditoria |

## Limites de taxa

- Busca: `RATE_LIMIT_SEARCH_PER_MINUTE` (padrão 40/min por IP).
- Assistente: 30/min por IP.
- Demais endpoints: `RATE_LIMIT_PER_MINUTE` (padrão 120/min).
