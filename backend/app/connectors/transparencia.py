"""Conector do Portal da Transparência Federal (servidores e remuneração).

Documentação verificada em 2026-10:
- OpenAPI:  https://api.portaldatransparencia.gov.br/v3/api-docs
- Swagger:  https://api.portaldatransparencia.gov.br/swagger-ui/index.html

Autenticação: **obrigatória** via header `chave-api-dados`. A chave é gratuita,
mas pessoal e intransferível (https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email).
Sem a chave a API retorna HTTP 401.

Endpoints relevantes:
- GET /api-de-dados/servidores?orgaoServidorLotacao={codigo}&pagina={p}
- GET /api-de-dados/servidores/{id}
- GET /api-de-dados/servidores/remuneracao?id={id}&mesAno={AAAAMM}&pagina={p}

Observação importante: a remuneração é por servidor/mês. NÃO é tabela de cargos.
A lotação (campus/UORG) é resolvida no detalhe do servidor; o código do órgão
(ex.: IFSP 26439) NÃO identifica o campus por si só.
"""

from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from app.core.config import settings

# A base já inclui o prefixo `/api-de-dados` (ver config.transparencia_base_url).
TRANSPARENCIA_BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"


class TransparenciaConnector(BaseConnector):
    def __init__(self) -> None:
        headers = {}
        if settings.transparencia_api_key:
            headers["chave-api-dados"] = settings.transparencia_api_key
        super().__init__(
            ConnectorConfig(
                name="transparencia",
                base_url=settings.transparencia_base_url or TRANSPARENCIA_BASE_URL,
                timeout_seconds=45,
                max_retries=3,
                page_size=100,
                min_interval_seconds=0.4,
                headers=headers,
            )
        )

    @property
    def credentials_available(self) -> bool:
        return bool(settings.transparencia_api_key)

    def _require_credentials(self) -> None:
        if not self.credentials_available:
            raise ConnectorError(
                "Credencial ausente: defina TRANSPARENCIA_API_KEY no ambiente para "
                "consultar servidores e remunerações do Portal da Transparência. "
                "Obtenha uma chave gratuita em "
                "https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email"
            )

    # --- Consultas ---
    def fetch_servidores(
        self, orgao_code: str, *, pagina: int = 1
    ) -> list[dict[str, Any]]:
        self._require_credentials()
        payload = self._request(
            "/servidores",
            {"orgaoServidorLotacao": orgao_code, "pagina": pagina},
        )
        return payload if isinstance(payload, list) else []

    def fetch_servidor(self, servidor_id: int | str) -> dict[str, Any] | None:
        self._require_credentials()
        payload = self._request(f"/servidores/{servidor_id}")
        return payload if isinstance(payload, dict) else None

    def fetch_remuneracao(
        self, servidor_id: int | str, mes_ano: str, *, pagina: int = 1
    ) -> list[dict[str, Any]]:
        self._require_credentials()
        payload = self._request(
            "/servidores/remuneracao",
            {"id": servidor_id, "mesAno": mes_ano, "pagina": pagina},
        )
        return payload if isinstance(payload, list) else []

    # --- Extração defensiva (validar com dados reais quando houver chave) ---
    @staticmethod
    def extract_name(servidor: dict[str, Any]) -> str | None:
        pessoa = servidor.get("pessoa") or {}
        return pessoa.get("nome") or servidor.get("nome")

    @staticmethod
    def extract_masked_document(servidor: dict[str, Any]) -> str | None:
        pessoa = servidor.get("pessoa") or {}
        return (
            pessoa.get("cpfDescaracterizado")
            or pessoa.get("cpfFormatado")
            or servidor.get("cpfFormatado")
        )

    @staticmethod
    def extract_role(servidor: dict[str, Any]) -> str | None:
        funcao = servidor.get("funcao") or {}
        return funcao.get("descricaoFuncaoCargo") or funcao.get("descricao")

    @staticmethod
    def extract_campus_uorg(detalhe: dict[str, Any] | None) -> str | None:
        """Resolve o campus (UORG de lotação) a partir do detalhe do servidor."""
        if not detalhe:
            return None
        for key in ("fichasCargoEfetivo", "fichasFuncao", "fichasDemaisSituacoes"):
            fichas = detalhe.get(key) or []
            for ficha in fichas:
                uorg = ficha.get("uorgLotacao") or {}
                nome = uorg.get("nome") if isinstance(uorg, dict) else str(uorg)
                if nome:
                    return nome
        return None

    @staticmethod
    def extract_remuneracao(remuneracao: dict[str, Any]) -> dict[str, Any]:
        """Extrai bruto/líquido/deduções de uma ficha de remuneração."""
        bruto = remuneracao.get("remuneracaoBasicaBruta")
        liquido = remuneracao.get("valorTotalRemuneracaoAposDeducoes")
        mes_ano = str(remuneracao.get("mesAno") or "")
        ano = int(mes_ano[:4]) if len(mes_ano) >= 4 and mes_ano[:4].isdigit() else None
        mes = int(mes_ano[4:6]) if len(mes_ano) >= 6 and mes_ano[4:6].isdigit() else None
        return {
            "gross": bruto,
            "net": liquido,
            "year": ano,
            "month": mes,
            "mes_ano": mes_ano,
            "observacoes": remuneracao.get("observacoes"),
        }
