from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import ActivityLog, Employee
from .common import get_employee_or_404

router = APIRouter(prefix="/api/export", tags=["export"])

HEADER = ["Event ID", "Employee ID", "Employee Name", "Role", "Department", "Timestamp (UTC)", "Event Type",
          "Domain", "URL", "Filename", "Source"]
SOURCE_LABEL = {"historical_cert": "Historical CERT Data (synthetic)", "chrome_extension": "Live Chrome Extension"}


def _safe(v) -> str:
    """Neutralise CSV/formula injection when opened in a spreadsheet."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def _rows(employee_id: str | None):
    db = SessionLocal()
    try:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(HEADER)
        yield "﻿" + buf.getvalue()
        stmt = (select(ActivityLog, Employee).join(Employee, Employee.employee_id == ActivityLog.employee_id)
                .order_by(ActivityLog.timestamp, ActivityLog.id))
        if employee_id:
            stmt = stmt.where(ActivityLog.employee_id == employee_id)
        for a, e in db.execute(stmt.execution_options(yield_per=2000)):
            buf.seek(0)
            buf.truncate()
            w.writerow([a.id, a.employee_id, _safe(e.name), _safe(e.role), _safe(e.department),
                        a.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), a.event_type,
                        _safe(a.domain), _safe(a.url), _safe(a.filename), SOURCE_LABEL.get(a.source, a.source)])
            yield buf.getvalue()
    finally:
        db.close()


@router.get("/activity.csv")
def export_activity(employee_id: str | None = None, db: Session = Depends(get_db)):
    eid = None
    if employee_id:
        eid = get_employee_or_404(db, employee_id).employee_id
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"hackviz_activity_{eid or 'all'}_{stamp}.csv"
    return StreamingResponse(_rows(eid), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
