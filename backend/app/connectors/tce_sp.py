"""Conector do TCE-SP — Portal da Transparência Municipal (despesas).

Documentação e respostas verificadas em 2026-10:
- Documentação: https://transparencia.tce.sp.gov.br/apis
- Conjunto de dados: https://transparencia.tce.sp.gov.br/conjunto-de-dados
- Base:          https://transparencia.tce.sp.gov.br
- Sem autenticação.

Rota de despesas: `GET /api/json/despesas/{municipio}/{exercicio}/{mes}`
- `municipio`: slug (ex.: `salto`), obtido em `/api/json/municipios`.
- `exercicio`: 4 dígitos. A documentação cita 2014–2019, mas a API respondeu
  inclusive 2019–2026 na verificação; não presumimos cobertura — testamos.
- `mes`: 1–12.

Cada item é um **evento** de despesa com campos:
`orgao, mes, evento, nr_empenho, id_fornecedor, nm_fornecedor,
dt_emissao_despesa, vl_despesa`.

Importante: é despesa **municipal**, não contrato. Não vinculamos a contratos.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.connectors.base import BaseConnector, ConnectorConfig
from app.models.enums import MunicipalExpenseStage

TCE_SP_BASE_URL = "https://transparencia.tce.sp.gov.br"

# Palavras-chave (contidas no valor de `evento`). "Valor Pago",
# "Valor Liquidado", "Anulação", "Reforço", "Empenhado".
_STAGE_KEYWORDS = [
    ("anul", MunicipalExpenseStage.ANULACAO),
    ("refor", MunicipalExpenseStage.REFORCO),
    ("liquid", MunicipalExpenseStage.LIQUIDADO),
    ("pago", MunicipalExpenseStage.PAGO),
    ("empenh", MunicipalExpenseStage.EMPENHADO),
]


class TceSpConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            ConnectorConfig(
                name="tce_sp",
                base_url=TCE_SP_BASE_URL,
                timeout_seconds=60,
                max_retries=4,
                page_size=100,
                min_interval_seconds=0.5,
                headers={"Accept": "application/json"},
            )
        )

    def fetch_despesas(self, municipio: str, ano: int, mes: int) -> list[dict[str, Any]]:
        payload = self._request(
            f"/api/json/despesas/{municipio}/{ano}/{mes}", allow_not_found=True
        )
        if payload is None:
            return []
        return payload if isinstance(payload, list) else []

    @staticmethod
    def month_name_to_number(name: str | None) -> int | None:
        if not name:
            return None
        months = {
            "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
            "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
            "outubro": 10, "novembro": 11, "dezembro": 12,
        }
        return months.get(name.strip().lower())

    @staticmethod
    def map_stage(evento: str | None) -> MunicipalExpenseStage | None:
        text = (evento or "").strip().lower()
        for keyword, stage in _STAGE_KEYWORDS:
            if keyword in text:
                return stage
        return None

    @staticmethod
    def parse_supplier(raw_id: str | None) -> tuple[str | None, str | None]:
        """Separa tipo e documento do `id_fornecedor`.

        Formatos observados: `CNPJ - PESSOA JURÍDICA - 58645656000141`,
        `CPF - PESSOA FÍSICA - 123456` (CPF parcial), `SEM IDENTIFICAÇÃO`.
        Retorna (tipo, documento_dígitos) — documento só quando tem 11/14 dígitos.
        """
        if not raw_id:
            return None, None
        parts = [p.strip() for p in raw_id.split(" - ")]
        digits = re.sub(r"\D", "", parts[-1]) if parts else ""
        if "CNPJ" in raw_id.upper() or len(digits) == 14:
            tipo = "PJ"
        elif "CPF" in raw_id.upper() or len(digits) == 11:
            tipo = "PF"
        else:
            tipo = None
        document = digits if len(digits) in (11, 14) else None
        return tipo, document

    @staticmethod
    def build_external_key(raw: dict[str, Any]) -> str:
        """Chave natural determinística do evento (para idempotência)."""
        parts = [
            str(raw.get("orgao") or ""),
            str(raw.get("mes") or ""),
            str(raw.get("evento") or ""),
            str(raw.get("nr_empenho") or ""),
            str(raw.get("id_fornecedor") or ""),
            str(raw.get("dt_emissao_despesa") or ""),
            str(raw.get("vl_despesa") or ""),
        ]
        return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def source_url(municipio: str, ano: int, mes: int) -> str:
        return f"{TCE_SP_BASE_URL}/api/json/despesas/{municipio}/{ano}/{mes}"
