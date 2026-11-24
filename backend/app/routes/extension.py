"""Chrome extension pairing. Pairing proves the employee exists; it is tracked separately
from successful event transmission (last_event_at / events_received)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Employee, ExtensionSession
from ..schemas import PairIn, TokenIn

router = APIRouter(prefix="/api/extension", tags=["extension"])


def _session_out(s: ExtensionSession, emp: Employee | None) -> dict:
    return {"session_token": s.session_token, "employee_id": s.employee_id,
            "employee_name": emp.name if emp else None, "role": emp.role if emp else None,
            "department": emp.department if emp else None, "paired_at": s.paired_at,
            "last_heartbeat_at": s.last_heartbeat_at, "last_event_at": s.last_event_at,
            "events_received": s.events_received, "disconnected_at": s.disconnected_at}


@router.post("/pair", status_code=201)
def pair(body: PairIn, db: Session = Depends(get_db)):
    emp = db.scalar(select(Employee).where(Employee.employee_id == body.employee_id))
    if emp is None:
        raise HTTPException(404, f"Employee ID {body.employee_id} does not exist")
    now = datetime.now(timezone.utc)
    s = ExtensionSession(session_token=secrets.token_urlsafe(24), employee_id=emp.employee_id, paired_at=now,
                         last_heartbeat_at=now, extension_version=body.extension_version)
    db.add(s)
    db.commit()
    return _session_out(s, emp)


@router.post("/heartbeat")
def heartbeat(body: TokenIn, db: Session = Depends(get_db)):
    s = db.scalar(select(ExtensionSession).where(ExtensionSession.session_token == body.session_token))
    if s is None or s.disconnected_at is not None:
        raise HTTPException(401, "Pairing not found or disconnected")
    s.last_heartbeat_at = datetime.now(timezone.utc)
    db.commit()
    emp = db.scalar(select(Employee).where(Employee.employee_id == s.employee_id))
    return _session_out(s, emp)


@router.post("/unpair")
def unpair(body: TokenIn, db: Session = Depends(get_db)):
    s = db.scalar(select(ExtensionSession).where(ExtensionSession.session_token == body.session_token))
    if s is None:
        raise HTTPException(404, "Pairing not found")
    if s.disconnected_at is None:
        s.disconnected_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}


@router.get("/sessions")
def sessions(active_only: bool = True, db: Session = Depends(get_db)):
    stmt = select(ExtensionSession)
    if active_only:
        stmt = stmt.where(ExtensionSession.disconnected_at.is_(None))
    rows = list(db.scalars(stmt.order_by(ExtensionSession.paired_at.desc()).limit(20)))
    emps = {e.employee_id: e for e in db.scalars(select(Employee).where(
        Employee.employee_id.in_({r.employee_id for r in rows})))} if rows else {}
    out = []
    for r in rows:
        d = _session_out(r, emps.get(r.employee_id))
        d.pop("session_token")  # never expose tokens to the dashboard
        out.append(d)
    return out
