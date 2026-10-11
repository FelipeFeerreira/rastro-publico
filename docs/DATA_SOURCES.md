# Fontes de dados e requisitos

Este documento descreve as fontes oficiais, seus requisitos de acesso e o que já está
integrado. Nenhum endpoint é inventado: todos foram verificados na documentação
oficial.

---

## 1. PNCP — Portal Nacional de Contratações Públicas ✅ integrado

- **Portal:** https://pncp.gov.br/
- **Documentação de consulta:** https://pncp.gov.br/api/consulta/swagger-ui/index.html
- **Documentação de ingestão:** https://pncp.gov.br/pncp-api/v3/api-docs
- **Manual:** https://pncp.gov.br/manual/pt-br/latest/singlehtml
- **Autenticação:** não exigida para consulta.
- **Cobertura:** contratações sob a Lei 14.133/2021 (União, estados, municípios).

### Endpoints utilizados

| Uso | Método e rota | Observações |
|-----|---------------|-------------|
| Contratações por publicação | `GET /v1/contratacoes/publicacao` | `codigoModalidadeContratacao` obrigatório; `tamanhoPagina ≥ 10` |
| Contratações por atualização | `GET /v1/contratacoes/atualizacao` | Para sincronização incremental |
| Contratos | `GET /v1/contratos` | Por data de publicação |
| Itens | `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens` | Base `api/pncp`; mais lento |
| Resultados | `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{item}/resultados` | Preços homologados |

### Modalidades (`codigoModalidadeContratacao`)

1 Leilão · 2 Diálogo competitivo · 3 Concorrência · 4 Concurso · 5 Pregão · 6 Dispensa ·
7 Inexigibilidade · 8 Manifestação de interesse · 9 Pré-qualificação · 10 Credenciamento ·
11 Leilão eletrônico · 12 Diálogo competitivo eletrônico · 13 Concorrência eletrônica.

---

## 2. Portal da Transparência 🟡 catalogado, integração pendente

- **Portal:** https://portaldatransparencia.gov.br/
- **API:** https://api.portaldatransparencia.gov.br/swagger-ui/index.html
- **Autenticação:** **exige chave de API gratuita** (`TRANSPARENCIA_API_KEY`).
- **Cobertura:** execução orçamentária e financeira, despesas, servidores e benefícios
  do Poder Executivo Federal.
- **Status:** catálogo e schema prontos; conector a implementar (Milestone 6).

> Para habilitar: obtenha a chave em https://api.portaldatransparencia.gov.br e defina
> `TRANSPARENCIA_API_KEY` no ambiente.

---

## 3. Câmara dos Deputados (Dados Abertos) 🟡 catalogado, integração pendente

- **Portal:** https://dadosabertos.camara.leg.br/
- **Documentação:** https://dadosabertos.camara.leg.br/swagger/api.html
- **Autenticação:** não exigida.
- **Cobertura:** despesas parlamentares (cota), proposições, votações, deputados.
- **Status:** catalogado; conector a implementar (Milestone 6).

---

## 4. Comprasnet Contratos (Contratos.gov.br) ✅ integrado (federal, por UASG)

- **Portal:** https://contratos.comprasnet.gov.br/
- **OpenAPI:** https://contratos.comprasnet.gov.br/docs/api-docs.json
- **Swagger:** https://contratos.comprasnet.gov.br/api/docs
- **Autenticação:** não exigida para leitura.
- **Cobertura:** contratos administrativos e empenhos com força de contrato das
  **unidades gestoras federais (UASG)**, ativos e inativos.

### Endpoints utilizados (verificados)

| Uso | Rota | Observações |
|-----|------|-------------|
| Contratos ativos | `GET /api/contrato/ug/{uasg}` | Lista sem paginação |
| Contratos inativos | `GET /api/contrato/inativo/ug/{uasg}` | Lista sem paginação |
| Registro original | `GET /api/contrato/id/{id}` | URL preservada em `contracts.source_url` |

### Identidade da unidade — atenção

- A chave de unidade é a **unidade gestora** (`contratante.orgao.unidade_gestora.codigo`),
  **não** o campo `unidade_compra` (que pode apontar para outra unidade requisitante).
- O código do órgão pai (ex.: IFSP `26439`) **não** isola o campus: outro campus do IFSP
  compartilha o mesmo órgão (e o mesmo CNPJ institucional). O filtro confiável é a UASG.
- A importação valida cada registro contra a UASG solicitada e rejeita divergências.

### Piloto verificado: IFSP Campus Salto (UASG 158364)

- Órgão pai: `26439` (IFSP). Município: Salto/SP (IBGE `3545209`). Âmbito: **federal**.
- Resposta ao vivo (2026-10-11): **233 contratos ativos + 20 inativos = 253**;
  todos com `unidade_gestora.codigo = 158364` e `orgao.codigo = 26439`.
- Tipos observados: `Contrato`, `Empenho`, `Termo de Adesão`, `Outros`.

### Comando de importação

```bash
python -m app.cli comprasnet --uasg 158364 \
  --municipio 3545209 --nome-municipio Salto --uf SP
# opções: --sem-inativos  --max N
```

### Procedimento de verificação

```bash
# 1) contagens no banco por sistema/UASG
python -m app.cli stats
# 2) via API
curl "http://localhost:8000/api/v1/contratos?uasg=158364&page_size=1"          # total = 253
curl "http://localhost:8000/api/v1/contratos?source_system=comprasnet"          # total = 253
curl "http://localhost:8000/api/v1/orgaos?uasg=158364"                          # IFSP - CAMPUS SALTO
```

### Reconciliação com o PNCP

Um mesmo contrato pode aparecer no PNCP e no Comprasnet. As tabelas preservam
`source_system` + `external_id` (chave natural única por sistema), mantendo múltiplas
proveniências separadas em vez de sobrescrever registros.

> **Nota futura:** o site histórico de Compras.gov.br foi reorganizado; grande parte dos
> dados federais de contratações também é publicada no PNCP. Integrações de execução
> financeira serão avaliadas separadamente.

---

## 5. Portais estaduais e municipais

- Integração futura via conectores modulares dedicados, respeitando a documentação e os
  limites de cada portal. A arquitetura de `connectors/` já prevê extensibilidade e a
  `data_sources` registra cobertura e status por fonte.

---

## 6. Execução financeira — Comprasnet (empenhado / liquidado / pago) ✅ integrado

- **Rotas** (sem autenticação):
  - `GET /api/contrato/{id}/empenhos` → empenhos com `empenhado`, `liquidado`, `pago`, `rp*`.
  - `GET /api/contrato/{id}/faturas` → faturas/notas (documentos de apoio; **não somadas**).
- **Sem contagem dupla:** os estágios financeiros vêm dos **empenhos** (fonte canônica).
  As faturas documentam a liquidação que já está agregada no empenho; somá-las junto
  contaria o mesmo dinheiro duas vezes, por isso não viram lançamento de pagamento.
- **Proveniência:** cada lançamento guarda `source_system`, `external_id`
  (`empenho:{id}:{estágio}` / `fatura:{id}`), URL de origem e data de coleta.
- **Estágios separados:** “empenhado” reserva, “liquidado” confere, “pago” efetiva.
  Valor contratado **nunca** é exibido como pago.

### Piloto verificado: IFSP Campus Salto (UASG 158364)

```bash
python -m app.cli comprasnet-pagamentos --uasg 158364
```

Resultado real (2026-10-11): **1.233 lançamentos de empenho** (411 empenhado, 411
liquidado, 411 pago) em 249 contratos, 0 erros.
Empenhado R$ 14.700.551,70 · Liquidado R$ 139.967,62 · Pago R$ 8.212.820,59.

> Observação de qualidade: na fonte, o campo `liquidado` do empenho pode estar
> sub-registrado em relação a `pago`; o painel informa isso ao cidadão.

Verificação:

```bash
curl "http://localhost:8000/api/v1/pagamentos?uasg=158364"
curl "http://localhost:8000/api/v1/contratos/{id}"        # payment_summary por estágio
```

---

## 7. Remuneração de servidores — investigada, **bloqueada** (sem chave/acesso)

Prioridade: IFSP Campus Salto (federal, UASG 158364) e Prefeitura de Salto/SP
(municipal, IBGE 3545209). **Nenhum registro de salário foi importado** — os dados
oficiais não estavam acessíveis neste ambiente. Não foram usados dados estimados.

| Fonte | Situação | Motivo verificado |
|-------|----------|-------------------|
| Portal da Transparência (API federal) | **credencial ausente** | Requer `TRANSPARENCIA_API_KEY`; sem ela retorna HTTP 401. OpenAPI: `https://api.portaldatransparencia.gov.br/v3/api-docs` |
| Dados Abertos do IFSP (CKAN) | **bloqueado (WAF)** | `https://dados.ifsp.edu.br/api/3/action/...` respondeu HTTP 202 vazio |
| Prefeitura de Salto — Remuneração (Prescon/APEX) | **indisponível** | `saltotransparencia.presconinformatica.com.br:8443` inacessível (porta bloqueada) |

Quando a credencial estiver disponível, o comando (já implementado) importa servidores
**verificando o campus pela UORG de lotação** (não atribui todo o IFSP ao campus Salto):

```bash
export TRANSPARENCIA_API_KEY="sua-chave"
python -m app.cli transparencia-servidores --orgao 26439 --mes 202501 \
  --campus "IFSP - CAMPUS SALTO"
```

Estado exposto pela API: `GET /api/v1/salarios/fontes`.

---

## 8. Despesas municipais — TCE-SP ✅ integrado (Salto/SP)

- **Documentação:** https://transparencia.tce.sp.gov.br/apis
- **Conjunto de dados:** https://transparencia.tce.sp.gov.br/conjunto-de-dados
- **Autenticação:** não exigida.
- **Rota:** `GET /api/json/despesas/{municipio}/{exercicio}/{mes}` (também `xml`).
  - `municipio` = slug (ex.: `salto`), listado em `GET /api/json/municipios`.
  - `mes` = 1–12. Sem paginação (lista completa do mês).

### Cobertura — verificada por execução

A documentação cita exercício **2014–2019**, mas a API **respondeu com dados reais
de 2019 a 2026** na verificação. Não presumimos cobertura: testamos cada ano.

### Campos por evento

`orgao`, `mes`, `evento`, `nr_empenho`, `id_fornecedor`, `nm_fornecedor`,
`dt_emissao_despesa`, `vl_despesa`. Cada linha é um **evento** de despesa, **não**
um contrato — não criamos vínculo com contratos.

### Estágios e cancelamentos

`Empenhado` → empenhado · `Valor Liquidado` → liquidado · `Valor Pago` → pago ·
`Anulação` → anulação · `Reforço` → reforço. O valor **empenhado líquido** é
`empenhado + reforço − anulação`. Estágios nunca são somados como se fossem o
mesmo (evita contagem dupla).

### Importação

```bash
python -m app.cli tce-sp-despesas --municipio salto --ibge 3545209 --uf SP \
  --nome-municipio Salto --ano 2025 --mes-inicio 1 --mes-fim 12
```

### Resultado real (Salto/SP, 2026-10-11)

- **2025:** 43.944 eventos — empenhado R$ 836.881.760,36 · liquidado R$ 725.785.937,96
  · pago R$ 724.934.362,80 · anulação R$ 75.330.146,38.
- **2026:** 28.279 eventos — empenhado R$ 763.877.890,47 · liquidado R$ 534.044.074,97
  · pago R$ 526.748.797,56 · anulação R$ 57.807.546,91.
- **Total 72.223 eventos**, 3 instituições (Prefeitura, Câmara, SAAE), ~1.666
  fornecedores identificados por CNPJ.

### Verificação

```bash
curl "http://localhost:8000/api/v1/despesas-municipais?municipio_ibge=3545209&ano=2025"
curl "http://localhost:8000/api/v1/despesas-municipais/resumo?municipio_ibge=3545209&ano=2025"
```

> **Separação:** despesa municipal (TCE-SP) fica em tabela própria
> (`municipal_expenses`), sem vínculo com contratos e separada da despesa federal
> do IFSP Campus Salto.

---

## Diretrizes de coleta

1. **Verificar antes de implementar.** Confirmar documentação, autenticação, schema,
   endpoints e limites — nunca presumir que um conjunto de dados exista.
2. **Respeitar limites.** Rate limiting, backoff exponencial e respeito a `Retry-After`.
3. **Preservar a origem.** Guardar ID original, URL do registro e documentação.
4. **Normalizar e deduplicar.** Chave natural estável por tipo de registro.
5. **Registrar a coleta.** `collection_runs` com contadores, erros e timestamps.
6. **Distinguir estágios financeiros.** Estimado, homologado, empenhado, liquidado, pago.
7. **Comunicar cobertura.** Exibir quando uma fonte está desatualizada, incompleta,
   indisponível ou fora da cobertura.
