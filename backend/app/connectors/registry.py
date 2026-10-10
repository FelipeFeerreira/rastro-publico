"""Registro de conectores disponíveis por código de fonte."""

from __future__ import annotations

from app.connectors.base import BaseConnector
from app.connectors.pncp import PNCPConnector

CONNECTORS: dict[str, type[BaseConnector]] = {
    "pncp": PNCPConnector,
}


def get_connector(code: str) -> BaseConnector:
    try:
        return CONNECTORS[code]()
    except KeyError as exc:  # pragma: no cover - erro de configuração
        raise ValueError(f"Conector desconhecido: {code}") from exc
