from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SOURCE_LIVE, ActivityLog, Employee, ExtensionSession
from ..schemas import ActivityBatchIn, ActivityIn
from .common import activity_out

router = APIRouter(prefix="/api/activity", tags=["activity"])


def _ingest(db: Session, ev: ActivityIn) -> dict:
    """Validate + persist one live event. Never waits for analysis."""
    emp = db.scalar(select(Employee).where(Employee.employee_id == ev.employee_id))
    if emp is None:
        raise HTTPException(404, f"Unknown employee ID {ev.employee_id} - pair the extension with an existing employee")
    sess = None
    if ev.session_token:
        sess = db.scalar(select(ExtensionSession).where(ExtensionSession.session_token == ev.session_token))
        if sess is None or sess.disconnected_at is not None:
            raise HTTPException(401, "Extension pairing is no longer valid - pair again")
        if sess.employee_id != ev.employee_id:
            raise HTTPException(403, "Event employee does not match the paired employee")
    if ev.client_event_id:
        dup = db.scalar(select(ActivityLog.id).where(ActivityLog.client_event_id == ev.client_event_id))
        if dup is not None:
            return {"id": dup, "duplicate": True}
    meta = dict(ev.metadata or {})
    row = ActivityLog(employee_id=ev.employee_id, event_type=ev.event_type, domain=ev.domain, url=ev.url,
                      filename=ev.filename, timestamp=ev.timestamp, source=SOURCE_LIVE, safe_metadata=meta or None,
                      client_event_id=ev.client_event_id, received_at=datetime.now(timezone.utc))
    try:
        with db.begin_nested():  # savepoint: a duplicate must not roll back the rest of a batch
            db.add(row)
    except IntegrityError:
        dup = db.scalar(select(ActivityLog.id).where(ActivityLog.client_event_id == ev.client_event_id))
        return {"id": dup, "duplicate": True}
    if sess is not None:
        sess.events_received += 1
        sess.last_event_at = row.received_at
        sess.last_heartbeat_at = row.received_at
    return {"id": row.id, "duplicate": False}


@router.post("", status_code=201)
def post_activity(ev: ActivityIn, db: Session = Depends(get_db)):
    res = _ingest(db, ev)
    db.commit()
    return res


@router.post("/batch", status_code=201)
def post_activity_batch(body: ActivityBatchIn, db: Session = Depends(get_db)):
    """Used by the extension to flush events queued while the backend was unavailable."""
    results = []
    for raw in body.events:
        cid = str(raw.get("client_event_id"))[:64] if raw.get("client_event_id") else None
        try:
            ev = ActivityIn.model_validate(raw)
        except ValidationError as exc:
            msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            results.append({"client_event_id": cid, "error": msg[:300], "status": 422})
            continue
        try:
            results.append({"client_event_id": ev.client_event_id, **_ingest(db, ev)})
        except HTTPException as exc:
            results.append({"client_event_id": ev.client_event_id, "error": exc.detail, "status": exc.status_code})
    db.commit()
    return {"results": results}


@router.get("")
def list_activity(employee_id: str | None = None, source: str | None = None, event_type: str | None = None,
                  since_id: int | None = Query(None, ge=0), limit: int = Query(50, ge=1, le=500),
                  offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(ActivityLog)
    if employee_id:
        stmt = stmt.where(ActivityLog.employee_id == employee_id.strip().upper())
    if source:
        stmt = stmt.where(ActivityLog.source == source)
    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)
    if since_id is not None:
        stmt = stmt.where(ActivityLog.id > since_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(stmt.order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
                           .limit(limit).offset(offset)))
    return {"total": total, "items": activity_out(rows, db)}


@router.get("/{event_id}")
def get_activity(event_id: int, db: Session = Depends(get_db)):
    row = db.get(ActivityLog, event_id)
    if row is None:
        raise HTTPException(404, f"Activity record {event_id} not found")
    out = activity_out([row], db)[0]
    emp = db.scalar(select(Employee).where(Employee.employee_id == row.employee_id))
    if emp:
        out.update(role=emp.role, department=emp.department)
    return out
