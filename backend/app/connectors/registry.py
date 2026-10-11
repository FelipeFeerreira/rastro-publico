"""Registro de conectores disponíveis por código de fonte."""

from __future__ import annotations

from app.connectors.base import BaseConnector
from app.connectors.comprasnet import ComprasnetContratosConnector
from app.connectors.pncp import PNCPConnector
from app.connectors.tce_sp import TceSpConnector
from app.connectors.transparencia import TransparenciaConnector

CONNECTORS: dict[str, type[BaseConnector]] = {
    "pncp": PNCPConnector,
    "comprasnet": ComprasnetContratosConnector,
    "transparencia": TransparenciaConnector,
    "tce_sp": TceSpConnector,
}


def get_connector(code: str) -> BaseConnector:
    try:
        return CONNECTORS[code]()
    except KeyError as exc:  # pragma: no cover - erro de configuração
        raise ValueError(f"Conector desconhecido: {code}") from exc
