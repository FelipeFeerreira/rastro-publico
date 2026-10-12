"""Infraestrutura base para conectores de dados públicos.

Oferece: cliente HTTP com timeout, retries com backoff exponencial, respeito a
`Retry-After`, limite de taxa simples, paginação e registro de erros. Cada
conector concreto apenas descreve endpoints e o mapeamento de dados.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorError(RuntimeError):
    """Erro irrecuperável ao consultar uma fonte de dados."""


@dataclass
class ConnectorConfig:
    name: str
    base_url: str
    timeout_seconds: int = 30
    max_retries: int = 4
    page_size: int = 50
    min_interval_seconds: float = 0.2
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Page:
    """Página padronizada de resultados de um conector."""

    items: list[dict[str, Any]]
    page_number: int
    total_pages: int | None
    total_records: int | None
    has_more: bool


class BaseConnector:
    """Cliente HTTP resiliente para uma fonte pública."""

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._last_request_at = 0.0
        self._client: httpx.Client | None = None

    # --- ciclo de vida ---
    def __enter__(self) -> BaseConnector:
        self._client = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            headers={"User-Agent": f"RastroPublico/0.1 (+transparencia) {self.config.headers.get('User-Agent', '')}".strip()},
            follow_redirects=True,
        )
        return self

    def __exit__(self, *exc: object) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # --- infraestrutura ---
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self.config.min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        allow_not_found: bool = False,
    ) -> Any:
        if self._client is None:
            raise ConnectorError("Conector usado fora do contexto (use `with`).")

        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(path, params=clean_params)
                self._last_request_at = time.monotonic()

                # Algumas fontes retornam 404 para um recurso inexistente
                # (ex.: unidade sem contratos). Quando explicitamente permitido,
                # isso é tratado como "vazio", não como falha.
                if allow_not_found and response.status_code == 404:
                    return None

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "1"))
                    logger.warning(
                        "Rate limit de %s; aguardando %.1fs",
                        self.config.name,
                        retry_after,
                        extra={"connector": self.config.name},
                    )
                    time.sleep(min(retry_after, 30))
                    continue
                if 500 <= response.status_code < 600:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}", request=response.request, response=response
                    )
                if response.status_code >= 400:
                    # 4xx (exceto 429) são erros de contrato: não insistir.
                    raise ConnectorError(
                        f"{self.config.name}: HTTP {response.status_code} em {path}: "
                        f"{response.text[:200]}"
                    )
                return response.json()

            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                backoff = min(2 ** (attempt - 1), 15)
                logger.warning(
                    "Falha (%s/%s) em %s%s: %s. Retry em %ss",
                    attempt,
                    self.config.max_retries,
                    self.config.name,
                    path,
                    exc,
                    backoff,
                    extra={"connector": self.config.name},
                )
                if attempt == self.config.max_retries:
                    break
                time.sleep(backoff)

        raise ConnectorError(
            f"{self.config.name}: falha após {self.config.max_retries} tentativas em {path}"
        ) from last_error

    def download(self, path: str) -> bytes:
        """Baixa um recurso binário (ex.: CSV/ZIP) com retries e rate limit."""
        if self._client is None:
            raise ConnectorError("Conector usado fora do contexto (use `with`).")

        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(path)
                self._last_request_at = time.monotonic()
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "1"))
                    time.sleep(min(retry_after, 30))
                    continue
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 400:
                    raise ConnectorError(
                        f"{self.config.name}: HTTP {response.status_code} em {path}"
                    )
                return response.content
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                backoff = min(2 ** (attempt - 1), 15)
                logger.warning(
                    "Falha de download (%s/%s) em %s%s: %s",
                    attempt, self.config.max_retries, self.config.name, path, exc,
                    extra={"connector": self.config.name},
                )
                if attempt == self.config.max_retries:
                    break
                time.sleep(backoff)
        raise ConnectorError(
            f"{self.config.name}: falha no download após {self.config.max_retries} "
            f"tentativas em {path}"
        ) from last_error

    # --- paginação ---
    def paginate(
        self,
        path: str,
        params: dict[str, Any],
        page_param: str = "pagina",
        size_param: str = "tamanhoPagina",
        max_pages: int | None = None,
    ) -> Iterator[Page]:
        """Itera páginas no formato padrão do PNCP."""
        page_number = 1
        while True:
            query = {**params, page_param: page_number, size_param: self.config.page_size}
            payload = self._request(path, query)
            items = payload.get("data", [])
            total_pages = payload.get("totalPaginas")
            total_records = payload.get("totalRegistros")
            has_more = bool(items) and (total_pages is None or page_number < total_pages)
            yield Page(
                items=items,
                page_number=page_number,
                total_pages=total_pages,
                total_records=total_records,
                has_more=has_more,
            )
            if not has_more or (max_pages is not None and page_number >= max_pages):
                break
            page_number += 1
