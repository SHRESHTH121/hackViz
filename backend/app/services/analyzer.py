"""Context building, LLM prompting, validation and persistence of assessments.

Flow: select batch -> baseline + indicators -> compact prompt -> Ollama ->
JSON schema validation -> evidence-ID verification -> save + advance cursor
(in one transaction). If anything fails, nothing is saved and the cursor is
NOT advanced, so events are never skipped."""
from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SOURCE_HISTORICAL, SOURCE_LIVE, ActivityLog, Anomaly, AnalysisState, Employee
from ..schemas import LLMAssessment
from . import ollama_client
from .domain_catalog import categorize, expected_categories
from .indicators import compute_indicators

SYSTEM_PROMPT = """You are a cybersecurity insider-risk assessment assistant.

Analyze employee browser activity metadata in the context of the employee's job role, department, historical activity, and recent activity sequence.

Identify suspicious patterns that may warrant security investigation.

Do not assume malicious intent.
Do not treat after-hours activity alone as suspicious.
Do not flag a single unfamiliar website visit without supporting context.
Distinguish normal role-related activities from potentially unusual behaviour.
Consider legitimate explanations.
Use only the supplied activity records as evidence.
Never invent event IDs, actions, or evidence.
A visit to an upload or file-sharing page does not prove that a file was uploaded.
Explain why an activity sequence may warrant investigation.
Recommend human review instead of automatic punitive action.
An anomaly assessment is an investigative lead, not proof of misconduct.

The rule-based "supporting indicators" are hints computed by simple heuristics; they can be false positives. Weigh them against the role and history.

Risk rubric:
- low: the activity is explained by the role and the employee's usual behaviour; no indicators, or only weak ones.
- medium: an unusual combination or a moderate indicator that a reviewer should check, although legitimate explanations are plausible.
- high: a strong indicator that the role and history do not explain - for example sensitive-looking files downloaded or copied and then, shortly after, external file-sharing, personal e-mail or removable-media activity.
Behaviour that appears only rarely in the history is not automatically normal; routine means frequent.
Set is_anomaly to true when the activity warrants human review (medium or high).

Answer ONLY with a JSON object with these keys:
- is_anomaly (boolean)
- risk_level ("low", "medium" or "high"; must be "low" when is_anomaly is false, and "medium" or "high" when it is true)
- confidence (number between 0 and 1: your subjective estimate)
- reason (2-4 sentences explaining the assessment, referring to event IDs like #123)
- evidence_event_ids (array of integer event IDs copied from the supplied records that support the reason; may be empty when is_anomaly is false)
- recommended_action (one or two sentences recommending proportionate human review)"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_anomaly": {"type": "boolean"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "evidence_event_ids": {"type": "array", "items": {"type": "integer"}},
        "recommended_action": {"type": "string"},
    },
    "required": ["is_anomaly", "risk_level", "confidence", "reason", "evidence_event_ids", "recommended_action"],
}


class AnalysisError(RuntimeError):
    def __init__(self, message: str, code: str = "analysis_error"):
        super().__init__(message)
        self.code = code


class NothingToAnalyze(AnalysisError):
    def __init__(self, message: str = "No activity recorded for this employee yet"):
        super().__init__(message, "empty_activity")


def event_dict(a: ActivityLog) -> dict:
    return {"id": a.id, "timestamp": a.timestamp, "event_type": a.event_type, "domain": a.domain, "url": a.url,
            "filename": a.filename, "source": a.source, "safe_metadata": a.safe_metadata or {}}


# ----------------------------------------------------------------- baseline
def build_baseline(db: Session, employee_id: str) -> dict:
    """Compact statistical summary of the employee's historical (synthetic CERT-style) activity."""
    tz = settings.org_tz
    rows = db.execute(
        select(ActivityLog.event_type, ActivityLog.domain, ActivityLog.url, ActivityLog.timestamp,
               ActivityLog.safe_metadata)
        .where(ActivityLog.employee_id == employee_id, ActivityLog.source == SOURCE_HISTORICAL)
    ).all()
    if not rows:
        return {"has_history": False, "total_events": 0, "known_domains": [], "typical_hours_local": [9.0, 19.0],
                "avg_downloads_per_day": 0.0}
    types = Counter(r.event_type for r in rows)
    days = {r.timestamp.astimezone(tz).date() for r in rows}
    nav_domains = Counter(r.domain for r in rows if r.event_type == "navigation" and r.domain)
    cats = Counter(categorize(r.domain, r.url) for r in rows if r.event_type == "navigation")
    hours = sorted(r.timestamp.astimezone(tz).hour + r.timestamp.astimezone(tz).minute / 60 for r in rows
                   if r.event_type not in ("logoff",))
    p10, p90 = hours[int(len(hours) * 0.05)], hours[min(len(hours) - 1, int(len(hours) * 0.95))]
    ext_mail = sum(1 for r in rows if r.event_type == "email" and r.domain and not r.domain.endswith("corvane.example"))
    first = min(r.timestamp for r in rows)
    last = max(r.timestamp for r in rows)
    return {
        "has_history": True,
        "total_events": len(rows),
        "period": f"{first.astimezone(tz):%Y-%m-%d} to {last.astimezone(tz):%Y-%m-%d}",
        "active_days": len(days),
        "event_types": dict(types.most_common()),
        "avg_events_per_day": round(len(rows) / max(1, len(days)), 1),
        "avg_downloads_per_day": round(types.get("download", 0) / max(1, len(days)), 2),
        "top_domains": nav_domains.most_common(12),
        "known_domains": sorted({r.domain for r in rows if r.domain}),
        "navigation_categories": dict(cats.most_common(8)),
        "typical_hours_local": [round(p10, 1), round(p90, 1)],
        "removable_media_events": types.get("removable_media", 0),
        "external_emails": ext_mail,
    }


# ----------------------------------------------------------------- batch selection
def get_state(db: Session, employee_id: str) -> AnalysisState:
    st = db.get(AnalysisState, employee_id)
    if st is None:
        st = AnalysisState(employee_id=employee_id, last_analyzed_event_id=0)
        db.add(st)
        db.flush()
    return st


def unanalyzed_live_events(db: Session, employee_id: str, cursor: int, limit: int) -> list[ActivityLog]:
    return list(db.scalars(
        select(ActivityLog).where(ActivityLog.employee_id == employee_id, ActivityLog.source == SOURCE_LIVE,
                                  ActivityLog.id > cursor)
        .order_by(ActivityLog.id).limit(limit)))


def select_batch(db: Session, employee_id: str, mode: str) -> tuple[list[ActivityLog], list[ActivityLog]]:
    """Return (new_live_events, context_events). Context = earlier events that precede the batch."""
    st = get_state(db, employee_id)
    max_n = settings.max_recent_events
    new = unanalyzed_live_events(db, employee_id, st.last_analyzed_event_id, max_n)
    if not new and mode == "auto":
        return [], []
    # With new live events: up to 15 preceding records as context. Without (manual): the latest max_n records.
    n_context = max(0, min(15, max_n - len(new))) if new else max_n
    before_ts = new[0].timestamp if new else None
    q = select(ActivityLog).where(ActivityLog.employee_id == employee_id)
    if before_ts is not None:
        q = q.where(ActivityLog.timestamp <= before_ts, ActivityLog.id.not_in([e.id for e in new]))
    ctx = list(db.scalars(q.order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc()).limit(n_context)))
    ctx.reverse()
    return new, ctx


# ----------------------------------------------------------------- prompt
def _fmt_event(e: dict, tz) -> str:
    t = e["timestamp"].astimezone(tz)
    src = "LIVE" if e["source"] == SOURCE_LIVE else "HIST"
    path = ""
    if e.get("url"):
        rest = e["url"].split("://", 1)[-1]
        path = rest[len(e["domain"] or ""):] if e.get("domain") and rest.startswith(e["domain"]) else rest
        path = path[:70]
    m = e.get("safe_metadata") or {}
    extra = []
    for k in ("activity", "application", "device", "attachments", "recipients", "destination", "file_size_kb",
              "transition"):
        if k in m and m[k] not in (None, ""):
            extra.append(f"{k}={m[k]}")
    parts = [f"#{e['id']}", f"{t:%Y-%m-%d %a %H:%M}", src, e["event_type"], e.get("domain") or "-", path or "-"]
    if e.get("filename"):
        parts.append(f"file={e['filename'][-80:]}")
    parts.append(f"cat={e.get('category') or categorize(e.get('domain'), e.get('url'))}")
    if extra:
        parts.append(" ".join(extra))
    return " | ".join(parts)


def build_prompt(emp: Employee, baseline: dict, new: list[dict], ctx: list[dict], indicators: list[dict]) -> str:
    tz = settings.org_tz
    exp = sorted(expected_categories(emp.role, emp.department))
    lines = [
        "EMPLOYEE",
        f"id={emp.employee_id}; role={emp.role}; department={emp.department}",
        f"categories usually expected for this role: {', '.join(exp)}",
        "",
        "HISTORICAL BASELINE (fictional CERT-style synthetic history, summary only)",
    ]
    if baseline.get("has_history"):
        lines += [
            f"period {baseline['period']}, {baseline['active_days']} active days, "
            f"{baseline['avg_events_per_day']} events/day, {baseline['avg_downloads_per_day']} downloads/day",
            f"event types: {json.dumps(baseline['event_types'])}",
            f"usual hours (local): {baseline['typical_hours_local'][0]:.0f}:00-{baseline['typical_hours_local'][1]:.0f}:00",
            "top domains: " + ", ".join(f"{d} ({n})" for d, n in baseline["top_domains"]),
            f"navigation categories: {json.dumps(baseline['navigation_categories'])}",
            f"removable media events: {baseline['removable_media_events']}; external emails: {baseline['external_emails']}",
        ]
    else:
        lines.append("no historical activity on record (new employee) - judge against role expectations only")
    lines += ["", "Record format: #id | local time | HIST=historical/LIVE=collected by browser extension | type | "
                  "domain | path | details"]
    if ctx:
        lines += ["", f"PRECEDING ACTIVITY (context, {len(ctx)} records)"] + [_fmt_event(e, tz) for e in ctx]
    if new:
        lines += ["", f"NEW LIVE ACTIVITY TO ASSESS ({len(new)} records)"] + [_fmt_event(e, tz) for e in new]
    else:
        lines += ["", "No new live activity: assess the most recent activity above."]
    lines += ["", "SUPPORTING INDICATORS (heuristic hints, may be benign)"]
    if indicators:
        lines += [f"- [{i['strength']}] {i['code']}: {i['detail']} (events {', '.join('#' + str(x) for x in i['event_ids'][:12])})"
                  for i in indicators]
    else:
        lines.append("- none triggered")
    lines += ["", "Assess whether this activity warrants a security investigation, applying the risk rubric. "
                  "Return the JSON object only."]
    return "\n".join(lines)


# ----------------------------------------------------------------- validation
def validate_response(raw: dict, allowed_ids: set[int]) -> tuple[LLMAssessment, list[str]]:
    """Schema + consistency validation, then evidence verification against supplied IDs."""
    notes: list[str] = []
    data = dict(raw)
    # Accept ids given as "#123" / "123" strings but nothing else.
    ev = data.get("evidence_event_ids", [])
    if isinstance(ev, list):
        fixed = []
        for x in ev:
            if isinstance(x, str) and x.strip().lstrip("#").isdigit():
                fixed.append(int(x.strip().lstrip("#")))
            else:
                fixed.append(x)
        data["evidence_event_ids"] = fixed
    try:
        a = LLMAssessment.model_validate(data)
    except ValidationError as exc:
        msgs = "; ".join(f"{'.'.join(str(p) for p in er['loc']) or 'response'}: {er['msg']}" for er in exc.errors())
        raise AnalysisError(f"Model response failed validation: {msgs}", "invalid_response") from exc
    ids = list(dict.fromkeys(a.evidence_event_ids))
    invalid = [i for i in ids if i not in allowed_ids]
    if invalid:
        notes.append(f"removed evidence IDs not present in the supplied records: {invalid}")
        ids = [i for i in ids if i in allowed_ids]
    if a.is_anomaly and not ids:
        raise AnalysisError("Model flagged an anomaly without any valid supporting event IDs", "invalid_evidence")
    a.evidence_event_ids = ids
    return a, notes


# ----------------------------------------------------------------- main entry
def analyze_employee(db: Session, employee_id: str, mode: str = "manual", force: bool = False) -> dict:
    """Run one analysis. Returns {"status": "saved"|"skipped"|"duplicate", "anomaly_id": ...}.
    Raises AnalysisError / OllamaError on failure (caller records the failure; cursor is untouched)."""
    emp = db.scalar(select(Employee).where(Employee.employee_id == employee_id))
    if emp is None:
        raise AnalysisError(f"Unknown employee {employee_id}", "unknown_employee")
    new_rows, ctx_rows = select_batch(db, employee_id, mode)
    if not new_rows and not ctx_rows:
        if mode == "auto":
            return {"status": "skipped", "reason": "no new live activity"}
        raise NothingToAnalyze()

    analyzed_ids = sorted(e.id for e in ctx_rows + new_rows)
    if not new_rows and not force:
        # Duplicate-analysis prevention: same window already assessed and nothing new arrived.
        prev = db.scalar(select(Anomaly).where(Anomaly.employee_id == employee_id)
                         .order_by(Anomaly.created_at.desc()).limit(1))
        if prev is not None and sorted(prev.analyzed_event_ids or []) == analyzed_ids:
            return {"status": "duplicate", "anomaly_id": prev.id,
                    "reason": "This activity window was already analyzed and no new activity has arrived."}

    baseline = build_baseline(db, employee_id)
    new = [event_dict(e) for e in new_rows]
    ctx = [event_dict(e) for e in ctx_rows]
    window = sorted(ctx + new, key=lambda e: (e["timestamp"], e["id"]))
    indicators = compute_indicators(window, baseline, emp.role, emp.department, settings.org_tz)
    prompt = build_prompt(emp, baseline, new, ctx, indicators)
    allowed = set(analyzed_ids)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    started = datetime.now(timezone.utc)
    last_err: Exception | None = None
    assessment = None
    notes: list[str] = []
    raw_text = ""
    total_ms = 0
    for attempt in range(2):
        raw_text, stats = ollama_client.chat(messages, RESPONSE_SCHEMA)
        total_ms += stats["elapsed_ms"]
        try:
            assessment, notes = validate_response(ollama_client.parse_json_object(raw_text), allowed)
            if attempt:
                notes.append("accepted on second attempt after a rejected first response")
            break
        except (AnalysisError, ollama_client.OllamaBadResponse) as exc:
            last_err = exc
            messages = messages + [
                {"role": "assistant", "content": raw_text[:2000]},
                {"role": "user", "content": f"Your answer was rejected: {exc}. Reply again with ONLY the JSON "
                                            "object, following every rule. Use only event IDs from the records."}]
    if assessment is None:
        raise AnalysisError(f"Model response rejected twice: {last_err}", "invalid_response")

    st = get_state(db, employee_id)
    anomaly = Anomaly(
        employee_id=employee_id,
        is_anomaly=assessment.is_anomaly,
        risk_level=assessment.risk_level,
        confidence=round(float(assessment.confidence), 3),
        reason=assessment.reason.strip(),
        evidence_event_ids=assessment.evidence_event_ids,
        recommended_action=assessment.recommended_action.strip(),
        analysis_source="auto_batch" if mode == "auto" else "manual",
        batch_id=str(uuid.uuid4()),
        batch_start_event_id=min(analyzed_ids),
        batch_end_event_id=max(analyzed_ids),
        analyzed_event_ids=analyzed_ids,
        live_events_in_batch=len(new),
        indicators=indicators,
        model_name=settings.ollama_model,
        raw_response=raw_text[:8000],
        validation_notes=notes,
        duration_ms=total_ms,
        created_at=datetime.now(timezone.utc),
    )
    db.add(anomaly)
    if new_rows:
        st.last_analyzed_event_id = max(st.last_analyzed_event_id, max(e.id for e in new_rows))
    st.last_success_at = datetime.now(timezone.utc)
    st.last_attempt_at = started
    st.last_error = None
    st.consecutive_failures = 0
    st.next_retry_at = None
    db.commit()
    return {"status": "saved", "anomaly_id": anomaly.id, "risk_level": anomaly.risk_level,
            "is_anomaly": anomaly.is_anomaly, "events_analyzed": len(analyzed_ids), "live_events": len(new),
            "duration_ms": total_ms}


def pending_live_counts(db: Session) -> list[dict]:
    """Employees with live events not yet covered by a successful analysis."""
    st = AnalysisState
    q = (select(ActivityLog.employee_id, func.count(ActivityLog.id), func.max(ActivityLog.received_at),
                func.max(st.next_retry_at), func.max(st.last_error))
         .outerjoin(st, st.employee_id == ActivityLog.employee_id)
         .where(ActivityLog.source == SOURCE_LIVE,
                ActivityLog.id > func.coalesce(st.last_analyzed_event_id, 0))
         .group_by(ActivityLog.employee_id))
    return [{"employee_id": r[0], "unanalyzed_live_events": r[1], "last_received_at": r[2],
             "next_retry_at": r[3], "last_error": r[4]} for r in db.execute(q).all()]
