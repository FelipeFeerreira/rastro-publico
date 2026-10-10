"""Conector do Portal Nacional de Contratações Públicas (PNCP).

Documentação oficial verificada em 2026-10:
- Consulta: https://pncp.gov.br/api/consulta/v3/api-docs
- Ingestão: https://pncp.gov.br/pncp-api/v3/api-docs
- Manual:   https://pncp.gov.br/manual/pt-br/latest/singlehtml
- Base consulta: https://pncp.gov.br/api/consulta
- Base api:      https://pncp.gov.br/api/pncp

O PNCP não exige autenticação para consultas. O parâmetro
`codigoModalidadeContratacao` é obrigatório nas consultas de contratações, por
isso a sincronização por período itera sobre as modalidades da Lei 14.133/2021.
`tamanhoPagina` deve ser >= 10 (limite do portal; usamos valores maiores).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorConfig, Page
from app.core.config import settings

# Modalidades de contratação (tabela de domínio do PNCP).
MODALITY_CODES: dict[int, str] = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concorrência - Eletrônica",
    4: "Concurso",
    5: "Pregão - Eletrônico",
    6: "Dispensa",
    7: "Inexigibilidade",
    8: "Manifestação de Interesse",
    9: "Pré-qualificação",
    10: "Credenciamento",
    11: "Leilão - Presencial",
    12: "Diálogo Competitivo - Presencial",
    13: "Concorrência - Presencial",
}

PNCP_API_BASE = "https://pncp.gov.br/api/pncp"


def _format_date(value: date | datetime | str) -> str:
    if isinstance(value, str):
        return value.replace("-", "")
    return value.strftime("%Y%m%d")


class PNCPConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            ConnectorConfig(
                name="pncp",
                base_url=settings.pncp_base_url,
                timeout_seconds=settings.pncp_timeout_seconds,
                max_retries=settings.pncp_max_retries,
                page_size=max(settings.pncp_page_size, 10),
            )
        )

    # --- Contratações ---
    def iter_publications(
        self,
        start: date | datetime | str,
        end: date | datetime | str,
        *,
        modality_codes: list[int] | None = None,
        uf: str | None = None,
        municipality_ibge: str | None = None,
        cnpj: str | None = None,
        max_pages_per_modality: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Itera contratações publicadas no período, por modalidade."""
        codes = modality_codes or list(MODALITY_CODES)
        for code in codes:
            params = {
                "dataInicial": _format_date(start),
                "dataFinal": _format_date(end),
                "codigoModalidadeContratacao": code,
                "uf": uf,
                "codigoMunicipioIbge": municipality_ibge,
                "cnpj": cnpj,
            }
            for page in self.paginate(
                "/v1/contratacoes/publicacao", params, max_pages=max_pages_per_modality
            ):
                yield from page.items

    def iter_contracts(
        self,
        start: date | datetime | str,
        end: date | datetime | str,
        *,
        cnpj: str | None = None,
        max_pages: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        params = {
            "dataInicial": _format_date(start),
            "dataFinal": _format_date(end),
            "cnpjOrgao": cnpj,
        }
        for page in self.paginate("/v1/contratos", params, max_pages=max_pages):
            yield from page.items

    # --- Itens e resultados (base pncp-api) ---
    def fetch_items(self, cnpj: str, year: int, sequential: int) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_number = 1
        while True:
            payload = self._request(
                f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens",
                {"pagina": page_number, "tamanhoPagina": max(settings.pncp_page_size, 10)},
            )
            data = payload if isinstance(payload, list) else payload.get("data", [])
            items.extend(data)
            if len(data) < 10:
                break
            page_number += 1
        return items

    def fetch_item_results(
        self, cnpj: str, year: int, sequential: int, item_number: int
    ) -> list[dict[str, Any]]:
        payload = self._request(
            f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{year}/{sequential}"
            f"/itens/{item_number}/resultados",
            {"pagina": 1, "tamanhoPagina": 50},
        )
        return payload if isinstance(payload, list) else payload.get("data", [])

    # --- URL pública do registro ---
    @staticmethod
    def public_url(cnpj: str, year: int, sequential: int) -> str:
        return f"https://pncp.gov.br/app/editais/{cnpj}/{year}/{sequential}"

    def page_preview(self, **kwargs: Any) -> Page:  # pragma: no cover - utilidade
        return next(self.paginate("/v1/contratacoes/publicacao", kwargs))
