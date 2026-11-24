"""Load the fictional dataset into PostgreSQL (idempotent).

    python -m app.seed            # create tables, import if missing
    python -m app.seed --reset    # DROP all hackViz tables and re-import (destroys live data!)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import subprocess
import sys
from datetime import datetime

from sqlalchemy import func, insert, select

from .config import PROJECT_DIR, settings
from .database import Base, SessionLocal, engine, init_db
from .models import SOURCE_HISTORICAL, ActivityLog, Employee

log = logging.getLogger("hackviz.seed")


def ensure_dataset() -> None:
    emp = settings.data_dir / "employees.json"
    act = settings.data_dir / "historical_activity.csv"
    if emp.exists() and act.exists():
        return
    log.warning("Generated dataset not found - running data/generate_dataset.py")
    subprocess.run([sys.executable, str(PROJECT_DIR / "data" / "generate_dataset.py")], check=True)


def seed(verbose: bool = True) -> dict:
    init_db()
    ensure_dataset()
    data = json.loads((settings.data_dir / "employees.json").read_text(encoding="utf-8"))
    added_emp = 0
    added_events = 0
    with SessionLocal() as db:
        existing = set(db.scalars(select(Employee.employee_id)))
        for e in data["employees"]:
            if e["employee_id"] in existing:
                continue
            db.add(Employee(employee_id=e["employee_id"], name=e["name"], role=e["role"],
                            department=e["department"], email=e.get("email"),
                            profile={**e.get("profile", {}), "dataset": data["label"]}, is_synthetic=True))
            added_emp += 1
        db.commit()

        hist = db.scalar(select(func.count()).select_from(ActivityLog).where(ActivityLog.source == SOURCE_HISTORICAL))
        if hist == 0:
            rows = []
            with (settings.data_dir / "historical_activity.csv").open(encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                    meta["dataset"] = "synthetic_cert_style"
                    rows.append({
                        "employee_id": r["employee_id"], "event_type": r["event_type"],
                        "domain": r["domain"] or None, "url": r["url"] or None, "filename": r["filename"] or None,
                        "timestamp": datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
                        "source": SOURCE_HISTORICAL, "safe_metadata": meta, "dataset_record_id": r["record_id"],
                        "received_at": datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
                    })
            for i in range(0, len(rows), 1000):
                db.execute(insert(ActivityLog), rows[i:i + 1000])
            db.commit()
            added_events = len(rows)
    result = {"employees_added": added_emp, "historical_events_imported": added_events}
    if verbose:
        log.info("seed: %s", result)
    return result


def reset() -> None:
    from . import models  # noqa: F401
    Base.metadata.drop_all(bind=engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop all tables first (deletes live data)")
    a = ap.parse_args()
    if a.reset:
        reset()
        print("tables dropped")
    print(seed())
