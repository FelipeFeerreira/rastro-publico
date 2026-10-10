"""Fixtures de teste: banco SQLite isolado e cliente de API."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# Configura o ambiente de teste ANTES de importar a aplicação.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)  # noqa: SIM115
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["AI_PROVIDER"] = "disabled"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.analysis.engine import ensure_rules  # noqa: E402
from app.services.reference_data import seed_reference_data  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db() -> Iterator[None]:
    """Recria o schema e os dados de referência antes de cada teste (isolamento)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_reference_data(db)
        ensure_rules(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
