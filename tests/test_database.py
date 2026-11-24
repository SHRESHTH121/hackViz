"""PostgreSQL connectivity, schema, seeding and persistence."""
import csv

from sqlalchemy import create_engine, func, inspect, select, text


def test_connection_is_postgresql(fresh_db):
    from app.database import check_connection, engine

    ok, info = check_connection()
    assert ok, info
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert "PostgreSQL" in info


def test_tables_created(fresh_db):
    from app.database import engine

    names = set(inspect(engine).get_table_names())
    assert {"employees", "activity_logs", "anomalies", "analysis_state", "extension_sessions"} <= names


def test_ten_initial_employees(db, fresh_db):
    from app.models import Employee

    # Other test modules may have added employees; the seeded (synthetic) set must be exactly these 10.
    emps = list(db.scalars(select(Employee).where(Employee.is_synthetic.is_(True)).order_by(Employee.employee_id)))
    assert [e.employee_id for e in emps] == [f"EMP{i:03d}" for i in range(1, 11)]
    assert fresh_db["employees_added"] == 10 and fresh_db["historical_events_imported"] > 4000
    assert emps[1].role == "Software Developer (SDE1)" and emps[6].department == "IT"


def test_historical_import_matches_csv(db):
    from app.config import settings
    from app.models import SOURCE_HISTORICAL, ActivityLog

    with (settings.data_dir / "historical_activity.csv").open(encoding="utf-8") as f:
        n_csv = sum(1 for _ in csv.DictReader(f))
    n_db = db.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.source == SOURCE_HISTORICAL))
    assert n_db == n_csv
    orphans = db.scalar(text("SELECT count(*) FROM activity_logs a LEFT JOIN employees e "
                             "ON e.employee_id = a.employee_id WHERE e.id IS NULL"))
    assert orphans == 0


def test_seed_is_idempotent(fresh_db):
    from app.seed import seed

    again = seed(verbose=False)
    assert again == {"employees_added": 0, "historical_events_imported": 0}


def test_no_anomalies_precreated(fresh_db):
    # Alerts only exist after real model inference - seeding creates none.
    assert fresh_db["anomalies_after_seed"] == 0


def test_persistence_across_new_engine(client):
    """Simulates a backend restart: a brand-new engine/connection pool still sees committed rows."""
    import os

    r = client.post("/api/employees", json={"employee_id": "PERSIST1", "name": "Persist Check", "role": "Tester",
                                            "department": "QA"})
    assert r.status_code == 201
    url = os.environ["DATABASE_URL"]
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            row = c.execute(text("SELECT name FROM employees WHERE employee_id='PERSIST1'")).first()
        assert row and row[0] == "Persist Check"
    finally:
        eng.dispose()


def test_rejects_non_postgres_url(monkeypatch):
    import importlib

    import app.config as cfg

    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    try:
        cfg.load_settings()
        raise AssertionError("SQLite URL must be rejected")
    except cfg.ConfigError as e:
        assert "PostgreSQL" in str(e)
    importlib.invalidate_caches()
