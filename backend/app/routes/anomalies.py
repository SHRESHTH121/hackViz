from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActivityLog, Anomaly
from ..services import ollama_client
from ..services.worker import worker
from .common import activity_out, anomaly_out, get_employee_or_404

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/anomalies")
def list_anomalies(employee_id: str | None = None, risk_level: str | None = None,
                   only_anomalies: bool = False, limit: int = Query(100, ge=1, le=500),
                   since_id: int | None = Query(None, ge=0), db: Session = Depends(get_db)):
    stmt = select(Anomaly)
    if employee_id:
        stmt = stmt.where(Anomaly.employee_id == employee_id.strip().upper())
    if risk_level:
        stmt = stmt.where(Anomaly.risk_level == risk_level.lower())
    if only_anomalies:
        stmt = stmt.where(Anomaly.is_anomaly.is_(True))
    if since_id is not None:
        stmt = stmt.where(Anomaly.id > since_id)
    rows = list(db.scalars(stmt.order_by(Anomaly.created_at.desc(), Anomaly.id.desc()).limit(limit)))
    return anomaly_out(rows, db)


@router.get("/anomalies/{anomaly_id}")
def get_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    a = db.get(Anomaly, anomaly_id)
    if a is None:
        raise HTTPException(404, f"Assessment {anomaly_id} not found")
    out = anomaly_out([a], db)[0]
    ids = set(a.evidence_event_ids or []) | set(a.analyzed_event_ids or [])
    rows = list(db.scalars(select(ActivityLog).where(ActivityLog.id.in_(ids)).order_by(ActivityLog.timestamp,
                                                                                         ActivityLog.id)))
    events = activity_out(rows, db)
    ev = set(a.evidence_event_ids or [])
    out["evidence_events"] = [e for e in events if e["id"] in ev]
    out["analyzed_events"] = events
    out["raw_response"] = a.raw_response
    return out


@router.post("/analyze/{employee_id}", status_code=202)
def analyze_now(employee_id: str, force: bool = False, wait: bool = False,
                timeout: float = Query(300, ge=1, le=900), db: Session = Depends(get_db)):
    """Queue an on-demand analysis. Returns immediately (202) unless wait=true."""
    emp = get_employee_or_404(db, employee_id)
    if db.scalar(select(ActivityLog.id).where(ActivityLog.employee_id == emp.employee_id).limit(1)) is None:
        raise HTTPException(422, f"{emp.employee_id} has no activity to analyze yet")
    oc = ollama_client.check()
    if not oc["reachable"]:
        raise HTTPException(503, f"Ollama is not reachable at {oc['url']}. Start it with `ollama serve`.")
    if not oc["model_available"]:
        raise HTTPException(503, f"Model {oc['model']} is not installed. Run: ollama pull {oc['model']}")
    if not worker.alive:
        raise HTTPException(503, "Analysis worker is not running")
    job, created = worker.request(emp.employee_id, "manual", force)
    if wait:
        job.done.wait(timeout)
    body = {"queued": created, "already_in_progress": not created, "job": job.public()}
    code = 200 if (wait and job.done.is_set()) else 202
    return JSONResponse(content=_jsonable(body), status_code=code)


@router.get("/analysis/status")
def analysis_status():
    return worker.status()


def _jsonable(o):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(o)
