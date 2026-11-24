from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import SOURCE_HISTORICAL, SOURCE_LIVE, ActivityLog, Anomaly, AnalysisState, Employee
from ..schemas import EmployeeCreate, EmployeeOut
from ..services.worker import worker
from .common import activity_out, anomaly_out, get_employee_or_404

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _latest_assessments(db: Session) -> dict[str, Anomaly]:
    sub = (select(Anomaly.employee_id, func.max(Anomaly.id).label("mid")).group_by(Anomaly.employee_id).subquery())
    rows = db.scalars(select(Anomaly).join(sub, Anomaly.id == sub.c.mid))
    return {a.employee_id: a for a in rows}


def _activity_stats(db: Session) -> dict[str, dict]:
    q = (select(ActivityLog.employee_id,
                func.count(ActivityLog.id),
                func.sum(case((ActivityLog.source == SOURCE_HISTORICAL, 1), else_=0)),
                func.sum(case((ActivityLog.source == SOURCE_LIVE, 1), else_=0)),
                func.max(ActivityLog.timestamp),
                func.max(case((ActivityLog.source == SOURCE_LIVE, ActivityLog.received_at), else_=None)))
         .group_by(ActivityLog.employee_id))
    return {r[0]: {"total_activity": r[1], "historical_activity": int(r[2] or 0), "live_activity": int(r[3] or 0),
                   "last_activity": r[4], "last_live_received": r[5]} for r in db.execute(q).all()}


def employee_summary(emp: Employee, stats: dict, latest: Anomaly | None, pending: int = 0) -> dict:
    d = EmployeeOut.model_validate(emp).model_dump()
    s = stats or {"total_activity": 0, "historical_activity": 0, "live_activity": 0, "last_activity": None,
                  "last_live_received": None}
    d.update(s)
    d["risk_status"] = latest.risk_level if latest else "unassessed"
    d["latest_assessment_id"] = latest.id if latest else None
    d["latest_assessment_at"] = latest.created_at if latest else None
    d["unanalyzed_live_events"] = pending
    return d


def _pending(db: Session) -> dict[str, int]:
    q = (select(ActivityLog.employee_id, func.count(ActivityLog.id))
         .outerjoin(AnalysisState, AnalysisState.employee_id == ActivityLog.employee_id)
         .where(ActivityLog.source == SOURCE_LIVE,
                ActivityLog.id > func.coalesce(AnalysisState.last_analyzed_event_id, 0))
         .group_by(ActivityLog.employee_id))
    return {r[0]: r[1] for r in db.execute(q).all()}


@router.get("")
def list_employees(db: Session = Depends(get_db)):
    emps = list(db.scalars(select(Employee).order_by(Employee.employee_id)))
    stats = _activity_stats(db)
    latest = _latest_assessments(db)
    pend = _pending(db)
    return [employee_summary(e, stats.get(e.employee_id), latest.get(e.employee_id), pend.get(e.employee_id, 0))
            for e in emps]


@router.post("", status_code=201)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Employee.id).where(Employee.employee_id == body.employee_id)) is not None:
        raise HTTPException(409, f"Employee ID {body.employee_id} already exists")
    if body.email and db.scalar(select(Employee.id).where(func.lower(Employee.email) == body.email.lower())):
        raise HTTPException(409, f"Email {body.email} is already used by another employee")
    emp = Employee(employee_id=body.employee_id, name=body.name, role=body.role, department=body.department,
                   email=body.email, is_synthetic=False, created_at=datetime.now(timezone.utc))
    db.add(emp)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, f"Employee ID {body.employee_id} already exists") from exc
    db.refresh(emp)
    return employee_summary(emp, None, None)


@router.get("/{employee_id}")
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = get_employee_or_404(db, employee_id)
    stats = _activity_stats(db).get(emp.employee_id)
    latest = _latest_assessments(db).get(emp.employee_id)
    d = employee_summary(emp, stats, latest, _pending(db).get(emp.employee_id, 0))
    st = db.get(AnalysisState, emp.employee_id)
    d["analysis_state"] = None if st is None else {
        "last_analyzed_event_id": st.last_analyzed_event_id, "last_success_at": st.last_success_at,
        "last_error": st.last_error, "next_retry_at": st.next_retry_at,
        "consecutive_failures": st.consecutive_failures}
    d["analysis_job"] = worker.job_for(emp.employee_id)
    d["latest_assessment"] = anomaly_out([latest], db)[0] if latest else None
    return d


@router.get("/{employee_id}/activity")
def employee_activity(employee_id: str, source: str | None = None, event_type: str | None = None,
                      q: str | None = Query(None, max_length=100), limit: int = Query(100, ge=1, le=1000),
                      offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    emp = get_employee_or_404(db, employee_id)
    stmt = select(ActivityLog).where(ActivityLog.employee_id == emp.employee_id)
    if source:
        stmt = stmt.where(ActivityLog.source == source)
    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(func.coalesce(ActivityLog.domain, "") + " " + func.coalesce(ActivityLog.url, "")
                                     + " " + func.coalesce(ActivityLog.filename, "")).like(like))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(stmt.order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
                           .limit(limit).offset(offset)))
    return {"total": total, "items": activity_out(rows, db)}


@router.get("/{employee_id}/anomalies")
def employee_anomalies(employee_id: str, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    emp = get_employee_or_404(db, employee_id)
    rows = list(db.scalars(select(Anomaly).where(Anomaly.employee_id == emp.employee_id)
                           .order_by(Anomaly.created_at.desc()).limit(limit)))
    return anomaly_out(rows, db)


@router.get("/{employee_id}/timeline")
def employee_timeline(employee_id: str, days: int = Query(45, ge=1, le=365), db: Session = Depends(get_db)):
    emp = get_employee_or_404(db, employee_id)
    tz = settings.org_tz
    latest = db.scalar(select(func.max(ActivityLog.timestamp)).where(ActivityLog.employee_id == emp.employee_id))
    since = (latest or datetime.now(timezone.utc)) - timedelta(days=days)
    rows = db.execute(select(ActivityLog.timestamp, ActivityLog.source, ActivityLog.event_type)
                      .where(ActivityLog.employee_id == emp.employee_id, ActivityLog.timestamp >= since)).all()
    by_day: dict[str, dict] = {}
    types: dict[str, dict] = {}
    for ts, src, et in rows:
        key = "live" if src == SOURCE_LIVE else "historical"
        k = ts.astimezone(tz).strftime("%Y-%m-%d")
        by_day.setdefault(k, {"date": k, "historical": 0, "live": 0})[key] += 1
        types.setdefault(et, {"event_type": et, "historical": 0, "live": 0})[key] += 1
    return {"daily": [by_day[k] for k in sorted(by_day)],
            "event_types": sorted(types.values(), key=lambda x: -(x["historical"] + x["live"]))}
