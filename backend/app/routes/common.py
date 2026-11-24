from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ActivityLog, Anomaly, Employee
from ..schemas import ActivityOut, AnomalyOut, normalize_employee_id


def get_employee_or_404(db: Session, employee_id: str) -> Employee:
    try:
        eid = normalize_employee_id(employee_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    emp = db.scalar(select(Employee).where(Employee.employee_id == eid))
    if emp is None:
        raise HTTPException(404, f"Employee {eid} not found")
    return emp


def names(db: Session, ids: set[str]) -> dict[str, Employee]:
    if not ids:
        return {}
    return {e.employee_id: e for e in db.scalars(select(Employee).where(Employee.employee_id.in_(ids)))}


def activity_out(rows: list[ActivityLog], db: Session) -> list[dict]:
    emap = names(db, {r.employee_id for r in rows})
    out = []
    for r in rows:
        d = ActivityOut.model_validate(r).model_dump()
        e = emap.get(r.employee_id)
        d["employee_name"] = e.name if e else None
        out.append(d)
    return out


def anomaly_out(rows: list[Anomaly], db: Session) -> list[dict]:
    emap = names(db, {r.employee_id for r in rows})
    out = []
    for r in rows:
        d = AnomalyOut.model_validate(r).model_dump()
        e = emap.get(r.employee_id)
        if e:
            d.update(employee_name=e.name, role=e.role, department=e.department)
        out.append(d)
    return out
