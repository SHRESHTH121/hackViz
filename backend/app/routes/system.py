from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import check_connection, get_db
from ..models import SOURCE_HISTORICAL, SOURCE_LIVE, ActivityLog, Anomaly, Employee, ExtensionSession
from ..services import ollama_client
from ..services.worker import worker

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health():
    db_ok, db_info = check_connection()
    return {"status": "ok" if db_ok else "degraded", "backend": "ok", "database": "ok" if db_ok else "error",
            "database_info": db_info, "time": datetime.now(timezone.utc)}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    db_ok, db_info = check_connection()
    oc = ollama_client.check()
    now = datetime.now(timezone.utc)
    out = {
        "backend": {"ok": True, "time": now},
        "database": {"ok": db_ok, "info": db_info, "engine": "PostgreSQL"},
        "ollama": {"ok": oc["reachable"], "url": oc["url"], "model": oc["model"],
                   "model_available": oc["model_available"], "installed_models": oc["models"], "error": oc["error"]},
        "analysis": worker.status(),
        "monitoring": None,
    }
    if db_ok:
        sessions = list(db.scalars(select(ExtensionSession).where(ExtensionSession.disconnected_at.is_(None))
                                   .order_by(ExtensionSession.paired_at.desc()).limit(10)))
        emps = {e.employee_id: e for e in db.scalars(select(Employee).where(
            Employee.employee_id.in_({s.employee_id for s in sessions})))} if sessions else {}
        last_live = db.execute(select(ActivityLog.received_at, ActivityLog.employee_id)
                               .where(ActivityLog.source == SOURCE_LIVE)
                               .order_by(ActivityLog.id.desc()).limit(1)).first()
        live_recent = db.scalar(select(func.count(ActivityLog.id)).where(
            ActivityLog.source == SOURCE_LIVE, ActivityLog.received_at >= now - timedelta(minutes=60)))
        paired = []
        for s in sessions:
            hb_age = (now - s.last_heartbeat_at).total_seconds() if s.last_heartbeat_at else None
            ev_age = (now - s.last_event_at).total_seconds() if s.last_event_at else None
            e = emps.get(s.employee_id)
            paired.append({
                "employee_id": s.employee_id, "employee_name": e.name if e else None, "role": e.role if e else None,
                "paired_at": s.paired_at, "last_heartbeat_at": s.last_heartbeat_at, "last_event_at": s.last_event_at,
                "events_received": s.events_received,
                "connection": "online" if hb_age is not None and hb_age < 120 else "stale",
                "transmitting": ev_age is not None and ev_age < 300,
            })
        out["monitoring"] = {
            "paired_extensions": paired,
            "last_live_event_at": last_live[0] if last_live else None,
            "last_live_event_employee": last_live[1] if last_live else None,
            "live_events_last_hour": live_recent,
            "status": ("transmitting" if any(p["transmitting"] for p in paired) else
                       "paired_idle" if any(p["connection"] == "online" for p in paired) else
                       "no_active_pairing"),
        }
    return out


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    total_emp = db.scalar(select(func.count(Employee.id)))
    hist = db.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.source == SOURCE_HISTORICAL))
    live = db.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.source == SOURCE_LIVE))
    active = db.scalar(select(func.count(func.distinct(ActivityLog.employee_id))).where(
        ActivityLog.source == SOURCE_LIVE, ActivityLog.received_at >= now - timedelta(hours=24)))
    assessments = db.scalar(select(func.count(Anomaly.id)))
    anomalies = db.scalar(select(func.count(Anomaly.id)).where(Anomaly.is_anomaly.is_(True)))
    high = db.scalar(select(func.count(Anomaly.id)).where(Anomaly.is_anomaly.is_(True), Anomaly.risk_level == "high"))
    by_type = db.execute(select(ActivityLog.event_type, ActivityLog.source, func.count(ActivityLog.id))
                         .group_by(ActivityLog.event_type, ActivityLog.source)).all()
    types: dict[str, dict] = {}
    for et, src, n in by_type:
        d = types.setdefault(et, {"event_type": et, "historical": 0, "live": 0})
        d["live" if src == SOURCE_LIVE else "historical"] += n
    # local calendar day in the organisation's timezone
    day = func.date(func.timezone("UTC", ActivityLog.timestamp) + timedelta(minutes=settings.org_utc_offset_minutes))
    daily = db.execute(select(day, ActivityLog.source, func.count(ActivityLog.id))
                       .group_by(day, ActivityLog.source).order_by(day)).all()
    days: dict[str, dict] = {}
    for d, src, n in daily:
        k = d.isoformat()
        r = days.setdefault(k, {"date": k, "historical": 0, "live": 0})
        r["live" if src == SOURCE_LIVE else "historical"] += n
    risk = db.execute(select(Anomaly.risk_level, func.count(Anomaly.id)).group_by(Anomaly.risk_level)).all()
    return {
        "total_employees": total_emp, "active_employees": active, "historical_activity": hist,
        "live_activity": live, "assessments": assessments, "anomalies_detected": anomalies,
        "high_risk_alerts": high,
        "event_types": sorted(types.values(), key=lambda x: -(x["historical"] + x["live"])),
        "daily": list(days.values())[-60:],
        "risk_distribution": {r: n for r, n in risk},
    }
