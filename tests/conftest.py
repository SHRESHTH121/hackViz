"""Test setup: runs against a separate PostgreSQL database (<dbname>_test) so demo data is untouched.

Run from the project root with the backend virtualenv:
    backend\\.venv\\Scripts\\python -m pytest tests -v
    backend\\.venv\\Scripts\\python -m pytest tests -v -m "not ollama"   # skip real LLM inference tests
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "data"))

_env = {**dotenv_values(BACKEND / ".env"), **os.environ}
_base_url = _env.get("DATABASE_URL", "")
if not _base_url.startswith("postgresql"):
    raise RuntimeError("Tests need DATABASE_URL (PostgreSQL) in backend/.env")
_prefix, _dbname = _base_url.rsplit("/", 1)
TEST_DB = (_dbname.split("?")[0] or "hackviz") + "_test"
os.environ["DATABASE_URL"] = f"{_prefix}/{TEST_DB}"
os.environ["ANALYSIS_AUTO_ENABLED"] = "false"  # tests trigger analysis explicitly


def _ensure_test_database() -> None:
    import psycopg

    dsn = _prefix.replace("postgresql+psycopg://", "postgresql://") + "/postgres"
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB}"')


_ensure_test_database()


def pytest_configure(config):
    config.addinivalue_line("markers", "ollama: performs real inference against the local Ollama server")


@pytest.fixture(scope="session")
def fresh_db():
    from app.database import Base, engine
    from app import models  # noqa: F401
    from app.seed import seed

    from sqlalchemy import func, select
    from app.database import SessionLocal

    Base.metadata.drop_all(bind=engine)
    result = seed(verbose=False)
    with SessionLocal() as s:
        result["anomalies_after_seed"] = s.scalar(select(func.count(models.Anomaly.id)))
    return result


@pytest.fixture(scope="session")
def client(fresh_db):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(fresh_db):
    from app.database import SessionLocal

    s = SessionLocal()
    yield s
    s.rollback()
    s.close()
