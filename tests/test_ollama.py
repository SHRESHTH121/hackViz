"""Real inference tests against the local Ollama server (qwen2.5:3b). Marked `ollama`.

These tests do NOT mock the model. They post real-shaped live events through the API,
run the actual analysis pipeline and check the stored, validated result."""
import dataclasses
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.services import ollama_client

pytestmark = pytest.mark.ollama
RESULTS_LOG = []


def _now(offset=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat()


def _post(client, emp, event_type, url, filename=None, offset=0):
    r = client.post("/api/activity", json={"employee_id": emp, "event_type": event_type, "url": url, "filename": filename,
                                           "timestamp": _now(offset), "client_event_id": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def ollama_ready():
    c = ollama_client.check()
    if not c["reachable"]:
        pytest.skip(f"Ollama not reachable: {c['error']}")
    return c


def test_ollama_connection_and_model(ollama_ready):
    assert ollama_ready["reachable"]
    assert ollama_ready["model_available"], f"qwen2.5:3b missing; installed: {ollama_ready['models']}"


def test_structured_json_from_model(ollama_ready):
    from app.services.analyzer import RESPONSE_SCHEMA

    content, stats = ollama_client.chat(
        [{"role": "system", "content": "Reply with JSON only."},
         {"role": "user", "content": "Activity: #1 navigation github.com. Employee is a software developer. "
                                     "Assess insider risk."}], RESPONSE_SCHEMA, timeout=300)
    obj = ollama_client.parse_json_object(content)
    assert set(RESPONSE_SCHEMA["required"]) <= set(obj)
    assert stats["elapsed_ms"] > 0


def _analyze(db, emp, mode="manual", force=False):
    from app.services.analyzer import analyze_employee
    t0 = time.time()
    res = analyze_employee(db, emp, mode, force)
    res["wall_s"] = round(time.time() - t0, 1)
    return res


def _check_saved(db, res, live_ids):
    from app.models import ActivityLog, Anomaly, AnalysisState
    a = db.get(Anomaly, res["anomaly_id"])
    assert a is not None and a.model_name == "qwen2.5:3b"
    assert a.risk_level in ("low", "medium", "high") and 0 <= a.confidence <= 1
    assert (not a.is_anomaly) == (a.risk_level == "low")
    # every evidence ID was part of the supplied records and exists in PostgreSQL
    assert set(a.evidence_event_ids) <= set(a.analyzed_event_ids)
    if a.evidence_event_ids:
        n = db.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.id.in_(a.evidence_event_ids)))
        assert n == len(a.evidence_event_ids)
    assert set(live_ids) <= set(a.analyzed_event_ids)
    st = db.get(AnalysisState, a.employee_id)
    assert st.last_analyzed_event_id >= max(live_ids), "cursor must advance past analyzed live events"
    RESULTS_LOG.append({"employee": a.employee_id, "is_anomaly": a.is_anomaly, "risk": a.risk_level,
                        "confidence": a.confidence, "evidence": a.evidence_event_ids, "reason": a.reason,
                        "indicators": [i["code"] for i in a.indicators], "seconds": res["wall_s"]})
    return a


def test_live_batch_analysis_finance_exfil_like_sequence(client, db, ollama_ready):
    """Finance analyst: sensitive-looking downloads followed by external file-sharing navigation."""
    emp = "EMP004"
    ids = [
        _post(client, emp, "navigation", "https://finance.corvane.internal/reports/quarterly", offset=-300),
        _post(client, emp, "download", "https://finance.corvane.internal/export/payroll_master.xlsx", "payroll_master_FY26.xlsx", -280),
        _post(client, emp, "download", "https://finance.corvane.internal/export/vendor_bank_accounts.csv", "vendor_bank_accounts.csv", -270),
        _post(client, emp, "download", "https://finance.corvane.internal/export/salary_bands.xlsx", "salary_bands_all_staff.xlsx", -260),
        _post(client, emp, "navigation", "https://wetransfer.com/", offset=-200),
        _post(client, emp, "navigation", "https://wetransfer.com/upload", offset=-190),
    ]
    res = _analyze(db, emp, "auto")
    assert res["status"] == "saved", res
    a = _check_saved(db, res, ids)
    assert any(i["code"] == "sensitive_transfer_sequence" for i in a.indicators)
    # auto mode with nothing new -> skipped, no duplicate analysis
    assert _analyze(db, emp, "auto")["status"] == "skipped"


def test_role_aware_developer_normal_browsing(client, db, ollama_ready):
    """Developer doing ordinary development browsing (same volume of events)."""
    emp = "EMP002"
    ids = [_post(client, emp, "navigation", u, offset=-100 + i) for i, u in enumerate([
        "https://github.com/corvane/api-gateway", "https://stackoverflow.com/questions/123",
        "https://docs.python.org/3/library/asyncio.html", "https://fastapi.tiangolo.com/tutorial/",
        "https://github.com/corvane/api-gateway/pulls", "https://pypi.org/project/httpx/"])]
    res = _analyze(db, emp, "auto")
    assert res["status"] == "saved", res
    _check_saved(db, res, ids)


def test_manual_duplicate_prevention(client, db, ollama_ready):
    from app.models import Anomaly
    emp = "EMP009"
    first = _analyze(db, emp, "manual")  # no live events -> analyzes most recent historical window
    assert first["status"] == "saved"
    a = db.get(Anomaly, first["anomaly_id"])
    assert a.live_events_in_batch == 0 and len(a.analyzed_event_ids) >= 20
    second = _analyze(db, emp, "manual")
    assert second["status"] == "duplicate" and second["anomaly_id"] == first["anomaly_id"]


def test_empty_activity_handling(client, db):
    from app.services.analyzer import NothingToAnalyze, analyze_employee
    client.post("/api/employees", json={"employee_id": "EMPTY02", "name": "Fresh Hire", "role": "Sales Executive", "department": "Sales"})
    with pytest.raises(NothingToAnalyze):
        analyze_employee(db, "EMPTY02", "manual")
    assert analyze_employee(db, "EMPTY02", "auto")["status"] == "skipped"


def test_timeout_does_not_skip_events(client, db, monkeypatch, ollama_ready):
    from app.models import Anomaly, AnalysisState
    from app.services.analyzer import analyze_employee
    emp = "EMP006"
    ids = [_post(client, emp, "navigation", "https://miro.com/app/board/x", offset=-10)]
    before = db.scalar(select(func.count(Anomaly.id)).where(Anomaly.employee_id == emp))
    monkeypatch.setattr(ollama_client, "settings", dataclasses.replace(ollama_client.settings, ollama_timeout=0.001))
    with pytest.raises(ollama_client.OllamaTimeout):
        analyze_employee(db, emp, "auto")
    db.rollback()
    st = db.get(AnalysisState, emp)
    assert st is None or st.last_analyzed_event_id < ids[0], "cursor must not advance on failure"
    assert db.scalar(select(func.count(Anomaly.id)).where(Anomaly.employee_id == emp)) == before


def test_missing_model_and_unreachable(monkeypatch):
    with pytest.raises(ollama_client.ModelMissing):
        ollama_client.chat([{"role": "user", "content": "hi"}], model="does-not-exist:1b", timeout=30)
    monkeypatch.setattr(ollama_client, "settings", dataclasses.replace(ollama_client.settings, ollama_url="http://127.0.0.1:9"))
    with pytest.raises(ollama_client.OllamaUnavailable):
        ollama_client.chat([{"role": "user", "content": "hi"}], timeout=5)
    assert ollama_client.check()["reachable"] is False


def test_api_analyze_now_endpoint(client, ollama_ready):
    """Full API path: Analyze Now -> background worker -> saved alert retrievable with evidence."""
    _post(client, "EMP010", "navigation", "https://arxiv.org/abs/2410.00001", offset=-20)
    r = client.post("/api/analyze/EMP010", params={"wait": "true", "timeout": 600})
    assert r.status_code == 200, r.text
    job = r.json()["job"]
    assert job["state"] == "done", job
    aid = job["result"]["anomaly_id"]
    detail = client.get(f"/api/anomalies/{aid}").json()
    assert detail["employee_name"] == "Aditya Nair" and detail["model_name"] == "qwen2.5:3b"
    assert {e["id"] for e in detail["evidence_events"]} == set(detail["evidence_event_ids"])
    for eid in detail["evidence_event_ids"]:
        assert client.get(f"/api/activity/{eid}").status_code == 200
    RESULTS_LOG.append({"employee": "EMP010", "api_alert": aid, "risk": detail["risk_level"], "reason": detail["reason"]})


def teardown_module(_):
    if RESULTS_LOG:
        print("\n=== Real Ollama assessments produced during tests ===")
        print(json.dumps(RESULTS_LOG, indent=2, default=str))
