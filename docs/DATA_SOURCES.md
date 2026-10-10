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

## 4. Compras.gov.br

- **Portal:** https://www.gov.br/compras/
- **Observação:** grande parte dos dados federais de contratações é publicada também no
  PNCP. A integração dedicada será avaliada após os conectores de execução financeira.

---

## 5. Portais estaduais e municipais

- Integração futura via conectores modulares dedicados, respeitando a documentação e os
  limites de cada portal. A arquitetura de `connectors/` já prevê extensibilidade e a
  `data_sources` registra cobertura e status por fonte.

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
