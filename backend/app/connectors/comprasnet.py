"""Conector do Comprasnet Contratos (contratos.comprasnet.gov.br).

Documentação e respostas verificadas em 2026-10:
- OpenAPI:  https://contratos.comprasnet.gov.br/docs/api-docs.json
- Swagger:  https://contratos.comprasnet.gov.br/api/docs
- Base:     https://contratos.comprasnet.br  ->  https://contratos.comprasnet.gov.br
- Sem autenticação para leitura.

Endpoints usados:
- GET /api/contrato/ug/{unidade_codigo}          -> contratos ATIVOS da UG (UASG)
- GET /api/contrato/inativo/ug/{unidade_codigo}  -> contratos INATIVOS da UG (UASG)
- GET /api/contrato/id/{contrato_id}             -> detalhe/registro original

Observações verificadas nas respostas reais:
- A chave de unidade é a **unidade gestora** (`contratante.orgao.unidade_gestora.codigo`),
  não o campo `unidade_compra` (que pode apontar para outra unidade requisitante).
- O código do órgão pai (ex.: 26439 no IFSP) NÃO é suficiente para isolar o campus;
  o filtro confiável é a UASG.
- A resposta é uma lista sem paginação; o volume é limitado pela própria unidade.
"""

from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector, ConnectorConfig

COMPRASNET_BASE_URL = "https://contratos.comprasnet.gov.br"


class ComprasnetContratosConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            ConnectorConfig(
                name="comprasnet",
                base_url=COMPRASNET_BASE_URL,
                timeout_seconds=45,
                max_retries=4,
                page_size=100,
                min_interval_seconds=0.3,
                headers={"Accept": "application/json"},
            )
        )

    # --- Coleta por unidade (UASG) ---
    def fetch_unit_contracts(self, uasg: str, *, active: bool = True) -> list[dict[str, Any]]:
        """Contratos ativos ou inativos de uma unidade gestora (UASG)."""
        path = (
            f"/api/contrato/ug/{uasg}"
            if active
            else f"/api/contrato/inativo/ug/{uasg}"
        )
        payload = self._request(path, allow_not_found=True)
        if payload is None:  # unidade inexistente/sem contratos
            return []
        if isinstance(payload, list):
            return payload
        return payload.get("data", []) if isinstance(payload, dict) else []

    def fetch_unit_contracts_all(
        self, uasg: str, *, include_inactive: bool = True
    ) -> list[dict[str, Any]]:
        """Contratos ativos (e opcionalmente inativos) de uma UASG.

        Cada item recebe a marca interna `_batch_active` para correlação, sem
        alterar o payload original da fonte.
        """
        contracts: list[dict[str, Any]] = []
        for raw in self.fetch_unit_contracts(uasg, active=True):
            contracts.append({**raw, "_batch_active": True})
        if include_inactive:
            for raw in self.fetch_unit_contracts(uasg, active=False):
                contracts.append({**raw, "_batch_active": False})
        return contracts

    # --- Preservação de origem / extração defensiva ---
    @staticmethod
    def contract_source_url(external_id: str | int) -> str:
        return f"{COMPRASNET_BASE_URL}/api/contrato/id/{external_id}"

    @staticmethod
    def extract_uasg(raw: dict[str, Any]) -> str | None:
        return (
            ((raw.get("contratante") or {}).get("orgao") or {}).get("unidade_gestora") or {}
        ).get("codigo")

    @staticmethod
    def extract_unit_name(raw: dict[str, Any]) -> str | None:
        unidade = (
            ((raw.get("contratante") or {}).get("orgao") or {}).get("unidade_gestora") or {}
        )
        return unidade.get("nome") or unidade.get("nome_resumido")

    @staticmethod
    def extract_organization_code(raw: dict[str, Any]) -> str | None:
        return ((raw.get("contratante") or {}).get("orgao") or {}).get("codigo")

    @staticmethod
    def extract_organization_name(raw: dict[str, Any]) -> str | None:
        return ((raw.get("contratante") or {}).get("orgao") or {}).get("nome")
