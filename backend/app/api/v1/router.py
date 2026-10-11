"""Agregador de rotas da API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analysis,
    assistant,
    auth,
    contracts,
    entities,
    health,
    investigations,
    monitoring,
    payments,
    procurements,
    salaries,
    search,
    sources,
    suppliers,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sources.router)
api_router.include_router(search.router)
api_router.include_router(procurements.router)
api_router.include_router(contracts.router)
api_router.include_router(payments.router)
api_router.include_router(salaries.router)
api_router.include_router(suppliers.router)
api_router.include_router(entities.router)
api_router.include_router(analysis.router)
api_router.include_router(assistant.router)
api_router.include_router(auth.router)
api_router.include_router(investigations.router)
api_router.include_router(monitoring.router)
api_router.include_router(admin.router)
