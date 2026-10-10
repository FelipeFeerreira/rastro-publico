"""Engine e fábrica de sessões do banco de dados."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine_kwargs: dict = {"echo": settings.db_echo, "pool_pre_ping": True, "future": True}

if settings.database_url.startswith("postgresql"):
    _engine_kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
elif settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(connect_args={"check_same_thread": False})

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: abre e fecha uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Contexto transacional para scripts, ingestão e tarefas assíncronas."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
