"""Tarefas assíncronas opcionais (Celery + Redis).

Ativado apenas quando ENABLE_CELERY=true e Redis está disponível. A aplicação
funciona sem Celery; a ingestão também pode rodar via CLI ou em background do
FastAPI para volumes pequenos.
"""

from __future__ import annotations

from datetime import date

from app.core.config import settings

try:
    from celery import Celery
except Exception:  # pragma: no cover - dependência opcional
    Celery = None  # type: ignore


if Celery is not None:
    celery_app = Celery(
        "rastro_publico",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Sao_Paulo",
        enable_utc=True,
        task_time_limit=3600,
    )

    @celery_app.task(name="ingest_pncp")
    def ingest_pncp_task(start: str, end: str, with_items: bool = False) -> dict:
        from app.db.session import session_scope
        from app.services.ingestion import IngestionService

        with session_scope() as db:
            run = IngestionService(db).ingest_pncp_publications(
                date.fromisoformat(start), date.fromisoformat(end), with_items=with_items
            )
            return {"run_id": run.id, "status": run.status.value}

    @celery_app.task(name="run_audit")
    def run_audit_task(limit: int = 500) -> dict:
        from app.db.session import session_scope
        from app.services.analysis.engine import AuditEngine

        with session_scope() as db:
            return {"findings": AuditEngine(db).run_scan(limit=limit)}
else:  # pragma: no cover
    celery_app = None
