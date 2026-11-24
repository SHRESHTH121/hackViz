"""Validation of model output, evidence checking and rule-based indicators (no LLM calls)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.services import ollama_client
from app.services.analyzer import AnalysisError, build_prompt, validate_response
from app.services.indicators import compute_indicators

ALLOWED = {101, 102, 103, 104}
GOOD = {"is_anomaly": True, "risk_level": "high", "confidence": 0.8, "reason": "Sensitive download #102 then file sharing #103.",
        "evidence_event_ids": [102, 103], "recommended_action": "Review with the employee's manager."}


def test_valid_response_accepted():
    a, notes = validate_response(GOOD, ALLOWED)
    assert a.risk_level == "high" and a.evidence_event_ids == [102, 103] and notes == []


def test_string_ids_and_case_normalised():
    a, _ = validate_response({**GOOD, "risk_level": "HIGH", "evidence_event_ids": ["#102", "103"]}, ALLOWED)
    assert a.risk_level == "high" and a.evidence_event_ids == [102, 103]


@pytest.mark.parametrize("patch", [
    {"risk_level": "critical"},
    {"confidence": 1.7},
    {"confidence": -0.1},
    {"is_anomaly": False, "risk_level": "high"},      # no anomaly must be low
    {"is_anomaly": True, "risk_level": "low"},        # anomaly must be medium/high
    {"reason": ""},
    {"recommended_action": None},
])
def test_invalid_responses_rejected(patch):
    with pytest.raises(AnalysisError):
        validate_response({**GOOD, **patch}, ALLOWED)


def test_missing_field_rejected():
    bad = dict(GOOD)
    bad.pop("confidence")
    with pytest.raises(AnalysisError):
        validate_response(bad, ALLOWED)


def test_invented_evidence_ids_removed_and_noted():
    a, notes = validate_response({**GOOD, "evidence_event_ids": [102, 999, 5]}, ALLOWED)
    assert a.evidence_event_ids == [102]
    assert notes and "999" in notes[0]


def test_anomaly_with_only_invented_ids_rejected():
    with pytest.raises(AnalysisError):
        validate_response({**GOOD, "evidence_event_ids": [999]}, ALLOWED)


def test_no_anomaly_without_evidence_ok():
    a, _ = validate_response({**GOOD, "is_anomaly": False, "risk_level": "low", "evidence_event_ids": []}, ALLOWED)
    assert not a.is_anomaly


def test_json_parsing():
    assert ollama_client.parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ollama_client.OllamaBadResponse):
        ollama_client.parse_json_object("not json at all")
    with pytest.raises(ollama_client.OllamaBadResponse):
        ollama_client.parse_json_object("[1, 2]")


def _ev(i, minutes, et, domain=None, url=None, filename=None, source="chrome_extension", meta=None):
    t0 = datetime(2026, 11, 24, 5, 0, tzinfo=timezone.utc)
    return {"id": i, "timestamp": t0 + timedelta(minutes=minutes), "event_type": et, "domain": domain, "url": url,
            "filename": filename, "source": source, "safe_metadata": meta or {}}


BASE = {"has_history": True, "known_domains": ["github.com", "stackoverflow.com"], "typical_hours_local": [9.0, 19.0],
        "avg_downloads_per_day": 0.5}


def test_indicator_sensitive_download_then_file_sharing():
    evs = [_ev(1, 0, "navigation", "finance.corvane.internal", "https://finance.corvane.internal/x"),
           _ev(2, 2, "download", "finance.corvane.internal", "https://finance.corvane.internal/e", "payroll_master.xlsx"),
           _ev(3, 9, "navigation", "wetransfer.com", "https://wetransfer.com/upload")]
    ind = compute_indicators(evs, BASE, "Finance Analyst", "Finance", settings.org_tz)
    seq = [i for i in ind if i["code"] == "sensitive_transfer_sequence"]
    assert seq and seq[0]["strength"] == "strong" and {2, 3} <= set(seq[0]["event_ids"])
    assert "does NOT prove" in seq[0]["detail"]


def test_single_unfamiliar_site_is_not_strong():
    evs = [_ev(1, 0, "navigation", "github.com", "https://github.com/"),
           _ev(2, 3, "navigation", "some-new-blog.example", "https://some-new-blog.example/post")]
    ind = compute_indicators(evs, BASE, "Software Developer (SDE1)", "Engineering", settings.org_tz)
    assert not any(i["strength"] in ("strong", "moderate") for i in ind), ind


def test_role_awareness_of_sensitive_systems():
    evs = [_ev(1, 0, "navigation", "admin.corvane.internal", "https://admin.corvane.internal/users"),
           _ev(2, 5, "navigation", "admin.corvane.internal", "https://admin.corvane.internal/groups")]
    sysadmin = compute_indicators(evs, BASE, "System Administrator", "IT", settings.org_tz)
    intern = compute_indicators(evs, BASE, "Management Intern", "Management", settings.org_tz)
    assert not any(i["code"] == "sensitive_system_outside_role" for i in sysadmin)
    assert any(i["code"] == "sensitive_system_outside_role" for i in intern)


def test_download_burst_and_off_hours_alone():
    evs = [_ev(i, i, "download", "example.org", f"https://example.org/{i}", f"f{i}.zip") for i in range(1, 5)]
    ind = compute_indicators(evs, BASE, "Data Analyst", "Analytics", settings.org_tz)
    assert any(i["code"] == "download_burst" for i in ind)
    # off-hours navigation alone produces no indicator
    late = [_ev(9, 18 * 60, "navigation", "github.com", "https://github.com/")]
    assert compute_indicators(late, BASE, "Software Developer (SDE1)", "Engineering", settings.org_tz) == []


def test_prompt_is_compact_and_labelled():
    class E:  # minimal employee stub
        employee_id, role, department = "EMP002", "Software Developer (SDE1)", "Engineering"
    new = [_ev(i, i, "navigation", "github.com", "https://github.com/corvane/repo") for i in range(1, 36)]
    p = build_prompt(E, {"has_history": False}, new, [], [])
    assert "NEW LIVE ACTIVITY TO ASSESS (35 records)" in p and "role=Software Developer (SDE1)" in p
    assert "#35" in p and len(p) < 9000
