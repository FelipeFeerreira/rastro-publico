"""Aplicação FastAPI do Rastro Público."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("app.request")

DESCRIPTION = """
**Rastro Público** é uma plataforma independente de transparência de gastos
públicos brasileiros. Esta API expõe busca unificada, dados de contratações do
PNCP, comparação de preços e um motor de auditoria determinístico.

A plataforma **não** é um serviço oficial do governo e **não** emite conclusões
sobre irregularidades. Todos os valores são provenientes de fontes públicas
oficiais e preservam link para o registro de origem.
"""

app = FastAPI(
    title="Rastro Público API",
    description=DESCRIPTION,
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        logger.exception("Erro não tratado", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno. Tente novamente mais tarde.", "request_id": request_id},
        )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-process-time-ms"] = str(duration_ms)
    logger.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        response.status_code,
        extra={"request_id": request_id, "duration_ms": duration_ms},
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Exceção não tratada: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": __version__,
        "docs": "/api/docs",
        "api": settings.api_v1_prefix,
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
