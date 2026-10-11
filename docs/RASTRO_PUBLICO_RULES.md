# Rastro Público — Local Data and Verification Rules

This file supplements the repository-root `AGENTS.md` and applies to all changes.

## Existing repository — preserve and extend
- Backend modules already include `app/connectors/pncp.py`, `app/services/ingestion.py`, `app/services/analysis/`, `app/api/v1/`, SQLAlchemy models and Alembic migrations.
- Existing CLI (`python -m app.cli`) supports PNCP ingestion and contract collection, but no campus-specific UASG filtering was identified in the reviewed ZIP.
- Existing `GovernmentEntity` lookup is based primarily on CNPJ. Check whether an institutional CNPJ is shared by multiple administrative units before deciding how to represent a campus.
- Existing frontend has procurement, contract, supplier, government-entity, municipality, finding, AI and investigation pages. Reuse them before creating new ones.
- Do not assume that working code means government records have already been collected. Confirm imported rows in a real database.

## Salto pilot — jurisdiction and identity
- Pilot city: **Salto/SP**, IBGE **3545209**, not Salto de Pirapora.
- Priority 1: **IFSP Campus Salto**, a **federal** unit, UASG **158364**; parent federal organization code **26439**.
- Priority 2: **Prefeitura de Salto**, a separate municipal institution and financial dataset.
- The parent IFSP organization code is NOT a sufficient campus filter. Prefer validated UASG or another source-confirmed unit identifier; do not attribute other campuses' contracts to Salto.
- Unit location and administrative jurisdiction are different concepts. Municipality-based views must explicitly separate municipal spending from federal spending taking place in Salto.

## Official references to validate against actual current responses
- IFSP UASG list: https://www.ifsp.edu.br/institucional/88-assuntos/administracao/2450-contratos
- Comprasnet Contratos OpenAPI: https://contratos.comprasnet.gov.br/api/docs
- Comprasnet documented routes include `/api/contrato/ug/{unidade_codigo}` (active contracts) and `/api/contrato/inativo/ug/{unidade_codigo}` (inactive). Verify response, availability and eligibility before use. Do not present active-only results as a complete historical dataset.
- PNCP: https://pncp.gov.br/api/consulta/swagger-ui/index.html
- TCE-SP municipal Salto: https://transparencia.tce.sp.gov.br/municipio/salto

## Provenance, quality and ingestion
- Preserve official external IDs, source URLs, identifiers, source system, financial-stage semantics, relevant dates and collection timestamps.
- Keep amounts as decimals; missing/unknown values remain NULL, never 0 by default.
- Handle pagination, bounds, retries, deduplication, re-import idempotency, and partial failures. Do not over-fetch or bypass access protections.
- Source availability and imported date/record counts must be verified by execution, never inferred from documentation or mocked tests.
- Data may be incomplete, delayed or superseded. State what period/status a query covers and the last successful sync.
- Avoid duplicates if a contract appears in both PNCP and Comprasnet; preserve multiple provenance references or explicitly describe reconciliation rules.

## Verification and public safety
- Add tests for records belonging to other UASGs, unknown unit, missing fields, duplicate IDs, updated contracts and upstream failures.
- No self-declared corruption verdicts, political rankings, or allegations. Expose methodology and review status instead.
- Never expose sensitive credentials or unnecessary personal data. Keep evidence reports traceable and appropriately access-controlled.
- Use narrowly scoped tasks. Before new integrations, document live endpoints, the test command run, observed sample count, coverage limits and any blockers.
